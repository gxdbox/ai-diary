# AI Diary 后端部署指南

## 前置条件

- 阿里云服务器（Alibaba Cloud Linux）
- 已备案域名 + SSL 证书
- SSH 访问权限

## 一、服务器环境准备

```bash
# 1. 更新系统
sudo yum update -y

# 2. 安装 Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# 3. 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. 安装 Nginx
sudo yum install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# 5. 创建项目目录
mkdir -p ~/ai-diary && cd ~/ai-diary
```

## 二、上传项目文件

### 方法1：使用 scp（推荐）

在本地 Mac 终端执行：

```bash
# 上传后端代码到服务器
scp -r /Users/pony/Documents/code/ai/ai_diary/backend/* root@你的服务器IP:~/ai-diary/
```

### 方法2：使用 Git

```bash
# 在服务器上
cd ~/ai-diary
git clone https://github.com/gxdbox/ai-diary.git .
```

## 三、配置环境变量

```bash
# 创建 .env 文件
cd ~/ai-diary
cat > .env << 'EOF'
DASHSCOPE_API_KEY=你的阿里云API密钥
DATABASE_URL=sqlite+aiosqlite:///./ai_diary.db
CHROMA_PERSIST_DIR=./data/chroma_data
EOF
```

## 四、配置 Nginx + HTTPS

### 1. 上传 SSL 证书

```bash
# 创建证书目录
sudo mkdir -p /etc/nginx/ssl

# 上传证书文件（在本地执行）
scp your-cert.pem root@服务器IP:/etc/nginx/ssl/
scp your-key.pem root@服务器IP:/etc/nginx/ssl/
```

### 2. 配置 Nginx

```bash
# 编辑配置
sudo vi /etc/nginx/conf.d/ai-diary.conf
```

粘贴以下内容（替换域名和证书路径）：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/your-cert.pem;
    ssl_certificate_key /etc/nginx/ssl/your-key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### 3. 重启 Nginx

```bash
sudo nginx -t  # 测试配置
sudo systemctl restart nginx
```

## 五、启动后端服务

### 方式1：使用 systemd（推荐）

systemd 提供进程管理、自动重启和日志收集功能。

#### 5.1 安装 systemd 服务

```bash
# 在服务器上执行
cd ~/ai-diary

# 复制服务文件到 systemd 目录
sudo cp backend/ai-diary.service /etc/systemd/system/

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable ai-diary

# 创建日志目录
mkdir -p logs
```

#### 5.2 启动服务

```bash
# 启动服务
sudo systemctl start ai-diary

# 查看服务状态
sudo systemctl status ai-diary

# 查看实时日志
sudo journalctl -u ai-diary -f
```

#### 5.3 常用管理命令

```bash
# 启动服务
sudo systemctl start ai-diary

# 停止服务
sudo systemctl stop ai-diary

# 重启服务
sudo systemctl restart ai-diary

# 查看服务状态
sudo systemctl status ai-diary

# 查看实时日志
sudo journalctl -u ai-diary -f

# 查看最近 100 行日志
sudo journalctl -u ai-diary -n 100

# 查看今天的日志
sudo journalctl -u ai-diary --since today

# 禁用开机自启
sudo systemctl disable ai-diary
```

#### 5.4 日志位置

- 应用日志：`/root/ai-diary/logs/app.log`
- 错误日志：`/root/ai-diary/logs/error.log`
- systemd 日志：`sudo journalctl -u ai-diary`

### 方式2：使用 Docker Compose（备选）

如果需要使用容器化部署，可以使用 Docker Compose。

```bash
cd ~/ai-diary

# 构建并启动
sudo docker-compose up -d --build

# 查看日志
sudo docker-compose logs -f

# 检查状态
sudo docker-compose ps
```

### 方式3：手动启动（仅用于调试）

```bash
cd ~/ai-diary
mkdir -p logs

# 后台运行（不推荐生产环境使用）
nohup /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 >> logs/uvicorn.log 2>&1 &

# 查看进程
ps aux | grep uvicorn

# 停止服务
pkill -f "uvicorn app.main:app"
```

## 六、配置防火墙

```bash
# 开放端口
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

在阿里云控制台也要开放 80 和 443 端口（安全组规则）。

## 七、验证部署

```bash
# 测试 API
curl https://your-domain.com/health
```

## 八、配置 Sentry 错误追踪（推荐）

Sentry 提供实时错误监控和告警功能，帮助快速定位生产环境问题。

### 1. 注册 Sentry 账号

访问 [https://sentry.io/signup/](https://sentry.io/signup/) 免费注册账号。

### 2. 创建新项目

- 登录后点击 "Create Project"
- 选择 **FastAPI** 框架
- 设置项目名称为 "AI Diary"
- 复制生成的 DSN（格式：`https://xxx@sentry.io/xxx`）

### 3. 配置环境变量

在服务器的 `.env` 文件中添加：

```bash
# 编辑 .env 文件
vi ~/ai-diary/.env

# 添加以下行（替换为你的 DSN）
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### 4. 重启服务

```bash
# 使用 systemd 重启
sudo systemctl restart ai-diary

# 查看启动日志确认 Sentry 初始化成功
sudo journalctl -u ai-diary -f
```

### 5. 验证 Sentry 集成

#### 5.1 触发测试错误

重启服务后,访问测试端点触发错误:

```bash
curl https://51pic.xyz/test/sentry-error
```

该端点会触发 `ZeroDivisionError`,Sentry 应该自动捕获并上报。

#### 5.2 检查 Sentry Dashboard

1. 登录 Sentry Dashboard: https://sentry.io/organizations/your-org/issues/

2. 应该在 "Issues" 页面看到新的错误报告:
   - **错误类型**: ZeroDivisionError
   - **消息**: division by zero
   - **请求路径**: /test/sentry-error

3. 点击错误详情可以看到:
   - 完整的堆栈跟踪
   - 请求参数和 headers
   - 用户 IP 地址(如果启用了 send_default_pii)
   - 环境变量信息

#### 5.3 注意事项

- ✅ 测试完成后可以删除 `/test/sentry-error` 端点或限制访问
- ⚠️ 生产环境建议移除测试端点,避免被滥用
- ℹ️ `send_default_pii=True` 会发送用户 IP 等敏感信息,根据隐私政策决定是否启用

### 免费额度说明

- **免费计划**：每月 5,000 个错误事件
- **适合场景**：小型项目和个人应用完全够用
- **采样率调整**：如果流量较大，可在 `main.py` 中调整 `traces_sample_rate=0.1` 降低成本

### 注意事项

1. ✅ Sentry 仅在 `APP_ENV=production` 时启用，开发环境不会上报错误
2. ✅ DSN 通过环境变量管理，不会硬编码到代码中
3. ✅ 自动捕获未处理异常、HTTP 5xx 错误、性能数据
4. ⚠️ 如需关闭 Sentry，只需删除 `.env` 中的 `SENTRY_DSN` 或设置为空字符串

## 十、配置 Prometheus + Grafana 监控

Prometheus 提供实时性能指标监控,Grafana 提供可视化 Dashboard。

### 快速开始

详细的配置指南和故障排查请查看: [PROMETHEUS_GRAFANA_SETUP.md](./PROMETHEUS_GRAFANA_SETUP.md)

**访问地址:**
- Prometheus: http://8.136.124.182:9090
- Grafana: http://8.136.124.182:3002 (admin / ai-diary-admin-2026)

### 部署命令

```bash
# 在服务器上执行
cd ~/ai-diary
docker compose -f docker-compose.monitoring.yml up -d
```

### 配置文件

项目根目录包含以下配置文件:
- `docker-compose.monitoring.yml` - 容器编排配置
- `prometheus.yml` - Prometheus 主配置
- `alert_rules.yml` - 告警规则(占位)

### 验证部署

```bash
# 检查容器状态
ssh root@8.136.124.182 "docker ps | grep -E 'prometheus|grafana'"

# 检查 Prometheus target 状态
ssh root@8.136.124.182 "curl -s 'http://localhost:9090/api/v1/targets' | python3 -m json.tool"

# 检查 Grafana 健康状态
ssh root@8.136.124.182 "curl -s http://localhost:3002/api/health"
```

### 安全建议

⚠️ **生产环境必须限制 `/metrics` 端点访问!**

详见 [PROMETHEUS_GRAFANA_SETUP.md](./PROMETHEUS_GRAFANA_SETUP.md) 中的"安全建议"章节。

## 十一、修改 iOS App 配置

修改 `iOS/AIDiary/AIDiary/Config/AppConfig.swift`:

```swift
static let environment: Environment = .production  // 改为 production
```

并将 `.production` 的 `baseURL` 改为你的域名。

## 十、配置自动备份

### 1. 备份脚本说明

项目提供了自动备份脚本 `scripts/backup_database.sh`,可以定期备份 SQLite 数据库和 ChromaDB 向量数据。

**功能特性:**
- ✅ 自动备份 SQLite 数据库 (`ai_diary.db`)
- ✅ 自动备份 ChromaDB 向量数据 (`chroma_data/`)
- ✅ 保留最近 7 天的本地备份,自动清理旧备份
- ✅ **支持上传到阿里云 OSS,实现异地容灾**(详见 [OSS_BACKUP_SETUP.md](./OSS_BACKUP_SETUP.md))
- ✅ 详细的日志记录(输出到控制台和日志文件)
- ✅ 错误处理和验证机制

### 2. 配置环境变量

在服务器的 `.env` 文件中配置 OSS 凭据(可选):

```bash
ssh root@8.136.124.182
cd /root/ai-diary
vi .env
```

添加以下配置:

```bash
# 阿里云 OSS 备份配置(可选,不配置则仅本地备份)
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BACKUP_BUCKET_NAME=ai-diary-backups
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BACKUP_PATH=backups/
```

**详细配置指南**: 查看 [OSS_BACKUP_SETUP.md](./OSS_BACKUP_SETUP.md)

### 3. 配置定时任务

在服务器上编辑 crontab：

```bash
ssh root@8.136.124.182 "crontab -e"
```

添加以下行（每天凌晨 2 点执行备份）：

```cron
0 2 * * * /root/ai-diary/scripts/backup_database.sh
```

保存并退出编辑器。

### 4. 验证定时任务

```bash
# 查看已配置的定时任务
ssh root@8.136.124.182 "crontab -l"

# 手动测试备份脚本
ssh root@8.136.124.182 "cd /root/ai-diary && ./scripts/backup_database.sh"

# 查看备份文件
ssh root@8.136.124.182 "ls -lh /root/ai-diary/backups/"
```

### 5. 查看备份日志

```bash
# 实时查看备份日志
ssh root@8.136.124.182 "tail -f /root/ai-diary/logs/backup.log"

# 查看最近的备份记录
ssh root@8.136.124.182 "cat /root/ai-diary/logs/backup.log"
```

### 6. 恢复数据库

如果需要从备份恢复：

```bash
# 停止服务
ssh root@8.136.124.182 "pkill -f uvicorn"

# 恢复 SQLite 数据库（替换为实际备份文件名）
ssh root@8.136.124.182 "cp /root/ai-diary/backups/ai_diary_20250101_020000.db /root/ai-diary/ai_diary.db"

# 恢复 ChromaDB 数据（替换为实际备份文件名）
ssh root@8.136.124.182 "tar xzf /root/ai-diary/backups/chroma_data_20250101_020000.tar.gz -C /root/ai-diary/"

# 重启服务
ssh root@8.136.124.182 "cd /root/ai-diary && nohup /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"

# 验证服务
curl https://51pic.xyz/health
```

### 7. 备份文件命名规则

- **SQLite 备份**: `ai_diary_YYYYMMDD_HHMMSS.db`
- **ChromaDB 备份**: `chroma_data_YYYYMMDD_HHMMSS.tar.gz`

示例：
```
ai_diary_20250115_020000.db
chroma_data_20250115_020000.tar.gz
```

### 8. OSS 异地容灾备份

如果配置了 OSS 凭据,备份脚本会自动上传到阿里云 OSS。查看详细配置:

👉 **[OSS_BACKUP_SETUP.md](./OSS_BACKUP_SETUP.md)** - 完整的 OSS 配置、验证和恢复指南

**快速验证 OSS 上传:**

```bash
# 手动执行备份(会同时上传到 OSS)
ssh root@8.136.124.182 "cd /root/ai-diary && ./scripts/backup_database.sh"

# 查看备份日志,确认 OSS 上传成功
ssh root@8.136.124.182 "tail -20 /root/ai-diary/logs/backup.log"

# 通过 ossutil 验证 OSS 中的备份文件
ssh root@8.136.124.182 "ossutil ls oss://ai-diary-backups/backups/"
```

**从 OSS 恢复备份:**

```bash
# 停止服务
ssh root@8.136.124.182 "sudo systemctl stop ai-diary"

# 从 OSS 下载最新备份
ssh root@8.136.124.182 "ossutil cp oss://ai-diary-backups/backups/database/ai_diary_YYYYMMDD_HHMMSS.db /tmp/"
ssh root@8.136.124.182 "ossutil cp oss://ai-diary-backups/backups/chromadb/chroma_data_YYYYMMDD_HHMMSS.tar.gz /tmp/"

# 恢复文件
ssh root@8.136.124.182 "cp /tmp/ai_diary_*.db /root/ai-diary/ai_diary.db"
ssh root@8.136.124.182 "tar xzf /tmp/chroma_data_*.tar.gz -C /root/ai-diary/"

# 重启服务
ssh root@8.136.124.182 "sudo systemctl start ai-diary"

# 验证服务
curl https://51pic.xyz/health
```

⚠️ **重要提示**: 
- 建议每月测试一次 OSS 备份恢复流程,确保备份可用
- 生产环境建议使用 RAM 用户而非主账号 AccessKey
- 定期检查 OSS 存储费用,设置生命周期规则自动清理旧备份

## 常用命令

### systemd 管理（推荐）

```bash
# 查看服务状态
sudo systemctl status ai-diary

# 重启服务
sudo systemctl restart ai-diary

# 停止服务
sudo systemctl stop ai-diary

# 启动服务
sudo systemctl start ai-diary

# 查看实时日志
sudo journalctl -u ai-diary -f

# 查看最近 100 行日志
sudo journalctl -u ai-diary -n 100
```

### Docker Compose 管理（备选）

```bash
# 查看日志
sudo docker-compose logs -f

# 重启服务
sudo docker-compose restart

# 停止服务
sudo docker-compose down

# 更新代码后重新部署
sudo docker-compose up -d --build
```

## 注意事项

1. 确保域名已备案并在阿里云解析到服务器 IP
2. 确保阿里云安全组开放了 80 和 443 端口
3. API 密钥不要泄露，使用环境变量管理
4. **定期备份数据库** - 建议配置自动备份脚本（见第九节），或手动执行：
   ```bash
   ssh root@8.136.124.182 "cd /root/ai-diary && ./scripts/backup_database.sh"
   ```
5. **systemd 服务配置**：
   - 首次部署需要安装服务文件：`sudo cp backend/ai-diary.service /etc/systemd/system/`
   - 修改服务文件后需重新加载：`sudo systemctl daemon-reload`
   - 服务会自动重启（Restart=always），无需手动监控进程
   - 日志通过 systemd journal 管理，也可查看 `/root/ai-diary/logs/` 目录
6. **故障排查**：
   - 服务启动失败：`sudo journalctl -u ai-diary -n 50 --no-pager`
   - 检查配置文件语法：`systemd-analyze verify /etc/systemd/system/ai-diary.service`