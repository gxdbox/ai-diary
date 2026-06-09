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

logger = logging.getLogger(__name__)


class EntityExtractor:
    """使用 DeepSeek AI 提取日记中的实体"""

    def __init__(self, db: Session):
        self.db = db

    async def extract_entities(self, text: str) -> Dict:
        """
        从日记文本中提取人物、地点、关系和事件

        Args:
            text: 日记文本

        Returns:
            Dict: {
                "characters": ["张三", "李四"],
                "locations": ["北京", "咖啡厅"],
                "relationships": [
                    {"person_a": "张三", "person_b": "李四", "type": "朋友"}
                ],
                "events": ["一起喝咖啡"]
            }
        """
        if not text or len(text.strip()) < 10:
            return {
                "characters": [],
                "locations": [],
                "relationships": [],
                "events": []
            }

        prompt = f"""你是一个专业的实体提取助手。请从以下日记文本中提取关键信息。

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
2. locations: 提取所有提到的地点、场所
3. relationships: 推断人物之间的关系（朋友/家人/同事/同学/恋人/陌生人等）
4. events: 提取关键事件或活动（简短描述）
5. 如果某类信息不存在，返回空数组
6. 关系类型必须是中文，如："朋友"、"家人"、"同事"、"同学"、"恋人"、"陌生人"
"""

        try:
            response = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3
            )

            # 解析 JSON 响应
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
            # 尝试直接解析
            entities = json.loads(response)

            # 验证字段
            if not isinstance(entities, dict):
                raise ValueError("响应不是字典格式")

            # 确保所有必需字段存在
            entities.setdefault("characters", [])
            entities.setdefault("locations", [])
            entities.setdefault("relationships", [])
            entities.setdefault("events", [])

            return entities

        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON
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

            # 完全失败时返回空结构
            return {
                "characters": [],
                "locations": [],
                "relationships": [],
                "events": []
            }

    async def save_entities(self, entities: Dict, diary_id: int, created_at: datetime) -> None:
        """
        保存提取的实体到数据库

        Args:
            entities: 提取的实体数据
            diary_id: 日记 ID
            created_at: 日记创建时间
        """
        try:
            # 保存人物
            character_ids = {}
            for char_name in entities.get("characters", []):
                char_id = await self._save_character(char_name, created_at)
                if char_id:
                    character_ids[char_name] = char_id

            # 保存地点
            for loc_name in entities.get("locations", []):
                await self._save_location(loc_name, created_at)

            # 保存关系
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
            # 不抛出异常，避免影响日记创建流程

    async def _save_character(self, name: str, appearance_time: datetime) -> Optional[int]:
        """保存或更新人物实体"""
        try:
            # 检查是否已存在
            result = self.db.execute(
                text("SELECT id, appearance_count FROM characters WHERE name = :name"),
                {"name": name}
            )
            row = result.fetchone()

            if row:
                # 更新现有人物
                char_id = row[0]
                count = row[1]
                self.db.execute(
                    text("""
                        UPDATE characters
                        SET appearance_count = :count,
                            last_appearance = :last_time,
                            updated_at = :updated_at
                        WHERE id = :id
                    """),
                    {
                        "count": count + 1,
                        "last_time": appearance_time.isoformat(),
                        "updated_at": datetime.utcnow().isoformat(),
                        "id": char_id
                    }
                )
                self.db.commit()
                return char_id
            else:
                # 创建新人物
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
            # 检查是否已存在
            result = self.db.execute(
                text("SELECT id, visit_count FROM locations WHERE name = :name"),
                {"name": name}
            )
            row = result.fetchone()

            if row:
                # 更新现有地点
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
                # 创建新地点
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
            # 确保 char_a_id < char_b_id 以避免重复
            if char_a_id > char_b_id:
                char_a_id, char_b_id = char_b_id, char_a_id

            # 检查是否已存在
            result = self.db.execute(
                text("""
                    SELECT id, strength FROM relationships
                    WHERE character_a_id = :a_id AND character_b_id = :b_id
                """),
                {"a_id": char_a_id, "b_id": char_b_id}
            )
            row = result.fetchone()

            if row:
                # 更新现有关系（增加强度）
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
                # 创建新关系
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
