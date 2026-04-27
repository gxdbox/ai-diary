"""
结构化记忆模型 - 基于 ProactAgent 论文思想

两种记忆类型：
1. Factual Memory（事实记忆）：用户基本信息、偏好、习惯
2. Episodic Memory（情节记忆）：历史日记内容、事件记录
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    """记忆类型枚举"""
    FACTUAL = "factual"      # 事实记忆：用户信息、偏好
    EPISODIC = "episodic"    # 情节记忆：历史日记、事件


class MemoryItem(BaseModel):
    """记忆条目"""
    id: Optional[int] = None
    memory_type: MemoryType = Field(..., description="记忆类型")
    content: str = Field(..., description="记忆内容")
    keywords: List[str] = Field(default=[], description="关键词标签")
    source_diary_id: Optional[int] = Field(None, description="来源日记ID")
    importance_score: float = Field(default=0.5, ge=0, le=1, description="重要性评分")
    access_count: int = Field(default=0, description="被访问次数")
    last_accessed: Optional[datetime] = Field(None, description="最后访问时间")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # 元数据（根据记忆类型不同而不同）
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="额外元数据")


class FactualMemory(BaseModel):
    """事实记忆 - 用户基本信息"""
    user_preferences: Dict[str, Any] = Field(default={}, description="用户偏好")
    common_topics: List[str] = Field(default=[], description="常写主题")
    emotional_patterns: Dict[str, float] = Field(default={}, description="情绪分布")
    writing_habits: Dict[str, Any] = Field(default={}, description="写作习惯")
    last_updated: datetime = Field(default_factory=datetime.now)


class EpisodicMemory(BaseModel):
    """情节记忆 - 历史日记摘要"""
    memory_id: Optional[int] = Field(None, description="记忆ID（用于反馈）")
    diary_id: int = Field(..., description="日记ID")
    summary: str = Field(..., description="日记摘要")
    key_events: List[str] = Field(default=[], description="关键事件")
    emotion: str = Field(..., description="情绪类型")
    topics: List[str] = Field(default=[], description="主题标签")
    date: datetime = Field(..., description="日记日期")

    # 用于检索的关键信息
    retrieval_keys: List[str] = Field(default=[], description="检索关键词")


class RetrievalRequest(BaseModel):
    """主动检索请求"""
    current_context: str = Field(..., description="当前上下文（正在写的内容）")
    retrieval_type: Optional[MemoryType] = Field(None, description="指定检索类型，不指定则全类型检索")
    max_results: int = Field(default=5, ge=1, le=20, description="最大返回数量")
    min_importance: float = Field(default=0.3, ge=0, le=1, description="最小重要性阈值")


class RetrievalResult(BaseModel):
    """检索结果"""
    memory: MemoryItem
    relevance_score: float = Field(..., ge=0, le=1, description="相关性评分")
    retrieval_reason: str = Field(..., description="检索原因（为什么这条记忆相关）")


class ProactiveRetrievalResponse(BaseModel):
    """主动检索响应"""
    should_retrieve: bool = Field(..., description="是否需要检索")
    retrieval_trigger: Optional[str] = Field(None, description="检索触发原因")
    results: List[RetrievalResult] = Field(default=[], description="检索结果")
    suggestion: Optional[str] = Field(None, description="AI给出的建议")