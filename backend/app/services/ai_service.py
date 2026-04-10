"""
DeepSeek AI服务 (OpenAI兼容API)
"""
import httpx
import json
import os
from typing import Dict, List, Optional
import logging
import asyncio

from app.data.emotions import EMOTION_VOCABULARY, EMOTION_DIMENSIONS

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
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """模拟响应（用于测试）"""
        if "清洗" in prompt or "删除口语填充词" in prompt:
            return "今天天气不错，我想出去走走。周末约朋友吃饭吧。"
        elif "情绪" in prompt and "JSON" in prompt:
            return '{"emotion": "高兴", "secondary_emotions": ["期待"], "dimension": "positive", "score": 7.5, "keywords": ["不错", "约朋友"], "confidence": 0.85}'
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
        """分析文本情绪 - 使用精细化的情绪分类体系"""

        # 构建情绪词汇表提示（分组展示）
        emotion_groups = {
            "积极情绪": ["幸福", "快乐", "欣喜", "欢快", "高兴", "满足", "感恩", "自豪", "期待", "激动", "狂喜", "温情", "自信", "欣慰", "无忧无虑", "如释重负", "归家之喜", "温馨", "冷静"],
            "消极情绪": ["愤怒", "焦虑", "悲伤", "恐惧", "绝望", "沮丧", "忧郁", "孤独", "内疚", "羞耻", "懊悔", "遗憾", "愤恨", "嫉妒", "不满", "气恼", "困惑", "震惊", "恐慌", "厌倦", "冷漠", "气馁", "失望", "厌恶", "惧怕", "尴尬", "仇恨", "不堪重负", "烦躁", "担忧"],
            "复杂情绪": ["怀旧思乡", "惆怅", "物哀", "隐忍", "人去心空", "异境茫然", "失落", "矛盾", "乡愁", "悲天悯人"],
            "社交情绪": ["共情", "同情", "幸灾乐祸", "替人脸红", "怕麻烦别人", "妒忌", "竞争", "义愤", "怜悯"],
        }

        # 构建提示词
        emotion_list_parts = []
        for group, emotions in emotion_groups.items():
            emotion_list_parts.append(f"\n【{group}】\n{', '.join(emotions)}")

        emotion_list = "".join(emotion_list_parts)

        prompt = f"""你是一个专业的情绪分析专家。请分析以下日记内容，从给定的情绪词汇中选择最匹配的情绪。

【日记内容】
{text}

【情绪词汇表】（基于《心情词典》精细化分类）
{emotion_list}

【分析要求】
1. 从词汇表中选择最匹配的情绪词（可以选择主要情绪和次要情绪）
2. 判断情绪维度：positive（积极）、negative（消极）、mixed（复杂）、social（社交相关）
3. 评估情绪强度（1-10）
4. 提取表达情绪的关键词

请返回以下JSON格式（仅返回JSON，不要其他内容）：
{{
    "emotion": "主要情绪（从词汇表中选择一个最匹配的）",
    "secondary_emotions": ["次要情绪1", "次要情绪2"],
    "dimension": "情绪维度（positive/negative/mixed/social）",
    "score": 情绪强度（1-10）,
    "keywords": ["关键词1", "关键词2"],
    "confidence": 信心度（0.0-1.0）
}}"""

        result = await self.call_llm(prompt)

        try:
            # 尝试解析JSON
            json_str = result.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            parsed = json.loads(json_str)

            # 验证并修正情绪词
            primary = parsed.get("emotion", "冷静")
            primary = self._validate_emotion(primary)

            return {
                "emotion": primary,
                "secondary_emotions": parsed.get("secondary_emotions", [])[:2],
                "dimension": parsed.get("dimension", "mixed"),
                "score": float(parsed.get("score", 5.0)),
                "keywords": parsed.get("keywords", [])[:5],
                "confidence": float(parsed.get("confidence", 0.8))
            }
        except json.JSONDecodeError:
            logger.warning(f"JSON解析失败，使用默认值: {result}")
            return {
                "emotion": "冷静",
                "secondary_emotions": [],
                "dimension": "mixed",
                "score": 5.0,
                "keywords": [],
                "confidence": 0.5
            }

    def _validate_emotion(self, emotion: str) -> str:
        """验证情绪词是否在词汇表中，否则映射到最接近的"""
        # 常见情绪映射表
        mapping = {
            "开心": "高兴",
            "难过": "悲伤",
            "伤心": "悲伤",
            "生气": "愤怒",
            "害怕": "恐惧",
            "担心": "担忧",
            "着急": "焦虑",
            "烦躁": "厌倦",
            "郁闷": "忧郁",
            "失落": "惆怅",
            "无聊": "厌倦",
            "平静": "冷静",
            "放松": "无忧无虑",
            "累": "倦怠",
            "疲惫": "倦怠",
            "兴奋": "激动",
            "倦怠": "倦怠",
        }
        return mapping.get(emotion, emotion)

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