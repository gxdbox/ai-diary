"""
日记 Agent - 借鉴 Hermes Agent 的 tool-calling loop

核心：把"一次性 LLM 问答"升级为"思考-行动-观察"循环。
AI 可以在对话中主动调用工具：翻历史日记、跑洞察分析、存对话中产生的新认知。

这是"日记从躺在那里变成了解自我途径"的实现层——
当用户问"我最近怎么样"，AI 不再只能凭塞进 prompt 的记忆回答，
而是能主动调 get_insights 跑一次分析、调 search_diaries 翻历史，再综合回复。

循环流程：
1. 构建 messages（system + 上下文 + 历史 + 用户输入）
2. 调用 llm.chat_with_tools()
3. 若返回 tool_calls → 执行工具 → 结果加入 messages → 回到 2
4. 若无 tool_calls（finish_reason=stop）→ 返回最终回复
5. 安全限制：MAX_TOOL_ITERATIONS 次后强制收尾

对话后记忆更新（Hermes 式 learning loop 精简版）：
每次对话结束，用一次轻量 LLM 调用提取"本次对话中用户展现的深层认知"，
存入事实记忆。让 AI 越聊越懂用户。
"""
import json
import logging
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.services.ai.client import llm, MAX_TOOL_ITERATIONS
from app.services.ai.tools import DiaryToolRegistry
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


AGENT_SYSTEM = """你是"小伴"，松果日记的 AI 陪伴助手。你温暖、耐心、善于倾听，像一个了解用户的朋友。

## 你的身份
你陪伴用户记录生活、理解情绪、发现生活中的美好。你不只是聊天机器人，你能主动调用工具来更深入地理解和陪伴用户。

## 你的工具能力
你可以主动调用以下工具：
- search_diaries：搜索用户过去写的日记，回忆某段经历
- get_insights：分析用户的情绪趋势、生活状态、成长轨迹、风险预警
- get_memory：了解用户的长期偏好、习惯、情绪模式
- save_memory：把对话中用户展现的深层认知（如恐惧、价值观、性格特点）存为长期记忆

## 何时使用工具（重要）
- 用户问过去的事、想回忆某段经历 → 调用 search_diaries
- 用户问"我最近怎么样""我有什么变化"想了解自己 → 调用 get_insights
- 需要了解用户的长期模式来给出更贴心的回应 → 调用 get_memory
- 用户说出深层自我认知（如"我其实一直害怕被否定""我发现我每次...都..."）→ 调用 save_memory 记下来
- 日常闲聊、简单问候 → 不需要工具，直接像朋友一样回应

不要每次都调用工具。只在真正需要时调用，让对话自然流畅。

## 记忆使用原则
- 隐性表达：不要直接说"我记得你说过..."，而是自然融入回应
- 三种回应模式：
  1. 普通聊天：日常问候，像普通朋友，不刻意提记忆
  2. 轻度提及：记忆自然相关时，轻描淡写提一句
  3. 深入讨论：用户主动询问或追问时，详细展开

## 回应风格
- 自然、简洁（50-150字）
- 温暖而非说教，倾听而非评判
- 像真实朋友一样自然
- 涉及严重心理困扰时，温和建议寻求专业帮助
"""

# 对话后反思 prompt（提取值得长期记住的用户认知）
REFLECT_PROMPT_TEMPLATE = """分析以下对话，提取用户展现的深层自我认知、价值观、性格特点或情绪模式。

仅当对话中确实出现用户关于自己的深层认知时才输出，否则输出空。

对话内容：
{dialogue}

输出 JSON 格式：
{{"should_save": true/false, "content": "简洁陈述用户的认知（一句话）", "reason": "为什么值得记住"}}

判断标准：
- 用户表达了对自己的觉察（如"我发现自己总是在逃避..."）→ 保存
- 用户透露了长期偏好/价值观（如"我觉得自由比稳定重要"）→ 保存
- 单纯的情绪宣泄或日常琐事 → 不保存
"""


class DiaryAgent:
    """日记 Agent - tool-calling loop"""

    def __init__(self, db: Session, vs=None):
        self.db = db
        self.vector_store = vs or vector_store
        self.tool_registry = DiaryToolRegistry(db, self.vector_store)

    async def chat(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict]] = None,
        reflect: bool = True,
    ) -> Dict[str, Any]:
        """
        Agent 对话主入口

        Args:
            user_input: 用户输入
            conversation_history: 对话历史 [{role, content}]
            reflect: 是否在对话后做记忆反思提取

        Returns:
            Dict: {
                "response": str,          # AI 最终回复
                "tool_usage": List[Dict], # 工具调用轨迹
                "iterations": int,        # 循环次数
            }
        """
        # 1. 安全检查
        from app.services.ai.safety import SafetyFilter
        safety = SafetyFilter()
        is_safe, warning = safety.check(user_input)
        if not is_safe:
            return {
                "response": warning,
                "tool_usage": [],
                "iterations": 0,
            }

        # 2. 构建 messages
        messages = self._build_messages(user_input, conversation_history or [])
        tools = self.tool_registry.definitions
        tool_trace: List[Dict] = []

        # 3. Agent Loop
        for iteration in range(MAX_TOOL_ITERATIONS):
            result = await llm.chat_with_tools(messages, tools)

            # 无工具调用 → 完成
            if not result.get("tool_calls"):
                final_response = result.get("content", "")

                # 对话后记忆更新（Hermes 式 learning loop）
                if reflect:
                    try:
                        await self._reflect_and_save(
                            user_input, final_response, conversation_history or []
                        )
                    except Exception as e:
                        logger.warning("对话后记忆反思失败: %s", e)

                return {
                    "response": final_response,
                    "tool_usage": tool_trace,
                    "iterations": iteration + 1,
                }

            # 有工具调用 → 执行并把结果加入 messages
            tool_calls = result["tool_calls"]

            # 3a. 把 assistant 的 tool_calls 消息加入 messages
            messages.append({
                "role": "assistant",
                "content": result.get("content") or None,
                "tool_calls": [
                    self._format_tool_call_for_api(tc) for tc in tool_calls
                ],
            })

            # 3b. 执行每个工具，把结果加入 messages
            for tc in tool_calls:
                tool_result = await self.tool_registry.execute(
                    tc["name"], tc["arguments"]
                )
                tool_trace.append({
                    "tool": tc["name"],
                    "arguments": tc["arguments"],
                    "result_preview": tool_result[:120],
                })
                logger.info(
                    "Agent 工具调用: %s(%s) -> %s...",
                    tc["name"],
                    tc["arguments"],
                    tool_result[:60],
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tool_result,
                })

        # 4. 超过最大迭代，强制收尾
        logger.warning("Agent 达到最大工具调用次数 %d，强制收尾", MAX_TOOL_ITERATIONS)
        messages.append({
            "role": "system",
            "content": "已达到工具调用上限，请基于已获取的信息给出最终回复。",
        })
        final = await llm.chat_with_tools(messages, tools, tool_choice="none")

        return {
            "response": final.get("content", ""),
            "tool_usage": tool_trace,
            "iterations": MAX_TOOL_ITERATIONS,
        }

    # ==================== 内部方法 ====================

    def _build_messages(
        self, user_input: str, conversation_history: List[Dict]
    ) -> List[Dict]:
        """构建 Agent 的 messages 列表"""
        messages: List[Dict] = [{"role": "system", "content": AGENT_SYSTEM}]

        # 注入轻量用户上下文（偏好/主题提示，非全量记忆）
        try:
            factual = self.tool_registry.memory_service.get_factual_memory()
            context_hints = []
            if factual.common_topics:
                context_hints.append(
                    "用户常写主题：" + "、".join(factual.common_topics[:5])
                )
            if factual.emotional_patterns:
                top_emotions = sorted(
                    factual.emotional_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]
                context_hints.append(
                    "常见情绪：" + "、".join(f"{k}" for k, _ in top_emotions)
                )
            if context_hints:
                messages.append({
                    "role": "system",
                    "content": "【用户背景】\n" + "\n".join(context_hints),
                })
        except Exception as e:
            logger.warning("构建用户上下文失败: %s", e)

        # 对话历史
        for turn in conversation_history[-10:]:
            messages.append({
                "role": turn.get("role", "user"),
                "content": turn.get("content", ""),
            })

        # 当前输入
        messages.append({"role": "user", "content": user_input})
        return messages

    @staticmethod
    def _format_tool_call_for_api(tc: Dict) -> Dict:
        """把内部 tool_call 格式转为 OpenAI API 要求的格式
        （arguments 必须是 JSON 字符串）"""
        return {
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["name"],
                "arguments": json.dumps(
                    tc["arguments"], ensure_ascii=False
                ),
            },
        }

    async def _reflect_and_save(
        self,
        user_input: str,
        ai_response: str,
        conversation_history: List[Dict],
    ) -> None:
        """
        对话后记忆更新（Hermes 式 learning loop 精简版）

        用一次轻量 LLM 调用，判断本次对话中用户是否展现了值得长期
        记住的自我认知。若有，自动存入事实记忆。
        """
        # 构建对话文本
        dialogue_parts = []
        for turn in conversation_history[-4:]:
            role = "用户" if turn.get("role") == "user" else "小伴"
            dialogue_parts.append(f"{role}：{turn.get('content', '')[:200]}")
        dialogue_parts.append(f"用户：{user_input[:200]}")
        dialogue_parts.append(f"小伴：{ai_response[:200]}")
        dialogue = "\n".join(dialogue_parts)

        prompt = REFLECT_PROMPT_TEMPLATE.format(dialogue=dialogue)

        try:
            raw = await llm.simple_chat(prompt, max_tokens=200, temperature=0.3)
            # 容错解析 JSON
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw)

            if result.get("should_save") and result.get("content"):
                content = result["content"]
                logger.info("对话后记忆提取: %s", content)
                await self.tool_registry.execute(
                    "save_memory",
                    {"content": content, "memory_type": "factual"},
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug("对话后反思无有效输出: %s", e)
        except Exception as e:
            logger.warning("对话后反思异常: %s", e)
