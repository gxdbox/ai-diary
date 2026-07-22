"""
统一 LLM 客户端 - 所有 AI 调用的唯一入口

职责：
1. 封装 LLM API 调用细节
2. 统一错误处理和降级
3. 便于切换模型 Provider
"""
import json
import httpx
import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Agent Loop 安全限制
MAX_TOOL_ITERATIONS = 5


class LLMClient:
    """统一 LLM 调用客户端"""

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.model = DEEPSEEK_MODEL

    async def chat(
        self,
        messages: List[Dict],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        调用 LLM（消息列表模式）

        Args:
            messages: OpenAI 格式消息列表
            max_tokens: 最大生成 token 数
            temperature: 采样温度
            top_p: 核采样参数

        Returns:
            str: 模型回复文本
        """
        if not self.api_key:
            logger.warning("未配置 API Key，使用模拟响应")
            return self._mock_response(messages)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM 调用失败: {response.status_code} - {response.text}")
                    raise Exception(f"LLM 调用失败: {response.text}")

        except httpx.TimeoutException:
            logger.error("LLM 调用超时")
            return self._fallback_response()
        except Exception as e:
            logger.error(f"LLM 服务异常: {str(e)}")
            return self._fallback_response()

    async def simple_chat(self, prompt: str, max_tokens: int = 2000, temperature: float = None) -> str:
        """
        简单文本模式调用

        Args:
            prompt: 用户提示词
            max_tokens: 最大生成 token 数
            temperature: 采样温度（None 使用默认值）

        Returns:
            str: 模型回复文本
        """
        messages = [{"role": "user", "content": prompt}]
        kwargs = {"max_tokens": max_tokens}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await self.chat(messages, **kwargs)

    def _mock_response(self, messages: List[Dict]) -> str:
        """模拟响应（用于开发/测试）"""
        user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break

        if "清洗" in user_msg or "删除口语填充词" in user_msg:
            return "今天天气不错，我想出去走走。周末约朋友吃饭吧。"
        elif "情绪" in user_msg and "JSON" in user_msg:
            return '{"emotion": "高兴", "secondary_emotions": ["期待"], "energy": 6, "intensity": 6, "keywords": ["不错", "约朋友"], "confidence": 0.85}'
        elif "主题" in user_msg or "标签" in user_msg:
            return "生活,社交"
        elif "关键事件" in user_msg:
            return "约朋友吃饭"
        else:
            return "这是一个模拟响应。"

    def _fallback_response(self) -> str:
        """降级响应"""
        return "抱歉，我暂时无法连接到服务。请稍后再试。"

    async def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        """
        支持 function calling 的 LLM 调用

        DeepSeek API 兼容 OpenAI 格式，原生支持 tools 参数。

        Args:
            messages: 消息列表（含历史 tool 结果）
            tools: 工具定义列表（OpenAI function 格式）
            max_tokens: 最大生成 token 数
            temperature: 采样温度
            tool_choice: 工具选择策略 ("auto" | "none" | 指定工具)

        Returns:
            Dict: {
                "content": str,           # 文本回复（无工具调用时）
                "tool_calls": List|None,   # 工具调用列表
                "finish_reason": str,      # "stop" | "tool_calls"
            }

            tool_calls 元素格式::
                {"id": str, "name": str, "arguments": dict}
        """
        if not self.api_key:
            logger.warning("未配置 API Key，使用模拟响应")
            return {
                "content": self._mock_response(messages),
                "tool_calls": None,
                "finish_reason": "stop",
            }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": tools,
            "tool_choice": tool_choice,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data["choices"][0]["message"]
                    finish_reason = data["choices"][0].get("finish_reason", "stop")

                    # 解析 tool_calls（arguments 是 JSON 字符串，需解析为 dict）
                    raw_tool_calls = message.get("tool_calls")
                    tool_calls = None
                    if raw_tool_calls:
                        tool_calls = []
                        for tc in raw_tool_calls:
                            func = tc.get("function", {})
                            raw_args = func.get("arguments", "{}")
                            try:
                                parsed_args = (
                                    json.loads(raw_args)
                                    if isinstance(raw_args, str)
                                    else raw_args
                                )
                            except (json.JSONDecodeError, TypeError):
                                logger.warning(
                                    "tool arguments 解析失败: %s", raw_args
                                )
                                parsed_args = {}
                            tool_calls.append({
                                "id": tc.get("id", ""),
                                "name": func.get("name", ""),
                                "arguments": parsed_args,
                            })

                    return {
                        "content": message.get("content") or "",
                        "tool_calls": tool_calls,
                        "finish_reason": finish_reason,
                    }
                else:
                    logger.error(
                        "LLM tool 调用失败: %s - %s",
                        response.status_code,
                        response.text,
                    )
                    raise Exception(f"LLM 调用失败: {response.text}")

        except httpx.TimeoutException:
            logger.error("LLM tool 调用超时")
            return {
                "content": self._fallback_response(),
                "tool_calls": None,
                "finish_reason": "stop",
            }
        except Exception as e:
            logger.error("LLM tool 服务异常: %s", str(e))
            return {
                "content": self._fallback_response(),
                "tool_calls": None,
                "finish_reason": "stop",
            }


llm = LLMClient()
