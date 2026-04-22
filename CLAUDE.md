# 松果日记 - AI Diary 项目开发指南

## 项目概述

松果日记是一款 AI 驱动的语音日记应用，包含：
- **iOS 前端**: SwiftUI + SwiftData 本地缓存
- **后端**: FastAPI + SQLite + 向量搜索
- **部署**: 阿里云服务器 (8.136.124.182)

---

## iOS Swift 开发规范（重要）

### 1. 必须编译验证

**每次修改 Swift 代码后，必须立即运行编译验证：**

```bash
cd iOS/AIDiary && xcodebuild -scheme AIDiary -destination 'platform=iOS Simulator,name=iPhone 17 Pro' build
```

**禁止在编译失败的情况下提交代码！**

### 2. 字段命名映射

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

### 3. Swift 并发注意事项

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

### 4. Preview 代码注意

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

### 5. SwiftData 缓存限制

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

## 后端开发规范

### 1. API 字段命名

使用 `snake_case`，与数据库字段一致：

```python
class DiaryResponse(BaseModel):
    raw_text: str
    weather_icon: str  # 不是 weatherIcon
```

### 2. 必须导入 datetime

任何使用 `datetime` 的文件必须导入：

```python
from datetime import datetime
```

### 3. 数据库 JSON 字段

存储 JSON 数据时使用 `json.dumps()`，读取时用 `json.loads()`：

```python
diary.weather = json.dumps(weather_data.model_dump())
weather = json.loads(diary.weather) if diary.weather else None
```

---

## Git 提交规范

### Commit 格式

```
<type>: <简短描述>

<详细说明（可选）>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

**type 类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `chore`: 配置/杂项
- `refactor`: 重构
- `docs`: 文档

---

## 部署流程

### 后端部署

```bash
# 1. 上传代码
sshpass -p '密码' scp -r backend/app root@8.136.124.182:~/ai-diary/

# 2. 数据库迁移（如需要）
ssh root@8.136.124.182 "sqlite3 ~/ai-diary/ai_diary.db 'ALTER TABLE diaries ADD COLUMN xxx TEXT;'"

# 3. 重启服务
ssh root@8.136.124.182 "pkill -f uvicorn; cd ~/ai-diary && /opt/conda/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &"

# 4. 验证
curl https://51pic.xyz/health
```

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

### 经验教训：

2026-04-22 的位置权限问题，反复调试几十次才解决。根本原因是 `GENERATE_INFOPLIST_FILE = YES` 导致自定义 Info.plist 不生效，需要通过 `INFOPLIST_KEY_NSLocationWhenInUseUsageDescription` 在 project.pbxproj 中配置。

---

## 功能开发完成后的清理流程（重要）

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
grep -r "print(" iOS/AIDiary/AIDiary/Sources/

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

## Claude 工作流程承诺

**在每次对话中，Claude 将：**

1. **修改 Swift 代码后立即编译验证**
2. **修改后端代码后测试 API 响应**
3. **提交前再次确认编译/API 正常**
4. **遇到错误时先修复再继续，不跳过**

---

## 项目关键路径

| 路径 | 说明 |
|------|------|
| `iOS/AIDiary/AIDiary/` | iOS SwiftUI 代码 |
| `backend/app/api/` | FastAPI 路由 |
| `backend/app/db/database.py` | SQLAlchemy 模型 |
| `backend/app/models/diary.py` | Pydantic 模型 |
| `.claude/memory/` | Claude 项目记忆 |