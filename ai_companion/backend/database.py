# AI伴侣 - 数据库模块

import sqlite3
import json
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

DB_PATH = "data/ai_companion.db"


@contextmanager
def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        # 反馈表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                rating INTEGER NOT NULL,
                feedback_type TEXT,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        conn.commit()


class ConversationDB:
    """对话历史管理"""

    @staticmethod
    def save_conversation(
        user_input: str,
        ai_response: str,
        diary_id: Optional[int] = None,
        emotion_before: Optional[str] = None
    ) -> int:
        """保存对话记录"""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (diary_id, user_input, ai_response, emotion_before, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (diary_id, user_input, ai_response, emotion_before, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def get_recent_conversations(limit: int = 5) -> List[dict]:
        """获取最近的对话历史"""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT user_input, ai_response, created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_conversation_by_id(conv_id: int) -> Optional[dict]:
        """获取单条对话"""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conv_id,)
            ).fetchone()
            return dict(row) if row else None


class FeedbackDB:
    """用户反馈管理"""

    @staticmethod
    def save_feedback(
        conversation_id: Optional[int],
        rating: int,
        feedback_type: Optional[str] = None,
        comment: Optional[str] = None
    ) -> int:
        """保存用户反馈"""
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO feedbacks (conversation_id, rating, feedback_type, comment, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, rating, feedback_type, comment, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def get_feedback_stats() -> dict:
        """获取反馈统计"""
        with get_db() as conn:
            # 平均评分
            avg_rating = conn.execute(
                "SELECT AVG(rating) as avg FROM feedbacks"
            ).fetchone()["avg"] or 0

            # 反馈类型分布
            type_dist = conn.execute(
                """
                SELECT feedback_type, COUNT(*) as count
                FROM feedbacks
                WHERE feedback_type IS NOT NULL
                GROUP BY feedback_type
                """
            ).fetchall()

            # 最近反馈
            recent = conn.execute(
                """
                SELECT f.*, c.user_input, c.ai_response
                FROM feedbacks f
                LEFT JOIN conversations c ON f.conversation_id = c.id
                ORDER BY f.created_at DESC
                LIMIT 10
                """
            ).fetchall()

            return {
                "average_rating": round(avg_rating, 2),
                "total_feedbacks": len(recent),
                "type_distribution": {r["feedback_type"]: r["count"] for r in type_dist},
                "recent_feedbacks": [dict(r) for r in recent]
            }


# 初始化数据库
init_db()