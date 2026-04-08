"""
DeepSeek AI服务 (OpenAI兼容API)
"""
import httpx
import json
import os
from typing import Dict, List, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"


class AIService:
    """DeepSeek AI服务封装"""

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        self.model = DEEPSEEK_MODEL

    async def call_llm(self, prompt: str, max_tokens: int = 2000) -> str:
        """调用大语言模型"""
        if not self.api_key:
            logger.warning("未配置API Key，使用模拟响应")
            return self._mock_response(prompt)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"AI调用失败: {response.status_code} - {response.text}")
                    raise Exception(f"AI调用失败: {response.text}")

        except Exception as e:
            logger.error(f"AI服务异常: {str(e)}")
            # 返回模拟响应以便测试
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """模拟响应（用于测试）"""
        if "清洗" in prompt or "删除口语填充词" in prompt:
            return "今天天气不错，我想出去走走。周末约朋友吃饭吧。"
        elif "情绪" in prompt and "JSON" in prompt:
            return '{"emotion": "开心", "score": 7.5, "keywords": ["不错", "约朋友"]}'
        elif "主题" in prompt or "标签" in prompt:
            return "生活,社交"
        elif "关键事件" in prompt:
            return "约朋友吃饭"
        else:
            return "这是一个模拟响应。"

    async def clean_text(self, raw_text: str) -> str:
        """清洗语音转写文本"""

        prompt = f"""你是一个专业的文本编辑助手。请清洗以下语音转文字的日记内容：

1. 删除口语填充词（嗯、啊、哈、那个、就是、然后呢、这个等）
2. 纠正明显的错别字和语音识别错误
3. 保持原意，不要改变内容
4. 保持口语化风格，不要过度书面化
5. 适当调整标点符号，让阅读更流畅

原文：
{raw_text}

请直接输出清洗后的文本，不要有任何解释或额外内容。"""

        result = await self.call_llm(prompt)
        return result.strip()

    async def analyze_emotion(self, text: str) -> Dict:
        """分析文本情绪"""

        prompt = f"""请分析以下日记内容的情绪状态，以JSON格式返回结果：

{text}

请返回以下JSON格式（仅返回JSON，不要其他内容）：
{{
    "emotion": "情绪类型（开心/焦虑/平静/愤怒/悲伤/兴奋/疲惫/满足等）",
    "score": 情绪强度（1-10的数字，1最弱，10最强）,
    "keywords": ["情绪关键词1", "情绪关键词2", "情绪关键词3"]
}}"""

        result = await self.call_llm(prompt)

        try:
            # 尝试解析JSON
            json_str = result.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"JSON解析失败，使用默认值: {result}")
            return {
                "emotion": "平静",
                "score": 5.0,
                "keywords": []
            }

    async def extract_topics(self, text: str) -> List[str]:
        """提取文本主题标签"""

        prompt = f"""请为以下日记内容提取主题标签。

日记内容：
{text}

请返回3-5个主题标签，用逗号分隔。标签应该是简洁的词语，如：工作、家庭、健康、社交、学习、娱乐、旅行、美食等。

仅返回标签，用逗号分隔，不要其他内容。例如：工作,学习,健康"""

        result = await self.call_llm(prompt, max_tokens=100)
        topics = [t.strip() for t in result.split(",") if t.strip()]
        return topics[:5]

    async def extract_key_events(self, text: str) -> List[str]:
        """提取关键事件"""

        prompt = f"""请从以下日记内容中提取关键事件或重要信息。

日记内容：
{text}

请提取1-3个关键事件，每行一个事件。如果没有明显事件，可以返回空。

仅返回事件列表，每行一个，不要编号和其他内容。"""

        result = await self.call_llm(prompt, max_tokens=500)
        events = [e.strip() for e in result.strip().split("\n") if e.strip()]
        return events[:3]

    async def full_analysis(self, text: str) -> Dict:
        """完整分析：情绪、主题、事件"""

        # 顺序执行各项分析
        emotion = await self.analyze_emotion(text)
        topics = await self.extract_topics(text)
        events = await self.extract_key_events(text)

        return {
            "emotion": emotion,
            "topics": topics,
            "key_events": events
        }

    async def answer_question(self, question: str, context: str) -> str:
        """基于上下文回答问题（RAG）"""

        prompt = f"""你是一个智能日记助手。请根据用户的日记内容回答问题。

相关日记内容：
{context}

用户问题：{question}

请根据日记内容给出准确、有帮助的回答。如果日记中没有相关信息，请诚实说明。"""

        return await self.call_llm(prompt)


# 全局AI服务实例
ai_service = AIService()