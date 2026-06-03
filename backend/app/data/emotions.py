"""
情绪分类数据 - 基于《心情词典》(The Book of Human Emotions)
作者：蒂凡尼·瓦特·史密斯 (Tiffany Watt Smith)
"""

# 情绪词条列表：英文原名 -> 中文翻译
EMOTION_VOCABULARY = {
    # A
    "Abhiman": "由爱生恨",
    "Acedia": "倦怠",
    "Amae": "撒娇依赖",
    "Ambiguphobia": "非解释清楚不可",
    "Anger": "愤怒",
    "Anticipation": "期待",
    "Anxiety": "焦虑",
    "Apathy": "冷漠",
    "L'appel Du Vide": "虚空的呼唤",
    "Awumbuk": "人去心空",

    # B
    "Bafflement": "不知所措",
    "Basorexia": "亲吻渴望",
    "Befuddlement": "茫然",
    "Bewilderment": "困惑",
    "Boredom": "厌倦",
    "Brabant": "作死",
    "Broodiness": "求子心切",

    # C
    "Calm": "冷静",
    "Carefree": "无忧无虑",
    "Cheerfulness": "欢快",
    "Cheesed Off": "气恼",
    "Claustrophobia": "幽闭恐惧",
    "The Collywobbles": "肠胃焦虑",
    "Comfort": "安慰",
    "Compassion": "同情",
    "Compersion": "多元之爱",
    "Confidence": "自信",
    "Contempt": "藐视",
    "Contentment": "满足",
    "Courage": "勇气",
    "Curiosity": "好奇",
    "Cyberchondria": "网络自诊焦虑",

    # D
    "Delight": "欣喜",
    "Dépaysement": "异境茫然",
    "Desire": "欲望",
    "Despair": "绝望",
    "The Desire To Disappear": "避世",
    "Disappointment": "失望",
    "Disgruntlement": "不满",
    "Disgust": "厌恶",
    "Dismay": "气馁",
    "Dolce Far Niente": "偷懒之乐",
    "Dread": "惧怕",

    # E
    "Ecstasy": "狂喜",
    "Embarrassment": "尴尬",
    "Empathy": "共情",
    "Envy": "嫉羡",
    "Euphoria": "欣快",
    "Exasperation": "激怒",
    "Excitement": "激动",

    # F
    "Fago": "悲天悯人",
    "Fear": "恐惧",
    "Feeling Good About Yourself": "自我感觉良好",
    "A Formal Feeling": "肃穆之感",
    "Feeling Like A Fraud": "冒牌者感",
    "Frustration": "沮丧",

    # G
    "Gezelligheid": "温馨",
    "Gladsomeness": "高兴",
    "Glee": "欢乐",
    "Gratitude": "感恩",
    "Greng Jai": "怕麻烦别人",
    "Grief": "悲痛",
    "Guilt": "内疚",

    # H
    "Han": "隐忍",
    "Happiness": "幸福",
    "Hatred": "仇恨",
    "The Heebie-Jeebies": "神经过敏",
    "Hiraeth": "乡愁",
    "The Urge To Hoard": "收藏欲",
    "Homefulness": "归家之喜",
    "Homesickness": "思乡",
    "Hopefulness": "充满希望",
    "In A Huff": "满腔怒火",
    "Feeling Humble": "低声下气",
    "Humiliation": "羞辱",
    "Hunger": "饥饿",
    "Hwyl": "激昂",

    # I
    "Ijirashii": "被他人顽强感动",
    "Iktsuarpok": "望眼欲穿",
    "Ilinx": "炫酷",
    "Impatience": "不耐烦",
    "Indignation": "义愤",
    "Inhabitiveness": "安居乐业",
    "Feeling Insulted": "被侮辱",
    "Irritation": "恼怒",

    # J
    "Jealousy": "妒忌",
    "Joy": "快乐",

    # K
    "Kaukokaipuu": "远方向往",

    # L
    "Liget": "化愤怒为力量",
    "Litost": "羞愤",
    "Loneliness": "孤独",
    "Love": "爱",

    # M
    "Malu": "自惭形秽",
    "Man": "热望",
    "Matutolypea": "起床气",
    "Mehameha": "怕鬼",
    "Melancholy": "忧郁",
    "A Bit Miffed": "有点气恼",
    "Mono No Aware": "物哀",
    "Morbid Curiosity": "猎奇",
    "Mudita": "随喜赞叹",

    # N
    "Nakhes": "以子为荣",
    "Nginyiwarringu": "惊吓",
    "Nostalgia": "怀旧思乡",

    # O
    "Oime": "亏欠感",
    "Feeling Overwhelmed": "不堪重负",

    # P
    "Panic": "恐慌",
    "Paranoia": "妄想",
    "Perversity": "乖戾",
    "Peur Des Espaces": "广场恐惧",
    "Philoprogenitiveness": "怜爱情结",
    "A Fit Of Pique": "突然的恼怒",
    "Pity": "怜悯",
    "Going Postal": "暴躁",
    "Pride": "自豪",
    "Pronoia": "不设防",

    # R
    "Rage": "狂怒",
    "Regret": "遗憾",
    "Relief": "如释重负",
    "Reluctance": "勉强",
    "Remorse": "懊悔",
    "Reproachfulness": "责备",
    "Resentment": "愤恨",
    "Ringxiety": "手机幻听",
    "Rivalry": "竞争",
    "Road Rage": "路怒",
    "Ruinenlust": "废物迷恋",

    # S
    "Sadness": "悲伤",
    "Satisfaction": "满意",
    "Saudade": "惆怅",
    "Schadenfreude": "幸灾乐祸",
    "Self-Pity": "自怨自艾",
    "Shame": "羞耻",
    "Shock": "震惊",
    "Smugness": "自以为是",
    "Song": "愤愤不平",
    "Surprise": "惊讶",
    "Suspicion": "多疑",

    # T
    "Technostress": "技术应激",
    "Terror": "惊骇",
    "Torschlusspanik": "时间焦虑",
    "Toska": "忧虑不安",
    "Triumph": "获胜之喜",

    # U
    "Umpty": "烦躁",
    "Uncertainty": "不确定",

    # V
    "Vengefulness": "复仇",
    "Vergüenza Ajena": "替人脸红",
    "Viraha": "情欲",
    "Vulnerability": "脆弱",

    # W
    "Wanderlust": "漫游欲",
    "Warm Glow": "温情",
    "Wonder": "惊奇",
    "Worry": "担忧",

    # Z
    "Żal": "失落的忧愁",
}

# 常用中文情绪词（用于直接匹配）
COMMON_CN_EMOTIONS = list(EMOTION_VOCABULARY.values())

# 情绪分类维度（用于辅助分析）
EMOTION_DIMENSIONS = {
    "positive": [
        "幸福", "快乐", "欣喜", "欢快", "高兴", "欢乐", "满足", "满意",
        "感恩", "自豪", "充满希望", "期待", "激动", "狂喜", "欣快",
        "如释重负", "温情", "自信", "欣慰", "随喜赞叹", "获胜之喜",
        "无忧无虑", "归家之喜", "以子为荣", "温馨", "安慰", "冷静",
        "好奇", "勇气", "共情", "同情", "怜悯", "怜爱情结", "多元之爱",
        "偷懒之乐", "漫游欲", "远方向往", "惊奇", "惊喜"
    ],
    "negative": [
        "愤怒", "焦虑", "悲伤", "恐惧", "绝望", "沮丧", "忧郁", "孤独",
        "内疚", "羞耻", "羞辱", "懊悔", "遗憾", "愤恨", "嫉妒", "妒忌",
        "嫉羡", "不满", "气恼", "恼怒", "困惑", "不知所措", "茫然",
        "震惊", "恐慌", "惊骇", "厌世", "厌倦", "冷漠", "气馁",
        "失望", "厌恶", "惧怕", "尴尬", "仇恨", "神经过敏",
        "自怨自艾", "自惭形秽", "不堪重负", "烦躁", "担忧",
        "忧虑不安", "时间焦虑", "路怒", "暴躁", "狂怒",
        "羞愤", "亏欠感", "脆弱", "不确定", "多疑", "妄想",
        "幸灾乐祸", "愤愤不平", "作死", "起床气", "怕鬼"
    ],
    "mixed": [
        "怀旧思乡", "乡愁", "思乡", "惆怅", "物哀", "失落的忧愁",
        "人去心空", "隐忍", "悲天悯人", "异境茫然", "虚空的呼唤",
        "猎奇", "撒娇依赖", "求子心切", "收藏欲", "亲吻渴望",
        "情欲", "避世", "复仇", "竞争", "废物的迷恋"
    ],
    "social": [
        "共情", "同情", "怜悯", "幸灾乐祸", "替人脸红", "多元之爱",
        "怕麻烦别人", "社交焦虑", "妒忌", "嫉羡", "竞争", "义愤",
        "被侮辱", "藐视", "不满", "责备"
    ],
}

# 情绪强度参考值（用于辅助评分）
EMOTION_INTENSITY_REFERENCE = {
    "high": ["狂怒", "狂喜", "绝望", "惊骇", "恐惧", "仇恨", "暴怒"],
    "medium": ["愤怒", "焦虑", "激动", "兴奋", "沮丧", "忧郁", "震惊"],
    "low": ["平静", "满足", "满意", "无忧无虑", "冷静", "有点气恼", "困惑"],
}