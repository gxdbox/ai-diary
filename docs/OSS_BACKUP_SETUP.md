# 阿里云 OSS 备份配置指南

## 概述

本指南介绍如何配置阿里云 OSS 自动备份,实现数据库的异地容灾存储。

**功能特性:**
- ✅ 自动上传 SQLite 数据库和 ChromaDB 向量数据到 OSS
- ✅ 保留 30 天内的 OSS 备份,自动清理旧备份节省成本
- ✅ 支持环境变量配置,无需硬编码敏感信息
- ✅ ossutil 自动安装,无需手动操作
- ✅ 未配置 OSS 凭据时自动跳过,不影响本地备份

---

## 1. 创建 OSS Bucket

### 步骤:

1. **登录阿里云控制台**: https://oss.console.aliyun.com/

2. **点击 "创建 Bucket"**

3. **配置 Bucket 参数:**
   - **Bucket 名称**: `ai-diary-backups` (建议使用此名称或自定义)
   - **区域**: 选择与服务器相同的区域(如华东1-杭州)
   - **存储类型**: 标准存储
   - **读写权限**: 私有(推荐,更安全)
   - **版本控制**: 可选开启,提供额外保护
   - **服务端加密**: 建议开启 AES-256 加密

4. **点击 "确定" 完成创建**

---

## 2. 获取 AccessKey

### 方式1: 使用 RAM 用户(推荐,更安全)

1. **访问 RAM 控制台**: https://ram.console.aliyun.com/users

2. **创建 RAM 用户:**
   - 点击 "创建用户"
   - 用户名: `ai-diary-backup-user`
   - 勾选 "OpenAPI 调用访问"
   - 点击 "确定"

3. **保存 AccessKey ID 和 Secret** (只显示一次!)

4. **授权策略:**
   - 进入该用户的 "权限管理" 页面
   - 点击 "新增授权"
   - 选择 "自定义策略" → "新建权限策略"
   - 粘贴以下策略内容:

```json
{
    "Version": "1",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "oss:PutObject",
                "oss:GetObject",
                "oss:DeleteObject",
                "oss:ListObjects"
            ],
            "Resource": [
                "acs:oss:*:*:ai-diary-backups/*"
            ]
        }
    ]
}
```

   - 命名策略: `AI-Diary-Backup-Policy`
   - 返回用户授权页面,绑定该策略

### 方式2: 使用主账号 AccessKey(不推荐)

⚠️ **警告**: 主账号 AccessKey 具有所有权限,泄露风险极高!

1. 点击右上角头像 → AccessKey 管理
2. 点击 "创建 AccessKey"
3. 保存 AccessKey ID 和 Secret(只显示一次!)

---

## 3. 配置环境变量

### 在服务器上编辑 .env 文件:

```bash
ssh root@8.136.124.182
cd /root/ai-diary
vi .env
```

### 添加以下配置项:

```bash
# 阿里云 OSS 备份配置
OSS_ACCESS_KEY_ID=LTAI5tXXXXXXXXXXXXXXXX
OSS_ACCESS_KEY_SECRET=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
OSS_BACKUP_BUCKET_NAME=ai-diary-backups
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BACKUP_PATH=backups/
```

**参数说明:**
- `OSS_ACCESS_KEY_ID`: 从步骤 2 获取的 AccessKey ID
- `OSS_ACCESS_KEY_SECRET`: 从步骤 2 获取的 AccessKey Secret
- `OSS_BACKUP_BUCKET_NAME`: OSS Bucket 名称
- `OSS_ENDPOINT`: OSS Endpoint(根据区域选择,见下方列表)
- `OSS_BACKUP_PATH`: OSS 中的备份路径前缀

### 常用 Region Endpoint 对照表:

| 区域 | Endpoint |
|------|----------|
| 华东1(杭州) | oss-cn-hangzhou.aliyuncs.com |
| 华东2(上海) | oss-cn-shanghai.aliyuncs.com |
| 华北1(青岛) | oss-cn-qingdao.aliyuncs.com |
| 华北2(北京) | oss-cn-beijing.aliyuncs.com |
| 华南1(深圳) | oss-cn-shenzhen.aliyuncs.com |

---

## 4. 测试备份

### 手动执行备份脚本:

```bash
cd /root/ai-diary
./scripts/backup_database.sh
```

### 预期输出示例:

```
[2025-01-15 02:00:00] ==========================================
[2025-01-15 02:00:00] 开始备份...
[2025-01-15 02:00:00] 备份目录: /root/ai-diary/backups
[2025-01-15 02:00:00] 日期标记: 20250115_020000
[2025-01-15 02:00:01] ✅ SQLite 数据库备份完成: ai_diary_20250115_020000.db (大小: 2.3M)
[2025-01-15 02:00:02] ✅ ChromaDB 数据备份完成: chroma_data_20250115_020000.tar.gz (大小: 15M)
[2025-01-15 02:00:02] 🧹 清理 7 天前的旧备份...
[2025-01-15 02:00:02]    没有需要清理的旧备份
[2025-01-15 02:00:02] 📤 开始上传到 OSS...
[2025-01-15 02:00:03]    上传数据库备份...
[2025-01-15 02:00:05]    ✅ 数据库备份已上传到 OSS: backups/database/ai_diary_20250115_020000.db
[2025-01-15 02:00:05]    上传 ChromaDB 备份...
[2025-01-15 02:00:08]    ✅ ChromaDB 备份已上传到 OSS: backups/chromadb/chroma_data_20250115_020000.tar.gz
[2025-01-15 02:00:08]    清理30天前的 OSS 备份...
[2025-01-15 02:00:09]    ✅ OSS 旧备份清理完成
[2025-01-15 02:00:09] ✅ OSS 上传完成
[2025-01-15 02:00:09] ==========================================
[2025-01-15 02:00:09] 当前备份文件:
[2025-01-15 02:00:09]   ai_diary_20250115_020000.db - 2.3M
[2025-01-15 02:00:09]   chroma_data_20250115_020000.tar.gz - 15M
[2025-01-15 02:00:09] 备份目录总大小: 18M
[2025-01-15 02:00:09] ✅ 备份完成!
```

### 如果未配置 OSS 凭据:

```
[2025-01-15 02:00:00] ⚠️  警告: 未配置 OSS 凭据,跳过 OSS 上传
[2025-01-15 02:00:00]    如需启用 OSS 备份,请在 .env 文件中配置:
[2025-01-15 02:00:00]    OSS_ACCESS_KEY_ID、OSS_ACCESS_KEY_SECRET、OSS_BACKUP_BUCKET_NAME
```

---

## 5. 验证 OSS 上传

### 方法1: 通过 OSS 控制台查看

1. 登录 OSS 控制台: https://oss.console.aliyun.com/
2. 进入 `ai-diary-backups` Bucket
3. 点击 "文件管理"
4. 应该能看到以下目录结构:
   ```
   backups/
   ├── database/
   │   └── ai_diary_20250115_020000.db
   └── chromadb/
       └── chroma_data_20250115_020000.tar.gz
   ```

### 方法2: 通过命令行验证

```bash
# 列出 OSS 中的备份文件
ossutil ls oss://ai-diary-backups/backups/

# 查看详细信息
ossutil ls oss://ai-diary-backups/backups/database/
ossutil ls oss://ai-diary-backups/backups/chromadb/
```

---

## 6. 恢复备份

### 场景1: 从 OSS 恢复最新备份

```bash
# 1. 停止服务
sudo systemctl stop ai-diary

# 2. 从 OSS 下载最新备份(替换为实际文件名)
ossutil cp oss://ai-diary-backups/backups/database/ai_diary_20250115_020000.db /tmp/ai_diary_restore.db
ossutil cp oss://ai-diary-backups/backups/chromadb/chroma_data_20250115_020000.tar.gz /tmp/chroma_data_restore.tar.gz

# 3. 备份当前数据库(以防万一)
cp /root/ai-diary/ai_diary.db /root/ai-diary/ai_diary.db.backup_before_restore

# 4. 恢复数据库文件
cp /tmp/ai_diary_restore.db /root/ai-diary/ai_diary.db
tar xzf /tmp/chroma_data_restore.tar.gz -C /root/ai-diary/

# 5. 重启服务
sudo systemctl start ai-diary

# 6. 验证服务
curl https://51pic.xyz/health
```

### 场景2: 从本地备份恢复

```bash
# 1. 停止服务
sudo systemctl stop ai-diary

# 2. 从本地备份恢复
cp /root/ai-diary/backups/ai_diary_20250115_020000.db /root/ai-diary/ai_diary.db
tar xzf /root/ai-diary/backups/chroma_data_20250115_020000.tar.gz -C /root/ai-diary/

# 3. 重启服务
sudo systemctl start ai-diary

# 4. 验证服务
curl https://51pic.xyz/health
```

---

## 7. 配置定时任务

### 编辑 crontab:

```bash
crontab -e
```

### 添加以下行(每天凌晨 2 点执行):

```cron
0 2 * * * cd /root/ai-diary && ./scripts/backup_database.sh >> /root/ai-diary/logs/backup_cron.log 2>&1
```

### 验证定时任务:

```bash
# 查看已配置的定时任务
crontab -l

# 查看定时任务日志
tail -f /root/ai-diary/logs/backup_cron.log
```

---

## 8. 成本优化建议

### 8.1 设置生命周期规则

在 OSS 控制台配置自动清理规则:

1. 进入 Bucket → "基础设置" → "生命周期"
2. 点击 "创建规则"
3. 配置:
   - **规则名称**: `auto-cleanup-old-backups`
   - **适用文件**: 指定前缀 `backups/`
   - **过期天数**: 30 天
   - **状态**: 启用

### 8.2 使用低频访问存储

如果备份访问频率低,可以转换为低频访问类型:

1. 进入 Bucket → "基础设置" → "存储类型转换"
2. 创建规则: 30 天后转为低频访问,90 天后转为归档存储

### 8.3 估算存储成本

假设:
- 数据库大小: 10 MB
- ChromaDB 大小: 50 MB
- 每天备份: 60 MB
- 保留 30 天: 1.8 GB

**费用估算**(华东1-杭州):
- 标准存储: 0.12 元/GB/月 × 1.8 GB ≈ 0.22 元/月
- PUT 请求: 0.01 元/万次 × 60 次/月 ≈ 0.0006 元/月
- GET 请求(恢复时): 0.01 元/万次

**总计**: 约 0.22 元/月,成本极低!

---

## 9. 故障排查

### 问题1: ossutil 安装失败

**症状**: 脚本提示 "ossutil 安装失败"

**解决方案**:
```bash
# 手动安装 ossutil
curl https://gosspublic.alicdn.com/ossutil/install.sh | bash

# 验证安装
which ossutil
ossutil --version
```

### 问题2: 上传失败 - AccessDenied

**症状**: 日志显示 "上传失败" 或 "AccessDenied"

**原因**: AccessKey 权限不足或配置错误

**解决方案**:
1. 检查 `.env` 文件中的 AccessKey 是否正确
2. 确认 RAM 用户已授予 OSS 写入权限
3. 测试 ossutil 配置:
   ```bash
   ossutil config -e oss-cn-hangzhou.aliyuncs.com -i YOUR_KEY_ID -k YOUR_KEY_SECRET
   ossutil ls oss://ai-diary-backups/
   ```

### 问题3: Endpoint 错误

**症状**: 连接超时或 "Endpoint 不存在"

**解决方案**:
1. 确认 `OSS_ENDPOINT` 与 Bucket 所在区域一致
2. 参考第 3 节的 Endpoint 对照表
3. 测试连通性:
   ```bash
   ping oss-cn-hangzhou.aliyuncs.com
   ```

### 问题4: 磁盘空间不足

**症状**: 备份失败,提示 "No space left on device"

**解决方案**:
1. 检查磁盘使用情况:
   ```bash
   df -h /root/ai-diary/backups
   ```
2. 清理旧备份:
   ```bash
   # 删除 7 天前的本地备份
   find /root/ai-diary/backups -name "ai_diary_*.db" -mtime +7 -delete
   find /root/ai-diary/backups -name "chroma_data_*.tar.gz" -mtime +7 -delete
   ```
3. 考虑增加磁盘容量或缩短本地保留时间

---

## 10. 安全最佳实践

### ✅ 推荐做法:

1. **使用 RAM 用户而非主账号**
   - 最小权限原则,仅授予必要的 OSS 权限
   - 定期轮换 AccessKey(建议每 90 天)

2. **保护 .env 文件**
   ```bash
   chmod 600 /root/ai-diary/.env
   chown root:root /root/ai-diary/.env
   ```

3. **不要将 .env 提交到 Git**
   - 确认 `.gitignore` 包含 `.env`
   - 使用 `.env.example` 作为模板

4. **启用 OSS 服务端加密**
   - 在 Bucket 配置中开启 AES-256 加密
   - 或使用 KMS 密钥管理

5. **定期测试恢复流程**
   - 每月至少进行一次恢复演练
   - 验证备份文件的完整性

### ❌ 避免的做法:

1. **不要在代码中硬编码 AccessKey**
2. **不要将 AccessKey 分享给他人**
3. **不要使用主账号 AccessKey**
4. **不要公开 .env 文件或截图**
5. **不要禁用 OSS Bucket 的访问日志**

---

## 11. 监控和告警

### 11.1 监控备份状态

```bash
# 检查最近的备份日志
tail -n 50 /root/ai-diary/logs/backup.log

# 检查备份文件是否存在
ls -lh /root/ai-diary/backups/ai_diary_*.db | tail -1
```

### 11.2 配置邮件告警(可选)

在 crontab 中添加错误通知:

```cron
# 如果备份失败,发送邮件给管理员
0 2 * * * cd /root/ai-diary && ./scripts/backup_database.sh || echo "备份失败!" | mail -s "AI Diary 备份告警" admin@example.com
```

### 11.3 集成到监控系统

如果使用 Prometheus + Grafana,可以添加自定义指标:

```python
# 在 backend/app/main.py 中添加
from prometheus_client import Gauge

backup_success = Gauge('database_backup_success', 'Last backup status')
backup_size = Gauge('database_backup_size_bytes', 'Last backup size in bytes')
```

---

## 附录: 常见问题 FAQ

**Q: 可以同时使用多个 OSS Bucket 吗?**  
A: 可以,修改脚本支持多 Bucket 上传,或在不同区域创建冗余备份。

**Q: 备份会影响服务器性能吗?**  
A: 影响很小。备份在凌晨执行,ossutil 上传是异步的,不会阻塞其他服务。

**Q: 如果网络中断,备份会失败吗?**  
A: ossutil 支持断点续传,网络恢复后会自动继续上传。

**Q: 如何验证备份文件的完整性?**  
A: 可以使用 md5sum 校验:
```bash
md5sum /root/ai-diary/ai_diary.db
ossutil stat oss://ai-diary-backups/backups/database/ai_diary_YYYYMMDD_HHMMSS.db
```

**Q: ChromaDB 备份是否必需?**  
A: 是的。ChromaDB 存储向量索引,丢失会导致语义搜索功能失效。

---

## 相关文档

- [部署指南](./DEPLOY.md)
- [架构设计](./ARCHITECTURE.md)
- [API 文档](./API.md)

---

**最后更新**: 2025-01-15  
**维护者**: AI Diary Team
