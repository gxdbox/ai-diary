"""
文本清洗服务
"""
import re
from typing import List, Tuple

# 口语填充词列表
FILLER_WORDS = [
    "嗯", "啊", "哈", "那个", "就是", "然后呢", "这个", "呃", "额",
    "就是说", "可以说", "怎么说呢", "其实吧", "怎么说", "对吧",
    "是不是", "你知道吗", "你懂的", "哎呀", "哇塞"
]


class TextCleaner:
    """文本清洗器"""

    def __init__(self, custom_fillers: List[str] = None):
        self.filler_words = FILLER_WORDS + (custom_fillers or [])

    def remove_filler_words(self, text: str) -> str:
        """移除口语填充词"""
        result = text
        for filler in self.filler_words:
            # 使用正则表达式匹配独立的填充词
            pattern = r'\b' + re.escape(filler) + r'\b'
            result = re.sub(pattern, '', result)

        # 清理多余的空格
        result = re.sub(r'\s+', ' ', result)
        return result.strip()

    def fix_punctuation(self, text: str) -> str:
        """修正标点符号"""
        # 英文标点转中文
        punct_map = {
            ',': '，',
            '.': '。',
            '?': '？',
            '!': '！',
            ':': '：',
            ';': '；',
            '(': '（',
            ')': '）',
        }

        result = text
        for eng, chn in punct_map.items():
            # 只转换独立的标点，避免影响数字中的标点
            result = re.sub(r'(?<![0-9])' + re.escape(eng) + r'(?![0-9])', chn, result)

        return result

    def fix_common_errors(self, text: str) -> str:
        """修正常见识别错误"""
        common_errors = {
            "在在做": "在做",
            "我我": "我",
            "你你": "你",
            "他他": "他",
            "是是": "是",
            "的有": "的有",
            "的的": "的",
        }

        result = text
        for wrong, right in common_errors.items():
            result = result.replace(wrong, right)

        return result

    def clean(self, text: str) -> str:
        """执行完整清洗流程"""
        result = text
        result = self.remove_filler_words(result)
        result = self.fix_punctuation(result)
        result = self.fix_common_errors(result)
        return result

    def get_clean_stats(self, original: str, cleaned: str) -> dict:
        """获取清洗统计信息"""
        return {
            "original_length": len(original),
            "cleaned_length": len(cleaned),
            "removed_chars": len(original) - len(cleaned),
            "removed_percentage": round((len(original) - len(cleaned)) / len(original) * 100, 2) if original else 0
        }


# 全局清洗器实例
text_cleaner = TextCleaner()