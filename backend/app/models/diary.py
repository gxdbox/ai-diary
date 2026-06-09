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
    title: Optional[str] = None
    cleaned_text: Optional[str] = None
    emotion: Optional[str] = None
    emotion_score: Optional[float] = None  # 保留兼容，逐步废弃
    emotion_energy: Optional[float] = None  # 新增：情绪能量值(-10到+10)
    emotion_intensity: Optional[float] = None  # 新增：情绪强度(1-10)
    emotion_keywords: Optional[List[str]] = []
    secondary_emotions: Optional[List[str]] = []
    emotion_dimension: Optional[str] = None  # 保留兼容，逐步废弃
    emotion_confidence: Optional[float] = None
    topics: Optional[List[str]] = []
    key_events: Optional[List[str]] = []
    recording_duration: Optional[int] = None
    audio_url: Optional[str] = None
    word_count: int = 0
    weather: Optional[dict] = None
    images: Optional[List[str]] = []
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
    emotion: str = Field(..., description="主要情绪类型")
    secondary_emotions: List[str] = Field(default=[], description="次要情绪")
    dimension: Optional[str] = Field(None, description="情绪维度(兼容旧版)")
    score: Optional[float] = Field(None, ge=1, le=10, description="情绪强度(兼容旧版)")
    energy: float = Field(..., ge=-10, le=10, description="情绪能量值")
    intensity: float = Field(..., ge=1, le=10, description="情绪强度")
    keywords: List[str] = Field(default=[], description="情绪关键词")
    confidence: float = Field(default=0.8, ge=0, le=1, description="识别信心度")


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


class WeatherData(BaseModel):
    """天气数据"""
    temperature: int = Field(..., description="温度")
    weather: str = Field(..., description="天气类型")
    weather_icon: str = Field(..., description="天气图标代码")
    location: str = Field(..., description="城市")


class WeatherRequest(BaseModel):
    """天气更新请求"""
    diary_id: int = Field(..., description="日记ID")
    weather: WeatherData = Field(..., description="天气数据")


class ImageUploadResponse(BaseModel):
    """单张图片上传响应"""
    key: str = Field(..., description="OSS object key")
    url: str = Field(..., description="签名 URL（1小时有效）")
    size: int = Field(..., description="文件大小（字节）")


class ImageDeleteRequest(BaseModel):
    """删除图片请求"""
    diary_id: int = Field(..., description="日记ID")
    image_key: str = Field(..., description="OSS object key")


# ========== 虚拟世界相关模型 ==========

class CharacterResponse(BaseModel):
    """人物实体响应"""
    id: int
    name: str
    appearance_count: int
    avatar_color: str
    first_appearance: datetime
    last_appearance: datetime

    class Config:
        from_attributes = True


class RelationshipResponse(BaseModel):
    """人物关系响应"""
    id: int
    character_a_id: int
    character_b_id: int
    character_a_name: Optional[str] = None
    character_b_name: Optional[str] = None
    relationship_type: str
    strength: float
    last_interaction: Optional[datetime] = None

    class Config:
        from_attributes = True


class LocationResponse(BaseModel):
    """地点实体响应"""
    id: int
    name: str
    visit_count: int
    last_visit: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorldStatsResponse(BaseModel):
    """虚拟世界统计信息"""
    total_characters: int = 0
    total_relationships: int = 0
    total_locations: int = 0
    most_active_character: Optional[CharacterResponse] = None
    strongest_relationship: Optional[RelationshipResponse] = None