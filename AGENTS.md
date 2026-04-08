# AI Diary - Agentic Coding Guidelines

## Project Overview

AI智能日记 App - React Native + FastAPI 智能语音日记应用

**Structure:**
```
ai_diary/
├── backend/           # FastAPI 后端 (Python 3.9+)
├── mobile/            # React Native 前端 (Node 18+)
└── docs/              # 文档
```

---

## Build & Run Commands

### Backend (Python)

```bash
cd backend

# 创建/激活虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DASHSCOPE_API_KEY

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档：http://localhost:8000/docs
```

### Mobile (React Native)

```bash
cd mobile

# 安装依赖
npm install

# iOS (需要 Xcode)
cd ios && pod install && cd ..
npm run ios

# Android
npm run android

# 启动 Metro Bundler
npm start
```

---

## Testing

### Backend Tests (pytest)

```bash
cd backend
source venv/bin/activate

# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_api.py

# 运行单个测试函数
pytest tests/test_api.py::test_health_check -v

# 带输出详情
pytest -v -s
```

### Mobile Tests (Jest)

```bash
cd mobile

# 运行测试
npm test

# 运行单个测试文件
npm test -- --testPathPattern=App.test.tsx

# 监听模式
npm test -- --watch
```

---

## Linting & Type Checking

### Backend

```bash
# 当前项目无 lint 配置，建议添加
pip install ruff black mypy
ruff check backend/app
black --check backend/app
```

### Mobile

```bash
cd mobile

# Lint
npm run lint

# TypeScript 检查
npx tsc --noEmit
```

---

## Code Style Guidelines

### Python (Backend)

**Imports:**
```python
# 顺序：标准库 → 第三方库 → 本地模块
from dotenv import load_dotenv
from fastapi import FastAPI
from app.services import ai_service
```

**Naming:**
- 文件/模块：`snake_case.py`
- 函数/变量：`snake_case`
- 类：`PascalCase`
- 常量：`UPPER_CASE`

**Types:**
- 使用类型注解（Python 3.9+ 语法）
- 使用 Pydantic 模型做数据验证

**Error Handling:**
```python
# 使用具体异常类型
try:
    result = await ai_service.analyze(text)
except DashScopeError as e:
    raise HTTPException(500, f"AI 服务错误：{e}")
```

**Async:**
- API 层全异步
- 使用 `async/await`
- 数据库使用 `aiosqlite`

---

### TypeScript (Mobile)

**Imports:**
```typescript
// 顺序：React → 第三方库 → 本地模块 (带 @/ 别名)
import React from 'react';
import { View } from 'react-native';
import { DiaryCard } from '@/components/DiaryCard';
```

**Naming:**
- 文件/组件：`PascalCase.tsx`
- 函数/变量：`camelCase`
- 类型/接口：`PascalCase`
- 常量：`UPPER_CASE`

**Types:**
```typescript
// 优先使用 interface 定义对象类型
interface Diary {
  id: string;
  content: string;
  emotion: EmotionType;
}

// 使用 type 做联合类型
type EmotionType = 'positive' | 'negative' | 'neutral';
```

**Error Handling:**
```typescript
try {
  const response = await apiService.createDiary(content);
} catch (error) {
  if (error instanceof AxiosError) {
    console.error('API 错误:', error.message);
  }
}
```

---

## Architecture Patterns

### Backend

- **路由层** (`app/api/`): 只处理 HTTP 逻辑
- **服务层** (`app/services/`): 业务逻辑
- **模型层** (`app/models/`): SQLAlchemy 模型
- **数据库** (`app/db/`): 数据库连接和初始化

### Mobile

- **Screens** (`src/screens/`): 页面级组件
- **Components** (`src/components/`): 可复用组件
- **Services** (`src/services/`): API/存储调用
- **Store** (`src/store/`): Zustand 状态管理
- **Types** (`src/types/`): TypeScript 类型定义

---

## Environment Variables

### Backend (.env)
```bash
DASHSCOPE_API_KEY=your_api_key
DATABASE_URL=sqlite+aiosqlite:///./ai_diary.db
CHROMA_PERSIST_DIR=./chroma_data
DEBUG=true
```

### Mobile
- API 地址硬编码在 `src/services/apiService.ts`
- 默认：`http://localhost:8000`

---

## Development Workflow

1. **后端开发**:
   - 修改代码后自动重载
   - 测试：`pytest tests/test_api.py::test_function_name -v`
   - API 文档：http://localhost:8000/docs

2. **前端开发**:
   - Metro Bundler 自动重载
   - 模拟器热更新
   - 类型检查：`npx tsc --noEmit`

3. **提交前检查**:
   - 后端测试通过
   - 前端 lint 通过
   - TypeScript 无错误

---

## Common Tasks

### 添加新的 API 端点

1. 在 `backend/app/api/` 创建路由文件
2. 在 `backend/app/main.py` 注册 router
3. 编写测试用例
4. 更新 API 文档

### 添加新的移动端页面

1. 在 `mobile/src/screens/` 创建组件
2. 在 `mobile/src/App.tsx` 添加路由
3. 在 `mobile/src/screens/index.ts` 导出

### 修改 AI 服务逻辑

1. 编辑 `backend/app/services/ai_service.py`
2. 更新相关 API 端点
3. 测试 AI 响应格式

---

## Debugging Tips

- **后端**: 使用 `--reload` 自动重载，查看 uvicorn 日志
- **前端**: 使用 React Native Debugger 或 Flipper
- **数据库**: `backend/ai_diary.db` 是 SQLite 文件
- **向量数据**: `backend/chroma_data/` 存储 ChromaDB 数据

---

## Important Notes

1. **不要提交**: `.env`, `venv/`, `node_modules/`, `*.db`, `__pycache__/`
2. **API Key**: 永远不要提交 DASHSCOPE_API_KEY 到 Git
3. **测试**: 每个新功能必须配套测试用例
4. **类型**: 后端必须用 Pydantic，前端必须用 TypeScript
