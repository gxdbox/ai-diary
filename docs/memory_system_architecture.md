# AI Diary 记忆系统架构设计

> 基于《06-上下文管理技巧》论文思想，结合项目现有实现升级

## 一、现有系统分析

### 已实现功能

| 模块 | 文件 | 功能 |
|------|------|------|
| 记忆服务 | `memory_service.py` | Factual/Episodic 双类型记忆管理 |
| 向量存储 | `vector_store.py` | ChromaDB 语义搜索 |
| 数据模型 | `memory.py` | MemoryItem、FactualMemory、EpisodicMemory |
| 主动检索 | `proactive_retrieval.py` | 基于上下文的主动记忆召回 |

### 待升级方向

1. **分层记忆体系** - 短期/中期/长期记忆管理
2. **上下文组装器** - 智能整合多源信息
3. **记忆衰减机制** - 光学压缩式遗忘
4. **上下文裁剪策略** - 有限窗口内最大化信息价值

---

## 二、系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        API 层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ diary.py │  │assistant │  │ memory.py│  │search.py │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼────────────┼────────────┼────────────┼─────────────────┘
        │            │            │            │
┌───────┼────────────┼────────────┼────────────┼─────────────────┐
│       │      服务层 │            │            │                │
│  ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐ ┌────▼─────┐          │
│  │diary_svc │ │assistant │ │memory_svc│ │search_svc│          │
│  │          │ │  _svc    │ │          │ │          │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │                │
│  ┌────▼────────────▼────────────▼────────────▼─────┐          │
│  │              Context Service (新增)              │          │
│  │         上下文组装 + 记忆管理 + 裁剪策略           │          │
│  └─────────────────────┬────────────────────────────┘          │
└────────────────────────┼───────────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────────┐
│                   核心组件层                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Context   │  │   Memory    │  │    Time    │             │
│  │  Assembler  │  │   Manager   │  │   Decay    │             │
│  │  (组装器)    │  │  (管理器)    │  │  (衰减器)   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                    │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐             │
│  │    User     │  │   Emotion   │  │   Memory    │             │
│  │   Profile   │  │  Analyzer   │  │  Extractor  │             │
│  │  (用户画像)  │  │ (情绪分析)   │  │ (记忆提取)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────────┐
│                     数据层                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   SQLite    │  │  ChromaDB   │  │   Redis     │             │
│  │ (关系数据)   │  │ (向量存储)   │  │ (会话缓存)   │ ← 可选      │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 分层记忆模型

```python
# 记忆时间分层
SHORT_TERM = {
    "ttl": "session",           # 会话级别，会话结束清除
    "capacity": 10,              # 最近10轮对话
    "storage": "in_memory"       # 内存存储
}

MID_TERM = {
    "ttl": "7_days",             # 保留7天
    "capacity": 50,               # 最多50条
    "storage": "sqlite"           # SQLite存储
}

LONG_TERM = {
    "ttl": "permanent",          # 永久保留
    "capacity": "unlimited",      # 无限制
    "storage": "sqlite + chroma"  # 关系+向量双重存储
}
```

---

## 三、核心模块设计

### 3.1 上下文组装器 (Context Assembler)

**职责**：整合多源信息，构建完整对话上下文

```python
class ContextAssembler:
    """上下文组装器 - 智能整合多源信息"""

    def assemble_context(
        self,
        user_id: int,
        current_input: str,
        conversation_history: List[Dict],
        max_tokens: int = 4000
    ) -> AssembledContext:
        """
        组装完整上下文

        Args:
            user_id: 用户ID
            current_input: 当前用户输入
            conversation_history: 对话历史
            max_tokens: 最大token限制

        Returns:
            AssembledContext: 组装后的上下文对象
        """
        pass

    def _get_user_profile(self, user_id: int) -> UserProfile:
        """获取用户画像"""
        pass

    def _retrieve_relevant_memories(
        self,
        query: str,
        top_k: int = 3,
        time_range: Optional[tuple] = None
    ) -> List[MemoryItem]:
        """检索相关记忆"""
        pass

    def _apply_context_compression(
        self,
        context: AssembledContext,
        target_tokens: int
    ) -> AssembledContext:
        """应用上下文压缩"""
        pass
```

**组装策略**：
1. 用户画像（固定优先级最高）
2. 相关长期记忆（Top-K 检索）
3. 近期对话历史（滑动窗口）
4. 当前输入

### 3.2 记忆管理器 (Memory Manager)

**职责**：管理记忆生命周期，实现智能遗忘

```python
class MemoryManager:
    """记忆管理器 - 分层记忆管理"""

    def __init__(self, db: Session, vector_store: VectorStore):
        self.db = db
        self.vector_store = vector_store
        self.time_decay = TimeDecayEngine()

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        metadata: Dict = None
    ) -> MemoryItem:
        """添加新记忆"""
        pass

    def get_relevant_memories(
        self,
        query: str,
        limit: int = 5,
        min_importance: float = 0.3
    ) -> List[MemoryItem]:
        """获取相关记忆"""
        pass

    def decay_old_memories(self, days_threshold: int = 30):
        """衰减旧记忆的重要性"""
        pass

    def promote_to_long_term(self, memory_id: int):
        """将重要记忆提升为长期记忆"""
        pass
```

### 3.3 时间衰减引擎 (Time Decay Engine)

**职责**：实现"光学压缩式"遗忘机制

```python
class TimeDecayEngine:
    """
    时间衰减引擎 - 模拟人类记忆衰减

    核心思想：近期记忆清晰，远期记忆模糊
    """

    # 衰减配置
    DECAY_CONFIG = {
        "recent": {      # < 3天
            "days": 3,
            "resolution": "high",      # 高分辨率
            "token_budget": 800,
            "decay_rate": 0.0
        },
        "weekly": {      # 3-7天
            "days": 7,
            "resolution": "medium",    # 中分辨率
            "token_budget": 256,
            "decay_rate": 0.1
        },
        "monthly": {     # 7-30天
            "days": 30,
            "resolution": "low",       # 低分辨率
            "token_budget": 64,
            "decay_rate": 0.3
        },
        "archived": {     # > 30天
            "days": float('inf'),
            "resolution": "minimal",   # 最小分辨率
            "token_budget": 32,
            "decay_rate": 0.5
        }
    }

    def calculate_importance(
        self,
        memory: MemoryItem,
        reference_time: datetime = None
    ) -> float:
        """
        计算记忆的实际重要性

        公式：effective_importance = base_importance * time_decay * access_boost

        - base_importance: 原始重要性评分
        - time_decay: 时间衰减因子 (指数衰减)
        - access_boost: 访问频率加成
        """
        pass

    def get_resolution_tier(self, created_at: datetime) -> str:
        """获取记忆的分辨率层级"""
        pass

    def compress_memory(self, memory: MemoryItem, resolution: str) -> str:
        """压缩记忆内容"""
        pass
```

### 3.4 用户画像管理 (User Profile)

**职责**：维护用户长期特征信息

```python
class UserProfile(BaseModel):
    """用户画像 - 结构化长期记忆"""

    # 基本信息
    user_id: int
    nickname: Optional[str] = None
    created_at: datetime

    # 情感特征
    emotional_profile: EmotionalProfile = Field(default_factory=EmotionalProfile)

    # 写作偏好
    writing_preferences: WritingPreferences = Field(default_factory=WritingPreferences)

    # 生活主题
    life_themes: List[str] = Field(default_factory=list)

    # 重要事件时间线
    key_events: List[KeyEvent] = Field(default_factory=list)

    # AI交互风格偏好
    interaction_preferences: InteractionPreferences = Field(default_factory=InteractionPreferences)


class EmotionalProfile(BaseModel):
    """情感画像"""
    # 情绪分布（过去30天）
    emotion_distribution: Dict[str, float] = Field(default_factory=dict)

    # 情绪触发因素
    stress_triggers: List[str] = Field(default_factory=list)
    joy_sources: List[str] = Field(default_factory=list)

    # 应对方式
    coping_mechanisms: List[str] = Field(default_factory=list)

    # 当前情绪状态
    current_mood: Optional[str] = None
    current_mood_intensity: float = 0.0


class KeyEvent(BaseModel):
    """关键事件"""
    date: datetime
    event: str
    emotion: str
    importance: float
    resolution: Optional[str] = None  # 事件结果/后续
```

---

## 四、上下文裁剪策略

### 4.1 裁剪优先级

```
优先级从高到低：
1. 系统提示词 + 角色设定      → 必须保留
2. 当前用户输入              → 必须保留
3. 用户画像核心信息          → 高优先级
4. 最近5轮对话              → 高优先级
5. 高重要性记忆(>0.7)        → 中优先级
6. 与当前输入语义相关的记忆   → 中优先级
7. 早期对话历史              → 低优先级，可摘要
8. 低重要性记忆(<0.3)        → 可丢弃
```

### 4.2 裁剪算法

```python
def prune_context(
    context: AssembledContext,
    max_tokens: int
) -> AssembledContext:
    """
    智能裁剪上下文

    策略：
    1. 计算当前token占用
    2. 若超限，按优先级从低到高裁剪
    3. 对话历史采用滑动窗口 + 摘要
    4. 记忆按时间衰减 + 重要性综合排序
    """
    current_tokens = count_tokens(context)

    if current_tokens <= max_tokens:
        return context

    # 1. 压缩早期对话历史为摘要
    if len(context.conversation_history) > 5:
        early_history = context.conversation_history[:-5]
        summary = summarize_conversation(early_history)
        context.conversation_summary = summary
        context.conversation_history = context.conversation_history[-5:]

    # 2. 裁剪低相关性记忆
    context.relevant_memories = [
        m for m in context.relevant_memories
        if m.importance_score > 0.3 or m.relevance_score > 0.3
    ]

    # 3. 应用时间衰减压缩
    for memory in context.relevant_memories:
        resolution = time_decay.get_resolution_tier(memory.created_at)
        if resolution != "high":
            memory.content = time_decay.compress_memory(memory, resolution)

    return context
```

---

## 五、记忆提及策略（避免监控感）

### 5.1 提及方式对比

| 方式 | 示例 | 效果 |
|------|------|------|
| ❌ 直白陈述 | "我记得你上周说你失眠了" | 监控感强 |
| ✅ 委婉引导 | "你之前提到睡眠有些困扰，最近有改善吗？" | 自然关怀 |
| ✅ 模式推断 | "考试前你总是会有些紧张，这次感觉怎么样？" | 理解感 |
| ✅ 情境化共情 | "能在高压下坚持下来真不容易" | 被看见 |

### 5.2 Prompt 模板设计

```python
MEMORY_MENTION_TEMPLATE = """
你是用户的日记伴侣。在回应时遵循以下原则：

## 记忆提及原则
1. **隐性记忆**：不要直接说"你之前说过..."，而是将记忆融入共情表达
2. **模式推断**：用"你有时候..."替代"你上次说..."
3. **情境关联**：将过去经历与当前状态自然连接
4. **尊重遗忘**：如果用户回避某话题，不要主动提起

## 示例
用户："终于考完试了！"
❌ 错误回应："我记得你上周说很担心这次考试，考得怎么样？"
✅ 正确回应："恭喜！能在压力下坚持下来真不容易，感觉怎么样？"

## 用户画像（用于理解用户，但不要直接复述）
{user_profile}

## 相关记忆（隐性融入回应，不要复述）
{relevant_memories}

## 当前对话
{conversation_history}

用户：{current_input}
"""
```

---

## 六、实现路线图

### Phase 1：基础架构升级（Week 1-2）

- [ ] 重构 MemoryService，支持分层存储
- [ ] 实现 TimeDecayEngine 时间衰减引擎
- [ ] 添加 ContextAssembler 上下文组装器

### Phase 2：智能裁剪（Week 3）

- [ ] 实现 token 计数与预算分配
- [ ] 实现对话历史摘要功能
- [ ] 实现记忆智能裁剪算法

### Phase 3：用户画像（Week 4）

- [ ] 设计 UserProfile 数据结构
- [ ] 实现画像自动更新机制
- [ ] 实现画像与记忆的关联

### Phase 4：Prompt优化（Week 5）

- [ ] 设计避免监控感的 Prompt 模板
- [ ] 实现动态 Prompt 组装
- [ ] A/B 测试与效果评估

---

## 七、文件结构规划

```
backend/app/
├── services/
│   ├── memory_service.py      # 现有 → 重构
│   ├── context_service.py     # 新增：上下文服务
│   └── user_profile_service.py # 新增：用户画像服务
│
├── core/
│   ├── context_assembler.py   # 新增：上下文组装器
│   ├── memory_manager.py      # 新增：记忆管理器
│   ├── time_decay.py          # 新增：时间衰减引擎
│   └── context_pruner.py      # 新增：上下文裁剪器
│
├── models/
│   ├── memory.py              # 现有 → 扩展
│   ├── user_profile.py        # 新增：用户画像模型
│   └── context.py             # 新增：上下文数据模型
│
└── prompts/
    ├── system_prompt.py       # 系统提示词
    └── memory_templates.py    # 记忆相关模板
```

---

## 八、参考资源

- 论文源码：https://github.com/congde/emotional_chat
- MCP协议上下文：`backend/modules/agent/protocol/mcp.py`
- 增强版上下文组装器：`backend/services/enhanced_context_assembler.py`
