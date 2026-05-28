# AI Diary - Agentic Coding Guidelines

## Project Overview

AI 智能日记 App - iOS (SwiftUI) + FastAPI 智能语音日记应用

```
ai_diary/
├── backend/           # FastAPI 后端 (Python 3.9+)
├── iOS/AIDiary/       # SwiftUI 前端
│   ├── AIDiary/       # 应用代码
│   ├── AIDiaryTests/  # 单元测试
│   └── AIDiaryUITests/# UI 测试
└── docs/              # 文档
```

**部署：** 阿里云 (8.136.124.182) → https://51pic.xyz

---

## Commands

### Python (Backend)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 测试
pytest
pytest tests/test_api.py::test_function_name -v

# Lint（暂无配置，建议添加）
pip install ruff black mypy
ruff check backend/app && black --check backend/app
```

### Swift (iOS)

```bash
# 编译验证 — 修改 Swift 代码后必须运行
xcodebuild -project iOS/AIDiary/AIDiary.xcodeproj \
  -scheme AIDiary \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  build

# 测试
xcodebuild test \
  -scheme AIDiary \
  -destination 'platform=iOS Simulator,name=iPhone 15'
```

---

## Code Style

### Python (Backend)

| 项目 | 规范 |
|------|------|
| 文件/函数/变量 | `snake_case` |
| 类 | `PascalCase` |
| 常量 | `UPPER_CASE` |
| 类型 | 类型注解 + Pydantic 模型 |
| 异步 | API 层全异步 `async/await` |
| API 字段 | `snake_case` (`raw_text` 不是 `rawText`) |

```python
# 导入顺序：标准库 → 第三方 → 本地
from datetime import datetime
from fastapi import FastAPI
from app.services import ai_service

# 数据库 JSON 字段
diary.weather = json.dumps(weather_data.model_dump())
weather = json.loads(diary.weather) if diary.weather else None
```

### Swift (iOS)

| 项目 | 规范 |
|------|------|
| 文件/类型/协议 | `PascalCase` |
| 函数/变量 | `camelCase` |
| 架构 | MVVM（View → ViewModel → Model） |
| API 映射 | 必须添加 `CodingKeys`（snake_case ↔ camelCase） |

**常见 CodingKeys 映射：**
`weather_icon`→`weatherIcon`, `created_at`→`createdAt`, `raw_text`→`rawText`, `emotion_score`→`emotionScore`

**并发：**
- `@ObservableObject` 默认 MainActor 隔离
- 单例使用 `Sendable` 协议，隔离方法用 `nonisolated`
- Codable struct 跨隔离上下文解码需 `nonisolated`

**SwiftData 注意：** 不支持复杂 struct（如 Weather），需拆分为多个字段存储，`toDiary()` 时重建。

**Preview：** 初始化必须传入所有字段（包括可选字段，用 `nil` 或默认值）。

---

## Architecture

| 层 | 后端 | iOS |
|----|------|-----|
| 视图/路由 | `app/api/` — HTTP 逻辑 | `Screens/` — 页面视图 |
| 业务逻辑 | `app/services/` | `ViewModels/` — @ObservableObject |
| 数据模型 | `app/models/` — SQLAlchemy | `Models/` — Codable struct |
| 本地缓存 | — | `Cache/` — SwiftData @Model |
| 数据存储 | `app/db/` — SQLAlchemy + SQLite | — |

---

## iOS Cache Strategy

**核心原则：网络数据优先，缓存作为备份。**

| 场景 | 行为 |
|------|------|
| 无筛选加载 | 网络数据 + 缓存独有的（保留离线创建的日记） |
| 有筛选加载 | 只用网络数据 |
| 网络成功 | 更新缓存 |
| 网络失败 | 用缓存兜底 |
| 创建/编辑/删除 | 立即操作缓存 + 后台同步网络 |

**任何数据增删改查功能都必须考虑缓存同步。**

---

## Environment & Deployment

### .env
```bash
DEEPSEEK_API_KEY=your_key
DATABASE_URL=sqlite+aiosqlite:///./ai_diary.db
DEBUG=true
```

### 部署
```bash
ssh root@8.136.124.182 "pkill -f uvicorn"
ssh root@8.136.124.182 "cd ~/ai-diary && cp ai_diary.db ai_diary.db.bak"
scp -r backend/app/* root@8.136.124.182:~/ai-diary/app/
ssh root@8.136.124.182 "cd ~/ai-diary && nohup /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"
curl https://51pic.xyz/health
```

---

## Important Rules

1. **编译验证** — 修改 Swift 代码后必须立即跑 `xcodebuild build`，通过才能认为任务完成
2. **测试** — 每个新功能必须配套测试用例
3. **不提交** — `.env`, `venv/`, `*.db`, `__pycache__/`, API Key
4. **权限诊断** — iOS 权限问题先查 `project.pbxproj` 的 `INFOPLIST_KEY_*` 配置，再查代码
5. **功能完成后清理** — 移除 `print()` 调试日志、测试数据、临时注释；保留必要的错误处理和 fallback 机制

---

## Git

```
<type>: <简短描述>
```
type: `feat` / `fix` / `chore` / `refactor` / `docs`

---

## Common Tasks

### 添加 API 端点
1. `backend/app/api/` 创建路由文件
2. `backend/app/main.py` 注册 router
3. 编写测试用例

### 添加 iOS 页面
1. `Screens/` 创建 SwiftUI 视图
2. `ContentView.swift` 添加路由

### 修改 AI 服务
1. 编辑 `backend/app/services/ai/`
2. 更新 API 端点
3. 测试 AI 响应格式

---

## Key Paths

| 路径 | 说明 |
|------|------|
| `backend/app/api/` | FastAPI 路由 |
| `backend/app/db/database.py` | SQLAlchemy 模型 |
| `backend/app/services/ai/` | AI 服务 |
| `iOS/AIDiary/AIDiary/Screens/` | SwiftUI 页面 |
| `iOS/AIDiary/AIDiary/Services/` | API 调用 |
| `iOS/AIDiary/AIDiary/Cache/` | SwiftData 缓存 |
