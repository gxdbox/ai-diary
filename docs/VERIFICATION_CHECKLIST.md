# AI Diary - 验证清单

本文档用于验证 Swift iOS 版本与 React Native 版本的功能兼容性。

## 一、API 兼容性验证

### 1.1 日记相关 API

| API端点 | RN 请求格式 | Swift 请求格式 | 状态 |
|--------|------------|---------------|------|
| POST /diary/create | `{ raw_text, recording_duration? }` | `CreateDiaryRequest` | ✅ 匹配 |
| GET /diary/list | `?page=1&page_size=20&emotion=xxx` | `fetchDiaries(page, pageSize, emotion)` | ✅ 匹配 |
| GET /diary/{id} | `/diary/{id}` | `fetchDiary(id)` | ✅ 匹配 |
| PUT /diary/{id} | `?cleaned_text=xxx` | `updateDiary(id, cleanedText)` | ✅ 匹配 |
| DELETE /diary/{id} | `/diary/{id}` | `deleteDiary(id)` | ✅ 匹配 |
| POST /diary/clean | `{ raw_text }` | `cleanText(rawText)` | ✅ 匹配 |

### 1.2 分析相关 API

| API端点 | RN 请求格式 | Swift 请求格式 | 状态 |
|--------|------------|---------------|------|
| GET /analysis/stats | `/analysis/stats` | `fetchStats()` | ✅ 匹配 |
| GET /analysis/emotion/trend | `?days=30` | `fetchEmotionTrend(days)` | ✅ 匹配 |
| GET /analysis/insights | `?days=30` | `fetchInsights(days)` | ✅ 匹配 |

### 1.3 搜索相关 API

| API端点 | RN 请求格式 | Swift 请求格式 | 状态 |
|--------|------------|---------------|------|
| POST /search/semantic | `{ query, limit }` | `semanticSearch(query, limit)` | ✅ 匹配 |
| POST /search/ask | `?question=xxx` | `askQuestion(question)` | ✅ 匹配 |
| GET /search/suggestions | `/search/suggestions` | `fetchSuggestions()` | ✅ 匹配 |

## 二、数据类型映射验证

### 2.1 Diary 类型

| RN 字段 | 类型 | Swift 字段 | 类型 | 状态 |
|--------|------|-----------|------|------|
| id | number | id | Int | ✅ |
| raw_text | string | raw_text | String | ✅ |
| cleaned_text | string \| null | cleaned_text | String? | ✅ |
| emotion | string \| null | emotion | String? | ✅ |
| emotion_score | number \| null | emotion_score | Double? | ✅ |
| emotion_keywords | string[] | emotion_keywords | [String] | ✅ |
| topics | string[] | topics | [String] | ✅ |
| key_events | string[] | key_events | [String] | ✅ |
| recording_duration | number \| null | recording_duration | Int? | ✅ |
| word_count | number | word_count | Int | ✅ |
| created_at | string | created_at | String | ✅ |
| updated_at | string | updated_at | String | ✅ |

### 2.2 Stats 类型

| RN 字段 | 类型 | Swift 字段 | 类型 | 状态 |
|--------|------|-----------|------|------|
| total_diaries | number | total_diaries | Int | ✅ |
| total_words | number | total_words | Int | ✅ |
| streak_days | number | streak_days | Int | ✅ |
| average_emotion_score | number | average_emotion_score | Double | ✅ |

### 2.3 Insight 类型

| RN 字段 | 类型 | Swift 字段 | 类型 | 状态 |
|--------|------|-----------|------|------|
| type | 'emotion' \| 'topic' \| 'habit' | type | InsightType | ✅ |
| insight | string | insight | String | ✅ |

## 三、UI 对照验证

### 3.1 TimelineScreen（时间轴页面）

| UI 元素 | RN 实现 | Swift 实现 | 状态 |
|--------|--------|-----------|------|
| 标题 "我的日记" | Text | Text | ✅ |
| 统计信息（总日记、连续天数） | Text | Text | ✅ |
| 日记卡片列表 | FlatList + DiaryCard | ScrollView + DiaryCard | ✅ |
| 下拉刷新 | RefreshControl | .refreshable | ✅ |
| 空状态 | 条件渲染 | 条件渲染 | ✅ |

### 3.2 RecordScreen（录音页面）

| UI 元素 | RN 实现 | Swift 实现 | 状态 |
|--------|--------|-----------|------|
| 日期显示 | Text | Text | ✅ |
| 录音按钮 | VoiceRecorder组件 | Button + Circle | ✅ |
| 录音状态（红色脉动） | 动画 | 状态切换 | ✅ |
| 实时转写卡片 | ScrollView + Text | ScrollView + Text | ✅ |
| 字数统计 | Text | Text | ✅ |
| 处理中遮罩 | ActivityIndicator | ProgressView | ✅ |

### 3.3 SearchScreen（搜索页面）

| UI 元素 | RN 实现 | Swift 实现 | 状态 |
|--------|--------|-----------|------|
| 搜索框 | TextInput | TextField | ✅ |
| 快捷问题 | TouchableOpacity chips | Button grid | ✅ |
| 搜索历史 | 条件列表 | 条件列表 | ✅ |
| 搜索结果 | FlatList | ScrollView + LazyVStack | ✅ |
| 相关度显示 | Text | Text | ✅ |

### 3.4 AnalyticsScreen（分析页面）

| UI 元素 | RN 实现 | Swift 实现 | 状态 |
|--------|--------|-----------|------|
| 时间范围选择器 | TouchableOpacity | Button | ✅ |
| 统计卡片（4个） | View cards | StatCard | ✅ |
| 情绪趋势图 | EmotionChart (chart-kit) | Chart (Swift Charts) | ✅ |
| 洞察卡片 | 条件渲染 | 条件渲染 | ✅ |

## 四、配色方案验证

| 元素 | 设计规范 | RN 实现 | Swift 实现 | 状态 |
|-----|---------|--------|-----------|------|
| 主色 | #8B7EC8 | ✅ | UIConstants.Colors.primary | ✅ |
| 辅助色 | #6BB6D6 | ✅ | UIConstants.Colors.secondary | ✅ |
| 背景 | #F5F5F7 | ✅ | UIConstants.Colors.background | ✅ |
| 文字主色 | #1D1D1F | ✅ | UIConstants.Colors.textPrimary | ✅ |
| 文字次色 | #6D6C6A | ✅ | UIConstants.Colors.textSecondary | ✅ |
| 成功色 | #34C759 | ✅ | UIConstants.Colors.success | ✅ |
| 警告色 | #FF9500 | ✅ | UIConstants.Colors.warning | ✅ |
| 错误色 | #FF3B30 | ✅ | UIConstants.Colors.error | ✅ |

## 五、功能验证矩阵

### 5.1 语音识别流程

| 步骤 | RN 实现 | Swift 实现 | 状态 |
|-----|--------|-----------|------|
| 请求权限 | Voice.requestPermissions | SFSpeechRecognizer.requestAuthorization | ✅ |
| 开始录音 | Voice.start | audioEngine.start | ✅ |
| 实时转写 | onSpeechResults回调 | recognitionTask回调 | ✅ |
| 暂停录音 | Voice.stop | audioEngine.pause | ✅ |
| 停止录音 | Voice.destroy | audioEngine.stop | ✅ |
| 时长统计 | Timer | Timer | ✅ |

### 5.2 日记创建流程

| 步骤 | RN 实现 | Swift 实现 | 状态 |
|-----|--------|-----------|------|
| 收集文本 | transcribedText | transcribedText | ✅ |
| 发送请求 | apiService.createDiary | diaryService.createDiary | ✅ |
| 处理响应 | navigation.navigate | NavigationStack | ✅ |

### 5.3 搜索流程

| 步骤 | RN 实现 | Swift 实现 | 状态 |
|-----|--------|-----------|------|
| 输入查询 | TextInput | TextField | ✅ |
| 发送请求 | apiService.semanticSearch | searchService.semanticSearch | ✅ |
| 显示结果 | FlatList | ScrollView | ✅ |
| 保存历史 | storageService.saveSearchHistory | history array | ✅ |

## 六、发布验证清单

- [x] 数据模型与 RN 版本一致
- [x] API 请求格式与 RN 版本一致
- [x] API 响应解析与 RN 版本一致
- [x] UI 布局与设计规范一致
- [x] 配色方案与设计规范一致
- [ ] 单元测试通过（待实现）
- [ ] UI 测试通过（待实现）
- [ ] 真机测试完成（待实现）
- [ ] 内存泄漏检查（待实现）

## 七、待完成事项

1. **本地存储服务** - Core Data 实现
2. **DiaryPreviewScreen** - 日记预览页面
3. **DiaryDetailScreen** - 日记详情页面
4. **单元测试** - Models 和 Services 测试
5. **UI 测试** - 流程测试
6. **真机验证** - 实际设备测试