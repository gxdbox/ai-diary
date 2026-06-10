"""
实体提取服务 - 从日记文本中自动识别人物、地点、关系和事件
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.ai.client import llm
from app.db.database import Character, Relationship, Location
from app.services.entity_normalizer import EntityNormalizer

logger = logging.getLogger(__name__)


class EntityExtractor:
    """使用 DeepSeek AI 提取日记中的实体"""

    def __init__(self, db: Session):
        self.db = db
        self.normalizer = EntityNormalizer(db)

    async def extract_entities(self, text: str, context: str = "") -> Dict:
        """
        从日记文本中提取人物、地点、关系和事件

        Args:
            text: 日记文本
            context: 已知实体上下文（用于别名归一化）

        Returns:
            Dict: {
                "characters": ["张三", "李四"],
                "locations": ["北京", "咖啡厅"],
                "relationships": [...],
                "events": [...]
            }
        """
        if not text or len(text.strip()) < 10:
            return {
                "characters": [],
                "locations": [],
                "relationships": [],
                "events": []
            }

        known_context = ""
        if context:
            known_context = f"\n\n已知人物数据库（包含别名信息）：\n{context}\n"

        prompt = f"""你是一个专业的实体提取助手。请从以下日记文本中提取关键信息。{known_context}

日记文本：
{text}

请严格按照以下 JSON 格式返回结果（不要包含其他文字）：
{{
  "characters": ["人物名称1", "人物名称2"],
  "locations": ["地点名称1", "地点名称2"],
  "relationships": [
    {{"person_a": "人物A", "person_b": "人物B", "type": "关系类型"}}
  ],
  "events": ["事件描述1", "事件描述2"]
}}

要求：
1. characters: 提取所有提到的人物姓名（不包括"我"）
2. 如果已知人物数据库中存在该人物，请使用数据库中的标准名称（即使文本中使用的是别名）
3. 如果文本中的人物明显是已知人物的不同称呼（如"儿子"对应"顾余杭"），请使用标准名称
4. locations: 提取所有提到的地点、场所
5. relationships: 推断人物之间的关系（朋友/家人/同事/同学/恋人/陌生人等）
6. events: 提取关键事件或活动（简短描述）
7. 如果某类信息不存在，返回空数组
8. 关系类型必须是中文，如："朋友"、"家人"、"同事"、"同学"、"恋人"、"陌生人"
"""

        try:
            response = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )

            entities = self._parse_response(response)
            logger.info(f"实体提取成功: {len(entities.get('characters', []))} 个人物, "
                       f"{len(entities.get('locations', []))} 个地点")
            return entities

        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return {
                "characters": [],
                "locations": [],
                "relationships": [],
                "events": []
            }

    def _parse_response(self, response: str) -> Dict:
        """解析 AI 响应，提取 JSON 数据"""
        try:
            entities = json.loads(response)
            if not isinstance(entities, dict):
                raise ValueError("响应不是字典格式")
            entities.setdefault("characters", [])
            entities.setdefault("locations", [])
            entities.setdefault("relationships", [])
            entities.setdefault("events", [])
            return entities
        except json.JSONDecodeError:
            logger.warning("JSON 解析失败，尝试从文本中提取")
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                try:
                    entities = json.loads(json_str)
                    entities.setdefault("characters", [])
                    entities.setdefault("locations", [])
                    entities.setdefault("relationships", [])
                    entities.setdefault("events", [])
                    return entities
                except:
                    pass
            return {
                "characters": [],
                "locations": [],
                "relationships": [],
                "events": []
            }

    async def save_entities(self, entities: Dict, diary_id: int, created_at: datetime) -> None:
        """
        保存提取的实体到数据库，自动进行别名归一化
        """
        try:
            known_entities = self.normalizer.get_known_entities()

            character_ids = {}
            for char_name in entities.get("characters", []):
                char_id = await self._save_character(char_name, created_at, known_entities)
                if char_id:
                    character_ids[char_name] = char_id

            for loc_name in entities.get("locations", []):
                await self._save_location(loc_name, created_at)

            for rel in entities.get("relationships", []):
                person_a = rel.get("person_a")
                person_b = rel.get("person_b")
                rel_type = rel.get("type", "unknown")

                if person_a in character_ids and person_b in character_ids:
                    await self._save_relationship(
                        character_ids[person_a],
                        character_ids[person_b],
                        rel_type,
                        created_at
                    )

            logger.info(f"实体保存成功: {len(character_ids)} 个人物, "
                       f"{len(entities.get('locations', []))} 个地点, "
                       f"{len(entities.get('relationships', []))} 个关系")

        except Exception as e:
            logger.error(f"保存实体失败: {e}")

    async def _save_character(self, name: str, appearance_time: datetime,
                               known_entities: Dict[str, dict]) -> Optional[int]:
        """保存或更新人物实体（含别名归一化）"""
        try:
            matched = self.normalizer.normalize(name, known_entities)

            if matched:
                char_id = matched["character_id"]
                canonical_name = matched["canonical_name"]

                if name != canonical_name:
                    self.normalizer.add_alias(char_id, name, source="llm", confidence=0.8)

                self.db.execute(
                    text("""
                        UPDATE characters
                        SET appearance_count = appearance_count + 1,
                            last_appearance = :last_time,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "last_time": appearance_time.isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "id": char_id
                    }
                )
                self.db.commit()
                return char_id
            else:
                result = self.db.execute(
                    text("SELECT id, appearance_count FROM characters WHERE name = :name"),
                    {"name": name}
                )
                row = result.fetchone()

                if row:
                    char_id = row[0]
                    self.db.execute(
                        text("""
                            UPDATE characters
                            SET appearance_count = appearance_count + 1,
                                last_appearance = :last_time,
                                updated_at = :updated_at
                            WHERE id = :id
                        """),
                        {
                            "last_time": appearance_time.isoformat(),
                            "updated_at": datetime.utcnow().isoformat(),
                            "id": char_id
                        }
                    )
                    self.db.commit()
                    return char_id
                else:
                    import random
                    colors = ["#4A90E2", "#F5A623", "#7ED321", "#BD10E0", "#D0021B", "#50E3C2"]
                    avatar_color = random.choice(colors)

                    result = self.db.execute(
                        text("""
                            INSERT INTO characters (name, first_appearance, last_appearance,
                                                  appearance_count, avatar_color, created_at, updated_at)
                            VALUES (:name, :first, :last, 1, :color, :created, :updated)
                        """),
                        {
                            "name": name,
                            "first": appearance_time.isoformat(),
                            "last": appearance_time.isoformat(),
                            "color": avatar_color,
                            "created": datetime.utcnow().isoformat(),
                            "updated": datetime.utcnow().isoformat()
                        }
                    )
                    self.db.commit()
                    return result.lastrowid

        except Exception as e:
            logger.error(f"保存人物失败 [{name}]: {e}")
            self.db.rollback()
            return None

    async def _save_location(self, name: str, visit_time: datetime) -> None:
        """保存或更新地点实体"""
        try:
            result = self.db.execute(
                text("SELECT id, visit_count FROM locations WHERE name = :name"),
                {"name": name}
            )
            row = result.fetchone()

            if row:
                loc_id = row[0]
                count = row[1]
                self.db.execute(
                    text("""
                        UPDATE locations
                        SET visit_count = :count,
                            last_visit = :last_time,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "count": count + 1,
                        "last_time": visit_time.isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "id": loc_id
                    }
                )
                self.db.commit()
            else:
                self.db.execute(
                    text("""
                        INSERT INTO locations (name, visit_count, last_visit, created_at, updated_at)
                        VALUES (:name, 1, :last, :created, :updated)
                    """),
                    {
                        "name": name,
                        "last": visit_time.isoformat(),
                        "created": datetime.utcnow().isoformat(),
                        "updated": datetime.utcnow().isoformat()
                    }
                )
                self.db.commit()

        except Exception as e:
            logger.error(f"保存地点失败 [{name}]: {e}")
            self.db.rollback()

    async def _save_relationship(self, char_a_id: int, char_b_id: int,
                                  rel_type: str, interaction_time: datetime) -> None:
        """保存或更新人物关系"""
        try:
            if char_a_id > char_b_id:
                char_a_id, char_b_id = char_b_id, char_a_id

            result = self.db.execute(
                text("""
                    SELECT id, strength FROM relationships
                    WHERE character_a_id = :a_id AND character_b_id = :b_id
                """),
                {"a_id": char_a_id, "b_id": char_b_id}
            )
            row = result.fetchone()

            if row:
                rel_id = row[0]
                current_strength = row[1]
                new_strength = min(1.0, current_strength + 0.1)

                self.db.execute(
                    text("""
                        UPDATE relationships
                        SET strength = :strength,
                            last_interaction = :last_time,
                            relationship_type = :rel_type,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "strength": new_strength,
                        "last_time": interaction_time.isoformat(),
                        "rel_type": rel_type,
                        "updated_at": datetime.utcnow().isoformat(),
                        "id": rel_id
                    }
                )
                self.db.commit()
            else:
                self.db.execute(
                    text("""
                        INSERT INTO relationships (character_a_id, character_b_id,
                                                 relationship_type, strength,
                                                 last_interaction, created_at, updated_at)
                        VALUES (:a_id, :b_id, :rel_type, 0.5, :last, :created, :updated)
                    """),
                    {
                        "a_id": char_a_id,
                        "b_id": char_b_id,
                        "rel_type": rel_type,
                        "last": interaction_time.isoformat(),
                        "created": datetime.utcnow().isoformat(),
                        "updated": datetime.utcnow().isoformat()
                    }
                )
                self.db.commit()

        except Exception as e:
            logger.error(f"保存关系失败 [{char_a_id}-{char_b_id}]: {e}")
            self.db.rollback()
