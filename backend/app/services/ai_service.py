"""
AI 服务 - 业务层

底层 LLM 调用委托给 services/ai/client.py (LLMClient)
本模块保留日记相关的 AI 业务方法
"""
import json
import asyncio
import logging
from typing import Dict, List

from app.services.ai.client import llm
from app.services.ai.prompts.cleaner import (
    TEXT_CLEANER_SYSTEM, CLEAN_TEXT_USER_TEMPLATE, build_cleaner_prompt
)
from app.data.emotions import EMOTION_VOCABULARY, EMOTION_DIMENSIONS

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务 - 日记分析业务方法"""

    async def call_llm(
        self, prompt: str, max_tokens: int = 2000, temperature: float = None
    ) -> str:
        """调用大语言模型（简单文本模式）"""
        kwargs = {"max_tokens": max_tokens}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await llm.simple_chat(prompt, **kwargs)

    async def call_llm_with_messages(
        self, messages: List[Dict], max_tokens: int = 2000, temperature: float = None
    ) -> str:
        """调用大语言模型（消息列表模式）"""
        kwargs = {"max_tokens": max_tokens}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return await llm.chat(messages, **kwargs)

    async def clean_text(self, raw_text: str) -> str:
        """清洗语音转写文本 — 使用 System Prompt 纠正 ASR 同音词错误

        三层处理流程：
        1. 前置：拼音模糊匹配 + 发音混淆规则矫正
        2. AI：注入自定义词典到 System Prompt，让 LLM 语义级纠错
        3. 后置：检查输出中词典词是否已正确出现，兜底修正
        """
        from app.api.dictionary import (
            dictionary_words, apply_dictionary_correction, post_correct
        )

        # 1. 前置处理：拼音/近音/英文匹配
        corrected_text = apply_dictionary_correction(raw_text)

        # 2. AI 清洗：注入自定义词典
        system_prompt = build_cleaner_prompt(
            list(dictionary_words) if dictionary_words else None
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": CLEAN_TEXT_USER_TEMPLATE.format(text=corrected_text)},
        ]

        result = await self.call_llm_with_messages(
            messages, max_tokens=2000, temperature=0.2
        )
        result = result.strip()

        # 3. 后置处理：词典词兜底检查
        result = post_correct(result, list(dictionary_words))

        return result

    async def analyze_emotion(self, text: str) -> Dict:
        """分析文本情绪 - 使用能量值+强度双维度体系"""
        emotion_groups = {
            "积极情绪": ["幸福", "快乐", "欣喜", "欢快", "高兴", "满足", "感恩", "自豪", "期待", "激动", "狂喜", "温情", "自信", "欣慰", "无忧无虑", "如释重负", "归家之喜", "温馨", "冷静"],
            "消极情绪": ["愤怒", "焦虑", "悲伤", "恐惧", "绝望", "沮丧", "忧郁", "孤独", "内疚", "羞耻", "懊悔", "遗憾", "愤恨", "嫉妒", "不满", "气恼", "困惑", "震惊", "恐慌", "厌倦", "冷漠", "气馁", "失望", "厌恶", "惧怕", "尴尬", "仇恨", "不堪重负", "烦躁", "担忧"],
            "复杂情绪": ["怀旧思乡", "惆怅", "物哀", "隐忍", "人去心空", "异境茫然", "失落", "矛盾", "乡愁", "悲天悯人"],
            "社交情绪": ["共情", "同情", "幸灾乐祸", "替人脸红", "怕麻烦别人", "妒忌", "竞争", "义愤", "怜悯"],
        }

        emotion_list_parts = []
        for group, emotions in emotion_groups.items():
            emotion_list_parts.append(f"\n【{group}】\n{', '.join(emotions)}")
        emotion_list = "".join(emotion_list_parts)

        prompt = f"""你是一个专业的情绪分析专家。请分析以下日记内容。

【日记内容】
{text}

【情绪词汇表】
{emotion_list}

【分析要求】
1. 从词汇表中选择最匹配的情绪词

2. 判断【情绪能量值】（-10到+10）：
   - 正数表示有正向能量、消耗少（如：快乐+6、平静+2、满足+4）
   - 负数表示有负向能量、消耗多（如：焦虑-6、狂怒-9、悲伤-7）
   - 需根据日记上下文判断，同一情绪词在不同语境下能量值不同

3. 判断【情绪强度】（1到10）：
   - 表示情绪的强烈程度，不区分正负
   - 高强度(8-10)：狂喜、狂怒、崩溃
   - 中强度(5-7)：快乐、愤怒、担忧
   - 低强度(1-4)：平静、轻微惆怅

【判断原则】
- 能量值核心：这个情绪对心理能量的影响
  - 消耗能量→负值，补充能量→正值
- 强度核心：情绪的激烈程度

请返回JSON格式（仅返回JSON）：
{{
    "emotion": "主要情绪",
    "secondary_emotions": ["次要情绪"],
    "energy": 能量值(-10到+10),
    "intensity": 强度(1-10),
    "keywords": ["关键词"],
    "confidence": 信心度(0.0-1.0)
}}"""

        result = await self.call_llm(prompt)

        try:
            json_str = result.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            parsed = json.loads(json_str)
            primary = parsed.get("emotion", "冷静")
            primary = self._validate_emotion(primary)

            energy = float(parsed.get("energy", 0))
            intensity = float(parsed.get("intensity", 5.0))
            energy = max(-10, min(10, energy))
            intensity = max(1, min(10, intensity))

            return {
                "emotion": primary,
                "secondary_emotions": parsed.get("secondary_emotions", [])[:2],
                "energy": energy,
                "intensity": intensity,
                "keywords": parsed.get("keywords", [])[:5],
                "confidence": float(parsed.get("confidence", 0.8)),
            }
        except json.JSONDecodeError:
            logger.warning(f"JSON解析失败: {result}")
            return {
                "emotion": "冷静",
                "secondary_emotions": [],
                "energy": 0.0,
                "intensity": 5.0,
                "keywords": [],
                "confidence": 0.5,
            }

    def _validate_emotion(self, emotion: str) -> str:
        """验证情绪词是否在词汇表中，否则映射到最接近的"""
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
        """完整分析：情绪、主题、事件 - 并行执行"""
        emotion, topics, events = await asyncio.gather(
            self.analyze_emotion(text),
            self.extract_topics(text),
            self.extract_key_events(text),
        )
        return {"emotion": emotion, "topics": topics, "key_events": events}

    async def answer_question(self, question: str, context: str) -> str:
        """基于上下文回答问题（RAG）"""
        prompt = f"""你是一个智能日记助手。请根据用户的日记内容回答问题。

相关日记内容：
{context}

用户问题：{question}

请根据日记内容给出准确、有帮助的回答。如果日记中没有相关信息，请诚实说明。"""

        return await self.call_llm(prompt)


ai_service = AIService()
