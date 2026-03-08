# 快速参考指南

## 文件变更清单

### 新建文件
1. **backend/utils/auth.py** - 认证和权限装饰器
   - @require_auth: 要求用户已登录
   - @require_admin: 要求用户是管理员
   
2. **backend/api/auth.py** - 认证API端点
   - POST /api/auth/register - 注册
   - POST /api/auth/login - 登录
   - GET /api/auth/profile - 获取用户信息

3. **PERMISSIONS.md** - 权限系统文档
4. **test_auth.py** - 测试脚本
5. **IMPLEMENTATION_SUMMARY.md** - 实现总结

### 修改的文件
1. **backend/utils/database.py**
   - ✓ 新增 users 表
   - ✓ 新增 audit_logs 表
   - ✓ members 表添加 user_id 字段

2. **backend/api/groups.py**
   - ✓ create_group() 添加 @require_admin
   - ✓ 记录审计日志

3. **backend/api/members.py**
   - ✓ add_member() 添加 @require_admin
   - ✓ 实现密钥分发
   - ✓ 记录审计日志

4. **backend/api/signatures.py**
   - ✓ create_signature() 添加认证检查
   - ✓ 添加密钥存在性验证
   - ✓ open_signature() 添加 @require_admin
   - ✓ 记录审计日志

5. **backend/app.py**
   - ✓ 导入 auth 模块
   - ✓ 注册 auth 蓝图

## 用户角色

### 管理员 (admin)
```
可执行操作：
- 创建群组
- 添加成员并分发密钥
- 验证签名
- 打开（追踪）签名
- 查看审计日志
```

### 普通用户 (user)
```
可执行操作：
- 登录/注册
- 查看群组和签名列表
- 生成签名（需要密钥）
- 查看自己的用户信息
```

## API 调用示例

### 1. 注册用户
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"pass123"}'
```

### 2. 创建群组（需要管理员权限）
```bash
curl -X POST http://localhost:5000/api/groups \
  -H "X-User-ID: 1" \
  -H "X-Token: your_token" \
  -H "Content-Type: application/json" \
  -d '{"name":"保密群组"}'
```

### 3. 添加成员（需要管理员权限）
```bash
curl -X POST http://localhost:5000/api/members \
  -H "X-User-ID: 1" \
  -H "X-Token: your_token" \
  -H "Content-Type: application/json" \
  -d '{"group_id":1,"name":"成员1","user_id":2}'
```

### 4. 签名（需要用户登录和密钥）
```bash
curl -X POST http://localhost:5000/api/signatures \
  -H "X-User-ID: 2" \
  -H "X-Token: user_token" \
  -H "Content-Type: application/json" \
  -d '{"group_id":1,"member_id":1,"message":"文件内容"}'
```

### 5. 追踪签名（需要管理员权限）
```bash
curl -X POST http://localhost:5000/api/signatures/1/open \
  -H "X-User-ID: 1" \
  -H "X-Token: admin_token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 首次设置步骤

1. **启动系统**
   ```bash
   cd kty04-management
   python backend/app.py
   ```

2. **注册管理员**
   ```bash
   # 使用注册API注册用户
   # 然后在数据库中更新角色
   sqlite3 data/database.db
   UPDATE users SET role='admin' WHERE id=1;
   ```

3. **测试权限系统**
   ```bash
   python test_auth.py
   ```

## 数据库查询

### 查看用户列表
```sql
SELECT id, username, role FROM users;
```

### 查看审计日志
```sql
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;
```

### 更新用户角色
```sql
UPDATE users SET role='admin' WHERE id=1;
UPDATE users SET role='user' WHERE id=2;
```

## 常见问题

**Q: 如何升级用户为管理员？**
A: 使用 SQL 命令更新 users 表的 role 字段

**Q: 忘记密码怎么办？**
A: 当前系统没有密码重置功能，需要在数据库中手动重置

**Q: 如何启用新的密钥？**
A: 删除旧的 memkey.json 文件，重新添加成员以获得新密钥

**Q: 如何检查操作记录？**
A: 查询 audit_logs 表，按 created_at 排序

## 检查清单

- [ ] 删除旧的数据库文件（如果有）
- [ ] 启动应用，数据库自动初始化
- [ ] 注册管理员用户并升级权限
- [ ] 运行 test_auth.py 验证权限系统
- [ ] 测试管理员创建群组
- [ ] 测试普通用户无法创建群组
- [ ] 完整测试工作流程

