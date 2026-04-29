#!/usr/bin/env python3
"""
AI伴侣 - 启动脚本

使用方式:
1. 设置环境变量: export DEEPSEEK_API_KEY="your-api-key"
2. 运行: python run.py
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from backend.app import app
import config

if __name__ == "__main__":
    # 检查 API Key
    if not config.DEEPSEEK_API_KEY:
        print("⚠️  警告: 未设置 DEEPSEEK_API_KEY 环境变量")
        print("请设置: export DEEPSEEK_API_KEY='your-api-key'")
        print("或创建 .env 文件")

    print(f"🚀 启动 AI伴侣服务...")
    print(f"   地址: http://{config.API_HOST}:{config.API_PORT}")
    print(f"   文档: http://{config.API_HOST}:{config.API_PORT}/docs")

    uvicorn.run(
        "backend.app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG
    )