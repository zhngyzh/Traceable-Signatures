"""
权限系统测试脚本
演示：
1. 用户注册和登录
2. 管理员创建群组
3. 管理员添加成员并分发密钥
4. 用户签名（需要密钥）
5. 管理员追踪签名
"""

import requests
import json

BASE_URL = 'http://localhost:5000/api'

# 测试用例
def test_auth_system():
    print("=" * 50)
    print("权限系统测试")
    print("=" * 50)
    
    # 1. 注册管理员账户
    print("\n[1] 注册管理员账户...")
    admin_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    resp = requests.post(f'{BASE_URL}/auth/register', json=admin_data)
    admin_info = resp.json()
    print(f"响应: {json.dumps(admin_info, ensure_ascii=False, indent=2)}")
    
    # 获取管理员的token
    admin_id = admin_info['user_id']
    admin_token = admin_info['token']
    
    # 2. 注册普通用户账户
    print("\n[2] 注册普通用户账户...")
    user_data = {
        'username': 'user1',
        'password': 'user123'
    }
    resp = requests.post(f'{BASE_URL}/auth/register', json=user_data)
    user_info = resp.json()
    print(f"响应: {json.dumps(user_info, ensure_ascii=False, indent=2)}")
    
    user_id = user_info['user_id']
    user_token = user_info['token']
    
    # 3. 普通用户尝试创建群组（应该失败）
    print("\n[3] 普通用户尝试创建群组（应该失败）...")
    headers = {
        'X-User-ID': str(user_id),
        'X-Token': user_token
    }
    group_data = {'name': '测试群组'}
    resp = requests.post(f'{BASE_URL}/groups', json=group_data, headers=headers)
    print(f"状态码: {resp.status_code}")
    print(f"响应: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
    
    # 4. 管理员创建群组
    print("\n[4] 管理员创建群组...")
    admin_headers = {
        'X-User-ID': str(admin_id),
        'X-Token': admin_token
    }
    group_data = {'name': '保密文件群组'}
    resp = requests.post(f'{BASE_URL}/groups', json=group_data, headers=admin_headers)
    group_info = resp.json()
    print(f"响应: {json.dumps(group_info, ensure_ascii=False, indent=2)}")
    group_id = group_info['group_id']
    
    # 5. 管理员为用户添加成员身份并分发密钥
    print("\n[5] 管理员为用户添加成员身份并分发密钥...")
    member_data = {
        'group_id': group_id,
        'name': 'user1',
        'user_id': user_id
    }
    resp = requests.post(f'{BASE_URL}/members', json=member_data, headers=admin_headers)
    member_info = resp.json()
    print(f"响应: {json.dumps(member_info, ensure_ascii=False, indent=2)}")
    member_id = member_info['member_id']
    
    # 6. 用户签名（需要密钥）
    print("\n[6] 用户签名（有密钥，应该成功）...")
    sig_data = {
        'group_id': group_id,
        'member_id': member_id,
        'message': '这是一个保密文件'
    }
    resp = requests.post(f'{BASE_URL}/signatures', json=sig_data, headers=headers)
    sig_info = resp.json()
    print(f"状态码: {resp.status_code}")
    print(f"响应: {json.dumps(sig_info, ensure_ascii=False, indent=2)}")
    
    if sig_info.get('success'):
        sig_id = sig_info['signature_id']
        
        # 7. 管理员验证签名
        print("\n[7] 管理员验证签名...")
        resp = requests.post(f'{BASE_URL}/signatures/{sig_id}/verify', json={}, headers=admin_headers)
        verify_info = resp.json()
        print(f"响应: {json.dumps(verify_info, ensure_ascii=False, indent=2)}")
        
        # 8. 管理员打开签名（追踪签名者）
        print("\n[8] 管理员打开签名（追踪签名者）...")
        resp = requests.post(f'{BASE_URL}/signatures/{sig_id}/open', json={}, headers=admin_headers)
        open_info = resp.json()
        print(f"响应: {json.dumps(open_info, ensure_ascii=False, indent=2)}")
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)

if __name__ == '__main__':
    test_auth_system()
