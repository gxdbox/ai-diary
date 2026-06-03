# AI智能日记App

基于 **iOS原生 Swift/SwiftUI** + FastAPI + DeepSeek AI 的智能语音日记应用。

## 功能特性

- 🎤 **语音录制** - 实时语音转文字，支持暂停/继续
- 🤖 **AI文本清洗** - 自动去除口语填充词、纠正错别字
- 😊 **情绪分析** - AI自动识别情绪类型和强度
- 🏷️ **主题提取** - 自动提取日记主题标签
- 🔍 **智能搜索** - 基于向量相似度的语义搜索
- 📊 **数据分析** - 情绪趋势图表和习惯洞察
- 💾 **本地存储** - Core Data 本地数据库，支持离线

## 项目结构

```
ai_diary/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 应用入口
│   │   ├── api/               # API路由
│   │   ├── services/          # 业务服务
│   │   ├── models/            # 数据模型
│   │   └── db/                # 数据库
│   ├── requirements.txt
│   └── .env.example
│
├── iOS/                        # iOS 原生移动端 (Swift/SwiftUI)
│   └── AIDiary/
│       ├── App/               # 应用入口
│       ├── Models/            # 数据模型
│       ├── Services/          # 服务层 (API, 语音识别, 存储)
│       ├── Views/             # SwiftUI 视图
│       │   ├── Screens/       # 页面
│       │   ├── Components/    # 组件
│       │   └── Navigation/    # 导航
│       ├── ViewModels/        # 视图模型 (MVVM)
│       ├── Utils/             # 工具类
│       └── Resources/         # 资源文件
│
└── docs/                       # 文档
    ├── API.md                 # API 文档
    ├── SETUP.md               # 安装指南
    └── VERIFICATION_CHECKLIST.md # 验证清单
```

## 快速开始

### 环境要求

- Xcode >= 15 (iOS开发)
- Python >= 3.9
- iOS >= 16.0 (目标设备)

### 后端配置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### iOS 移动端配置

```bash
# 打开 iOS 项目
cd iOS
open AIDiary.xcodeproj  # 或使用 Xcode 打开

# 在 Xcode 中配置：
# 1. 选择目标设备或模拟器
# 2. 点击运行 (Cmd+R)
```

> **注意**: 完整的 Xcode 项目配置需要通过 Xcode 创建。当前代码结构提供了完整的 Swift 源文件。

## API文档

启动后端后访问: http://localhost:8000/docs

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/diary/create` | POST | 创建日记（自动清洗+分析） |
| `/api/diary/list` | GET | 获取日记列表 |
| `/api/diary/{id}` | GET | 获取日记详情 |
| `/api/diary/clean` | POST | 文本清洗 |
| `/api/analysis/analyze` | POST | 情绪和主题分析 |
| `/api/search/semantic` | POST | 语义搜索 |
| `/api/search/ask` | POST | AI问答 |
| `/api/analysis/stats` | GET | 统计数据 |
| `/api/analysis/insights` | GET | AI洞察 |

## 环境变量

```bash
# 阿里云百炼API
DASHSCOPE_API_KEY=your_api_key_here

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./ai_diary.db

# 向量数据库
CHROMA_PERSIST_DIR=./chroma_data
```

## 技术栈

### 后端
- FastAPI - Web框架
- SQLAlchemy + aiosqlite - 异步数据库
- DeepSeek API - AI 服务
- ChromaDB - 向量存储

### iOS 移动端
- Swift 5.9+ - 编程语言
- SwiftUI - UI 框架
- MVVM - 架构模式
- URLSession - 网络请求
- Speech Framework - 语音识别
- Core Data - 本地存储
- Swift Charts - 图表绘制

## 开发指南

### 添加新的AI分析功能

1. 在 `backend/app/services/ai_service.py` 添加新的分析方法
2. 在 `backend/app/api/analysis.py` 添加新的API端点
3. 在移动端调用新API

### 自定义文本清洗规则

编辑 `backend/app/services/text_cleaner.py`:

```python
FILLER_WORDS = [
    "嗯", "啊", "哈", "那个", ...
]
```

## 部署

### 后端部署

```bash
# 使用Docker
docker build -t ai-diary-backend .
docker run -p 8000:8000 ai-diary-backend
```

### iOS打包

```bash
cd iOS/AIDiary
# 使用 Xcode 进行 Archive 和导出
```

## 许可证

MIT License
