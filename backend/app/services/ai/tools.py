"""
日记 Agent 工具集

借鉴 Hermes Agent 的 tool-calling 理念，将 ai-diary 已有的能力
（向量检索、洞察分析、记忆管理）封装为 LLM 可主动调用的工具。

这是"日记从躺在那里变成了解自我途径"的关键——AI 不再被动回答，
而是能在对话中主动翻历史日记、跑洞察分析、把对话中产生的新认知存入记忆。

工具清单（MVP 4 个）:
1. search_diaries  - 语义检索日记（复用 VectorStore）
2. get_insights    - 调用 InsightAnalyzer 获取深度洞察
3. get_memory      - 检索用户事实/情节记忆
4. save_memory     - 对话中产生的新认知存入记忆（Hermes 式 learning loop）
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.services.vector_store import VectorStore
from app.services.memory_service import MemoryService
from app.models.memory import MemoryType

logger = logging.getLogger(__name__)


class DiaryToolRegistry:
    """日记 Agent 工具注册表"""

    def __init__(
        self,
        db: Session,
        vector_store: VectorStore,
        memory_service: Optional[MemoryService] = None,
        insight_analyzer=None,
        user_id: Optional[int] = None,
    ):
        self.db = db
        self.vector_store = vector_store
        self.user_id = user_id
        self.memory_service = memory_service or MemoryService(db)
        # 延迟导入避免循环依赖
        if insight_analyzer is None:
            from app.services.insight_analyzer import insight_analyzer as _ia
            insight_analyzer = _ia
        self.insight_analyzer = insight_analyzer

    # ==================== 工具定义（OpenAI function 格式）====================

    @property
    def definitions(self) -> List[Dict]:
        """返回 OpenAI 兼容的 tools 定义列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_diaries",
                    "description": (
                        "语义搜索用户的历史日记内容。当需要回忆某段经历、"
                        "查找过往记录、或回答关于过去事件的问题时调用。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索词或语义查询，例如'工作压力'、'和家人吃饭'",
                            },
                            "days": {
                                "type": "integer",
                                "description": "回溯天数，默认30天",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_insights",
                    "description": (
                        "获取对用户日记的深度洞察分析，帮助用户认识自己。"
                        "可分析情绪健康、生活平衡、人际关系、成长趋势、风险预警等。"
                        "当用户询问'我最近怎么样''我有什么变化'或需要自我认知时调用。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "分析周期天数，默认90天",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_memory",
                    "description": (
                        "检索用户的长期记忆，包括事实记忆（偏好、习惯、情绪模式）"
                        "和情节记忆（历史日记摘要）。当需要了解用户的长期特征或"
                        "查找相似过往经历时调用。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_type": {
                                "type": "string",
                                "enum": ["factual", "episodic"],
                                "description": "记忆类型：factual=偏好/习惯，episodic=日记摘要",
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "检索关键词（可选）",
                            },
                        },
                        "required": ["memory_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": (
                        "将对话中发现的用户自我认知、情绪模式或重要信息保存为"
                        "长期记忆。例如用户说出'我其实一直很怕被否定'这类深层"
                        "认知时调用，让 AI 在未来对话中能记住。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "要保存的记忆内容（简洁陈述）",
                            },
                            "memory_type": {
                                "type": "string",
                                "enum": ["factual", "episodic"],
                                "description": "factual=用户偏好/认知，episodic=具体事件",
                                "default": "factual",
                            },
                            "importance": {
                                "type": "number",
                                "description": "重要性评分0-1，默认0.7",
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
        ]

    # ==================== 工具执行路由 ====================

    async def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """根据工具名执行对应 handler，返回文本结果供 LLM 使用"""
        try:
            if name == "search_diaries":
                return await self._search_diaries(**arguments)
            elif name == "get_insights":
                return await self._get_insights(**arguments)
            elif name == "get_memory":
                return await self._get_memory(**arguments)
            elif name == "save_memory":
                return await self._save_memory(**arguments)
            else:
                return f"未知工具: {name}"
        except Exception as e:
            logger.error("工具 %s 执行失败: %s", name, e)
            return f"工具执行失败: {str(e)}"

    # ==================== 工具实现 ====================

    async def _search_diaries(self, query: str, days: int = 30) -> str:
        """语义检索日记：向量召回 + DB 补全完整内容"""
        # 1. 向量语义检索
        results = self.vector_store.search(query, n_results=5, user_id=self.user_id)
        if not results:
            return "未找到相关日记。"

        # 2. 从 DB 获取完整日记内容并按时间过滤
        cutoff = datetime.utcnow() - timedelta(days=days)
        formatted = []

        for r in results:
            diary_id = r.get("id")
            try:
                row = self.db.execute(
                    sa_text(
                        "SELECT id, cleaned_text, raw_text, emotion, "
                        "emotion_score, topics, created_at "
                        "FROM diaries WHERE id = :did AND user_id = :uid"
                    ),
                    {"did": diary_id, "uid": self.user_id},
                ).fetchone()
            except Exception:
                continue

            if not row:
                continue

            created = row[6]
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created)
                except (ValueError, TypeError):
                    created = datetime.utcnow()
            if not created or created < cutoff:
                continue

            content = row[1] or row[2] or ""
            if len(content) > 300:
                content = content[:300] + "..."
            emotion = row[3] or "未知"
            score = row[4] if row[4] is not None else "-"
            date_str = created.strftime("%Y-%m-%d") if created else "未知"

            formatted.append(
                f"[{date_str}] 情绪:{emotion}({score})\n{content}"
            )

        if not formatted:
            return f"近{days}天未找到与『{query}』相关的日记。"

        return f"找到 {len(formatted)} 篇相关日记：\n\n" + "\n\n---\n\n".join(
            formatted
        )

    async def _get_insights(self, days: int = 90) -> str:
        """调用 InsightAnalyzer 生成深度洞察"""
        # 1. 从 DB 拉取近 N 天的日记
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = self.db.execute(
            sa_text(
                "SELECT id, cleaned_text, raw_text, emotion, emotion_score, "
                "topics, key_events, created_at "
                "FROM diaries WHERE created_at >= :cutoff AND user_id = :uid "
                "ORDER BY created_at DESC"
            ),
            {"cutoff": cutoff, "uid": self.user_id},
        ).fetchall()

        if not rows:
            return f"近{days}天没有日记数据，无法生成洞察。"

        # 2. 转为 InsightAnalyzer 期望的 dict 列表
        diaries = []
        for row in rows:
            topics = row[5]
            if isinstance(topics, str):
                try:
                    topics = json.loads(topics)
                except (json.JSONDecodeError, TypeError):
                    topics = []
            key_events = row[6]
            if isinstance(key_events, str):
                try:
                    key_events = json.loads(key_events)
                except (json.JSONDecodeError, TypeError):
                    key_events = []

            diaries.append({
                "id": row[0],
                "cleaned_text": row[1] or row[2] or "",
                "raw_text": row[2] or "",
                "emotion": row[3],
                "emotion_score": row[4] if row[4] is not None else 5,
                "topics": topics or [],
                "key_events": key_events or [],
                "created_at": row[7],
            })

        # 3. 调用分析器
        response = self.insight_analyzer.analyze(diaries, days=days)

        # 4. 格式化为 LLM 可读文本
        parts = [f"## 洞察分析（近{days}天，{len(diaries)}篇日记）"]
        parts.append(f"\n**总体：** {response.overall_summary}")

        for cat in response.categories:
            if not cat.insights:
                continue
            parts.append(f"\n### {cat.category_icon} {cat.category_name}")
            for ins in cat.insights:
                line = f"- **{ins.title}**：{ins.insight}"
                if ins.suggestion:
                    line += f"\n  _{ins.suggestion}_"
                parts.append(line)

        return "\n".join(parts) if len(parts) > 1 else "暂无可用的洞察。"

    async def _get_memory(
        self, memory_type: str, keywords: Optional[List[str]] = None
    ) -> str:
        """检索用户记忆"""
        if memory_type == "factual":
            factual = self.memory_service.get_factual_memory(user_id=self.user_id)
            parts = []
            if factual.common_topics:
                parts.append("常写主题：" + "、".join(factual.common_topics[:8]))
            if factual.emotional_patterns:
                pat = "、".join(
                    f"{k}{v}次" for k, v in factual.emotional_patterns.items()
                )
                parts.append(f"情绪模式：{pat}")
            if factual.user_preferences:
                parts.append(
                    "偏好：" + json.dumps(
                        factual.user_preferences, ensure_ascii=False
                    )
                )

            # 同时返回个体高重要性事实记忆（含对话中保存的自我认知）
            try:
                raw_memories = self.memory_service._get_memories_by_type(
                    MemoryType.FACTUAL, limit=20, user_id=self.user_id
                )
                individual = []
                for m in raw_memories:
                    score = m.get("importance_score", 0) or 0
                    content = m.get("content", "")
                    # 只包含 importance >= 0.7 的深层认知记忆
                    if score >= 0.7 and content:
                        individual.append(f"  - {content[:80]}")
                if individual:
                    parts.append("深层自我认知：")
                    parts.extend(individual)
            except Exception:
                pass  # 查询失败不影响已有结果

            return "\n".join(parts) if parts else "暂无事实记忆。"

        else:  # episodic
            episodes = self.memory_service.find_similar_episodic(
                keywords=keywords or [], limit=5, user_id=self.user_id
            )
            if not episodes:
                return "暂无相关情节记忆。"
            lines = []
            for ep in episodes:
                date_str = ep.date.strftime("%Y-%m-%d") if ep.date else "未知"
                topics = "、".join(ep.topics[:3]) if ep.topics else ""
                lines.append(
                    f"[{date_str}] {ep.emotion} | {topics}\n{ep.summary}"
                )
            return "\n\n".join(lines)

    async def _save_memory(
        self,
        content: str,
        memory_type: str = "factual",
        importance: float = 0.7,
    ) -> str:
        """保存对话中产生的新认知到记忆系统（Hermes 式 learning loop）"""
        if memory_type == "factual":
            # 用 content 的关键词作为 key
            key = content[:20] if len(content) > 20 else content
            self.memory_service.update_factual_memory(key=key, value=content, user_id=self.user_id)
            return f"已保存为事实记忆：{content[:50]}"
        else:
            # 情节记忆需要更多字段，这里用简化版
            self.memory_service.create_episodic_memory(
                diary_id=0,
                summary=content,
                key_events=[],
                emotion="neutral",
                topics=[],
                user_id=self.user_id,
            )
            return f"已保存为情节记忆：{content[:50]}"
