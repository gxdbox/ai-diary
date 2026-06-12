# Sentry 错误追踪配置指南

Sentry 是一个开源的错误追踪和性能监控平台,可以帮助您实时监控应用中的错误和异常。

## 1. 注册账号

访问 [https://sentry.io/signup/](https://sentry.io/signup/) 注册免费账号:

- 可以使用 GitHub、Google 或邮箱注册
- 选择 "Start for Free" 免费计划
- 完成邮箱验证

## 2. 创建项目

登录后创建新项目:

1. 点击左侧导航栏的 **"Projects"** → **"Create Project"**
2. 选择框架: **FastAPI** (或 Python)
3. 输入项目名称: `AI Diary`
4. 选择团队(如果有)
5. 点击 **"Create Project"**

## 3. 获取 DSN

在项目创建后,会自动显示配置页面:

1. 在 **"Configure SDK"** 部分找到 **"Client Keys (DSN)"**
2. 复制 DSN,格式类似:
   ```
   https://xxx@sentry.io/123456
   ```
   
   或者稍后在以下位置找到:
   - 进入项目设置: **Settings** → **Projects** → **Your Project**
   - 左侧菜单: **Client Keys (DSN)**
   - 复制显示的 DSN URL

## 4. 配置到服务器

将 DSN 添加到服务器的环境变量中:

```bash
# SSH 连接到服务器
ssh root@8.136.124.182

# 编辑 .env 文件
vim /root/ai-diary/.env

# 添加以下行(替换为您的实际 DSN)
SENTRY_DSN=https://your-dsn@sentry.io/xxx

# 保存退出后重启服务
sudo systemctl restart ai-diary
```

或者直接追加到 .env 文件:

```bash
ssh root@8.136.124.182 "echo 'SENTRY_DSN=https://your-dsn@sentry.io/xxx' >> /root/ai-diary/.env"
ssh root@8.136.124.182 "sudo systemctl restart ai-diary"
```

## 5. 验证配置

### 方法 1: 检查服务启动日志

```bash
ssh root@8.136.124.182 "journalctl -u ai-diary -n 20 --no-pager | grep sentry"
```

如果配置正确,应该看到 Sentry 初始化成功的日志。

### 方法 2: 触发测试错误(可选)

创建一个临时的测试端点来触发错误:

```python
# 在 backend/app/main.py 中添加临时测试端点
@app.get("/api/test-error")
async def test_error():
    """仅用于测试 Sentry 集成"""
    raise Exception("This is a test error from AI Diary")
```

然后访问:
```bash
curl https://51pic.xyz/api/test-error
```

### 方法 3: 查看 Sentry Dashboard

1. 访问 [https://sentry.io/organizations/your-org/issues/](https://sentry.io/organizations/your-org/issues/)
2. 切换到您的项目
3. 应该能看到捕获的错误事件
4. 点击错误查看详情,包括堆栈跟踪、环境信息等

## 6. 监控指标

Sentry 免费计划提供:

- ✅ 每月 **5,000 个错误事件**
- ✅ **7 天**数据保留
- ✅ 实时错误通知
- ✅ 详细的错误堆栈和上下文
- ✅ 用户反馈收集
- ✅ 性能监控(APM)基础功能

对于小项目来说完全够用!

## 7. 高级配置(可选)

### 设置错误采样率

在 `backend/app/main.py` 中可以调整采样率:

```python
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% 的性能追踪采样
    profiles_sample_rate=0.1,  # 10% 的性能分析采样
    environment="production",
    release="ai-diary@1.0.0"
)
```

### 配置错误通知

在 Sentry Dashboard 中:

1. 进入 **Settings** → **Projects** → **Your Project**
2. 左侧菜单: **Alerts**
3. 创建警报规则,例如:
   - 当新错误出现时发送邮件
   - 当错误频率超过阈值时发送 Slack/DingTalk 通知

### 忽略特定错误类型

某些预期内的错误可以忽略:

```python
from sentry_sdk import configure_scope

def ignore_expected_errors(event, hint):
    """忽略预期的错误类型"""
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        # 忽略特定的异常类型
        if isinstance(exc_value, (ValueError, KeyError)):
            return None
    return event

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    before_send=ignore_expected_errors,
    # ... 其他配置
)
```

## 8. 常见问题

### Q: Sentry 会影响性能吗?

A: Sentry 使用异步方式发送错误报告,对性能影响极小(< 1ms)。SDK 会在后台线程处理错误上报。

### Q: 如何禁用 Sentry?

A: 只需从 `.env` 文件中删除 `SENTRY_DSN` 或设置为空字符串,然后重启服务即可。代码中已自动检测 DSN 是否存在。

### Q: 数据会发送到哪里?

A: 默认发送到 Sentry 云端(sentry.io),也可以选择自建 Sentry 服务器。

### Q: 如何保护敏感信息?

A: Sentry 会自动过滤常见的敏感字段(如密码、信用卡号)。可以在初始化时配置额外的数据脱敏规则:

```python
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=False,  # 不发送个人身份信息
    max_request_body_size="never",  # 不发送请求体
    # ...
)
```

## 9. 相关资源

- 📚 [Sentry Python SDK 文档](https://docs.sentry.io/platforms/python/)
- 📚 [FastAPI 集成指南](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- 💬 [Sentry 社区论坛](https://forum.sentry.io/)
- 🐛 [GitHub Issues](https://github.com/getsentry/sentry-python/issues)

---

**提示**: 配置完成后,建议在开发环境中先测试,确保错误能正确上报到 Sentry,然后再在生产环境启用。
