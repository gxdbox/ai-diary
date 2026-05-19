# AI伴侣 - Prompt 加载器

import os
from typing import Optional

PROMPTS_DIR = "prompts"


def load_prompt(version: str = "v1.0") -> str:
    """加载指定版本的Prompt"""
    prompt_file = os.path.join(PROMPTS_DIR, f"xiaoban_{version}.md")

    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Prompt文件不存在: {prompt_file}")

    with open(prompt_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析Markdown，提取核心Prompt（去掉元数据和情绪模板）
    lines = content.split("\n")
    prompt_lines = []
    in_main_section = False
    in_emotion_section = False

    for line in lines:
        if line.startswith("---"):
            if not in_main_section and not in_emotion_section:
                in_main_section = True
                continue
            elif in_main_section and not in_emotion_section:
                in_main_section = False
                in_emotion_section = True
                continue
            else:
                break

        if in_main_section and not line.startswith("# 情绪类型"):
            prompt_lines.append(line)

    return "\n".join(prompt_lines)


def get_emotion_template(emotion: Optional[str] = None) -> str:
    """获取情绪匹配模板"""
    if not emotion:
        return ""

    emotion_templates = {
        "焦虑": "先安抚：\"听起来你最近压力很大...\" 引导思考具体原因。",
        "悲伤": "先共情：\"我能感受到你的难过...\" 表达陪伴和支持。",
        "愤怒": "先接纳：\"听起来这件事让你很生气...\" 理解情绪的自然性。",
        "困惑": "先共情：\"这种迷茫的感觉确实让人不安...\" 温和陪伴探索。",
        "孤独": "先连接：\"谢谢你愿意告诉我这些...\" 强调你并不孤单。",
        "恐惧": "先安抚：\"听起来这件事让你很害怕...\" 解释这是正常的反应。",
        "自豪": "先肯定：\"太棒了！这真的很不容易...\" 庆祝成就。",
        "不满": "先理解：\"听起来你对这件事不满意...\" 倾听具体困扰。",
        "矛盾": "先共情：\"这种纠结的感觉确实让人困惑...\" 探索两种想法。",
        "如释重负": "先祝贺：\"听起来你终于放下了...\" 肯定这个释然的时刻。"
    }

    return emotion_templates.get(emotion, "")


# 当前使用的Prompt版本
CURRENT_VERSION = "v1.0"


def get_system_prompt(emotion: Optional[str] = None) -> str:
    """获取完整的系统Prompt，可选添加情绪模板"""
    base_prompt = load_prompt(CURRENT_VERSION)

    if emotion:
        emotion_hint = get_emotion_template(emotion)
        if emotion_hint:
            base_prompt += f"\n\n## 当前用户情绪提示\n用户情绪类型为【{emotion}】，建议回应风格：{emotion_hint}"

    return base_prompt