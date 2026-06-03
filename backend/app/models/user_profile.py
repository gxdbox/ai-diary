"""
用户画像模型 - 结构化长期记忆

参考：06-上下文管理技巧 - 结构化记忆系统
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class InteractionStyle(str, Enum):
    """交互风格偏好"""
    WARM = "warm"              # 温暖关怀型
    RATIONAL = "rational"      # 理性分析型
    PLAYFUL = "playful"        # 轻松幽默型
    DEEP = "deep"              # 深度探讨型


class EmotionalProfile(BaseModel):
    """情感画像"""

    # 情绪分布（过去30天）
    emotion_distribution: Dict[str, float] = Field(
        default_factory=lambda: {},
        description="情绪类型及其频率分布"
    )

    # 情绪触发因素
    stress_triggers: List[str] = Field(
        default_factory=list,
        description="压力触发因素"
    )
    joy_sources: List[str] = Field(
        default_factory=list,
        description="快乐来源"
    )

    # 应对机制
    coping_mechanisms: List[str] = Field(
        default_factory=list,
        description="常用的应对方式"
    )

    # 当前情绪状态
    current_mood: Optional[str] = Field(default=None, description="当前情绪类型")
    current_mood_intensity: float = Field(default=0.0, ge=0, le=1, description="情绪强度")

    # 情绪稳定性指标
    emotional_stability: float = Field(
        default=0.5, ge=0, le=1,
        description="情绪稳定性评分（0-1）"
    )


class WritingPreferences(BaseModel):
    """写作偏好"""

    # 常见写作主题
    common_topics: List[str] = Field(
        default_factory=list,
        description="常写的主题"
    )

    # 写作频率
    writing_frequency: str = Field(
        default="moderate",
        description="写作频率：daily/weekly/moderate/rare"
    )

    # 平均日记长度
    average_length: int = Field(default=200, description="平均字数")

    # 常用表达方式
    expression_style: List[str] = Field(
        default_factory=list,
        description="表达风格：poetic/direct/detailed/brief"
    )

    # 写作时间偏好
    preferred_time: Optional[str] = Field(
        default=None,
        description="偏好写作时间：morning/afternoon/evening/night"
    )


class KeyEvent(BaseModel):
    """关键事件"""

    date: datetime = Field(..., description="事件日期")
    event: str = Field(..., description="事件描述")
    emotion: str = Field(default="neutral", description="关联情绪")
    importance: float = Field(default=0.5, ge=0, le=1, description="重要性评分")

    # 事件状态
    resolution: Optional[str] = Field(default=None, description="事件结果/后续")
    is_ongoing: bool = Field(default=False, description="是否正在进行")

    # 关联日记ID
    diary_ids: List[int] = Field(default_factory=list, description="关联的日记ID")


class InteractionPreferences(BaseModel):
    """AI交互偏好"""

    # 交互风格
    preferred_style: InteractionStyle = Field(
        default=InteractionStyle.WARM,
        description="偏好交互风格"
    )

    # 回复长度偏好
    response_length: str = Field(
        default="moderate",
        description="回复长度：brief/moderate/detailed"
    )

    # 是否喜欢追问
    likes_follow_up: bool = Field(default=True, description="是否喜欢追问")

    # 是否喜欢建议
    wants_suggestions: bool = Field(default=True, description="是否需要建议")

    # 敏感话题
    sensitive_topics: List[str] = Field(
        default_factory=list,
        description="敏感话题（避免主动提及）"
    )


class UserProfile(BaseModel):
    """用户画像 - 完整结构"""

    # 基本信息
    user_id: int = Field(..., description="用户ID")
    nickname: Optional[str] = Field(default=None, description="昵称")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_active: datetime = Field(default_factory=datetime.now, description="最后活跃时间")

    # 情感特征
    emotional_profile: EmotionalProfile = Field(
        default_factory=EmotionalProfile,
        description="情感画像"
    )

    # 写作偏好
    writing_preferences: WritingPreferences = Field(
        default_factory=WritingPreferences,
        description="写作偏好"
    )

    # 生活主题
    life_themes: List[str] = Field(
        default_factory=list,
        description="生活主题标签"
    )

    # 重要事件时间线
    key_events: List[KeyEvent] = Field(
        default_factory=list,
        description="关键事件列表"
    )

    # AI交互偏好
    interaction_preferences: InteractionPreferences = Field(
        default_factory=InteractionPreferences,
        description="交互偏好"
    )

    # 自定义标签（用户自定义的记忆点）
    custom_tags: Dict[str, Any] = Field(
        default_factory=dict,
        description="用户自定义标签"
    )

    def to_context_string(self) -> str:
        """转换为用于上下文的字符串描述"""
        parts = []

        if self.nickname:
            parts.append(f"用户昵称：{self.nickname}")

        if self.emotional_profile.current_mood:
            parts.append(f"当前情绪：{self.emotional_profile.current_mood}")

        if self.writing_preferences.common_topics:
            topics = "、".join(self.writing_preferences.common_topics[:5])
            parts.append(f"常写主题：{topics}")

        if self.life_themes:
            themes = "、".join(self.life_themes[:3])
            parts.append(f"生活主题：{themes}")

        if self.emotional_profile.stress_triggers:
            triggers = "、".join(self.emotional_profile.stress_triggers[:3])
            parts.append(f"压力来源：{triggers}")

        if self.key_events:
            recent_events = [
                e for e in self.key_events
                if (datetime.now() - e.date).days <= 30
            ][:3]
            if recent_events:
                events_str = "；".join([
                    f"{e.event}（{e.date.strftime('%m-%d')}）"
                    for e in recent_events
                ])
                parts.append(f"近期重要事件：{events_str}")

        return "\n".join(parts) if parts else "新用户，暂无画像信息"

    def get_summary(self) -> Dict[str, Any]:
        """获取画像摘要"""
        return {
            "nickname": self.nickname,
            "current_mood": self.emotional_profile.current_mood,
            "mood_intensity": self.emotional_profile.current_mood_intensity,
            "top_topics": self.writing_preferences.common_topics[:3],
            "life_themes": self.life_themes[:3],
            "recent_events_count": len([
                e for e in self.key_events
                if (datetime.now() - e.date).days <= 30
            ]),
            "interaction_style": self.interaction_preferences.preferred_style.value
        }
