"""
主动检索服务 - 基于 ProactAgent 论文思想

核心创新：Agent 主动判断"什么时候需要检索记忆"
而不是被动地在固定时机检索

检索触发条件：
1. 当前内容与历史记忆可能相关（关键词匹配）
2. 情绪变化，可能需要相关记忆支持
3. 用户可能需要写作建议（内容较短或停滞）
"""
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import re
from sqlalchemy.orm import Session

from app.models.memory import (
    MemoryType, MemoryItem, RetrievalRequest,
    RetrievalResult, ProactiveRetrievalResponse
)
from app.services.memory_service import MemoryService


class ProactiveRetrievalService:
    """主动检索服务 - 决定什么时候检索、检索什么"""

    def __init__(self, db: Session):
        self.db = db
        self.memory_service = MemoryService(db)

        # 检索触发阈值
        self.RETRIEVAL_THRESHOLDS = {
            "keyword_match": 0.3,      # 关词匹配阈值
            "emotion_change": 0.5,     # 情绪变化阈值
            "similarity": 0.4          # 相似度阈值
        }

        # 常见触发关键词（用户写日记时可能提到的话题）
        self.TRIGGER_KEYWORDS = {
            "work": ["工作", "上班", "公司", "同事", "老板", "项目", "任务"],
            "family": ["家人", "父母", "孩子", "老婆", "老公", "家庭"],
            "health": ["健康", "生病", "医院", "身体", "运动", "锻炼"],
            "travel": ["旅游", "旅行", "出差", "飞机", "酒店", "景点"],
            "food": ["吃饭", "美食", "餐厅", "做饭", "菜", "吃"],
            "weather": ["天气", "下雨", "晴天", "冷", "热", "风"],
            "emotion": ["开心", "难过", "生气", "焦虑", "压力大", "心情"],
            "event": ["今天", "昨天", "周末", "生日", "节日", "纪念"]
        }

    def should_retrieve(self, current_context: str) -> Tuple[bool, Optional[str]]:
        """
        判断是否需要主动检索

        返回：(是否检索, 检索原因)
        """
        # 1. 检查关键词触发
        matched_keywords = self._find_trigger_keywords(current_context)
        if matched_keywords:
            return True, f"发现关键词：{matched_keywords[:3]}"

        # 2. 检查情绪词触发
        emotion_keywords = self._find_emotion_keywords(current_context)
        if emotion_keywords:
            return True, f"情绪相关：{emotion_keywords[:3]}"

        # 3. 有问题内容，需要检索相关记忆
        if len(current_context) > 0:
            return True, "用户提问，检索相关记忆"

        return False, None

    def retrieve(self, request: RetrievalRequest) -> ProactiveRetrievalResponse:
        """
        执行主动检索

        流程：
        1. 判断是否需要检索
        2. 如果需要，确定检索什么类型的记忆
        3. 执行检索
        4. 返回结果和建议
        """
        should_retrieve, trigger_reason = self.should_retrieve(request.current_context)

        if not should_retrieve:
            return ProactiveRetrievalResponse(
                should_retrieve=False,
                retrieval_trigger=None,
                results=[],
                suggestion=None
            )

        # 执行检索
        results = []

        # 1. 检索情节记忆（最相关的历史日记）
        keywords = self._extract_keywords(request.current_context)
        similar_episodes = self.memory_service.find_similar_episodic(
            keywords=keywords,
            limit=request.max_results
        )

        for episode in similar_episodes:
            relevance = self._calculate_relevance(request.current_context, episode.summary)
            if relevance >= request.min_importance:
                results.append(RetrievalResult(
                    memory=MemoryItem(
                        memory_type=MemoryType.EPISODIC,
                        content=episode.summary,
                        keywords=episode.retrieval_keys,
                        source_diary_id=episode.diary_id,
                        importance_score=relevance
                    ),
                    relevance_score=relevance,
                    retrieval_reason=f"相似的历史日记：{episode.emotion}情绪，主题：{episode.topics[:3]}"
                ))

        # 2. 检索事实记忆（用户偏好）
        if request.retrieval_type == MemoryType.FACTUAL or request.retrieval_type is None:
            factual = self.memory_service.get_factual_memory()
            if factual.common_topics:
                topic_relevance = self._check_topic_relevance(keywords, factual.common_topics)
                if topic_relevance > 0.3:
                    results.append(RetrievalResult(
                        memory=MemoryItem(
                            memory_type=MemoryType.FACTUAL,
                            content=f"你常写的主题：{factual.common_topics[:5]}",
                            keywords=factual.common_topics,
                            importance_score=topic_relevance
                        ),
                        relevance_score=topic_relevance,
                        retrieval_reason="你的写作偏好"
                    ))

        return ProactiveRetrievalResponse(
            should_retrieve=True,
            retrieval_trigger=trigger_reason,
            results=results[:request.max_results],
            suggestion=None
        )

    def _find_trigger_keywords(self, text: str) -> List[str]:
        """查找触发检索的关键词"""
        matched = []
        for category, keywords in self.TRIGGER_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    matched.append(kw)
        return matched

    def _find_emotion_keywords(self, text: str) -> List[str]:
        """查找情绪关键词"""
        emotion_keywords = self.TRIGGER_KEYWORDS.get("emotion", [])
        matched = [kw for kw in emotion_keywords if kw in text]
        return matched

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本提取关键词"""
        # 简化实现：提取中文词汇
        keywords = []

        # 1. 匹配触发关键词
        for category, kws in self.TRIGGER_KEYWORDS.items():
            for kw in kws:
                if kw in text:
                    keywords.append(kw)

        # 2. 提取人名、地名等（简化）
        # 匹配"和XX"、"去XX"等模式
        patterns = [
            r"和[^\s]{2,3}",
            r"去[^\s]{2,3}",
            r"在[^\s]{2,3}",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches[:3])

        return keywords[:10]

    def _calculate_relevance(self, text1: str, text2: str) -> float:
        """计算两段文本的相关性"""
        # 简化实现：关键词重叠度
        kw1 = set(self._extract_keywords(text1))
        kw2 = set(self._extract_keywords(text2))

        if not kw1 or not kw2:
            return 0.0

        overlap = len(kw1 & kw2)
        union = len(kw1 | kw2)

        return overlap / union if union > 0 else 0.0

    def _check_topic_relevance(self, current_keywords: List[str],
                               user_topics: List[str]) -> float:
        """检查当前主题与用户偏好主题的相关性"""
        current_set = set(current_keywords)
        user_set = set(user_topics)

        overlap = len(current_set & user_set)
        return overlap / max(len(current_set), 1)

    def learn_from_feedback(self, retrieval_id: int, was_helpful: bool):
        """
        从用户反馈学习

        如果检索结果有帮助，增加该记忆的重要性
        如果没有帮助，降低重要性

        这是 ProactAgent 的核心：通过反馈改进检索策略
        """
        delta = 0.15 if was_helpful else -0.1
        self.memory_service.update_importance(retrieval_id, delta)

        # 更新行为技能的成功率
        # 如果检索有帮助，说明当前的检索策略是有效的