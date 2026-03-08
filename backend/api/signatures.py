"""
签名管理 API
"""
from flask import Blueprint, jsonify, request
from utils.database import get_db
from utils.key_manager import KeyManager
from utils.auth import require_admin, require_auth
from pygroupsig import groupsig, constants, crl
import json

bp = Blueprint('signatures', __name__, url_prefix='/api/signatures')
key_manager = KeyManager()

UINT_MAX = 2**32 - 1

@bp.route('', methods=['GET'])
def list_signatures():
    """获取签名列表"""
    group_id = request.args.get('group_id', type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    if group_id:
        cursor.execute(
            '''SELECT s.*, m.name as member_name, g.name as group_name
               FROM signatures s
               LEFT JOIN members m ON s.member_id = m.id
               LEFT JOIN groups g ON s.group_id = g.id
               WHERE s.group_id=?
               ORDER BY s.created_at DESC''',
            (group_id,)
        )
    else:
        cursor.execute(
            '''SELECT s.*, m.name as member_name, g.name as group_name
               FROM signatures s
               LEFT JOIN members m ON s.member_id = m.id
               LEFT JOIN groups g ON s.group_id = g.id
               ORDER BY s.created_at DESC'''
        )
    
    signatures_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({'signatures': signatures_list})

@bp.route('', methods=['POST'])
@require_auth
def create_signature():
    """创建签名（需要密钥验证）"""
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        member_id = data.get('member_id')
        message_text = data.get('message', '')
        
        if not group_id or not member_id or not message_text:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 验证成员是否拥有密钥（通过密钥文件存在）
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT memkey_path FROM members WHERE id=? AND group_id=?', 
                      (member_id, group_id))
        member_row = cursor.fetchone()
        conn.close()
        
        if not member_row or not member_row['memkey_path']:
            return jsonify({
                'success': False,
                'message': '成员密钥不存在，无法签名'
            }), 403
        
        # 初始化方案
        key_manager.init_scheme()
        
        # 加载密钥
        grpkey_obj, _, _ = key_manager.load_group_keys(group_id)
        memkey_obj = key_manager.load_member_key(group_id, member_id)
        
        # 签名
        sig_obj = groupsig.sign(message_text, memkey_obj, grpkey_obj, UINT_MAX)
        
        # 保存签名
        sig_data = key_manager.save_signature(sig_obj, message_text)
        
        # 保存到数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO signatures (group_id, member_id, message, signature_data)
               VALUES (?, ?, ?, ?)''',
            (group_id, member_id, message_text, sig_data)
        )
        sig_id = cursor.lastrowid
        
        # 记录审计日志
        user_id = request.headers.get('X-User-ID')
        cursor.execute(
            '''INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, 'create_signature', 'signatures', sig_id, f'用户 {member_id} 签名')
        )
        
        conn.commit()
        conn.close()
        
        # 清理
        key_manager.clear_scheme()
        
        return jsonify({
            'success': True,
            'message': '签名创建成功',
            'signature_id': sig_id
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'创建签名失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@bp.route('/<int:sig_id>/verify', methods=['POST'])
def verify_signature(sig_id):
    """验证签名"""
    try:
        # 初始化方案
        key_manager.init_scheme()
        
        # 从数据库获取签名
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM signatures WHERE id=?', (sig_id,))
        sig_record = cursor.fetchone()
        conn.close()
        
        if not sig_record:
            return jsonify({
                'success': False,
                'message': '签名不存在'
            }), 404
        
        # 加载密钥和签名
        group_id = sig_record['group_id']
        grpkey_obj, _, _ = key_manager.load_group_keys(group_id)
        sig_obj = key_manager.load_signature(sig_record['signature_data'])
        message_text = sig_record['message']
        
        # 验证
        is_valid = groupsig.verify(sig_obj, message_text, grpkey_obj)
        
        # 更新数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE signatures SET verified=? WHERE id=?',
            (1 if is_valid else 0, sig_id)
        )
        
        # 记录审计日志
        user_id = request.headers.get('X-User-ID')
        cursor.execute(
            '''INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id, 'verify_signature', 'signatures', sig_id, f'验证结果: {is_valid}')
        )
        
        conn.commit()
        conn.close()
        
        # 清理
        key_manager.clear_scheme()
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': '签名验证成功' if is_valid else '签名验证失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'验证签名失败: {str(e)}'
        }), 500

@bp.route('/<int:sig_id>/open', methods=['POST'])
@require_admin
def open_signature(sig_id):
    """打开签名（追踪签名者，仅管理员）"""
    try:
        # 初始化方案
        key_manager.init_scheme()
        
        # 从数据库获取签名
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM signatures WHERE id=?', (sig_id,))
        sig_record = cursor.fetchone()
        conn.close()
        
        if not sig_record:
            return jsonify({
                'success': False,
                'message': '签名不存在'
            }), 404
        
        # 加载密钥和签名
        group_id = sig_record['group_id']
        grpkey_obj, mgrkey_obj, gml_obj = key_manager.load_group_keys(group_id)
        sig_obj = key_manager.load_signature(sig_record['signature_data'])
        
        # 初始化 CRL
        crl_obj = crl.crl_init(constants.KTY04_CODE)
        
        # 打开签名
        gsopen = groupsig.open(sig_obj, mgrkey_obj, grpkey_obj, gml=gml_obj)
        signer_index = gsopen.get('index')
        
        # 更新数据库
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE signatures SET opened=?, signer_index=? WHERE id=?',
            (1, signer_index, sig_id)
        )
        
        # 记录审计日志
        admin_id = request.headers.get('X-User-ID')
        cursor.execute(
            '''INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
               VALUES (?, ?, ?, ?, ?)''',
            (admin_id, 'open_signature', 'signatures', sig_id, f'追踪签名者，索引: {signer_index}')
        )
        
        conn.commit()
        conn.close()
        
        # 清理
        key_manager.clear_scheme()
        
        return jsonify({
            'success': True,
            'message': '签名打开成功',
            'signer_index': signer_index
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'打开签名失败: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500
