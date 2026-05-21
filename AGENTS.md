# AI Diary - Agentic Coding Guidelines

## Project Overview

AI智能日记 App - iOS (SwiftUI) + FastAPI 智能语音日记应用

**Structure:**
```
ai_diary/
├── backend/           # FastAPI 后端 (Python 3.9+)
├── iOS/               # iOS 原生前端 (SwiftUI)
│   └── AIDiary/       # Xcode项目
│       ├── AIDiary/   # 应用代码
│       ├── AIDiaryTests/      # 单元测试
│       └── AIDiaryUITests/    # UI测试
└── docs/              # 文档
```

**部署：** 阿里云服务器 (8.136.124.182) → https://51pic.xyz

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
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 访问 API 文档：http://localhost:8000/docs
```

### iOS (SwiftUI)

```bash
cd iOS

# 打开Xcode项目
open AIDiary.xcodeproj

# 或使用Xcode打开
# File -> Open -> 选择 iOS/AIDiary.xcodeproj

# 运行模拟器
# 在Xcode中选择目标设备，点击运行按钮（Cmd+R）

# 运行测试
xcodebuild test -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 15'

# 编译验证（修改 Swift 代码后必须运行）
xcodebuild -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
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

### iOS Tests (XCTest)

```bash
cd iOS

# 运行所有测试
xcodebuild test -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 15'

# 运行单元测试
xcodebuild test -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 15' -only-testing:AIDiaryTests

# 运行UI测试
xcodebuild test -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 15' -only-testing:AIDiaryUITests
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

### iOS

```bash
cd iOS

# Swiftlint检查（如果已安装）
swiftlint

# 安装Swiftlint（如果未安装）
brew install swiftlint
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

**API 字段命名：**
```python
# 使用 snake_case，与数据库字段一致
class DiaryResponse(BaseModel):
    raw_text: str
    weather_icon: str  # 不是 weatherIcon
```

**必须导入 datetime：**
```python
from datetime import datetime
```

**数据库 JSON 字段：**
```python
diary.weather = json.dumps(weather_data.model_dump())
weather = json.loads(diary.weather) if diary.weather else None
```

---

### Swift (iOS)

**Imports:**
```swift
// 顺序：系统框架 → 第三方库 → 本地模块
import SwiftUI
import Foundation
// 第三方库
// 本地模块
```

**Naming:**
- 文件/组件：`PascalCase.swift`
- 函数/变量：`camelCase`
- 类型/协议：`PascalCase`
- 常量：`camelCase`（Swift推荐）

**Types:**
```swift
// 使用 struct 定义数据模型
struct Diary: Codable, Identifiable {
    let id: String
    let content: String
    let emotion: EmotionType
    let createdAt: Date
}

// 使用 enum 定义枚举
enum EmotionType: String, Codable {
    case positive = "positive"
    case negative = "negative"
    case neutral = "neutral"
}
```

**Error Handling:**
```swift
do {
    let response = try await apiService.createDiary(content)
} catch {
    print("API错误: \(error.localizedDescription)")
}
```

**MVVM Architecture:**
```swift
// Model: 数据模型
struct Diary { ... }

// ViewModel: 业务逻辑
@MainActor
class DiaryViewModel: ObservableObject {
    @Published var diaries: [Diary] = []
    
    func loadDiaries() async {
        // 业务逻辑
    }
}

// View: UI层
struct DiaryListView: View {
    @StateObject private var viewModel = DiaryViewModel()
    
    var body: some View {
        // UI代码
    }
}
```

**字段命名映射（重要）：**

Swift 使用 `camelCase`，后端 API 使用 `snake_case`，必须添加 `CodingKeys` 映射：

```swift
struct Weather: Codable {
    let weatherIcon: String  // Swift 用 camelCase

    enum CodingKeys: String, CodingKey {
        case weatherIcon = "weather_icon"  // 映射到 API 的 snake_case
    }
}
```

**常见映射**：
- `weatherIcon` → `weather_icon`
- `createdAt` → `created_at`
- `updatedAt` → `updated_at`
- `emotionScore` → `emotion_score`
- `rawText` → `raw_text`
- `cleanedText` → `cleaned_text`

**Swift 并发注意事项：**

- `@ObservableObject` 类默认被 MainActor 隔离
- 在 `Task.detached` 中调用需使用 `nonisolated` 方法
- 单例类需添加 `Sendable` 协议或使用 `nonisolated(unsafe)`
- Codable struct 在非隔离上下文解码需标记 `nonisolated`

```swift
// 正确示例
class LocationService: NSObject, CLLocationManagerDelegate, Sendable {
    static let shared = LocationService()

    nonisolated func getCurrentLocation(completion: @escaping (CLLocation?) -> Void) {
        // ...
    }
}
```

**Preview 代码注意：**

Preview 中的 Diary 初始化必须包含所有字段，包括可选字段（用合理默认值）：

```swift
Diary(
    id: 1,
    rawText: "测试",
    // ... 所有其他字段
    weather: Weather(temperature: 26, weather: "晴", weatherIcon: "100", location: "北京"),
    createdAt: Date(),
    updatedAt: Date()
)
```

**SwiftData 缓存限制：**

SwiftData 不支持复杂 struct（如 Weather），需拆分为多个字段：

```swift
@Model
class CachedDiary {
    var weatherTemperature: Int?
    var weatherText: String?
    var weatherIcon: String?
    var weatherLocation: String?

    func toDiary() -> Diary {
        // 从拆分字段重建 Weather
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
- **AI 子包** (`app/services/ai/`): 统一 LLM 调用、Prompt 模板、安全过滤

### iOS (SwiftUI)

- **Screens** (`AIDiary/Screens/`): 页面级视图
- **Components** (`AIDiary/Components/`): 可复用组件
- **Services** (`AIDiary/Services/`): API 调用、缓存管理
- **Models** (`AIDiary/Models/`): 数据模型定义
- **Cache** (`AIDiary/Cache/`): SwiftData 缓存模型

---

## Cache Strategy (iOS)

### 核心原则

**网络数据优先，缓存作为备份**

缓存用于：
1. 离线访问历史日记
2. 网络失败时兜底
3. 保留离线创建的日记

### 同步策略

| 场景 | 行为 | 说明 |
|------|------|------|
| **无筛选加载** | 网络数据 + 缓存独有的 | 最新数据 + 离线创建 |
| **有筛选加载** | 只用网络数据 | 保证筛选条件匹配 |
| **网络成功** | 更新缓存 | 缓存保持最新 |
| **网络失败** | 用缓存兜底 | 离线可访问 |
| **创建日记** | 先存缓存，后同步网络 | 保留离线创建 |
| **编辑日记** | 更新缓存 + 后台同步 | 不阻塞用户 |

### 代码示例

```swift
// 无筛选：网络优先 + 缓存独有的
for networkDiary in response.items {
    mergedDiaries.append(networkDiary)  // 网络版本优先
    cachedDict[networkDiary.id] = nil
}
for (_, cachedList) in cachedDict {
    mergedDiaries.append(contentsOf: cachedList)  // 保留离线创建
}

// 有筛选：只用网络数据
mergedDiaries = response.items
```

### 开发注意事项

**任何涉及数据增删改查的功能，都必须考虑缓存同步：**

1. 新增数据 → 先存缓存，后台同步网络
2. 更新数据 → 更新缓存 + 后台同步
3. 删除数据 → 删除缓存 + 后台同步
4. 查询数据 → 区分筛选/无筛选场景
5. 网络失败 → 用缓存兜底

---

## Environment Variables

### Backend (.env)
```bash
DEEPSEEK_API_KEY=your_api_key
DATABASE_URL=sqlite+aiosqlite:///./ai_diary.db
CHROMA_PERSIST_DIR=./chroma_data
DEBUG=true
```

### iOS
- API 地址配置在 `Services/APIService.swift`
- 默认：`http://localhost:8000`
- 生产环境：`https://51pic.xyz`

---

## Deployment

### 后端部署到阿里云

```bash
# 1. 停止服务
ssh root@8.136.124.182 "pkill -f uvicorn"

# 2. 备份数据库
ssh root@8.136.124.182 "cd ~/ai-diary && cp ai_diary.db ai_diary.db.bak"

# 3. 上传代码
scp -r backend/app/* root@8.136.124.182:~/ai-diary/app/

# 4. 启动服务
ssh root@8.136.124.182 "cd ~/ai-diary && nohup /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &"

# 5. 验证
curl https://51pic.xyz/health
```

---

## Development Workflow

1. **后端开发**:
   - 修改代码后自动重载
   - 测试：`pytest tests/test_api.py::test_function_name -v`
   - API 文档：http://localhost:8000/docs

2. **iOS开发**:
   - Xcode自动重载（Cmd+R）
   - 模拟器热更新
   - 使用预览功能快速调试（Canvas）

3. **提交前检查**:
   - 后端测试通过
   - iOS编译无错误
   - Swiftlint检查通过

---

## Common Tasks

### 添加新的 API 端点

1. 在 `backend/app/api/` 创建路由文件
2. 在 `backend/app/main.py` 注册 router
3. 编写测试用例
4. 更新 API 文档

### 添加新的iOS页面

1. 在 `iOS/AIDiary/AIDiary/Screens/` 创建SwiftUI视图
2. 在 `ContentView.swift` 或相应导航逻辑中添加路由
3. 如需要，在 `ViewModels/` 创建对应的ViewModel
4. 在 `Models/` 定义数据模型（如果需要新模型）

### 修改 AI 服务逻辑

1. 编辑 `backend/app/services/ai_service.py` 或 `backend/app/services/ai/`
2. 更新相关 API 端点
3. 测试 AI 响应格式

---

## iOS 权限问题诊断流程（重要教训）

**遇到 iOS 系统权限问题时，必须先检查项目配置，再检查代码！**

### 正确的诊断顺序：

1. **检查 project.pbxproj 配置**
   ```bash
   grep "INFOPLIST_KEY_NS" project.pbxproj
   grep "GENERATE_INFOPLIST_FILE" project.pbxproj
   ```
   - 如果 `GENERATE_INFOPLIST_FILE = YES`，权限描述必须通过 `INFOPLIST_KEY_*` 配置
   - 自定义 Info.plist 文件可能不生效

2. **验证权限描述是否存在**
   - 位置：`INFOPLIST_KEY_NSLocationWhenInUseUsageDescription`
   - 相机：`INFOPLIST_KEY_NSCameraUsageDescription`
   - 麦克风：`INFOPLIST_KEY_NSMicrophoneUsageDescription`
   - 照片：`INFOPLIST_KEY_NSPhotoLibraryUsageDescription`

3. **配置正确后再检查代码逻辑**

### 错误的诊断方式（教训）：

❌ 直接修改代码逻辑、添加调试日志
❌ 假设配置正确，在代码层面反复调试
❌ 忽略用户提供的线索（如"只有两个选项而不是四个")

---

## 功能开发完成后的清理流程

**每次功能开发完成后，必须执行以下清理步骤：**

### 清理内容：

1. **调试日志**
   - 移除所有 `print()` 调试语句（特别是带 emoji 标记的）
   - 保留必要的错误日志（使用 `logger` 或 `NSLog`）

2. **测试数据**
   - 检查数据库是否有测试记录需要删除
   - 检查代码中是否有硬编码的测试值

3. **不必要的注释**
   - 移除临时性的调试注释
   - 保留解释复杂逻辑的必要注释

### 清理流程：

```bash
# 1. 检查调试日志
grep -r "print(" iOS/AIDiary/AIDiary/

# 2. 检查测试数据关键词
grep -r "测试|test|debug|DEBUG" backend/app/
grep -r "测试|test|debug" iOS/AIDiary/AIDiary/

# 3. 清理并提交
git add <cleaned files>
git commit -m "chore: 清理调试日志，精简代码"

# 4. 合并分支到 master
git checkout master
git merge <feature-branch>
git push origin master
```

### 注意：

- **生产环境的 fallback 机制要保留**（如 `_mock_response`）
- **必要的错误处理和日志要保留**
- **功能说明注释可保留**，但调试注释要删除

---

## Git 提交规范

### Commit 格式

```
<type>: <简短描述>

<详细说明（可选）>
```

**type 类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `chore`: 配置/杂项
- `refactor`: 重构
- `docs`: 文档

---

## Debugging Tips

- **后端**: 使用 `--reload` 自动重载，查看 uvicorn 日志
- **iOS**: 使用Xcode内置调试器、LLDB、View Hierarchy
- **网络**: 使用Charles或Proxyman抓包
- **数据库**: `backend/ai_diary.db` 是 SQLite 文件
- **向量数据**: `backend/chroma_data/` 存储 ChromaDB 数据

---

## Important Notes

1. **不要提交**: `.env`, `venv/`, `node_modules/`, `*.db`, `__pycache__/`
2. **API Key**: 永远不要提交 DEEPSEEK_API_KEY 到 Git
3. **测试**: 每个新功能必须配套测试用例
4. **类型**: 后端必须用 Pydantic，iOS必须用Codable
5. **iOS缓存**: 任何数据操作都必须考虑缓存同步
6. **架构**: iOS使用MVVM架构，ViewModel负责业务逻辑
7. **编译验证**: 修改 Swift 代码后必须立即编译验证

---

## 项目关键路径

| 路径 | 说明 |
|------|------|
| `iOS/AIDiary/AIDiary/` | iOS SwiftUI 代码 |
| `backend/app/api/` | FastAPI 路由 |
| `backend/app/db/database.py` | SQLAlchemy 模型 |
| `backend/app/services/ai/` | AI 服务（LLM调用、Prompt、安全过滤） |
| `iOS/AIDiary/AIDiary/Cache/` | SwiftData 缓存模型 |
