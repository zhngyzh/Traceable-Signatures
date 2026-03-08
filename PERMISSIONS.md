# 权限系统使用指南

## 概述

该系统实现了一个简单的权限管理系统，分为两种角色：

- **管理员 (Admin)**：可以初始化系统、创建群组、添加成员、追踪签名
- **普通用户 (User)**：只能在获得密钥后生成签名

## 核心特性

### 1. 用户认证 (`/api/auth`)

#### 注册
```bash
POST /api/auth/register
Content-Type: application/json

{
    "username": "user1",
    "password": "password123"
}

响应:
{
    "success": true,
    "user_id": 1,
    "token": "token_string",
    "role": "user"  // 默认为普通用户
}
```

#### 登录
```bash
POST /api/auth/login
Content-Type: application/json

{
    "username": "user1",
    "password": "password123"
}

响应:
{
    "success": true,
    "user_id": 1,
    "token": "token_string",
    "role": "user"
}
```

### 2. 权限装饰器

#### `@require_auth`
任何已登录用户都可以访问

#### `@require_admin`
只有管理员可以访问

## 管理员角色设置

初次使用时，需要将某个用户升级为管理员：

```sql
UPDATE users SET role='admin' WHERE id=1;
```

## 工作流程

1. 用户注册/登录
2. 管理员创建群组
3. 管理员为用户添加成员并分发密钥
4. 用户使用密钥签名
5. 管理员验证和追踪签名
