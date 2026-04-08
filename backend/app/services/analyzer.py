"""
情绪和主题分析服务
"""
from typing import Dict, List, Optional
import logging
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class Analyzer:
    """分析器"""

    # 情绪类型映射
    EMOTION_CATEGORIES = {
        "positive": ["开心", "快乐", "兴奋", "满足", "感激", "希望", "幸福"],
        "negative": ["焦虑", "愤怒", "悲伤", "沮丧", "恐惧", "失望", "孤独"],
        "neutral": ["平静", "疲惫", "无聊", "困惑", "麻木"]
    }

    # 主题分类
    TOPIC_CATEGORIES = {
        "工作": ["工作", "加班", "会议", "项目", "同事", "老板", "任务", "deadline"],
        "生活": ["生活", "日常", "买菜", "做饭", "打扫", "家务"],
        "健康": ["健康", "运动", "健身", "跑步", "生病", "医院", "吃药"],
        "社交": ["朋友", "聚会", "约会", "聊天", "社交", "见面"],
        "家庭": ["家人", "父母", "孩子", "伴侣", "家庭", "亲情"],
        "学习": ["学习", "读书", "考试", "课程", "培训", "技能"],
        "娱乐": ["游戏", "电影", "音乐", "旅游", "娱乐", "爱好"],
        "情感": ["爱情", "感情", "喜欢", "爱", "恋爱", "分手"]
    }

    def categorize_emotion(self, emotion: str) -> str:
        """归类情绪类型"""
        for category, emotions in self.EMOTION_CATEGORIES.items():
            if emotion in emotions:
                return category
        return "neutral"

    def categorize_topics(self, topics: List[str]) -> Dict[str, List[str]]:
        """归类主题"""
        result = {}
        for topic in topics:
            for category, keywords in self.TOPIC_CATEGORIES.items():
                if any(kw in topic for kw in keywords):
                    if category not in result:
                        result[category] = []
                    result[category].append(topic)
                    break
        return result

    async def analyze(self, text: str) -> Dict:
        """完整分析文本"""
        try:
            # 使用AI服务进行分析
            analysis = await ai_service.full_analysis(text)

            # 补充分类信息
            if analysis.get("emotion"):
                analysis["emotion"]["category"] = self.categorize_emotion(
                    analysis["emotion"].get("emotion", "平静")
                )

            if analysis.get("topics"):
                analysis["topic_categories"] = self.categorize_topics(analysis["topics"])

            return analysis

        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            return {
                "emotion": {
                    "emotion": "平静",
                    "score": 5.0,
                    "keywords": [],
                    "category": "neutral"
                },
                "topics": [],
                "key_events": [],
                "topic_categories": {}
            }

    def get_emotion_summary(self, diaries: List[Dict]) -> Dict:
        """获取情绪统计摘要"""
        if not diaries:
            return {"average_score": 0, "distribution": {}, "trend": []}

        scores = [d.get("emotion_score", 5) for d in diaries if d.get("emotion_score")]
        emotions = [d.get("emotion", "平静") for d in diaries if d.get("emotion")]

        # 情绪分布
        distribution = {}
        for emotion in emotions:
            distribution[emotion] = distribution.get(emotion, 0) + 1

        return {
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "distribution": distribution,
            "total_count": len(diaries)
        }

    def get_topic_summary(self, diaries: List[Dict]) -> Dict:
        """获取主题统计摘要"""
        topic_count = {}

        for diary in diaries:
            topics = diary.get("topics", [])
            if isinstance(topics, str):
                import json
                try:
                    topics = json.loads(topics)
                except:
                    topics = []

            for topic in topics:
                topic_count[topic] = topic_count.get(topic, 0) + 1

        # 排序
        sorted_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)

        return {
            "top_topics": sorted_topics[:10],
            "total_topics": len(topic_count)
        }


# 全局分析器实例
analyzer = Analyzer()