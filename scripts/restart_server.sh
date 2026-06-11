#!/bin/bash
# 一键重启阿里云后端服务脚本

echo "🚀 开始重启阿里云后端服务..."
echo ""

SERVER="root@8.136.124.182"

# 停止旧服务
echo "⏹️  停止旧服务..."
ssh $SERVER 'pkill -f "uvicorn app.main:app"' 2>/dev/null
sleep 2

# 启动新服务
echo "▶️  启动新服务..."
ssh $SERVER 'cd ~/ai-diary && nohup /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &'
sleep 3

# 验证服务
echo "✅ 验证服务..."
HEALTH=$(ssh $SERVER 'curl -s http://localhost:8000/health')
echo "健康检查: $HEALTH"

if echo "$HEALTH" | grep -q "healthy"; then
    echo ""
    echo "🎉 部署成功！服务已重启"
    echo ""
    echo "测试日记创建速度："
    ssh $SERVER 'time curl -X POST http://localhost:8000/api/diary/create -H "Content-Type: application/json" -d "{\"raw_text\": \"今天天气很好\"}"'
else
    echo ""
    echo "❌ 部署失败，请检查服务器日志"
fi
