# AI伴侣 - 主聊天引擎

import os
import re
from typing import Optional
import httpx
from openai import OpenAI

import config


class AICompanionEngine:
    """AI伴侣核心引擎 - 使用DeepSeek API"""

    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.api_base = config.DEEPSEEK_API_BASE
        self.model = config.DEEPSEEK_MODEL
        self.client = None

        if self.api_key:
            self._init_client()

    def _init_client(self):
        """初始化 OpenAI 客户端（兼容 DeepSeek）"""
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                http_client=httpx.Client()
            )
            print("✓ DeepSeek API 初始化成功")
        except Exception as e:
            print(f"警告: API 初始化失败: {e}")
            self.client = None

    # Prompt 模板（按第05章结构化设计 + Few-shot示例）
    SYSTEM_PROMPT = """## 角色
你是"小伴"，用户的情感陪伴助手。你温暖、耐心、善于倾听，像一个体贴的朋友。

## 任务
当用户分享日记或倾诉心情时：
1. 先识别情绪：判断用户情绪类型（焦虑、悲伤、愤怒、困惑、孤独等）
2. 共情回应：用匹配的语言表达理解
3. 温和引导：鼓励倾诉更多，或引导思考角度
4. 给予支持：真诚的鼓励和陪伴感

回应风格：自然、简洁（50-100字）、适当使用表情（😊 🤗 💪）

## 约束
- 禁止诊断或治疗：你不是心理医生
- 禁止说教评判：不要"你应该..."式的语气
- 禁止冗长回应：保持简短温暖
- 危机干预：用户表达极端负面情绪时，回复预设的危机信息

## 示例（Few-shot）
用户：我今天被领导批评了，觉得自己好失败。
小伴：听起来你真的很委屈😔 被批评的感觉确实不好受，尤其是当你已经很努力的时候。你愿意说说发生了什么吗？

用户：我觉得没人理解我，好孤独。
小伴：孤独的感觉真的很沉重。谢谢你愿意告诉我这些🤗 我在这里听着呢，你并不孤单。

用户：最近总是睡不着，脑子里全是担心的事。
小伴：听起来焦虑一直缠绕着你，这种感觉一定很疲惫😔 当这些担心的事出现时，有没有哪一个是让你最在意的？"""

    def is_safe_input(self, text: str) -> tuple:
        """安全检查"""
        for word in config.BLOCKED_WORDS:
            if re.search(word, text):
                return False, config.CRISIS_RESPONSE
        return True, ""

    def chat(self, user_input: str) -> str:
        """生成回应"""
        # 安全检查
        is_safe, warning = self.is_safe_input(user_input)
        if not is_safe:
            return warning

        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"API 调用失败: {e}")
                return self._fallback_response()
        else:
            return self._fallback_response()

    def _fallback_response(self) -> str:
        """降级响应"""
        return "抱歉，我暂时无法连接到服务。请稍后再试。😊"


# 全局实例
_engine: Optional[AICompanionEngine] = None


def get_engine() -> AICompanionEngine:
    """获取引擎实例"""
    global _engine
    if _engine is None:
        _engine = AICompanionEngine()
    return _engine