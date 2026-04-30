# AI伴侣 - 主聊天引擎（支持对话记忆+情绪匹配+Prompt版本管理）

import os
import re
from typing import Optional, List
import httpx
from openai import OpenAI

import config
from backend.database import ConversationDB, FeedbackDB
from backend.modules.llm.core.prompt_loader import get_system_prompt, CURRENT_VERSION


class AICompanionEngine:
    """AI伴侣核心引擎 - 支持对话记忆和情绪匹配"""

    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.api_base = config.DEEPSEEK_API_BASE
        self.model = config.DEEPSEEK_MODEL
        self.client = None
        self.memory_limit = 5  # 滑动窗口：记住最近5轮对话

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
            print(f"✓ DeepSeek API 初始化成功 (Prompt版本: {CURRENT_VERSION})")
        except Exception as e:
            print(f"警告: API 初始化失败: {e}")
            self.client = None

    def is_safe_input(self, text: str) -> tuple:
        """安全检查"""
        for word in config.BLOCKED_WORDS:
            if re.search(word, text):
                return False, config.CRISIS_RESPONSE
        return True, ""

    def _build_messages(self, user_input: str, emotion: Optional[str] = None) -> List[dict]:
        """构建消息列表，包含对话历史"""
        messages = [
            {"role": "system", "content": get_system_prompt(emotion)}
        ]

        # 加载对话历史（滑动窗口）
        history = ConversationDB.get_recent_conversations(self.memory_limit)
        for conv in reversed(history):  # 按时间顺序
            messages.append({"role": "user", "content": conv["user_input"]})
            messages.append({"role": "assistant", "content": conv["ai_response"]})

        # 当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def chat(
        self,
        user_input: str,
        emotion: Optional[str] = None,
        diary_id: Optional[int] = None
    ) -> dict:
        """生成回应，返回完整结果"""
        # 安全检查
        is_safe, warning = self.is_safe_input(user_input)
        if not is_safe:
            return {"response": warning, "conversation_id": None, "safe": False}

        if self.client:
            try:
                # 构建消息（含历史）
                messages = self._build_messages(user_input, emotion)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    top_p=0.9,
                    max_tokens=500
                )

                ai_response = response.choices[0].message.content

                # 保存对话记录
                conv_id = ConversationDB.save_conversation(
                    user_input=user_input,
                    ai_response=ai_response,
                    diary_id=diary_id,
                    emotion_before=emotion
                )

                return {
                    "response": ai_response,
                    "conversation_id": conv_id,
                    "safe": True,
                    "emotion_detected": emotion,
                    "prompt_version": CURRENT_VERSION
                }

            except Exception as e:
                print(f"API 调用失败: {e}")
                return {"response": self._fallback_response(), "conversation_id": None, "safe": True}
        else:
            return {"response": self._fallback_response(), "conversation_id": None, "safe": True}

    def simple_chat(self, user_input: str) -> str:
        """简化接口，只返回回应文本"""
        result = self.chat(user_input)
        return result["response"]

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