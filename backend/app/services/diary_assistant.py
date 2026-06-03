"""
日记助手服务 - 基于 ProactAgent 论文思想

整合记忆系统和主动检索，提供智能问答辅助。
核心功能：
1. 从日记学习并存储记忆（后台异步）
2. 获取用户上下文（偏好、情绪模式）
3. 主动检索相关记忆用于问答
"""
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.memory import RetrievalRequest
from app.services.memory_service import MemoryService
from app.services.proactive_retrieval import ProactiveRetrievalService


class DiaryAssistantService:
    """智能日记助手服务"""

    def __init__(self, db: Session):
        self.db = db
        self.memory_service = MemoryService(db)
        self.retrieval_service = ProactiveRetrievalService(db)

    def learn_from_diary(self, diary_id: int, diary_data: Dict):
        """
        从新日记学习并更新记忆

        每次写完日记，系统自动提取并存储记忆
        """
        # 1. 提取并存储记忆
        self.memory_service.extract_from_diary(diary_data)

        # 2. 如果有情绪，更新情绪模式
        if diary_data.get("emotion"):
            self._update_emotion_pattern(diary_data["emotion"])

    def get_user_context(self) -> Dict:
        """
        获取用户完整上下文

        返回用户的偏好、常用主题、情绪分布
        """
        factual = self.memory_service.get_factual_memory()

        return {
            "preferences": factual.user_preferences,
            "common_topics": factual.common_topics[:10],
            "emotion_distribution": factual.emotional_patterns,
            "writing_habits": factual.writing_habits,
            "last_updated": factual.last_updated
        }

    def record_feedback(self, diary_id: int, memory_id: int, was_helpful: bool):
        """
        记录用户反馈并学习

        通过反馈改进检索策略
        """
        self.retrieval_service.learn_from_feedback(memory_id, was_helpful)

        if was_helpful:
            self.memory_service.update_importance(memory_id, delta=0.15)

    def _update_emotion_pattern(self, emotion: str):
        """更新情绪模式统计"""
        factual = self.memory_service.get_factual_memory()
        patterns = factual.emotional_patterns
        patterns[emotion] = patterns.get(emotion, 0) + 1

        self.memory_service.update_factual_memory(
            key="emotion_pattern",
            value=patterns
        )