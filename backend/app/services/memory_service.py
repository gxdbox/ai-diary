"""
记忆服务 - 基于 ProactAgent 论文思想

管理两种结构化记忆：
1. Factual Memory（事实记忆）
2. Episodic Memory（情节记忆）
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.memory import (
    MemoryType, MemoryItem, FactualMemory,
    EpisodicMemory
)


class MemoryService:
    """结构化记忆管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self._init_memory_tables()

    def _init_memory_tables(self):
        """初始化记忆相关表"""
        # 检查并创建记忆表（如果不存在）
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT DEFAULT '[]',
                    source_diary_id INTEGER,
                    importance_score REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    metadata TEXT DEFAULT '{}',
                    user_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # 安全迁移：为旧表添加 user_id 列
            try:
                self.db.execute(text("ALTER TABLE memories ADD COLUMN user_id INTEGER"))
            except Exception:
                pass  # 列已存在
            self.db.commit()
        except Exception as e:
            print(f"Memory table init error: {e}")

    # ==================== 事实记忆 ====================

    def get_factual_memory(self, user_id: Optional[int] = None) -> FactualMemory:
        """获取用户事实记忆（偏好、习惯等）"""
        memories = self._get_memories_by_type(MemoryType.FACTUAL, user_id=user_id)

        if not memories:
            return FactualMemory()

        # 汇总所有事实记忆
        preferences = {}
        common_topics = []
        emotional_patterns = {}
        writing_habits = {}

        for m in memories:
            # 解析 metadata JSON
            metadata = json.loads(m["metadata"]) if m["metadata"] else {}
            keywords = json.loads(m["keywords"]) if m["keywords"] else []

            if metadata:
                if "preference" in metadata:
                    preferences.update(metadata["preference"])
                if "emotion_pattern" in metadata:
                    emotional_patterns.update(metadata["emotion_pattern"])
                if "writing_habit" in metadata:
                    writing_habits.update(metadata["writing_habit"])
                # 兼容 topic_preference 格式
                if "topic_preference" in metadata:
                    for topic in metadata["topic_preference"]:
                        common_topics.append(topic)

            if keywords:
                common_topics.extend(keywords)

        return FactualMemory(
            user_preferences=preferences,
            common_topics=list(set(common_topics)),
            emotional_patterns=emotional_patterns,
            writing_habits=writing_habits,
            last_updated=datetime.now()
        )

    def update_factual_memory(self, key: str, value: Any, source_diary_id: Optional[int] = None, user_id: Optional[int] = None):
        """更新事实记忆"""
        existing = self._find_factual_memory_by_key(key, user_id=user_id)

        if existing:
            # 更新现有记忆
            metadata = json.loads(existing["metadata"]) if existing["metadata"] else {}
            metadata[key] = value
            self.db.execute(text("""
                UPDATE memories
                SET metadata = :metadata, updated_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE id = :id
            """), {"metadata": json.dumps(metadata), "id": existing["id"]})
        else:
            # 创建新记忆
            self.db.execute(text("""
                INSERT INTO memories (memory_type, content, keywords, source_diary_id, metadata, importance_score, user_id)
                VALUES ('factual', :content, '[]', :source_id, :metadata, 0.7, :user_id)
            """), {
                "content": f"{key}: {str(value)}",
                "source_id": source_diary_id,
                "metadata": json.dumps({key: value}),
                "user_id": user_id
            })

        self.db.commit()

    def _find_factual_memory_by_key(self, key: str, user_id: Optional[int] = None) -> Optional[Dict]:
        """查找包含特定key的事实记忆"""
        query = "SELECT * FROM memories WHERE memory_type = 'factual' AND content LIKE :key_pattern"
        params = {"key_pattern": f"{key}:%"}
        if user_id is not None:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        query += " LIMIT 1"
        result = self.db.execute(text(query), params)
        row = result.fetchone()
        return dict(row) if row else None

    # ==================== 情节记忆 ====================

    def get_episodic_memories(self, limit: int = 50, user_id: Optional[int] = None) -> List[EpisodicMemory]:
        """获取情节记忆（历史日记摘要）"""
        memories = self._get_memories_by_type(MemoryType.EPISODIC, limit, user_id=user_id)

        episodic_list = []
        for m in memories:
            metadata = json.loads(m["metadata"]) if m["metadata"] else {}
            keywords = json.loads(m["keywords"]) if m["keywords"] else []
            episodic_list.append(EpisodicMemory(
                memory_id=m["id"],
                diary_id=m["source_diary_id"] or 0,
                summary=m["content"],
                key_events=metadata.get("key_events", []),
                emotion=metadata.get("emotion", "neutral"),
                topics=keywords,
                date=datetime.fromisoformat(m["created_at"]) if m["created_at"] else datetime.now(),
                retrieval_keys=metadata.get("retrieval_keys", [])
            ))

        return episodic_list

    def create_episodic_memory(self, diary_id: int, summary: str,
                               key_events: List[str], emotion: str,
                               topics: List[str], user_id: Optional[int] = None):
        """从日记创建情节记忆"""
        # 生成检索关键词
        retrieval_keys = topics + key_events[:3]

        metadata = {
            "key_events": key_events,
            "emotion": emotion,
            "retrieval_keys": retrieval_keys
        }

        self.db.execute(text("""
            INSERT INTO memories (memory_type, content, keywords, source_diary_id, metadata, importance_score, user_id)
            VALUES ('episodic', :summary, :topics, :diary_id, :metadata, 0.6, :user_id)
        """), {
            "summary": summary,
            "topics": json.dumps(topics),
            "diary_id": diary_id,
            "metadata": json.dumps(metadata),
            "user_id": user_id
        })
        self.db.commit()

    def find_similar_episodic(self, keywords: List[str], limit: int = 5, user_id: Optional[int] = None) -> List[EpisodicMemory]:
        """查找相似的情节记忆"""
        user_filter = " AND user_id = :user_id" if user_id is not None else ""
        user_params = {"user_id": user_id} if user_id is not None else {}
        if not keywords:
            # 如果关键词为空，返回最新的几条记忆
            result = self.db.execute(text(f"""
                SELECT * FROM memories
                WHERE memory_type = 'episodic'{user_filter}
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit, **user_params})
        else:
            # 使用关键词匹配（同时搜索 keywords 和 content）
            keyword_pattern = "%" + keywords[0] + "%"

            result = self.db.execute(text(f"""
                SELECT * FROM memories
                WHERE memory_type = 'episodic'{user_filter}
                AND (keywords LIKE :pattern OR content LIKE :pattern)
                ORDER BY importance_score DESC, created_at DESC
                LIMIT :limit
            """), {"pattern": keyword_pattern, "limit": limit, **user_params})

        rows = result.fetchall()
        episodic_list = []
        for row in rows:
            m = dict(row._mapping) if hasattr(row, '_mapping') else dict(zip(row._fields, row))
            metadata = json.loads(m["metadata"]) if m["metadata"] else {}
            episodic_list.append(EpisodicMemory(
                memory_id=m["id"],
                diary_id=m["source_diary_id"] or 0,
                summary=m["content"],
                key_events=metadata.get("key_events", []),
                emotion=metadata.get("emotion", "neutral"),
                topics=json.loads(m["keywords"]) if m["keywords"] else [],
                date=datetime.fromisoformat(m["created_at"]) if m["created_at"] else datetime.now(),
                retrieval_keys=metadata.get("retrieval_keys", [])
            ))

        return episodic_list

    # ==================== 通用方法 ====================

    def _get_memories_by_type(self, memory_type: MemoryType, limit: int = 100, user_id: Optional[int] = None) -> List[Dict]:
        """获取指定类型的所有记忆"""
        query = "SELECT * FROM memories WHERE memory_type = :type"
        params = {"type": memory_type.value, "limit": limit}
        if user_id is not None:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        query += " ORDER BY importance_score DESC, last_accessed DESC LIMIT :limit"
        result = self.db.execute(text(query), params)

        rows = result.fetchall()
        # SQLAlchemy 2.0: 使用 _mapping 或 list(row.keys()) 来获取字典
        return [dict(zip(row._fields, row)) if hasattr(row, '_fields') else dict(row._mapping) for row in rows]

    def get_all_memories(self, user_id: Optional[int] = None) -> Dict[MemoryType, List[MemoryItem]]:
        """获取所有记忆，按类型分组"""
        result = {}
        for mt in [MemoryType.FACTUAL, MemoryType.EPISODIC]:
            memories = self._get_memories_by_type(mt, user_id=user_id)
            result[mt] = [
                MemoryItem(
                    id=m["id"],
                    memory_type=MemoryType(m["memory_type"]),
                    content=m["content"],
                    keywords=json.loads(m["keywords"]) if m["keywords"] else [],
                    source_diary_id=m["source_diary_id"],
                    importance_score=m["importance_score"],
                    access_count=m["access_count"],
                    last_accessed=datetime.fromisoformat(m["last_accessed"]) if m["last_accessed"] else None,
                    created_at=datetime.fromisoformat(m["created_at"]) if m["created_at"] else datetime.now(),
                    updated_at=datetime.fromisoformat(m["updated_at"]) if m["updated_at"] else datetime.now(),
                    metadata=json.loads(m["metadata"]) if m["metadata"] else {}
                )
                for m in memories
            ]
        return result

    def update_importance(self, memory_id: int, delta: float = 0.1, user_id: Optional[int] = None):
        """更新记忆重要性"""
        query = """
            UPDATE memories
            SET importance_score = MIN(1.0, MAX(0.0, importance_score + :delta)),
                last_accessed = CURRENT_TIMESTAMP,
                access_count = access_count + 1
            WHERE id = :id
        """
        params = {"delta": delta, "id": memory_id}
        if user_id is not None:
            query += " AND user_id = :user_id"
            params["user_id"] = user_id
        self.db.execute(text(query), params)
        self.db.commit()

    def extract_from_diary(self, diary_data: Dict, user_id: Optional[int] = None):
        """从日记数据提取并存储记忆"""
        diary_id = diary_data.get("id")
        cleaned_text = diary_data.get("cleaned_text", "")
        emotion = diary_data.get("emotion", "neutral")
        topics = diary_data.get("topics", [])
        key_events = diary_data.get("key_events", [])

        # 1. 创建情节记忆
        if cleaned_text:
            summary = cleaned_text[:200] + "..." if len(cleaned_text) > 200 else cleaned_text
            self.create_episodic_memory(
                diary_id=diary_id,
                summary=summary,
                key_events=key_events,
                emotion=emotion,
                topics=topics,
                user_id=user_id
            )

        # 2. 更新事实记忆（提取主题偏好）
        if topics:
            for topic in topics[:3]:
                self.update_factual_memory(
                    key="topic_preference",
                    value={topic: 1},
                    source_diary_id=diary_id,
                    user_id=user_id
                )

        # 3. 更新情绪模式
        if emotion:
            existing_patterns = self.get_factual_memory(user_id=user_id).emotional_patterns
            existing_patterns[emotion] = existing_patterns.get(emotion, 0) + 1
            self.update_factual_memory(
                key="emotion_pattern",
                value=existing_patterns,
                source_diary_id=diary_id,
                user_id=user_id
            )