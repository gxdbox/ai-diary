"""
深度洞察模型 - 帮助用户认识自己

四大分类：
1. 自我认知 🪞 - 天赋、性格、价值观、写作人格
2. 生活状态 🌿 - 情绪健康、生活平衡、人际关系
3. 风险预警 ⚠️ - 危机信号、方向偏差、能量黑洞
4. 成长激励 🌱 - 积极变化、希望方向、盲点提示

设计理念：日记的价值不在"囤积"，而在"提炼"——帮助用户真正认识自己
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class InsightCategory(str, Enum):
    """洞察分类枚举 - 用户视角的四大分类"""
    SELF_KNOWLEDGE = "self_knowledge"    # 自我认知 🪞
    LIFE_STATE = "life_state"            # 生活状态 🌿
    RISK_ALERT = "risk_alert"            # 风险预警 ⚠️
    GROWTH = "growth"                    # 成长激励 🌱


class InsightSubType(str, Enum):
    """洞察子类型"""
    # 自我认知
    TALENT = "talent"                    # 天赋识别
    WRITING_PERSONA = "writing_persona"  # 写作人格
    VALUE = "value"                      # 价值观
    CHARACTER = "character"              # 性格特点

    # 生活状态
    EMOTION_HEALTH = "emotion_health"    # 情绪健康
    LIFE_BALANCE = "life_balance"        # 生活平衡
    RELATIONSHIP = "relationship"        # 人际关系

    # 风险预警
    CRISIS_SIGNAL = "crisis_signal"      # 危机信号
    DIRECTION偏差 = "direction偏差"      # 方向偏差
    ENERGY黑洞 = "energy黑洞"            # 能量黑洞

    # 成长激励
    POSITIVE_CHANGE = "positive_change"  # 积极变化
    HOPE_DIRECTION = "hope_direction"    # 希望方向
    BLIND_SPOT = "blind_spot"            # 盲点提示

    # 原有类型（兼容）
    EMOTION = "emotion"                  # 情绪洞察
    TOPIC = "topic"                      # 主题洞察
    HABIT = "habit"                      # 习惯洞察


class SeverityLevel(str, Enum):
    """严重程度"""
    INFO = "info"        # 信息性，无风险
    WARNING = "warning"  # 警告，需要关注
    ALERT = "alert"      # 警报，需要行动


class DeepInsight(BaseModel):
    """单条深度洞察"""
    category: InsightCategory = Field(..., description="所属分类")
    sub_type: InsightSubType = Field(..., description="子类型")
    title: str = Field(..., description="洞察标题（简短，用于卡片标题）")
    insight: str = Field(..., description="洞察内容（完整描述）")
    evidence: List[str] = Field(default=[], description="数据支撑（来自日记的证据）")
    severity: SeverityLevel = Field(default=SeverityLevel.INFO, description="严重程度")
    suggestion: Optional[str] = Field(None, description="AI给出的建议")
    confidence: float = Field(default=0.7, ge=0, le=1, description="置信度")

    # 用于前端展示的额外信息
    icon: Optional[str] = Field(None, description="展示图标")
    trend: Optional[str] = Field(None, description="趋势方向：up/down/stable")


class InsightCategoryResult(BaseModel):
    """单个分类的洞察结果"""
    category: InsightCategory = Field(..., description="分类")
    category_name: str = Field(..., description="分类显示名称")
    category_icon: str = Field(..., description="分类图标")
    insights: List[DeepInsight] = Field(default=[], description="该分类下的洞察列表")
    highlight: Optional[str] = Field(None, description="该分类最重要的一条洞察摘要")


class DeepInsightResponse(BaseModel):
    """深度洞察API响应"""
    categories: List[InsightCategoryResult] = Field(default=[], description="四分类洞察结果")
    overall_summary: str = Field(..., description="整体洞察摘要（一句话概括）")
    stats_context: Dict[str, Any] = Field(default={}, description="统计背景数据")
    generated_at: str = Field(..., description="生成时间")
    analysis_period_days: int = Field(..., description="分析周期天数")


# ==================== 分析中间数据结构 ====================

class WritingTimeDistribution(BaseModel):
    """写作时间分布"""
    morning: int = Field(default=0, description="早晨6-12点")
    afternoon: int = Field(default=0, description="下午12-18点")
    evening: int = Field(default=0, description="晚上18-21点")
    night: int = Field(default=0, description="深夜21-24点")
    late_night: int = Field(default=0, description="凌晨0-6点")

    total: int = Field(default=0, description="总计")
    dominant_period: Optional[str] = Field(None, description="主导时间段")
    persona_name: Optional[str] = Field(None, description="人格名称")


class EmotionAnalysis(BaseModel):
    """情绪分析结果"""
    average_score: float = Field(default=0, description="平均情绪分")
    baseline_score: float = Field(default=0, description="历史baseline")
    deviation: float = Field(default=0, description="偏离baseline的程度")
    volatility: float = Field(default=0, description="波动性（标准差）")
    dominant_emotion: Optional[str] = Field(None, description="主导情绪")
    trend: Optional[str] = Field(None, description="趋势：improving/declining/stable")


class KeywordFrequency(BaseModel):
    """关键词频率分析"""
    keyword: str = Field(..., description="关键词")
    count: int = Field(default=0, description="出现次数")
    trend: str = Field(default="stable", description="趋势：rising/falling/stable")
    avg_emotion: float = Field(default=0, description="关联平均情绪")
    first_seen: Optional[str] = Field(None, description="首次出现日期")
    last_seen: Optional[str] = Field(None, description="最后出现日期")


class TopicDistribution(BaseModel):
    """话题分布"""
    topic: str = Field(..., description="话题")
    count: int = Field(default=0, description="出现次数")
    percentage: float = Field(default=0, description="占比")
    avg_emotion: float = Field(default=0, description="关联平均情绪")