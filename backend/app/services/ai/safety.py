"""
安全过滤 + 危机干预

来自 ai_companion，提供：
1. 输入安全检查（敏感词过滤）
2. 危机干预响应
3. 情绪类型识别
"""
import re
from typing import Optional, Tuple


BLOCKED_WORDS = [
    "自杀", "自残", "杀人", "爆炸", "毒品",
    "我想死", "活着没意义", "结束自己",
]

CRISIS_RESPONSE = """我非常关心你，你现在很不容易。如果你正在经历困难时刻，请立刻联系专业帮助：

心理援助热线：400-161-9995
北京心理危机研究与干预中心：010-82951332
生命热线：400-821-1215

你值得被帮助，请给自己一个机会。"""

EMOTION_TEMPLATES = {
    "焦虑": "先安抚：\"听起来你最近压力很大...\" 引导思考具体原因。",
    "悲伤": "先共情：\"我能感受到你的难过...\" 表达陪伴和支持。",
    "愤怒": "先接纳：\"听起来这件事让你很生气...\" 理解情绪的自然性。",
    "困惑": "先共情：\"这种迷茫的感觉确实让人不安...\" 温和陪伴探索。",
    "孤独": "先连接：\"谢谢你愿意告诉我这些...\" 强调你并不孤单。",
    "恐惧": "先安抚：\"听起来这件事让你很害怕...\" 解释这是正常的反应。",
    "自豪": "先肯定：\"太棒了！这真的很不容易...\" 庆祝成就。",
    "不满": "先理解：\"听起来你对这件事不满意...\" 倾听具体困扰。",
    "矛盾": "先共情：\"这种纠结的感觉确实让人困惑...\" 探索两种想法。",
    "如释重负": "先祝贺：\"听起来你终于放下了...\" 肯定这个释然的时刻。",
}


class SafetyFilter:
    """安全过滤器"""

    def check(self, text: str) -> Tuple[bool, str]:
        """
        检查输入是否安全

        Returns:
            (is_safe, warning): 安全标记和警告信息
        """
        for word in BLOCKED_WORDS:
            if re.search(word, text):
                return False, CRISIS_RESPONSE
        return True, ""

    @staticmethod
    def get_emotion_template(emotion: Optional[str] = None) -> str:
        """
        获取情绪匹配回应模板

        Args:
            emotion: 情绪类型

        Returns:
            str: 回应风格提示
        """
        if not emotion:
            return ""
        return EMOTION_TEMPLATES.get(emotion, "")

    @staticmethod
    def detect_emotion_type(emotion: str) -> Optional[str]:
        """
        将情绪标签映射到情绪模板类型

        Args:
            emotion: 情绪标签（来自日记分析）

        Returns:
            str: 匹配的情绪模板类型，或 None
        """
        mapping = {
            "焦虑": "焦虑", "担忧": "焦虑", "着急": "焦虑",
            "悲伤": "悲伤", "难过": "悲伤", "伤心": "悲伤", "忧郁": "悲伤",
            "愤怒": "愤怒", "生气": "愤怒", "气恼": "愤怒",
            "困惑": "困惑", "迷茫": "困惑",
            "孤独": "孤独", "寂寞": "孤独",
            "恐惧": "恐惧", "害怕": "恐惧", "惧怕": "恐惧",
            "自豪": "自豪", "骄傲": "自豪",
            "不满": "不满", "失望": "不满",
            "矛盾": "矛盾", "纠结": "矛盾",
            "如释重负": "如释重负", "安心": "如释重负",
        }
        return mapping.get(emotion)
