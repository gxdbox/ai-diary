# API文档

## 基础信息

- Base URL: `http://localhost:8000/api`
- Content-Type: `application/json`

## 日记接口

### 创建日记

```http
POST /diary/create
```

请求体:
```json
{
  "raw_text": "今天天气不错，嗯，我想出去走走...",
  "recording_duration": 120
}
```

响应:
```json
{
  "id": 1,
  "raw_text": "今天天气不错，嗯，我想出去走走...",
  "cleaned_text": "今天天气不错，我想出去走走。",
  "emotion": "开心",
  "emotion_score": 7.5,
  "emotion_keywords": ["开心", "不错"],
  "topics": ["生活", "天气"],
  "key_events": ["想出去走走"],
  "word_count": 12,
  "created_at": "2026-03-18T10:30:00"
}
```

### 获取日记列表

```http
GET /diary/list?page=1&page_size=20&emotion=开心
```

### 获取日记详情

```http
GET /diary/{id}
```

### 删除日记

```http
DELETE /diary/{id}
```

## 分析接口

### 文本清洗

```http
POST /diary/clean
```

请求体:
```json
{
  "raw_text": "嗯，今天天气不错啊..."
}
```

### 情绪分析

```http
POST /analysis/analyze
```

请求体:
```json
{
  "text": "今天工作很顺利，心情很好..."
}
```

响应:
```json
{
  "emotion": {
    "emotion": "开心",
    "score": 8.0,
    "keywords": ["顺利", "好"]
  },
  "topics": ["工作"],
  "key_events": ["工作顺利"]
}
```

### 统计数据

```http
GET /analysis/stats
```

### 情绪趋势

```http
GET /analysis/emotion/trend?days=30
```

### AI洞察

```http
GET /analysis/insights?days=30
```

## 搜索接口

### 语义搜索

```http
POST /search/semantic
```

请求体:
```json
{
  "query": "最近开心的事",
  "limit": 10
}
```

### AI问答

```http
POST /search/ask?question=我这个月在焦虑什么
```

### 搜索建议

```http
GET /search/suggestions
```