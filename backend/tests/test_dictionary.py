"""
自定义词典功能单元测试

测试拼音模糊匹配、发音混淆规则、后处理等核心函数。
"""
import pytest
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.dictionary import (
    levenshtein,
    pinyin_similarity,
    normalize_pinyin,
    get_pinyin,
    get_all_pinyins,
    is_english_word,
    apply_dictionary_correction,
)
from app.services.ai.prompts.cleaner import build_cleaner_prompt


class TestLevenshtein:
    """测试编辑距离计算"""

    def test_identical(self):
        assert levenshtein("abc", "abc") == 0
        assert levenshtein("", "") == 0

    def test_one_empty(self):
        assert levenshtein("", "abc") == 3
        assert levenshtein("abc", "") == 3

    def test_substitution(self):
        assert levenshtein("abc", "abd") == 1
        assert levenshtein("hello", "hallo") == 1

    def test_insertion_deletion(self):
        assert levenshtein("ab", "abc") == 1
        assert levenshtein("abc", "ab") == 1

    def test_chinese_pinyin(self):
        """中文拼音编辑距离"""
        assert levenshtein("tongtong", "tongtong") == 0
        assert levenshtein("tongtong", "tonton") == 2
        assert levenshtein("nantong", "lantong") == 1


class TestPinyinSimilarity:
    """测试拼音相似度"""

    def test_exact_match(self):
        assert pinyin_similarity("tongtong", "tongtong") == 1.0

    def test_similar(self):
        sim = pinyin_similarity("tongtong", "tonton")
        assert 0.7 < sim < 0.9

    def test_different(self):
        sim = pinyin_similarity("abc", "xyz")
        assert sim < 0.5

    def test_empty(self):
        assert pinyin_similarity("", "") == 1.0


class TestNormalizePinyin:
    """测试拼音模糊归一化（仅平翘舌）"""

    def test_zh_z(self):
        """平翘舌混淆：zh → z"""
        assert normalize_pinyin("zhong") == "zong"

    def test_z_unchanged(self):
        """z 不变化"""
        assert normalize_pinyin("zong") == "zong"

    def test_ch_c(self):
        """平翘舌混淆：ch → c"""
        assert normalize_pinyin("chang") == "cang"

    def test_sh_s(self):
        """平翘舌混淆：sh → s"""
        assert normalize_pinyin("shang") == "sang"

    def test_no_change_for_nl(self):
        """n/l 不归一化（由编辑距离处理）"""
        assert normalize_pinyin("nannan") == "nannan"
        assert normalize_pinyin("lanlan") == "lanlan"

    def test_no_change_for_fh(self):
        """f/h 不归一化（由编辑距离处理）"""
        assert normalize_pinyin("fang") == "fang"
        assert normalize_pinyin("hang") == "hang"

    def test_no_change_normal(self):
        """不需要归一化的拼音"""
        assert normalize_pinyin("ba") == "ba"
        assert normalize_pinyin("mama") == "mama"
        assert normalize_pinyin("tongtong") == "tongtong"


class TestGetPinyin:
    """测试拼音转换"""

    def test_simple(self):
        assert get_pinyin("桐") == "tong"

    def test_word(self):
        assert get_pinyin("桐桐") == "tongtong"

    def test_complex(self):
        """多字词"""
        p = get_pinyin("中国")
        assert p == "zhongguo" or p == "zhongguo"


class TestIsEnglishWord:
    """测试英文词汇判断"""

    def test_chinese_only(self):
        assert not is_english_word("桐桐")
        assert not is_english_word("中国")

    def test_english_only(self):
        assert is_english_word("Claude")
        assert is_english_word("hello")

    def test_mixed(self):
        assert is_english_word("Claude Code")
        assert is_english_word("AI日记")


class TestBuildCleanerPrompt:
    """测试动态 Prompt 构建"""

    def test_no_words(self):
        prompt = build_cleaner_prompt(None)
        assert "自定义词汇" not in prompt
        assert "语音转写校对专家" in prompt

    def test_empty_list(self):
        prompt = build_cleaner_prompt([])
        assert "自定义词汇" not in prompt

    def test_with_words(self):
        words = ["桐桐", "Claude Code", "张三"]
        prompt = build_cleaner_prompt(words)
        assert "自定义词汇" in prompt
        assert "桐桐" in prompt
        assert "Claude Code" in prompt
        assert "张三" in prompt
        assert "仅供参考" in prompt
        assert "专有名词" in prompt

    def test_max_50_words(self):
        """超过 50 个词时只注入前 50 个"""
        words = [f"word{i}" for i in range(100)]
        prompt = build_cleaner_prompt(words)
        # 只应出现前 50 个
        assert "word0" in prompt
        assert "word49" in prompt
        assert "word50" not in prompt


class TestApplyDictionaryCorrection:
    """测试词典校正（已废弃，仅保留用于前端功能）"""

    def test_noop_empty_cache(self):
        import app.api.dictionary as d
        d.dictionary_cache = {}
        d.dictionary_words = set()
        assert apply_dictionary_correction("今天带桐桐出去玩") == "今天带桐桐出去玩"
