# AI伴侣 - 主聊天引擎

import os
import re
from typing import Optional

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

import config


class AICompanionEngine:
    """AI伴侣核心引擎 - 使用DeepSeek API"""

    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.api_base = config.DEEPSEEK_API_BASE
        self.model = config.DEEPSEEK_MODEL
        self.chain = None

        if self.api_key and LANGCHAIN_AVAILABLE:
            self._init_chain()

    def _init_chain(self):
        """初始化 LangChain LCEL 链"""
        try:
            # 使用 DeepSeek API（兼容 OpenAI 接口）
            self.llm = ChatOpenAI(
                model=self.model,
                temperature=0.7,
                api_key=self.api_key,
                base_url=self.api_base
            )

            # Prompt 模板
            self.prompt_template = """你是用户的情感陪伴助手，名叫"小伴"。你温暖、耐心、善于倾听。

## 你的核心原则

1. 始终以共情开头，先接纳情绪，再提供支持
2. 使用温和、鼓励性语言，避免说教或评判
3. 适当使用表情符号增强亲和力（如 😊 🤗 💪）
4. 回应要自然，像朋友聊天一样，不要太长

## 回应方式

当用户分享内容时：
- 先表达你理解他们的感受
- 温和地引导用户思考或倾诉更多
- 给予真诚的鼓励和支持
- 只有在用户明确需要时才给建议

## 注意

- 你不是心理医生，不做诊断或治疗
- 如果用户表达极端负面情绪，回复危机干预信息
- 保持回应简洁温暖，不要过于冗长

---

用户：{input}
小伴："""

            self.prompt = ChatPromptTemplate.from_template(self.prompt_template)
            self.output_parser = StrOutputParser()

            # 构建链
            self.chain = self.prompt | self.llm | self.output_parser

            print("✓ DeepSeek API + LangChain 初始化成功")

        except Exception as e:
            print(f"警告: LangChain 初始化失败: {e}")
            self.chain = None

    def is_safe_input(self, text: str) -> tuple[bool, str]:
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

        if self.chain:
            try:
                response = self.chain.invoke({"input": user_input})
                return response
            except Exception as e:
                print(f"LangChain 调用失败: {e}")
                return self._fallback_response(user_input)
        else:
            return self._fallback_response(user_input)

    def _fallback_response(self, user_input: str) -> str:
        """降级响应（无 API 时）"""
        return "抱歉，我暂时无法连接到服务。请稍后再试。😊"


# 全局实例
engine = None


def get_engine() -> AICompanionEngine:
    """获取引擎实例"""
    if engine is None:
        engine = AICompanionEngine()
    return engine