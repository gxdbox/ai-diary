# AI Diary 架构文档

## 项目概述

AI智能日记是一款语音驱动的日记应用，用户通过语音录入，AI自动清洗文本、分析情绪、提取主题。

**技术栈：**
- **后端**: FastAPI + SQLite + ChromaDB
- **iOS**: SwiftUI + SwiftData

---

## 目录结构

```
ai_diary/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由层
│   │   │   └── diary.py       # 日记相关 API
│   │   │   └── dictionary.py  # 自定义词典 API
│   │   │   └ search.py        # 搜索相关 API
│   │   │   └ analysis.py     # 分析相关 API
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── ai_service.py  # AI 分析服务
│   │   │   ├── text_cleaner.py # 文本清洗
│   │   │   └── vector_store.py # 向量存储
│   │   ├── models/            # Pydantic 数据模型
│   │   ├── db/                # 数据库层
│   │   │   └── database.py    # SQLAlchemy 模型
│   │   └── main.py            # FastAPI 应用入口
│   ├── ai_diary.db            # SQLite 数据库
│   └── chroma_data/           # ChromaDB 向量数据
│
├── iOS/AIDiary/               # SwiftUI iOS 应用
│   └── AIDiary/
│       ├── Screens/           # 页面视图
│       │   ├── TimelineView.swift    # 时间轴主页
│       │   ├── RecordView.swift      # 录音页面
│       │   ├── DiaryDetailView.swift # 日记详情
│       │   ├── DiaryPreviewView.swift # AI分析预览
│       │   ├── DictionaryView.swift  # 自定义词典
│       │   └── SettingsView.swift    # 设置页面
│       ├── Components/        # 可复用组件
│       ├── Services/          # 服务层
│       │   ├── APIService.swift      # API 调用
│       │   ├── CacheService.swift    # 本地缓存
│       │   └── SpeechService.swift   # 语音识别
│       ├── Models/            # 数据模型
│       │   ├── Diary.swift           # 日记模型
│       │   ├── DictionaryEntry.swift # 词典模型
│       │   └── Notifications.swift   # 通知类型
│       └── Assets.xcassets/   # 资源文件
│
└── docs/                      # 文档
    ├── ARCHITECTURE.md        # 本架构文档
    ├── API.md                 # API 文档
    ├── SETUP.md               # 安装指南
    └── DEPLOY.md              # 部署指南
```

---

## 数据流架构

### 1. 创建日记流程

```
用户录音 → SpeechService → APIService.createDiary → 后端 AI 分析
                                                    ↓
                                            保存数据库 + 向量存储
                                                    ↓
                                            返回结果 → CacheService 缓存
                                                    ↓
                                            TimelineView 显示
```

### 2. 查看日记流程

```
TimelineView.loadData() → APIService.fetchDiaries → 网络返回
                                              ↓
                                      CacheService 合并/更新
                                              ↓
                                      显示日记列表
```

### 3. 搜索日记流程

```
用户输入 → APIService.semanticSearch → 后端向量检索
                                    ↓
                            返回相似日记 → 显示结果
```

---

## 缓存策略

### 设计原则

**网络数据优先，缓存作为备份**

缓存的作用：
1. **离线访问** - 无网络时可查看历史日记
2. **网络失败兜底** - API 请求失败时用缓存数据
3. **离线创建保留** - 临时保存未同步的日记

### 同步规则

| 场景 | 数据来源 | 缓存操作 |
|------|----------|----------|
| 无筛选加载 | 网络 + 缓存独有的 | 更新缓存 |
| 有筛选加载 | 仅网络 | 不更新缓存 |
| 创建日记 | 网络 → 缓存 | 保存到缓存 |
| 编辑日记 | 缓存 → 后台网络 | 更新缓存 |
| 删除日记 | 网络 → 缓存 | 删除缓存 |
| 网络失败 | 仅缓存 | 不操作 |

### 代码实现要点

```swift
// 无筛选：网络优先，缓存保留离线创建
for networkDiary in response.items {
    mergedDiaries.append(networkDiary)  // 用网络版本（最新）
    cachedDict[networkDiary.id] = nil   // 标记已处理
}
for (_, cachedList) in cachedDict {
    mergedDiaries.append(contentsOf: cachedList)  // 保留缓存独有的
}
await CacheService.shared.saveDiaries(mergedDiaries)  // 更新缓存

// 有筛选：只用网络，不查缓存
mergedDiaries = response.items
// 不更新缓存，避免缓存只保存筛选结果
```

---

## API 路由设计

### 路由顺序原则

**静态路由必须在动态路由（`/{id}`）之前**

```python
# 正确顺序
@router.get("/list")      # 第1
@router.get("/filters")   # 第2（静态）
@router.get("/{diary_id}") # 第3（动态）

# 错误顺序会导致 /filters 匹配到 /{diary_id}
```

### URL 编码

中文参数必须 URL 编码：
- "高兴" → `%E9%AB%98%E5%85%B4`
- "温情" → `%E6%B8%A9%E6%83%85`

Swift `URLComponents` 会自动编码查询参数。

---

## 开发规范

### 新增功能时必须考虑

1. **数据操作 → 缓存同步**
   - 增删改查都要更新 CacheService
   - 区分筛选/无筛选场景

2. **API 路由 → 静态优先**
   - `/filters` 放在 `//{id}` 前面
   - 避免路由匹配错误

3. **中文参数 → URL 编码**
   - 测试时验证编码是否正确
   - 后端 FastAPI 自动解码

4. **异步操作 → 不阻塞用户**
   - 编辑/删除先更新缓存，后台同步网络
   - 用户立即看到变化

### 测试检查清单

- [ ] 无筛选：显示网络 + 缓存独有日记
- [ ] 有筛选：仅显示匹配筛选条件的日记
- [ ] 网络失败：显示缓存数据
- [ ] 创建日记：缓存和网络都有
- [ ] 编辑日记：缓存立即更新，后台同步
- [ ] 删除日记：缓存和网络都删除
- [ ] 中文筛选：URL 编码正确

---

## 部署架构

```
┌─────────────────────────────────────────────┐
│              iOS App (SwiftUI)               │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │Timeline │  │ Record  │  │APIService   │  │
│  │  View   │  │  View   │  │CacheService │  │
│  └─────────┘  └─────────┘  └─────────────┘  │
└──────────────────────┬──────────────────────┘
                       │ HTTPS
                       ↓
┌─────────────────────────────────────────────┐
│         阿里云服务器 (8.136.124.182)          │
│  ┌─────────────────────────────────────┐    │
│  │         FastAPI (uvicorn)           │    │
│  │         Port: 8000                  │    │
│  └──────────────────┬──────────────────┘    │
│                     │                        │
│  ┌──────────────────┼──────────────────┐    │
│  │  SQLite (ai_diary.db)               │    │
│  │  ChromaDB (chroma_data/)            │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 数据库扩展规划

### 当前方案：SQLite

适用于：用户 < 5000，日记 < 10 万篇

**优点：**
- 部署简单，无需额外配置
- 单文件，备份方便
- 性能足够应对初期用户

**限制：**
- 单写入连接，并发写入会排队
- 文件锁会阻塞所有读写操作
- 数据量超过 10GB 性能下降

### 未来升级路线

```
当前 SQLite（用户 < 5000）
    ↓ 用户增长到 5000+
第一阶段：PostgreSQL（单机高性能）
    ↓ 用户增长到 5 万+
第二阶段：PostgreSQL + Redis（缓存热门数据）
    ↓ 用户增长到 50 万+
第三阶段：分布式架构
```

### 第一阶段：迁移 PostgreSQL

**触发条件：用户 > 5000 或日记 > 10 万**

**优点：**
- 支持并发写入（多连接同时写不同行）
- 更强大的索引和查询优化
- 成熟的运维工具和云服务支持

**改动成本：**
```python
# 当前 SQLite
DATABASE_URL = "sqlite+aiosqlite:///./ai_diary.db"

# 改 PostgreSQL（只需改连接字符串）
DATABASE_URL = "postgresql+asyncpg://user:pass@host/ai_diary"
```

- SQLAlchemy 代码几乎不变
- 阿里云 RDS PostgreSQL 有免费试用

### 第二阶段：添加 Redis 缓存

**触发条件：用户 > 5 万**

**缓存内容：**
- 热门日记内容
- 筛选结果（情绪/主题列表）
- 用户统计数据

### 第三阶段：分布式架构

**触发条件：用户 > 50 万**

**需要拆分：**
- 日记数据 → PostgreSQL 主从集群
- 向量数据 → 专用向量数据库（Pinecone、Milvus）
- 用户数据 → 分库分表

### 容量估算参考

| 用户规模 | 每用户日记 | 总日记数 | SQLite |
|----------|------------|----------|--------|
| 100 人 | 100 篇 | 1 万 | ✅ |
| 1 万用户 | 100 篇 | 100 万 | ⚠️ 需优化索引 |
| 10 万用户 | 100 篇 | 1000 万 | ❌ 写入瓶颈 |
| 100 万用户 | 100 篇 | 1 亿 | ❌ 需分布式 |

### 监控指标

当以下指标达到时，开始规划迁移：

- 日记总数 > 5 万 → 优化索引
- 日记总数 > 10 万 → 规划 PostgreSQL
- 并发写入延迟 > 500ms → 紧急迁移
- 用户数 > 5000 → 迁移 PostgreSQL

---

## 相关文档

- [API.md](./API.md) - API 接口详细说明
- [SETUP.md](./SETUP.md) - 开发环境搭建
- [DEPLOY.md](./DEPLOY.md) - 部署流程
- [../AGENTS.md](../AGENTS.md) - 开发规范和命令