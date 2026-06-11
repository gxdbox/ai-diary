"""
上下文数据模型 - 用于组装完整的对话上下文

参考：06-上下文管理技巧
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class MemoryTier(str, Enum):
    """记忆层级"""
    SHORT_TERM = "short_term"    # 短期记忆：当前会话
    MID_TERM = "mid_term"        # 中期记忆：7天内
    LONG_TERM = "long_term"      # 长期记忆：永久


class Resolution(str, Enum):
    """记忆分辨率"""
    HIGH = "high"        # 高分辨率：完整内容
    MEDIUM = "medium"    # 中分辨率：部分压缩
    LOW = "low"          # 低分辨率：摘要
    MINIMAL = "minimal"  # 最小分辨率：关键词


class AssembledContext(BaseModel):
    """组装后的完整上下文"""

    # 用户画像
    user_profile: Optional[Dict[str, Any]] = Field(default=None, description="用户画像摘要")

    # 相关记忆
    relevant_memories: List[Dict[str, Any]] = Field(
        default=[],
        description="检索到的相关记忆（已按重要性排序）"
    )

    # 对话历史
    conversation_history: List[Dict[str, str]] = Field(
        default=[],
        description="对话历史（用户输入和AI回复）"
    )

    # 早期对话摘要（当历史过长时）
    conversation_summary: Optional[str] = Field(
        default=None,
        description="早期对话的摘要"
    )

    # 当前输入
    current_input: str = Field(..., description="当前用户输入")

    # 情绪分析结果
    emotion_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="当前输入的情绪分析结果"
    )

    # 元数据
    total_tokens: int = Field(default=0, description="总token数")
    memory_tier_used: List[MemoryTier] = Field(default=[], description="使用的记忆层级")

    class Config:
        use_enum_values = True


class ConversationTurn(BaseModel):
    """单轮对话"""
    role: str = Field(..., description="角色：user 或 assistant")
    content: str = Field(..., description="对话内容")
    timestamp: datetime = Field(default_factory=datetime.now)
    emotion: Optional[str] = Field(default=None, description="情绪标签")
    importance: float = Field(default=0.5, description="重要性评分")


class ContextBudget(BaseModel):
    """上下文预算配置"""

    # 总token限制
    max_total_tokens: int = Field(default=4096, description="总token限制")

    # 各部分预算分配
    system_prompt_budget: int = Field(default=500, description="系统提示词预算")
    user_profile_budget: int = Field(default=300, description="用户画像预算")
    memories_budget: int = Field(default=800, description="记忆检索预算")
    conversation_budget: int = Field(default=1500, description="对话历史预算")
    current_input_budget: int = Field(default=500, description="当前输入预算")

    # 检索配置
    max_memories: int = Field(default=5, description="最多返回记忆数")
    max_conversation_turns: int = Field(default=10, description="最多对话轮数")
    min_importance_threshold: float = Field(default=0.3, description="最小重要性阈值")


class PromptContext(BaseModel):
    """用于组装 Prompt 的上下文"""

    system_prompt: str = Field(..., description="系统提示词")

    user_profile_section: str = Field(default="", description="用户画像部分")

    memories_section: str = Field(default="", description="相关记忆部分")

    conversation_section: str = Field(default="", description="对话历史部分")

    current_input: str = Field(..., description="当前输入")

    def to_messages(self) -> List[Dict[str, str]]:
        """转换为 OpenAI 格式的消息列表"""
        messages = [{"role": "system", "content": self.system_prompt}]

        # 添加用户画像和记忆作为系统上下文
        context_parts = []
        if self.user_profile_section:
            context_parts.append(self.user_profile_section)
        if self.memories_section:
            context_parts.append(self.memories_section)

        if context_parts:
            context_msg = "\n\n".join(context_parts)
            messages.append({"role": "system", "content": f"【上下文信息】\n{context_msg}"})

        # 添加对话历史
        if self.conversation_section:
            messages.append({"role": "system", "content": f"【对话历史】\n{self.conversation_section}"})

        # 添加当前输入
        messages.append({"role": "user", "content": self.current_input})

        return messages

    def to_single_prompt(self) -> str:
        """转换为单个 Prompt 字符串"""
        sections = [self.system_prompt]

        if self.user_profile_section:
            sections.append(f"\n【用户信息】\n{self.user_profile_section}")
        if self.memories_section:
            sections.append(f"\n【相关记忆】\n{self.memories_section}")
        if self.conversation_section:
            sections.append(f"\n【对话历史】\n{self.conversation_section}")

        sections.append(f"\n用户：{self.current_input}")

        return "\n".join(sections)
