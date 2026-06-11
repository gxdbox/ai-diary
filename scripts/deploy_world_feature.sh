#!/bin/bash
# AI Diary 后端快速部署脚本
# 用途：将优化后的代码部署到阿里云服务器

echo "======================================"
echo "AI Diary 后端部署脚本"
echo "======================================"
echo ""

SERVER_IP="8.136.124.182"
PROJECT_DIR="~/ai-diary"

echo "步骤 1: 上传更新的文件..."
scp backend/app/api/diary.py root@$SERVER_IP:$PROJECT_DIR/app/api/diary.py

if [ $? -eq 0 ]; then
    echo "✅ 文件上传成功"
else
    echo "❌ 文件上传失败"
    exit 1
fi

echo ""
echo "步骤 2: 连接到服务器并重启服务..."
echo "请在服务器上执行以下命令："
echo ""
echo "--- 复制以下命令并在服务器终端执行 ---"
cat << 'EOF'
# 停止旧服务
pkill -f "uvicorn app.main:app"

# 等待 2 秒
sleep 2

# 启动新服务
cd ~/ai-diary
nohup /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &

# 等待服务启动
sleep 2

# 验证服务
curl http://localhost:8000/health

# 测试日记创建速度
time curl -X POST http://localhost:8000/api/diary/create \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "今天天气很好，心情不错"}'
EOF

echo ""
echo "======================================"
echo "部署说明："
echo "1. 上面的命令已上传 diary.py 到服务器"
echo "2. 请 SSH 连接到服务器执行上面的命令"
echo "3. 如果健康检查返回 {\"status\":\"healthy\"} 则部署成功"
echo "4. 测试日记创建应该在 1 秒内完成"
echo "======================================"
