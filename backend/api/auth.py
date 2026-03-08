"""
用户认证 API
"""
from flask import Blueprint, jsonify, request
from utils.database import get_db
import hashlib
import secrets

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def hash_password(password):
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    """生成认证令牌"""
    return secrets.token_urlsafe(32)

@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400
        
        # 检查用户是否已存在
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'message': '用户已存在'
            }), 400
        
        # 创建用户（默认为普通用户）
        hashed_password = hash_password(password)
        token = generate_token()
        
        cursor.execute(
            'INSERT INTO users (username, password, role, token) VALUES (?, ?, ?, ?)',
            (username, hashed_password, 'user', token)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user_id': user_id,
            'token': token,
            'role': 'user'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'注册失败: {str(e)}'
        }), 500

@bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': '用户名和密码不能为空'
            }), 400
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        
        if not user or user['password'] != hash_password(password):
            conn.close()
            return jsonify({
                'success': False,
                'message': '用户名或密码错误'
            }), 401
        
        # 生成新的令牌
        token = generate_token()
        cursor.execute('UPDATE users SET token=? WHERE id=?', (token, user['id']))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user_id': user['id'],
            'token': token,
            'role': user['role'],
            'username': user['username']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'登录失败: {str(e)}'
        }), 500

@bp.route('/profile', methods=['GET'])
def get_profile():
    """获取当前用户信息"""
    try:
        user_id = request.headers.get('X-User-ID')
        token = request.headers.get('X-Token')
        
        if not user_id or not token:
            return jsonify({
                'success': False,
                'message': '未授权'
            }), 401
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id=? AND token=?', (user_id, token))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({
                'success': False,
                'message': '用户不存在或令牌无效'
            }), 401
        
        user_dict = dict(user)
        del user_dict['password']  # 不返回密码
        
        return jsonify({
            'success': True,
            'user': user_dict
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取用户信息失败: {str(e)}'
        }), 500
