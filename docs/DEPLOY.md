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

## 八、修改 iOS App 配置

修改 `iOS/AIDiary/AIDiary/Config/AppConfig.swift`:

```swift
static let environment: Environment = .production  // 改为 production
```

并将 `.production` 的 `baseURL` 改为你的域名。

## 九、配置自动备份

### 1. 备份脚本说明

项目提供了自动备份脚本 `scripts/backup_database.sh`，可以定期备份 SQLite 数据库和 ChromaDB 向量数据。

**功能特性：**
- ✅ 自动备份 SQLite 数据库 (`ai_diary.db`)
- ✅ 自动备份 ChromaDB 向量数据 (`chroma_data/`)
- ✅ 保留最近 7 天的备份，自动清理旧备份
- ✅ 详细的日志记录（输出到控制台和日志文件）
- ✅ 错误处理和验证机制

### 2. 配置定时任务

在服务器上编辑 crontab：

```bash
ssh root@8.136.124.182 "crontab -e"
```

添加以下行（每天凌晨 2 点执行备份）：

```cron
0 2 * * * /root/ai-diary/scripts/backup_database.sh
```

保存并退出编辑器。

### 3. 验证定时任务

```bash
# 查看已配置的定时任务
ssh root@8.136.124.182 "crontab -l"

# 手动测试备份脚本
ssh root@8.136.124.182 "cd /root/ai-diary && ./scripts/backup_database.sh"

# 查看备份文件
ssh root@8.136.124.182 "ls -lh /root/ai-diary/backups/"
```

### 4. 查看备份日志

```bash
# 实时查看备份日志
ssh root@8.136.124.182 "tail -f /root/ai-diary/logs/backup.log"

# 查看最近的备份记录
ssh root@8.136.124.182 "cat /root/ai-diary/logs/backup.log"
```

### 5. 恢复数据库

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

### 6. 备份文件命名规则

- **SQLite 备份**: `ai_diary_YYYYMMDD_HHMMSS.db`
- **ChromaDB 备份**: `chroma_data_YYYYMMDD_HHMMSS.tar.gz`

示例：
```
ai_diary_20250115_020000.db
chroma_data_20250115_020000.tar.gz
```

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