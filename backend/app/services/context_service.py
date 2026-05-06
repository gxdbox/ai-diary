"""
上下文服务 - 整合多源信息构建完整对话上下文

参考：06-上下文管理技巧
核心功能：
1. 组装用户画像、记忆、对话历史
2. 智能裁剪上下文
3. 生成结构化 Prompt
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from app.models.context import (
    AssembledContext, ContextBudget, PromptContext,
    MemoryTier, Resolution
)
from app.models.user_profile import UserProfile, EmotionalProfile, WritingPreferences
from app.core import TimeDecayEngine, ContextAssembler


class ContextService:
    """
    上下文服务 - 管理 AI 对话的完整上下文

    职责：
    1. 获取用户画像
    2. 检索相关记忆
    3. 管理对话历史
    4. 组装完整上下文
    5. 智能裁剪
    """

    def __init__(self, db: Session, vector_store=None):
        self.db = db
        self.vector_store = vector_store
        self.time_decay = TimeDecayEngine()
        self.assembler = ContextAssembler(db, vector_store)

    def build_context(
        self,
        user_input: str,
        user_id: int = 1,
        conversation_history: List[Dict] = None,
        budget: ContextBudget = None
    ) -> AssembledContext:
        """
        构建完整对话上下文

        Args:
            user_input: 当前用户输入
            user_id: 用户ID
            conversation_history: 对话历史 [{role, content}]
            budget: 上下文预算配置

        Returns:
            AssembledContext: 组装后的上下文
        """
        if budget is None:
            budget = ContextBudget()

        if conversation_history is None:
            conversation_history = []

        # 1. 获取用户画像
        user_profile = self._get_user_profile(user_id)

        # 2. 检索相关记忆
        relevant_memories = self._retrieve_memories(
            query=user_input,
            top_k=budget.max_memories,
            min_importance=budget.min_importance_threshold
        )

        # 3. 裁剪对话历史
        trimmed_history = self._trim_conversation_history(
            history=conversation_history,
            max_turns=budget.max_conversation_turns
        )

        # 4. 构建上下文
        context = AssembledContext(
            user_profile=user_profile.get_summary() if user_profile else None,
            relevant_memories=relevant_memories,
            conversation_history=trimmed_history,
            current_input=user_input
        )

        # 5. 计算 token 估算
        context.total_tokens = self._estimate_tokens(context)

        return context

    def _get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """获取用户画像"""
        try:
            # 从记忆表获取事实记忆
            result = self.db.execute(text("""
                SELECT content, metadata FROM memories
                WHERE memory_type = 'factual'
                ORDER BY importance_score DESC
                LIMIT 10
            """))
            rows = result.fetchall()

            if not rows:
                return None

            # 解析用户画像
            emotional_profile = EmotionalProfile()
            writing_preferences = WritingPreferences()
            life_themes = []
            key_events = []

            for row in rows:
                metadata = json.loads(row[1]) if row[1] else {}
                content = row[0]

                # 解析情绪模式
                if "emotion_pattern" in metadata:
                    emotional_profile.emotion_distribution = metadata["emotion_pattern"]

                # 解析主题偏好
                if "topic_preference" in metadata:
                    for topic in metadata["topic_preference"]:
                        if topic not in writing_preferences.common_topics:
                            writing_preferences.common_topics.append(topic)

            return UserProfile(
                user_id=user_id,
                emotional_profile=emotional_profile,
                writing_preferences=writing_preferences,
                life_themes=life_themes,
                key_events=key_events
            )

        except Exception as e:
            print(f"获取用户画像失败: {e}")
            return None

    def _retrieve_memories(
        self,
        query: str,
        top_k: int = 5,
        min_importance: float = 0.3
    ) -> List[Dict]:
        """检索相关记忆"""
        memories = []

        # 1. 从向量数据库检索
        if self.vector_store:
            try:
                results = self.vector_store.search(query, n_results=top_k)
                for r in results:
                    importance = r.get('metadata', {}).get('importance', 0.5)
                    if importance >= min_importance:
                        memories.append({
                            'text': r.get('text', ''),
                            'score': r.get('score', 0),
                            'importance': importance,
                            'metadata': r.get('metadata', {})
                        })
            except Exception as e:
                print(f"向量检索失败: {e}")

        # 2. 从关系数据库检索情节记忆
        try:
            result = self.db.execute(text("""
                SELECT id, content, keywords, source_diary_id, importance_score,
                       metadata, created_at
                FROM memories
                WHERE memory_type = 'episodic'
                ORDER BY importance_score DESC, created_at DESC
                LIMIT :limit
            """), {"limit": top_k})

            rows = result.fetchall()
            for row in rows:
                created_at = row[6] if row[6] else datetime.now()
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)

                # 应用时间衰减计算有效重要性
                effective_importance = self.time_decay.calculate_effective_importance(
                    base_importance=row[4] or 0.5,
                    created_at=created_at,
                    access_count=0
                )

                if effective_importance >= min_importance:
                    memories.append({
                        'id': row[0],
                        'text': row[1],
                        'keywords': json.loads(row[2]) if row[2] else [],
                        'source_diary_id': row[3],
                        'importance': effective_importance,
                        'metadata': json.loads(row[5]) if row[5] else {}
                    })
        except Exception as e:
            print(f"记忆检索失败: {e}")

        # 按重要性排序
        memories.sort(key=lambda x: x.get('importance', 0), reverse=True)
        return memories[:top_k]

    def _trim_conversation_history(
        self,
        history: List[Dict],
        max_turns: int = 10
    ) -> List[Dict]:
        """裁剪对话历史"""
        if len(history) <= max_turns:
            return history

        # 保留最近的 N 轮
        return history[-max_turns:]

    def _estimate_tokens(self, context: AssembledContext) -> int:
        """估算 token 数量"""
        total_chars = len(context.current_input)

        if context.user_profile:
            total_chars += len(json.dumps(context.user_profile, ensure_ascii=False))

        for memory in context.relevant_memories:
            total_chars += len(memory.get('text', ''))

        for turn in context.conversation_history:
            total_chars += len(turn.get('content', ''))

        # 中文约 1.5 字/token
        return int(total_chars / 1.5)

    def build_prompt_context(
        self,
        context: AssembledContext,
        system_prompt: str = None
    ) -> PromptContext:
        """
        构建 Prompt 上下文

        遵循避免监控感原则：
        - 不直接复述记忆内容
        - 将记忆融入共情表达
        """
        # 用户画像部分
        profile_section = ""
        if context.user_profile:
            profile = context.user_profile
            if profile.get('top_topics'):
                topics = "、".join(profile['top_topics'])
                profile_section += f"用户常写主题：{topics}\n"
            if profile.get('current_mood'):
                profile_section += f"当前情绪：{profile['current_mood']}\n"

        # 记忆部分（隐性融入）
        memories_section = ""
        if context.relevant_memories:
            memory_hints = []
            for m in context.relevant_memories[:3]:
                # 提取记忆中的主题提示，而非直接内容
                keywords = m.get('keywords', [])
                if keywords:
                    memory_hints.append(f"相关主题：{', '.join(keywords[:3])}")
            if memory_hints:
                memories_section = "\n".join(memory_hints)

        # 对话历史部分
        conversation_section = ""
        if context.conversation_history:
            turns = []
            for turn in context.conversation_history[-5:]:
                role = "用户" if turn.get('role') == 'user' else "AI"
                content = turn.get('content', '')[:100]
                turns.append(f"{role}：{content}")
            conversation_section = "\n".join(turns)

        return PromptContext(
            system_prompt=system_prompt or self._get_default_system_prompt(),
            user_profile_section=profile_section,
            memories_section=memories_section,
            conversation_section=conversation_section,
            current_input=context.current_input
        )

    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        return """你是一个温暖、耐心的日记陪伴者。

## 核心原则
1. **隐性记忆**：将记忆融入共情表达，不直接说"我记得你说过..."
2. **模式推断**：用"你有时候..."替代"你上次说..."
3. **情境关联**：自然地将过去经历与当前状态连接
4. **尊重遗忘**：如果用户回避某话题，不要主动提起

## 回应风格
- 温暖而非说教
- 倾听而非评判
- 建议而非指令
- 陪伴而非替代"""
