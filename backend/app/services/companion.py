"""
情感陪伴服务 — 融合 ai_companion 能力到统一架构

与 DiaryAssistantService 的区别：
- DiaryAssistantService: 日记内容问答（信息检索导向）
- CompanionService: 情感陪伴对话（情感支持导向）

共享：记忆系统、上下文服务、LLM 客户端
差异：Prompt 策略、安全过滤、回应风格
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.ai.client import llm
from app.services.ai.safety import SafetyFilter
from app.services.ai.prompts.companion import build_companion_messages
from app.services.context_service import ContextService
from app.services.vector_store import vector_store
from app.models.context import ContextBudget

logger = logging.getLogger(__name__)


class CompanionService:
    """情感陪伴服务"""

    def __init__(self, db: Session):
        self.db = db
        self.context_service = ContextService(db, vector_store)
        self.safety = SafetyFilter()

    async def chat(
        self,
        user_input: str,
        user_id: int = 1,
        conversation_history: Optional[List[Dict]] = None,
        diary_id: Optional[int] = None,
    ) -> Dict:
        """
        情感陪伴对话

        Args:
            user_input: 用户输入
            user_id: 用户 ID
            conversation_history: 对话历史 [{role, content}]
            diary_id: 可选：关联某篇日记

        Returns:
            Dict: {response, conversation_id, safe, ...}
        """
        # 1. 安全检查
        is_safe, warning = self.safety.check(user_input)
        if not is_safe:
            conv_id = self._save_conversation(
                user_id, user_input, warning, "companion"
            )
            return {
                "response": warning,
                "conversation_id": conv_id,
                "safe": False,
            }

        # 2. 获取情绪类型（如果关联日记，从日记获取）
        emotion = None
        if diary_id:
            emotion = self._get_diary_emotion(diary_id)

        # 3. 构建上下文（复用 ContextService）
        context = self.context_service.build_context(
            user_input=user_input,
            user_id=user_id,
            conversation_history=conversation_history or [],
            budget=ContextBudget(),
        )

        # 4. 构建 Prompt（情感陪伴专用）
        messages = build_companion_messages(
            user_input=user_input,
            user_profile=context.user_profile,
            memories=context.relevant_memories,
            conversation_history=conversation_history or [],
            emotion=emotion,
            diary_id=diary_id,
        )

        # 5. 调用 LLM
        response_text = await llm.chat(
            messages, max_tokens=500, temperature=0.7
        )

        # 6. 保存对话记录
        conv_id = self._save_conversation(
            user_id, user_input, response_text, "companion", diary_id, emotion
        )

        return {
            "response": response_text,
            "conversation_id": conv_id,
            "safe": True,
            "emotion_detected": emotion,
        }

    def get_conversation_history(
        self, user_id: int = 1, limit: int = 10, mode: Optional[str] = None
    ) -> List[Dict]:
        """
        获取对话历史

        Args:
            user_id: 用户 ID
            limit: 返回数量
            mode: 过滤模式 (companion/assistant/None=全部)

        Returns:
            List[Dict]: 对话历史列表
        """
        try:
            if mode:
                result = self.db.execute(
                    text("""
                        SELECT id, user_input, ai_response, mode, emotion_before, created_at
                        FROM conversations
                        WHERE user_id = :user_id AND mode = :mode
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "mode": mode, "limit": limit},
                )
            else:
                result = self.db.execute(
                    text("""
                        SELECT id, user_input, ai_response, mode, emotion_before, created_at
                        FROM conversations
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "limit": limit},
                )

            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "user_input": row[1],
                    "ai_response": row[2],
                    "mode": row[3],
                    "emotion_before": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                }
                for row in reversed(rows)
            ]
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    def _save_conversation(
        self,
        user_id: int,
        user_input: str,
        ai_response: str,
        mode: str = "companion",
        diary_id: Optional[int] = None,
        emotion: Optional[str] = None,
    ) -> int:
        """保存对话记录"""
        try:
            result = self.db.execute(
                text("""
                    INSERT INTO conversations
                    (user_id, diary_id, user_input, ai_response, mode, emotion_before, created_at)
                    VALUES (:user_id, :diary_id, :user_input, :ai_response, :mode, :emotion, :created_at)
                """),
                {
                    "user_id": user_id,
                    "diary_id": diary_id,
                    "user_input": user_input,
                    "ai_response": ai_response,
                    "mode": mode,
                    "emotion": emotion,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            self.db.commit()
            return result.lastrowid
        except Exception as e:
            logger.error(f"保存对话记录失败: {e}")
            self.db.rollback()
            return -1

    def _get_diary_emotion(self, diary_id: int) -> Optional[str]:
        """从日记获取情绪标签"""
        try:
            from app.db.database import Diary

            result = self.db.execute(
                text("SELECT emotion FROM diaries WHERE id = :id"),
                {"id": diary_id},
            )
            row = result.fetchone()
            if row and row[0]:
                from app.services.ai.safety import SafetyFilter

                return SafetyFilter.detect_emotion_type(row[0])
        except Exception as e:
            logger.error(f"获取日记情绪失败: {e}")
        return None
