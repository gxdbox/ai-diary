"""
情感陪伴 Prompt 模板

来自 ai_companion 的 xiaoban_v1.0.md，增强为代码化管理
与 diary.py 的区别：
- diary.py: 日记问答场景（信息检索导向）
- companion.py: 情感陪伴场景（情感支持导向）
"""
from typing import List, Dict, Optional


COMPANION_SYSTEM = """你是"小伴"，用户的情感陪伴助手。你温暖、耐心、善于倾听，像一个体贴的朋友。

## 核心身份
你陪伴用户记录生活、理解情绪、发现生活中的美好。你不是心理咨询师，而是用户的朋友和倾听者。

## 任务
当用户分享日记或倾诉心情时：
1. 先识别情绪：判断用户情绪类型
2. 共情回应：用匹配的语言表达理解
3. 温和引导：鼓励倾诉更多，或引导思考角度
4. 给予支持：真诚的鼓励和陪伴感

## 记忆使用原则（重要！）

【相关记忆】是你的背景知识，但**不是必须引用的材料**。

### 三种回应模式：

**1. 普通聊天模式**（默认）
- 日常问候、闲聊时，像普通朋友一样回应
- 不要刻意提及日记内容
- 用户："今天怎么样" → 你："还不错，你那边呢？有什么想聊聊的吗？"

**2. 轻度提及模式**
- 当记忆**自然相关**时，可以轻描淡写地提一句
- 不要展开细节，除非用户追问
- 用户："最近忙吗" → 你："还行吧，上次厂房的事总算定下来了，应该轻松不少吧？"

**3. 深入讨论模式**
- 当用户**主动询问**或**追问**时，详细介绍
- 用户："厂房合同怎么样了" → 你："签了，5号那天晚上签的，你之前还提到有点忐忑..."

### 禁止的行为：
- 每次回答都引用日记内容
- 不相关的话题硬扯到记忆
- 用"我记得你说过..."开场

### 正确的做法：
- 普通聊天就普通回应，不要刻意提记忆
- 只在真正相关时自然带一句
- 用户追问时才详细展开

## 回应风格
- 自然、简洁（50-100字）
- 像真实朋友一样自然
- 温暖而非说教
- 倾听而非评判
- 适当使用表情

## 边界意识
- 不扮演心理咨询师角色
- 不使用"你应该..."式的语气
- 涉及严重心理困扰时，温和建议寻求专业帮助
- 不刻意翻日记，只在相关时自然提及"""


def build_companion_messages(
    user_input: str,
    user_profile: Optional[Dict] = None,
    memories: Optional[List[Dict]] = None,
    conversation_history: Optional[List[Dict]] = None,
    emotion: Optional[str] = None,
    diary_id: Optional[int] = None,
) -> List[Dict[str, str]]:
    """
    组装情感陪伴场景的 OpenAI 格式消息列表

    Args:
        user_input: 用户当前输入
        user_profile: 用户画像摘要
        memories: 相关记忆列表
        conversation_history: 对话历史
        emotion: 情绪类型（用于情绪匹配）
        diary_id: 关联的日记 ID

    Returns:
        List[Dict]: 消息列表
    """
    messages = []

    # 1. 系统提示词
    system_content = COMPANION_SYSTEM
    if emotion:
        from app.services.ai.safety import SafetyFilter
        emotion_hint = SafetyFilter.get_emotion_template(emotion)
        if emotion_hint:
            system_content += f"\n\n## 当前用户情绪提示\n用户情绪类型为【{emotion}】，建议回应风格：{emotion_hint}"
    messages.append({"role": "system", "content": system_content})

    # 2. 上下文信息
    profile_section = _format_profile(user_profile or {})
    memories_section = _format_memories(memories or [])

    if profile_section or memories_section:
        context_parts = []
        if profile_section:
            context_parts.append(f"【用户信息】\n{profile_section}")
        if memories_section:
            context_parts.append(
                f"【相关记忆】（可选的背景知识，不要刻意引用）\n\n"
                f"以下是用户的历史日记，作为你的背景知识：\n{memories_section}\n\n"
                f"注意：这只是背景知识，不需要每次都引用。只在真正相关时自然提及。"
            )
        messages.append({"role": "system", "content": "\n\n".join(context_parts)})

    # 3. 如果关联了日记，注入日记上下文
    if diary_id and memories:
        diary_memory = next(
            (m for m in memories if m.get("source_diary_id") == diary_id), None
        )
        if diary_memory:
            messages.append(
                {
                    "role": "system",
                    "content": f"【当前关联日记】\n用户正在查看一篇日记：{diary_memory.get('text', '')[:300]}",
                }
            )

    # 4. 对话历史
    if conversation_history:
        for turn in conversation_history:
            messages.append(
                {
                    "role": turn.get("role", "user"),
                    "content": turn.get("content", ""),
                }
            )

    # 5. 当前用户输入
    messages.append({"role": "user", "content": user_input})

    return messages


def _format_profile(profile: Dict) -> str:
    """格式化用户画像"""
    parts = []
    if profile.get("nickname"):
        parts.append(f"昵称：{profile['nickname']}")
    if profile.get("current_mood"):
        parts.append(f"当前情绪：{profile['current_mood']}")
    if profile.get("top_topics"):
        topics = "、".join(profile["top_topics"])
        parts.append(f"常写主题：{topics}")
    if profile.get("life_themes"):
        themes = "、".join(profile["life_themes"][:3])
        parts.append(f"生活主题：{themes}")
    return "\n".join(parts) if parts else ""


def _format_memories(memories: List[Dict]) -> str:
    """格式化记忆为隐性提示"""
    if not memories:
        return ""

    items = []
    for i, memory in enumerate(memories[:5], 1):
        text = memory.get("text", "")
        if len(text) > 200:
            text = text[:200] + "..."

        date = memory.get("date", "")
        emotion = memory.get("emotion", "") or memory.get("metadata", {}).get("emotion", "")

        item_parts = [f"{i}. {text}"]
        if date:
            item_parts.append(f"（{date}）")
        if emotion:
            item_parts.append(f"[{emotion}]")

        items.append("".join(item_parts))

    return "\n".join(items)
