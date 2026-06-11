"""
实体归一化服务 - 别名匹配、实体去重

通过多种策略判断两个名称是否指代同一实体：
1. 别名表精确匹配
2. 字符重叠相似度
3. 子串包含关系
"""
import logging
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# 亲属称谓集合 — 这类词很可能是别名而非独立人物
KINSHIP_TERMS = {"儿子", "女儿", "爸爸", "妈妈", "老爸", "老妈",
                 "爷爷", "奶奶", "外公", "外婆", "老公", "老婆",
                 "丈夫", "妻子", "哥哥", "弟弟", "姐姐", "妹妹",
                 "表哥", "表弟", "表姐", "表妹", "侄子", "侄女",
                 "舅舅", "阿姨", "叔叔", "姑姑", "岳父", "岳母"}


class EntityNormalizer:
    """实体归一化器"""

    def __init__(self, db: Session):
        self.db = db

    def get_known_entities(self) -> Dict[str, dict]:
        """
        从数据库加载所有已知实体及其别名

        Returns:
            {别名: {"character_id": id, "canonical_name": name}}
        """
        mapping = {}

        # 加载 canonical names
        result = self.db.execute(
            text("SELECT id, name FROM characters")
        )
        for row in result.fetchall():
            char_id, name = row
            mapping[name] = {"character_id": char_id, "canonical_name": name}

        # 加载别名映射
        result = self.db.execute(
            text("""
                SELECT ca.alias, ca.character_id, c.name
                FROM character_aliases ca
                JOIN characters c ON c.id = ca.character_id
            """)
        )
        for row in result.fetchall():
            alias, char_id, canonical = row
            mapping[alias] = {"character_id": char_id, "canonical_name": canonical}

        return mapping

    def build_context(self) -> str:
        """
        构建已知实体上下文，供 LLM prompt 使用

        Returns:
            "已知人物：顾余杭（别名：航航、儿子、语杭）\n..."
        """
        # 获取所有人物及其别名
        result = self.db.execute(
            text("""
                SELECT c.id, c.name,
                       GROUP_CONCAT(ca.alias, '、') as alias_list
                FROM characters c
                LEFT JOIN character_aliases ca ON ca.character_id = c.id
                GROUP BY c.id
                ORDER BY c.appearance_count DESC
            """)
        )
        lines = []
        for row in result.fetchall():
            char_id, name, alias_str = row
            if alias_str:
                lines.append(f"{name}（别名：{alias_str}）")
            else:
                lines.append(name)

        if not lines:
            return ""

        return "已知人物：\n" + "\n".join(lines)

    def normalize(self, name: str, known_entities: Dict[str, dict]) -> Optional[dict]:
        """
        尝试将名称匹配到已知实体

        Returns:
            匹配到的实体信息，或 None 表示这是一个新实体
        """
        name = name.strip()
        if not name:
            return None

        # 1. 精确匹配（含别名表）
        if name in known_entities:
            return known_entities[name]

        # 2. 亲属称谓 + 上下文：如果名称本身就是亲属称谓词，标记但不自动合并
        if name in KINSHIP_TERMS:
            return None  # 由 LLM 决定

        # 3. 子串包含匹配（"余杭" → "顾余杭"）
        for known_name, info in known_entities.items():
            if name in known_name or known_name in name:
                if self._is_plausible_alias(name, known_name, known_entities):
                    return info

        # 4. 字符重叠相似度（中文名称用共用字符比例）
        for known_name, info in known_entities.items():
            similarity = self._char_overlap(name, known_name)
            if similarity >= 0.4:
                if self._is_plausible_alias(name, known_name, known_entities):
                    return info

        return None

    @staticmethod
    def _char_overlap(a: str, b: str) -> float:
        """计算两个字符串的字符重叠率"""
        if not a or not b:
            return 0.0
        set_a, set_b = set(a), set(b)
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    @staticmethod
    def _is_plausible_alias(new_name: str, known_name: str,
                            known_entities: Dict[str, dict]) -> bool:
        """
        判断别名是否合理，避免短串误匹配

        规则：
        - 单字名不自动匹配（如"明"）
        - 如果两者完全相等则不在此处理
        """
        new_name = new_name.strip()
        known_name = known_name.strip()

        if len(new_name) <= 1 or len(known_name) <= 1:
            return False
        if new_name == known_name:
            return False
        # 已知名称已在 mapping 中，跳过自己和别名
        if new_name in known_entities:
            return False
        return True

    def add_alias(self, character_id: int, alias: str,
                  source: str = "llm", confidence: float = 1.0) -> bool:
        """
        为人物添加别名记录

        Returns:
            是否成功添加（已存在则跳过）
        """
        alias = alias.strip()
        if not alias:
            return False

        # 检查是否已存在
        result = self.db.execute(
            text("SELECT id FROM character_aliases WHERE alias = :alias AND character_id = :char_id"),
            {"alias": alias, "char_id": character_id}
        )
        if result.fetchone():
            return False

        # 检查是否与 canonical name 相同
        result = self.db.execute(
            text("SELECT id FROM characters WHERE id = :id AND name = :alias"),
            {"id": character_id, "alias": alias}
        )
        if result.fetchone():
            return False

        try:
            self.db.execute(
                text("""
                    INSERT INTO character_aliases (character_id, alias, source, confidence, created_at)
                    VALUES (:char_id, :alias, :source, :confidence, :now)
                """),
                {
                    "char_id": character_id,
                    "alias": alias,
                    "source": source,
                    "confidence": confidence,
                    "now": __import__('datetime').datetime.utcnow().isoformat()
                }
            )
            self.db.commit()
            logger.info(f"添加别名: character_id={character_id}, alias={alias}")
            return True
        except Exception as e:
            logger.error(f"添加别名失败 [{alias}]: {e}")
            self.db.rollback()
            return False
