"""
Prompt 模板 - 避免监控感的情感对话模板

参考：06-上下文管理技巧 第五章
核心原则：
1. 隐性记忆表达 - 不直接复述用户说过的话
2. 模式推断 - 用"你有时候..."替代"你上次说..."
3. 情境化共情 - 将记忆融入关怀表达
4. 尊重遗忘 - 用户回避的话题不主动提起
"""
from typing import List, Dict, Optional
from string import Template


# ============================================================
# 系统提示词模板
# ============================================================

DIARY_COMPANION_SYSTEM = """你是一个温暖、耐心的日记陪伴者。

## 核心身份
你陪伴用户记录生活、理解情绪、发现生活中的美好。你不是心理咨询师，而是用户的朋友和倾听者。

## 如何使用记忆信息

当系统提供【相关记忆】时，这些是用户的历史日记内容。你应该：
1. **优先基于记忆内容回答用户问题** - 如果用户问"最近开心的事"，而记忆里有相关内容，直接回答
2. **不要用开场白敷衍** - 如"听到你想分享..."、"愿意和我分享吗..."
3. **自然融入记忆** - 比如"厂房租出去了，那天你提到等了一个多月..."

## 记忆表达原则（重要！）
⚠️ 绝对禁止：
- ❌ "我记得你上周说..."
- ❌ "你之前提到过..."
- ✅ 直接基于内容回答，自然融入

## 正确的回应方式

用户问"最近开心的事"：
- ✅ "厂房终于租出去了，那天你说等了一个多月，签合同时还有点忐忑，真好！"
- ✅ "你提到和孩子们一起包馄饨，虽然任务乏味但孩子们参与让过程有趣了"

用户追问细节：
- ✅ 自然继续，如"那天是5月5日，你说终于签了合同"

## 回应风格
- 温暖而非说教
- 倾听而非评判
- 直接回答而非反问
- 陪伴而非替代

## 边界意识
- 不扮演心理咨询师角色
- 涉及严重心理困扰时，温和建议寻求专业帮助"""


# ============================================================
# 上下文组装模板
# ============================================================

CONTEXT_TEMPLATE = Template("""【用户信息】
$profile_section

【相关记忆提示】
（注意：将以下记忆隐性地融入回应，不要直接复述）
$memories_section

【近期对话】
$conversation_section""")

# ============================================================
# 用户画像格式化
# ============================================================

def format_user_profile(profile: Dict) -> str:
    """格式化用户画像为自然语言"""
    parts = []

    if profile.get('nickname'):
        parts.append(f"昵称：{profile['nickname']}")

    if profile.get('current_mood'):
        mood = profile['current_mood']
        intensity = profile.get('mood_intensity', 0.5)
        if intensity > 0.7:
            parts.append(f"当前情绪较为{mood}")
        else:
            parts.append(f"情绪状态：{mood}")

    if profile.get('top_topics'):
        topics = "、".join(profile['top_topics'])
        parts.append(f"常写主题：{topics}")

    if profile.get('life_themes'):
        themes = "、".join(profile['life_themes'][:3])
        parts.append(f"生活主题：{themes}")

    return "\n".join(parts) if parts else "新用户"


# ============================================================
# 记忆格式化（隐性融入）
# ============================================================

def format_memories_implicit(memories: List[Dict]) -> str:
    """
    格式化记忆为隐性提示

    核心原则：
    - 传递记忆内容让AI知道用户经历过什么
    - 但提示AI不要用"我记得你说过..."的方式复述
    - 而是以自然的方式融入回答中
    """
    if not memories:
        return ""

    items = []
    for i, memory in enumerate(memories[:5], 1):
        text = memory.get('text', '')
        if len(text) > 200:
            text = text[:200] + "..."

        # 提取日期和情绪信息
        date = memory.get('date', '')
        emotion = memory.get('emotion', '') or memory.get('metadata', {}).get('emotion', '')

        item_parts = [f"{i}. {text}"]
        if date:
            item_parts.append(f"（{date}）")
        if emotion:
            item_parts.append(f"[{emotion}]")

        items.append("".join(item_parts))

    return "\n".join(items)


def format_memories_explicit(memories: List[Dict]) -> str:
    """
    格式化记忆为显式内容（用于调试或用户主动查看）

    注意：这是给用户查看的，不是给AI使用的
    """
    items = []
    for m in memories[:5]:
        text = m.get('text', '')
        if len(text) > 100:
            text = text[:100] + "..."
        importance = m.get('importance', 0.5)
        items.append(f"- {text}（重要性：{importance:.2f}）")

    return "\n".join(items) if items else "暂无相关记忆"


# ============================================================
# 对话历史格式化
# ============================================================

def format_conversation_history(history: List[Dict], max_turns: int = 5) -> str:
    """格式化对话历史"""
    if not history:
        return ""

    turns = []
    for turn in history[-max_turns:]:
        role = "用户" if turn.get('role') == 'user' else "AI"
        content = turn.get('content', '')
        if len(content) > 150:
            content = content[:150] + "..."
        turns.append(f"{role}：{content}")

    return "\n".join(turns)


# ============================================================
# 完整 Prompt 组装
# ============================================================

def build_diary_prompt(
    user_input: str,
    user_profile: Dict = None,
    memories: List[Dict] = None,
    conversation_history: List[Dict] = None,
    system_prompt: str = None
) -> str:
    """
    组装完整的日记对话 Prompt

    Args:
        user_input: 用户当前输入
        user_profile: 用户画像摘要
        memories: 相关记忆列表
        conversation_history: 对话历史
        system_prompt: 自定义系统提示词

    Returns:
        str: 完整的 Prompt 字符串
    """
    # 上下文部分
    profile_section = format_user_profile(user_profile or {})
    memories_section = format_memories_implicit(memories or [])
    conversation_section = format_conversation_history(conversation_history or [])

    context = CONTEXT_TEMPLATE.substitute(
        profile_section=profile_section,
        memories_section=memories_section,
        conversation_section=conversation_section
    )

    # 组装完整 Prompt
    full_prompt = f"""{system_prompt or DIARY_COMPANION_SYSTEM}

{context}

用户：{user_input}
AI："""

    return full_prompt


def build_messages_prompt(
    user_input: str,
    user_profile: Dict = None,
    memories: List[Dict] = None,
    conversation_history: List[Dict] = None,
    system_prompt: str = None
) -> List[Dict[str, str]]:
    """
    组装 OpenAI 格式的消息列表

    Returns:
        List[Dict]: 消息列表
    """
    messages = []

    # 系统消息
    messages.append({
        "role": "system",
        "content": system_prompt or DIARY_COMPANION_SYSTEM
    })

    # 上下文信息作为系统消息
    profile_section = format_user_profile(user_profile or {})
    memories_section = format_memories_implicit(memories or [])

    if profile_section or memories_section:
        context_parts = []
        if profile_section:
            context_parts.append(f"【用户信息】\n{profile_section}")
        if memories_section:
            context_parts.append(f"【相关记忆】\n{memories_section}")

        messages.append({
            "role": "system",
            "content": "\n\n".join(context_parts)
        })

    # 对话历史
    if conversation_history:
        for turn in conversation_history:
            messages.append({
                "role": turn.get('role', 'user'),
                "content": turn.get('content', '')
            })

    # 当前用户输入
    messages.append({
        "role": "user",
        "content": user_input
    })

    return messages


# ============================================================
# 特定场景模板
# ============================================================

# 用户分享喜悦时
JOY_RESPONSE_HINTS = """
- 分享用户的快乐
- 肯定用户的努力和成就
- 可以轻描淡写地提及相关背景（如"这次考试准备得辛苦了"）
- 不必过度强调过去的困难
"""

# 用户表达困扰时
CONCERN_RESPONSE_HINTS = """
- 表达理解和共情
- 不急于给建议，先倾听
- 可以隐性地提及用户的应对方式（如"你有时候会用运动来调节心情"）
- 温和地询问是否需要帮助
"""

# 用户回避话题时
AVOID_TOPIC_HINTS = """
- 敏感地察觉用户的回避
- 不要追问
- 自然地转移到用户愿意谈的话题
- 记住这个话题是敏感的
"""
