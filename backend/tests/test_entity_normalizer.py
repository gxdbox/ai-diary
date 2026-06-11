"""
实体归一化器单元测试

测试别名匹配、字符重叠相似度、亲属称谓过滤等核心逻辑。
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.entity_normalizer import EntityNormalizer


class TestCharOverlap:
    """测试字符重叠率计算"""

    def test_identical(self):
        assert EntityNormalizer._char_overlap("顾余杭", "顾余杭") == 1.0

    def test_partial_overlap(self):
        assert EntityNormalizer._char_overlap("顾余杭", "余杭") > 0.5

    def test_share_char(self):
        assert EntityNormalizer._char_overlap("语杭", "顾余杭") > 0.0

    def test_no_overlap(self):
        assert EntityNormalizer._char_overlap("张三", "李四") == 0.0

    def test_empty(self):
        assert EntityNormalizer._char_overlap("", "") == 0.0
        assert EntityNormalizer._char_overlap("abc", "") == 0.0


class TestIsPlausibleAlias:
    """测试别名合理性判断"""

    def test_single_char_rejected(self):
        assert not EntityNormalizer._is_plausible_alias("明", "顾余杭", {})
        assert not EntityNormalizer._is_plausible_alias("顾余杭", "明", {})

    def test_identical_rejected(self):
        assert not EntityNormalizer._is_plausible_alias("顾余杭", "顾余杭", {})

    def test_known_in_mapping_rejected(self):
        mapping = {"航航": {"character_id": 1, "canonical_name": "顾余杭"}}
        assert not EntityNormalizer._is_plausible_alias("航航", "顾余杭", mapping)

    def test_substring_accepted(self):
        assert EntityNormalizer._is_plausible_alias("余杭", "顾余杭", {})

    def test_related_names_accepted(self):
        # 共享"杭"字，子串匹配
        assert EntityNormalizer._is_plausible_alias("余杭", "顾余杭", {})


class TestNormalize:
    """测试 normalize 方法（逻辑层，不依赖 DB）"""

    def test_exact_match(self):
        mapping = {"顾余杭": {"character_id": 1, "canonical_name": "顾余杭"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("顾余杭", mapping)
        assert result is not None
        assert result["character_id"] == 1

    def test_alias_match(self):
        mapping = {"航航": {"character_id": 1, "canonical_name": "顾余杭"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("航航", mapping)
        assert result is not None
        assert result["character_id"] == 1
        assert result["canonical_name"] == "顾余杭"

    def test_substring_match(self):
        mapping = {"顾余杭": {"character_id": 1, "canonical_name": "顾余杭"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("余杭", mapping)
        assert result is not None
        assert result["character_id"] == 1

    def test_partial_overlap(self):
        mapping = {"顾余杭": {"character_id": 1, "canonical_name": "顾余杭"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("语杭", mapping)
        # 语杭 vs 顾余杭：重叠"杭"，重叠率 1/3=33%，< 40% → 不匹配
        assert result is None

    def test_kinship_term_not_matched(self):
        mapping = {"顾余杭": {"character_id": 1, "canonical_name": "顾余杭"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("儿子", mapping)
        assert result is None

    def test_new_entity(self):
        mapping = {}
        result = EntityNormalizer(normalizer_scope_mock).normalize("张三", mapping)
        assert result is None

    def test_single_char(self):
        mapping = {"张": {"character_id": 1, "canonical_name": "张"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("李", mapping)
        assert result is None

    def test_character_overlap_high_enough(self):
        mapping = {"刘德华": {"character_id": 1, "canonical_name": "刘德华"}}
        result = EntityNormalizer(normalizer_scope_mock).normalize("德华", mapping)
        # 重叠 2/3=66% ≥ 40% → 匹配
        assert result is not None
        assert result["character_id"] == 1


# Mock 对象 — 仅用于测试 normalize 的逻辑层方法
class _MockDB:
    def execute(self, *args, **kwargs):
        return _MockResult([])
    def close(self):
        pass


class _MockResult:
    def __init__(self, rows):
        self.rows = rows
    def fetchall(self):
        return self.rows
    def fetchone(self):
        return self.rows[0] if self.rows else None


normalizer_scope_mock = _MockDB()
