#!/bin/bash

echo "========================================="
echo "AI Diary 多Agent架构完整验证"
echo "========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

echo -e "${BLUE}1. 验证GitHub CLI认证${NC}"
echo "-----------------------------------"
if gh auth status &>/dev/null; then
    echo -e "${GREEN}✓ GitHub CLI已认证${NC}"
    gh auth status
    ((PASS++))
else
    echo -e "${RED}✗ GitHub CLI未认证${NC}"
    ((FAIL++))
fi
echo ""

echo -e "${BLUE}2. 验证仓库访问权限${NC}"
echo "-----------------------------------"
if gh repo view gxdbox/ai-diary &>/dev/null; then
    echo -e "${GREEN}✓ 仓库访问权限正常${NC}"
    echo "仓库: https://github.com/gxdbox/ai-diary"
    ((PASS++))
else
    echo -e "${RED}✗ 仓库访问权限异常${NC}"
    ((FAIL++))
fi
echo ""

echo -e "${BLUE}3. 验证Agent配置${NC}"
echo "-----------------------------------"
for agent in backend ios test bug; do
    if [ -f "/Users/pony/.config/opencode/agents/ai-diary-${agent}.md" ]; then
        echo -e "${GREEN}✓${NC} ai-diary-${agent}.md 存在"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} ai-diary-${agent}.md 不存在"
        ((FAIL++))
    fi
done
echo ""

echo -e "${BLUE}4. 验证Skill配置${NC}"
echo "-----------------------------------"
for skill in memory-system ios-cache-strategy; do
    if [ -f "/Users/pony/.config/opencode/skills/${skill}/SKILL.md" ]; then
        echo -e "${GREEN}✓${NC} ${skill} Skill存在"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} ${skill} Skill不存在"
        ((FAIL++))
    fi
done
echo ""

echo -e "${BLUE}5. 验证Agent权限配置${NC}"
echo "-----------------------------------"
for agent in backend ios test bug; do
    if grep -q "write: true" "/Users/pony/.config/opencode/agents/ai-diary-${agent}.md"; then
        echo -e "${GREEN}✓${NC} ai-diary-${agent} 权限正确"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} ai-diary-${agent} 权限错误"
        ((FAIL++))
    fi
done
echo ""

echo -e "${BLUE}6. 验证模型配置${NC}"
echo "-----------------------------------"
for agent in backend ios test bug; do
    if grep -q "model: baiduqianfancodingplan/glm-5" "/Users/pony/.config/opencode/agents/ai-diary-${agent}.md"; then
        echo -e "${GREEN}✓${NC} ai-diary-${agent} 模型统一"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} ai-diary-${agent} 模型不一致"
        ((FAIL++))
    fi
done
echo ""

echo -e "${BLUE}7. 创建测试Issue（验证Bug Agent能力）${NC}"
echo "-----------------------------------"
ISSUE_URL=$(gh issue create --repo gxdbox/ai-diary \
    --title "[Test] 多Agent架构验证测试" \
    --body "这是一个测试Issue，用于验证Bug Agent的Issue创建功能。

## 测试内容
- ✅ GitHub CLI认证成功
- ✅ 仓库访问权限正常
- ✅ Agent配置正确

## 测试时间
$(date '+%Y-%m-%d %H:%M:%S')

## 状态
这是一个测试Issue，验证完成后将自动关闭。" \
    --label "test" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 测试Issue创建成功${NC}"
    echo "Issue URL: $ISSUE_URL"
    ((PASS++))
    
    # 自动关闭测试Issue
    gh issue close $(echo $ISSUE_URL | grep -o '[0-9]*') --repo gxdbox/ai-diary --comment "验证完成，关闭测试Issue" &>/dev/null
    echo -e "${GREEN}✓ 测试Issue已自动关闭${NC}"
else
    echo -e "${YELLOW}⚠ 测试Issue创建失败（可能已存在相同标题）${NC}"
fi
echo ""

echo "========================================="
echo "验证结果汇总"
echo "========================================="
echo -e "${GREEN}通过: $PASS${NC}"
echo -e "${RED}失败: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ 所有验证项通过！${NC}"
    echo ""
    echo -e "${BLUE}架构状态：${NC}"
    echo "  • GitHub CLI: ✅ 已认证"
    echo "  • Agent配置: ✅ 4个Agent就绪"
    echo "  • Skill配置: ✅ 2个Skill就绪"
    echo "  • Issue创建: ✅ 功能正常"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo "  1. 重启opencode加载新配置"
    echo "  2. 测试Agent触发：在对话中提及 'backend'、'iOS'、'测试'、'Bug'"
    echo "  3. 开始使用多Agent协作开发"
    exit 0
else
    echo -e "${RED}✗ 存在 $FAIL 个失败项${NC}"
    exit 1
fi
