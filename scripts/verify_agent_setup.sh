#!/bin/bash

echo "========================================="
echo "AI Diary 多Agent架构验证脚本"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查结果
PASS=0
FAIL=0

# 检查函数
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 存在"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $1 不存在"
        ((FAIL++))
    fi
}

check_content() {
    if grep -q "$2" "$1"; then
        echo -e "${GREEN}✓${NC} $1 包含: $2"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $1 不包含: $2"
        ((FAIL++))
    fi
}

echo "1. 检查Agent配置文件..."
echo "-----------------------------------"
check_file "/Users/pony/.config/opencode/agents/ai-diary-backend.md"
check_file "/Users/pony/.config/opencode/agents/ai-diary-ios.md"
check_file "/Users/pony/.config/opencode/agents/ai-diary-test.md"
check_file "/Users/pony/.config/opencode/agents/ai-diary-bug.md"
echo ""

echo "2. 检查Skill配置文件..."
echo "-----------------------------------"
check_file "/Users/pony/.config/opencode/skills/memory-system/SKILL.md"
check_file "/Users/pony/.config/opencode/skills/ios-cache-strategy/SKILL.md"
echo ""

echo "3. 检查旧Agent是否已删除..."
echo "-----------------------------------"
if [ ! -f "/Users/pony/.config/opencode/agents/ozon.md" ]; then
    echo -e "${GREEN}✓${NC} ozon.md 已删除"
    ((PASS++))
else
    echo -e "${RED}✗${NC} ozon.md 仍存在"
    ((FAIL++))
fi

if [ ! -f "/Users/pony/.config/opencode/agents/review.md" ]; then
    echo -e "${GREEN}✓${NC} review.md 已删除"
    ((PASS++))
else
    echo -e "${RED}✗${NC} review.md 仍存在"
    ((FAIL++))
fi
echo ""

echo "4. 检查项目AGENTS.md是否已更新..."
echo "-----------------------------------"
check_content "/Users/pony/Documents/code/ai/ai_diary/AGENTS.md" "iOS (SwiftUI)"
check_content "/Users/pony/Documents/code/ai/ai_diary/AGENTS.md" "FastAPI 后端"
check_content "/Users/pony/Documents/code/ai/ai_diary/AGENTS.md" "SwiftUI"
echo ""

echo "5. 检查Agent配置内容..."
echo "-----------------------------------"
check_content "/Users/pony/.config/opencode/agents/ai-diary-backend.md" "mode: subagent"
check_content "/Users/pony/.config/opencode/agents/ai-diary-backend.md" "model: baiduqianfancodingplan/glm-5"
check_content "/Users/pony/.config/opencode/agents/ai-diary-backend.md" "write: true"
check_content "/Users/pony/.config/opencode/agents/ai-diary-ios.md" "mode: subagent"
check_content "/Users/pony/.config/opencode/agents/ai-diary-test.md" "mode: subagent"
check_content "/Users/pony/.config/opencode/agents/ai-diary-bug.md" "mode: subagent"
echo ""

echo "6. 检查Skill配置内容..."
echo "-----------------------------------"
check_content "/Users/pony/.config/opencode/skills/memory-system/SKILL.md" "name: memory-system"
check_content "/Users/pony/.config/opencode/skills/ios-cache-strategy/SKILL.md" "name: ios-cache-strategy"
echo ""

echo "========================================="
echo "验证结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASS${NC}"
echo -e "${RED}失败: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查项均通过！${NC}"
    echo ""
    echo "下一步操作："
    echo "1. 重启 opencode 以加载新配置"
    echo "2. 测试 backend agent: 在对话中提到 'backend' 或 'Python'"
    echo "3. 测试 ios agent: 在对话中提到 'iOS' 或 'Swift'"
    echo "4. 测试 test agent: 在对话中提到 '测试' 或 'pytest'"
    echo "5. 测试 bug agent: 在对话中提到 'Bug' 或 'Issue'"
    echo ""
    echo "配置完成！"
    exit 0
else
    echo -e "${RED}✗ 存在 $FAIL 个失败项，请检查上述错误${NC}"
    exit 1
fi
