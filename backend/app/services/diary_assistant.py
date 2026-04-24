"""
日记助手服务 - 基于 ProactAgent 论文思想

整合三种记忆和主动检索，提供智能日记辅助：
1. 根据当前内容主动检索相关记忆
2. 生成个性化写作建议
3. 提供相似历史日记参考
4. 预测情绪和主题
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.memory import (
    MemoryType, DiaryAssistRequest, DiaryAssistResponse,
    RetrievalResult, EpisodicMemory, ProactiveRetrievalResponse,
    RetrievalRequest
)
from app.models.diary import EmotionResult
from app.services.memory_service import MemoryService
from app.services.proactive_retrieval import ProactiveRetrievalService


class DiaryAssistantService:
    """智能日记助手服务 - ProactAgent 核心应用"""

    def __init__(self, db: Session):
        self.db = db
        self.memory_service = MemoryService(db)
        self.retrieval_service = ProactiveRetrievalService(db)

    def assist_writing(self, request: DiaryAssistRequest) -> DiaryAssistResponse:
        """
        智能辅助日记写作

        这是 ProactAgent 的核心应用场景：
        1. 分析当前内容
        2. 主动判断是否需要检索记忆
        3. 检索相关记忆和建议
        4. 返回个性化辅助信息
        """
        # 1. 执行主动检索
        retrieval_response = self.retrieval_service.retrieve(
            request=RetrievalRequest(
                current_context=request.current_text,
                max_results=5,
                min_importance=0.3
            )
        )

        # 2. 获取相关记忆
        relevant_memories = retrieval_response.results

        # 3. 获取相似历史日记
        similar_diaries = self._find_similar_diaries(request.current_text)

        # 4. 预测情绪
        emotion_prediction = self._predict_emotion(request.current_text)

        # 5. 生成主题建议
        topic_suggestions = self._suggest_topics(request.current_text)

        # 6. 生成写作建议
        suggestions = self._generate_writing_suggestions(
            current_text=request.current_text,
            relevant_memories=relevant_memories,
            emotion_prediction=emotion_prediction,
            topic_suggestions=topic_suggestions
        )

        return DiaryAssistResponse(
            relevant_memories=relevant_memories,
            suggestions=suggestions,
            similar_past_diaries=similar_diaries,
            emotion_prediction=emotion_prediction,
            topic_suggestions=topic_suggestions
        )

    def learn_from_diary(self, diary_id: int, diary_data: Dict):
        """
        从新日记学习并更新记忆

        这是 ProactAgent 的学习机制：
        - 每次写完日记，系统自动提取并存储记忆
        - 持续更新用户偏好、情绪模式、写作习惯
        """
        # 1. 提取并存储记忆
        self.memory_service.extract_from_diary(diary_data)

        # 2. 更新写作行为技能
        self._update_writing_skills(diary_data)

        # 3. 如果有情绪变化，更新情绪模式
        if diary_data.get("emotion"):
            self._update_emotion_pattern(diary_data["emotion"])

    def get_user_context(self) -> Dict:
        """
        获取用户完整上下文

        返回用户的偏好、习惯、常用主题等
        用于个性化服务
        """
        factual = self.memory_service.get_factual_memory()
        skills = self.memory_service.get_behavioral_skills()

        return {
            "preferences": factual.user_preferences,
            "common_topics": factual.common_topics[:10],
            "emotion_distribution": factual.emotional_patterns,
            "writing_habits": factual.writing_habits,
            "frequent_skills": [
                {"type": s.skill_type, "description": s.pattern_description}
                for s in skills[:5] if s.usage_count > 2
            ],
            "last_updated": factual.last_updated
        }

    def record_feedback(self, diary_id: int, memory_id: int, was_helpful: bool):
        """
        记录用户反馈并学习

        ProactAgent 的核心：通过反馈改进检索策略
        """
        self.retrieval_service.learn_from_feedback(memory_id, was_helpful)

        # 如果反馈是正面的，增加相关记忆类型的权重
        if was_helpful:
            self.memory_service.update_importance(memory_id, delta=0.15)

    def _find_similar_diaries(self, current_text: str) -> List[EpisodicMemory]:
        """查找相似的历史日记"""
        keywords = self.retrieval_service._extract_keywords(current_text)
        if not keywords:
            return []

        similar = self.memory_service.find_similar_episodic(keywords, limit=3)
        return similar

    def _predict_emotion(self, text: str) -> Optional[str]:
        """预测当前内容的情绪"""
        emotion_keywords = self.retrieval_service._find_emotion_keywords(text)

        if emotion_keywords:
            # 根据关键词映射到情绪类型
            emotion_map = {
                "开心": "happy", "高兴": "happy", "快乐": "happy",
                "难过": "sad", "伤心": "sad", "悲伤": "sad",
                "生气": "angry", "愤怒": "angry",
                "焦虑": "anxious", "担心": "anxious", "紧张": "anxious",
                "压力大": "stressed", "压力": "stressed",
                "平静": "neutral", "心情": "neutral"
            }

            for kw in emotion_keywords:
                if kw in emotion_map:
                    return emotion_map[kw]

        # 如果没有明显情绪词，根据用户历史情绪分布预测
        factual = self.memory_service.get_factual_memory()
        if factual.emotional_patterns:
            # 返回最常见的情绪
            most_common = max(
                factual.emotional_patterns.items(),
                key=lambda x: x[1]
            )
            return most_common[0]

        return "neutral"

    def _suggest_topics(self, text: str) -> List[str]:
        """建议写作主题"""
        suggestions = []

        # 1. 基于当前关键词扩展
        current_keywords = self.retrieval_service._extract_keywords(text)

        # 2. 基于用户常用主题
        factual = self.memory_service.get_factual_memory()
        user_topics = factual.common_topics

        # 3. 找出相关但未提及的主题
        for topic in user_topics[:5]:
            if topic not in current_keywords:
                suggestions.append(topic)

        # 4. 如果内容很短，提供通用建议
        if len(text) < 30:
            default_topics = [
                "今天的心情",
                "工作/学习进展",
                "与家人/朋友的互动",
                "健康与运动",
                "有趣的事情"
            ]
            suggestions.extend(default_topics[:3])

        return suggestions[:5]

    def _generate_writing_suggestions(
        self,
        current_text: str,
        relevant_memories: List[RetrievalResult],
        emotion_prediction: Optional[str],
        topic_suggestions: List[str]
    ) -> List[str]:
        """生成个性化写作建议"""
        suggestions = []

        # 1. 基于检索记忆的建议
        if relevant_memories:
            for memory in relevant_memories[:2]:
                if memory.memory.memory_type == MemoryType.EPISODIC:
                    suggestions.append(
                        f"之前你写过类似的内容，可以回忆当时的感受"
                    )
                elif memory.memory.memory_type == MemoryType.FACTUAL:
                    suggestions.append(
                        f"你常写的话题：{memory.memory.keywords[:3]}"
                    )

        # 2. 基于情绪的建议
        if emotion_prediction and emotion_prediction != "neutral":
            emotion_suggestions = {
                "happy": "可以记录让你开心的具体原因",
                "sad": "试着描述是什么让你感到难过",
                "anxious": "写下你在担心什么，有什么解决方案",
                "stressed": "记录压力来源，思考应对方法",
                "angry": "描述发生了什么，你的感受是什么"
            }
            if emotion_prediction in emotion_suggestions:
                suggestions.append(emotion_suggestions[emotion_prediction])

        # 3. 基于内容长度和停滞检测
        stagnation = self.retrieval_service._detect_stagnation(current_text)
        if stagnation:
            suggestions.append("试着换个角度，描述更多细节")

        if len(current_text) < 50 and current_text.strip():
            suggestions.append("可以继续写更多细节，比如人物、地点、感受")

        # 4. 基于行为技能的建议
        skills = self.memory_service.get_behavioral_skills()
        for skill in skills[:1]:
            if skill.usage_count > 3:
                suggestions.append(skill.pattern_description)

        return suggestions[:5]

    def _update_writing_skills(self, diary_data: Dict):
        """从日记提取写作行为技能"""
        cleaned_text = diary_data.get("cleaned_text", "")
        if not cleaned_text or len(cleaned_text) < 50:
            return

        # 检测写作模式
        patterns = self._detect_writing_patterns(cleaned_text)

        for pattern_type, pattern_desc in patterns:
            self.memory_service.update_behavioral_skill(
                skill_type=pattern_type,
                pattern=pattern_desc,
                example=cleaned_text[:100]
            )

    def _detect_writing_patterns(self, text: str) -> List[tuple]:
        """检测写作模式"""
        patterns = []

        # 检测时间记录习惯
        if "今天" in text or "早上" in text or "晚上" in text:
            patterns.append((
                "time_recording",
                "习惯按时间顺序记录事件"
            ))

        # 检测情绪描述习惯
        if "感到" in text or "觉得" in text or "心情" in text:
            patterns.append((
                "emotion_description",
                "习惯描述内心感受和情绪变化"
            ))

        # 检测事件描述习惯
        if "然后" in text or "接着" in text or "之后" in text:
            patterns.append((
                "event_sequence",
                "习惯按事件发展顺序描述"
            ))

        # 检测反思习惯
        if "反思" in text or "思考" in text or "总结" in text:
            patterns.append((
                "self_reflection",
                "习惯在日记中进行反思和总结"
            ))

        return patterns

    def _update_emotion_pattern(self, emotion: str):
        """更新情绪模式统计"""
        factual = self.memory_service.get_factual_memory()
        patterns = factual.emotional_patterns
        patterns[emotion] = patterns.get(emotion, 0) + 1

        self.memory_service.update_factual_memory(
            key="emotion_pattern",
            value=patterns
        )