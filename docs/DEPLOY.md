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

```bash
cd ~/ai-diary

# 构建并启动
sudo docker-compose up -d --build

# 查看日志
sudo docker-compose logs -f

# 检查状态
sudo docker-compose ps
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

## 常用命令

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
4. 定期备份数据库文件 `ai_diary.db`