"""
日记数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DiaryCreate(BaseModel):
    """创建日记请求"""
    raw_text: str = Field(..., description="原始语音转写文本")
    recording_duration: Optional[int] = Field(None, description="录音时长(秒)")


class DiaryResponse(BaseModel):
    """日记响应"""
    id: int
    raw_text: str
    cleaned_text: Optional[str] = None
    emotion: Optional[str] = None
    emotion_score: Optional[float] = None
    emotion_keywords: Optional[List[str]] = []
    topics: Optional[List[str]] = []
    key_events: Optional[List[str]] = []
    recording_duration: Optional[int] = None
    word_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiaryListResponse(BaseModel):
    """日记列表响应"""
    items: List[DiaryResponse]
    total: int
    page: int
    page_size: int


class CleanTextRequest(BaseModel):
    """文本清洗请求"""
    raw_text: str = Field(..., description="原始文本")


class CleanTextResponse(BaseModel):
    """文本清洗响应"""
    cleaned_text: str
    original_length: int
    cleaned_length: int


class AnalyzeRequest(BaseModel):
    """分析请求"""
    text: str = Field(..., description="待分析文本")


class EmotionResult(BaseModel):
    """情绪分析结果"""
    emotion: str = Field(..., description="情绪类型")
    score: float = Field(..., ge=1, le=10, description="情绪强度")
    keywords: List[str] = Field(default=[], description="情绪关键词")


class AnalyzeResponse(BaseModel):
    """分析响应"""
    emotion: EmotionResult
    topics: List[str] = Field(default=[], description="主题标签")
    key_events: List[str] = Field(default=[], description="关键事件")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")


class SearchResult(BaseModel):
    """搜索结果"""
    id: int
    text: str
    score: float
    created_at: datetime


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]
    query: str
    total: int