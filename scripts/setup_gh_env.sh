#!/bin/bash

echo "设置GitHub CLI环境变量..."

# 添加到shell配置文件
if [ -f ~/.zshrc ]; then
    echo 'export GH_HOST=github.com' >> ~/.zshrc
    echo "✓ 已添加到 ~/.zshrc"
elif [ -f ~/.bashrc ]; then
    echo 'export GH_HOST=github.com' >> ~/.bashrc
    echo "✓ 已添加到 ~/.bashrc"
fi

# 设置当前会话的环境变量
export GH_HOST=github.com

echo ""
echo "测试GitHub CLI..."
gh auth status

echo ""
echo "测试创建Issue..."
gh issue create --repo gxdbox/ai-diary \
    --title "[Test] 多Agent架构验证 - 环境变量测试" \
    --body "测试Bug Agent的Issue创建功能

## 测试内容
- GitHub CLI环境变量设置
- Issue创建功能验证

## 测试时间
$(date '+%Y-%m-%d %H:%M:%S')

此Issue用于验证多Agent架构的Bug Agent功能。" \
    --label "test"

echo ""
echo "✓ GitHub CLI配置完成！"
echo "请重启终端或运行: source ~/.zshrc"
