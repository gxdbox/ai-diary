#!/bin/bash
#
# Pre-commit hook: iOS Swift 编译检查
# 如果有 Swift 文件变更，自动运行编译验证
#

set -e

# 获取暂存的 Swift 文件
SWIFT_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.swift$' || true)

if [ -z "$SWIFT_FILES" ]; then
    echo "✅ 无 Swift 文件变更，跳过编译检查"
    exit 0
fi

echo "📋 检测到 Swift 文件变更:"
echo "$SWIFT_FILES"
echo ""
echo "🔨 正在编译验证..."

# 运行 iOS 编译
cd iOS/AIDiary
BUILD_OUTPUT=$(xcodebuild -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build 2>&1)
BUILD_STATUS=$?

if [ $BUILD_STATUS -ne 0 ]; then
    echo ""
    echo "❌ 编译失败！请修复错误后再提交。"
    echo ""
    echo "错误摘要:"
    echo "$BUILD_OUTPUT" | grep -E "error:" | head -10
    echo ""
    echo "💡 提示: 运行 'cd iOS/AIDiary && xcodebuild -scheme AIDiary build' 查看完整错误"
    exit 1
fi

echo ""
echo "✅ 编译成功！继续提交..."
exit 0