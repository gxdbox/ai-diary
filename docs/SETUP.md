# 环境搭建指南

## 开发环境

### 1. 安装Node.js

```bash
# macOS使用Homebrew
brew install node

# 验证安装
node -v  # 应该 >= 18
npm -v
```

### 2. 安装Python

```bash
# macOS使用Homebrew
brew install python@3.11

# 验证安装
python3 --version  # 应该 >= 3.9
```

### 3. 安装Xcode

从App Store安装Xcode，然后:

```bash
# 安装Command Line Tools
xcode-select --install

# 安装CocoaPods
sudo gem install cocoapods
```

## 后端环境

### 1. 创建虚拟环境

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置阿里云百炼

1. 访问 https://dashscope.aliyun.com
2. 注册/登录阿里云账号
3. 开通百炼服务
4. 创建API Key

```bash
# 配置环境变量
cp .env.example .env

# 编辑.env
DASHSCOPE_API_KEY=sk-xxxxxxxx
```

### 4. 启动后端

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看API文档

## 移动端环境

### 1. 安装依赖

```bash
cd mobile
npm install
```

### 2. iOS配置

```bash
cd ios
pod install
cd ..
```

### 3. 配置API地址

如果后端运行在其他地址，编辑 `src/services/apiService.ts`:

```typescript
const API_BASE_URL = 'http://你的IP地址:8000/api';
```

### 4. 运行应用

```bash
# iOS模拟器
npm run ios

# 指定模拟器
npm run ios -- --simulator="iPhone 15 Pro"
```

## 常见问题

### Q: 语音识别不工作

确保Info.plist中添加了权限:

```xml
<key>NSMicrophoneUsageDescription</key>
<string>AI日记需要使用麦克风来录制您的语音日记</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>AI日记需要语音识别权限来将您的语音转换为文字</string>
```

### Q: 无法连接后端

1. 确保后端正在运行
2. 检查防火墙设置
3. 使用实际IP地址而非localhost

### Q: iOS编译错误

```bash
# 清理缓存
cd ios
rm -rf Pods Podfile.lock
pod install
cd ..
rm -rf node_modules
npm install
```

### Q: ChromaDB初始化失败

确保Python版本兼容:
```bash
pip install chromadb==0.4.22
```