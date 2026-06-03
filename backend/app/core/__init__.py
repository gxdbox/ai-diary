"""
核心模块 - 上下文管理核心组件

包含：
- ContextAssembler: 上下文组装器
- MemoryManager: 记忆管理器
- TimeDecayEngine: 时间衰减引擎
- ContextPruner: 上下文裁剪器
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import math
import json

# 避免循环导入，使用 TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.memory import MemoryItem, MemoryType
    from app.models.context import AssembledContext, ContextBudget, Resolution, MemoryTier
    from app.models.user_profile import UserProfile


class TimeDecayEngine:
    """
    时间衰减引擎 - 模拟人类记忆衰减

    核心思想：近期记忆清晰，远期记忆模糊
    参考：06章 光学压缩式遗忘机制
    """

    # 衰减配置
    DECAY_CONFIG = {
        "recent": {      # < 3天
            "days": 3,
            "resolution": "high",
            "token_budget": 800,
            "decay_rate": 0.0
        },
        "weekly": {      # 3-7天
            "days": 7,
            "resolution": "medium",
            "token_budget": 256,
            "decay_rate": 0.1
        },
        "monthly": {     # 7-30天
            "days": 30,
            "resolution": "low",
            "token_budget": 64,
            "decay_rate": 0.3
        },
        "archived": {    # > 30天
            "days": float('inf'),
            "resolution": "minimal",
            "token_budget": 32,
            "decay_rate": 0.5
        }
    }

    def get_time_tier(self, created_at: datetime, reference_time: datetime = None) -> str:
        """
        获取记忆的时间层级

        Args:
            created_at: 记忆创建时间
            reference_time: 参考时间（默认为当前时间）

        Returns:
            str: 时间层级名称
        """
        if reference_time is None:
            reference_time = datetime.now()

        days_elapsed = (reference_time - created_at).days

        if days_elapsed < 3:
            return "recent"
        elif days_elapsed < 7:
            return "weekly"
        elif days_elapsed < 30:
            return "monthly"
        else:
            return "archived"

    def calculate_decay_factor(
        self,
        created_at: datetime,
        reference_time: datetime = None
    ) -> float:
        """
        计算时间衰减因子

        使用指数衰减：decay = e^(-decay_rate * days)

        Args:
            created_at: 记忆创建时间
            reference_time: 参考时间

        Returns:
            float: 衰减因子 (0-1)
        """
        if reference_time is None:
            reference_time = datetime.now()

        days_elapsed = (reference_time - created_at).days
        tier = self.get_time_tier(created_at, reference_time)
        decay_rate = self.DECAY_CONFIG[tier]["decay_rate"]

        return math.exp(-decay_rate * days_elapsed)

    def calculate_effective_importance(
        self,
        base_importance: float,
        created_at: datetime,
        access_count: int = 0,
        reference_time: datetime = None
    ) -> float:
        """
        计算记忆的有效重要性

        公式：effective = base * time_decay * access_boost

        Args:
            base_importance: 基础重要性 (0-1)
            created_at: 创建时间
            access_count: 访问次数
            reference_time: 参考时间

        Returns:
            float: 有效重要性 (0-1)
        """
        time_decay = self.calculate_decay_factor(created_at, reference_time)

        # 访问加成：每访问一次增加 5%，上限 50%
        access_boost = min(0.5, access_count * 0.05)
        access_factor = 1.0 + access_boost

        effective = base_importance * time_decay * access_factor
        return min(1.0, max(0.0, effective))

    def get_resolution_for_memory(
        self,
        created_at: datetime,
        importance: float = 0.5,
        reference_time: datetime = None
    ) -> str:
        """
        获取记忆的推荐分辨率

        高重要性记忆可以保留更高分辨率

        Args:
            created_at: 创建时间
            importance: 重要性评分
            reference_time: 参考时间

        Returns:
            str: 分辨率级别
        """
        base_tier = self.get_time_tier(created_at, reference_time)
        base_resolution = self.DECAY_CONFIG[base_tier]["resolution"]

        # 高重要性记忆可以提升一级分辨率
        if importance >= 0.8:
            resolution_order = ["minimal", "low", "medium", "high"]
            current_idx = resolution_order.index(base_resolution)
            if current_idx < len(resolution_order) - 1:
                return resolution_order[current_idx + 1]

        return base_resolution

    def get_token_budget_for_memory(
        self,
        created_at: datetime,
        importance: float = 0.5,
        reference_time: datetime = None
    ) -> int:
        """
        获取记忆的 token 预算

        Args:
            created_at: 创建时间
            importance: 重要性评分
            reference_time: 参考时间

        Returns:
            int: token 预算
        """
        tier = self.get_time_tier(created_at, reference_time)
        base_budget = self.DECAY_CONFIG[tier]["token_budget"]

        # 根据重要性调整
        importance_factor = 0.5 + importance  # 0.5 - 1.5
        return int(base_budget * importance_factor)


class ContextAssembler:
    """
    上下文组装器 - 整合多源信息构建完整上下文

    参考：06章 上下文管理的高级技巧
    """

    def __init__(self, db_session=None, vector_store=None):
        """
        初始化上下文组装器

        Args:
            db_session: 数据库会话
            vector_store: 向量存储实例
        """
        self.db = db_session
        self.vector_store = vector_store
        self.time_decay = TimeDecayEngine()

    def assemble(
        self,
        user_input: str,
        user_id: int = 1,
        conversation_history: List[Dict] = None,
        budget: "ContextBudget" = None,
        user_profile: "UserProfile" = None
    ) -> "AssembledContext":
        """
        组装完整上下文

        Args:
            user_input: 当前用户输入
            user_id: 用户ID
            conversation_history: 对话历史
            budget: 上下文预算配置
            user_profile: 用户画像

        Returns:
            AssembledContext: 组装后的上下文
        """
        from app.models.context import AssembledContext, ContextBudget

        if budget is None:
            budget = ContextBudget()

        if conversation_history is None:
            conversation_history = []

        # 1. 检索相关记忆
        relevant_memories = self._retrieve_memories(
            query=user_input,
            top_k=budget.max_memories,
            min_importance=budget.min_importance_threshold
        )

        # 2. 裁剪对话历史
        trimmed_history = self._trim_conversation_history(
            history=conversation_history,
            max_turns=budget.max_conversation_turns
        )

        # 3. 构建上下文
        context = AssembledContext(
            user_profile=user_profile.get_summary() if user_profile else None,
            relevant_memories=relevant_memories,
            conversation_history=trimmed_history,
            current_input=user_input
        )

        # 4. 计算 token 估算
        context.total_tokens = self._estimate_tokens(context)

        return context

    def _retrieve_memories(
        self,
        query: str,
        top_k: int = 5,
        min_importance: float = 0.3
    ) -> List[Dict]:
        """
        检索相关记忆

        Args:
            query: 查询文本
            top_k: 返回数量
            min_importance: 最小重要性阈值

        Returns:
            List[Dict]: 记忆列表
        """
        if self.vector_store is None:
            return []

        try:
            results = self.vector_store.search(query, n_results=top_k)
            # 过滤低重要性
            results = [
                r for r in results
                if r.get('metadata', {}).get('importance', 0.5) >= min_importance
            ]
            return results
        except Exception:
            return []

    def _trim_conversation_history(
        self,
        history: List[Dict],
        max_turns: int = 10
    ) -> List[Dict]:
        """
        裁剪对话历史

        Args:
            history: 对话历史
            max_turns: 最大轮数

        Returns:
            List[Dict]: 裁剪后的历史
        """
        if len(history) <= max_turns:
            return history

        # 保留最近的 N 轮
        return history[-max_turns:]

    def _estimate_tokens(self, context: "AssembledContext") -> int:
        """
        估算上下文的 token 数量

        粗略估算：中文约 1.5 字/token

        Args:
            context: 上下文对象

        Returns:
            int: 估算的 token 数
        """
        total_chars = len(context.current_input)

        if context.user_profile:
            total_chars += len(json.dumps(context.user_profile, ensure_ascii=False))

        for memory in context.relevant_memories:
            total_chars += len(memory.get('text', ''))

        for turn in context.conversation_history:
            total_chars += len(turn.get('content', ''))

        return int(total_chars / 1.5)


class MemoryManager:
    """
    记忆管理器 - 管理记忆生命周期

    参考：06章 记忆的"唤醒"与"遗忘"机制
    """

    def __init__(self, db_session=None, vector_store=None):
        self.db = db_session
        self.vector_store = vector_store
        self.time_decay = TimeDecayEngine()

    def add_memory(
        self,
        content: str,
        memory_type: str,
        importance: float = 0.5,
        metadata: Dict = None,
        diary_id: int = None
    ) -> int:
        """
        添加新记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型 (factual/episodic)
            importance: 重要性评分
            metadata: 元数据
            diary_id: 关联日记ID

        Returns:
            int: 记忆ID
        """
        from sqlalchemy import text
        import json

        try:
            result = self.db.execute(text("""
                INSERT INTO memories
                (memory_type, content, keywords, source_diary_id, importance_score, metadata)
                VALUES (:type, :content, :keywords, :diary_id, :importance, :metadata)
            """), {
                "type": memory_type,
                "content": content,
                "keywords": json.dumps(metadata.get('keywords', [])) if metadata else '[]',
                "diary_id": diary_id,
                "importance": importance,
                "metadata": json.dumps(metadata) if metadata else '{}'
            })
            self.db.commit()
            return result.lastrowid
        except Exception as e:
            print(f"添加记忆失败: {e}")
            return -1

    def get_relevant_memories(
        self,
        query: str,
        limit: int = 5,
        min_importance: float = 0.3,
        time_range: tuple = None
    ) -> List[Dict]:
        """
        获取相关记忆

        Args:
            query: 查询文本
            limit: 返回数量
            min_importance: 最小重要性
            time_range: 时间范围 (start_date, end_date)

        Returns:
            List[Dict]: 记忆列表
        """
        # 先从向量数据库检索
        if self.vector_store:
            results = self.vector_store.search(query, n_results=limit)
            return results

        return []

    def decay_old_memories(self, days_threshold: int = 30) -> int:
        """
        衰减旧记忆的重要性

        Args:
            days_threshold: 天数阈值

        Returns:
            int: 更新的记忆数量
        """
        from sqlalchemy import text
        from datetime import datetime, timedelta

        threshold_date = datetime.now() - timedelta(days=days_threshold)

        try:
            # 降低超过阈值天数的记忆重要性
            result = self.db.execute(text("""
                UPDATE memories
                SET importance_score = importance_score * 0.8,
                    updated_at = CURRENT_TIMESTAMP
                WHERE created_at < :threshold
                AND importance_score > 0.2
            """), {"threshold": threshold_date.isoformat()})
            self.db.commit()
            return result.rowcount
        except Exception:
            return 0

    def promote_important_memory(self, memory_id: int) -> bool:
        """
        提升记忆为长期重要记忆

        Args:
            memory_id: 记忆ID

        Returns:
            bool: 是否成功
        """
        from sqlalchemy import text

        try:
            self.db.execute(text("""
                UPDATE memories
                SET importance_score = MIN(1.0, importance_score + 0.2),
                    access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"id": memory_id})
            self.db.commit()
            return True
        except Exception:
            return False
