"""
AI智能日记App - FastAPI后端
"""
# 首先加载环境变量
import os
from pathlib import Path
from dotenv import load_dotenv

# 从项目根目录加载 .env（main.py 在 app/ 子目录下）
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# 仅在 production 环境启用 Sentry
if os.getenv("APP_ENV") == "production" and os.getenv("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=os.getenv("APP_ENV", "production"),
        release="ai-diary@1.0.0",
        send_default_pii=True  # 包含用户信息(可选)
    )
    import logging
    logging.getLogger(__name__).info("Sentry initialized successfully in production mode")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler

# 创建 logs 目录
os.makedirs("logs", exist_ok=True)

# 配置日志格式
log_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
)

# 文件日志处理器(带轮转)
file_handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# 控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.WARNING)

# 配置根日志器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

from app.api import diary, analysis, search, dictionary, assistant, companion, world
from app.api.test_sentry import router as test_router
from app.db.database import init_db, async_session_maker
from app.services.oss_service import oss_service

app = FastAPI(
    title="AI日记API",
    description="AI智能日记App后端服务",
    version="1.0.0"
)

# Prometheus 监控集成（可选）
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
except ImportError:
    # 如果未安装 prometheus-fastapi-instrumentator，跳过监控集成
    pass

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(diary.router, prefix="/api/diary", tags=["日记"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["分析"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])
app.include_router(dictionary.router, prefix="/api/dictionary", tags=["词典"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["智能助手"])
app.include_router(companion.router, prefix="/api/companion", tags=["情感陪伴"])
app.include_router(world.router, tags=["虚拟世界"])
app.include_router(test_router, tags=["测试"])


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库和词典缓存"""
    await init_db()
    # 加载词典缓存
    async with async_session_maker() as db:
        await dictionary.load_dictionary_cache(db)


@app.get("/")
async def root():
    return {"message": "AI日记API服务运行中", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """深度健康检查 - 验证所有关键组件状态"""
    from datetime import datetime
    from sqlalchemy import text
    import shutil
    
    checks = {}
    overall_status = "healthy"
    
    # 1. 检查数据库连接
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": f"Database error: {str(e)}"}
        overall_status = "degraded"
    
    # 2. 检查 ChromaDB 连通性
    try:
        from app.services.vector_store import vector_store
        # 确保已初始化
        if not vector_store._initialized:
            vector_store.init()
        
        collections = vector_store.client.list_collections()
        checks["chromadb"] = {
            "status": "ok", 
            "message": f"ChromaDB connected, {len(collections)} collections"
        }
    except Exception as e:
        checks["chromadb"] = {"status": "error", "message": f"ChromaDB error: {str(e)}"}
        overall_status = "degraded"
    
    # 3. 检查磁盘空间(备份目录)
    try:
        backup_dir = "/root/ai-diary/backups"
        if os.path.exists(backup_dir):
            total, used, free = shutil.disk_usage(backup_dir)
            free_gb = free / (1024**3)
            if free_gb < 1:  # 少于1GB警告
                checks["disk_space"] = {
                    "status": "warning",
                    "message": f"Low disk space: {free_gb:.2f}GB free"
                }
                if overall_status == "healthy":
                    overall_status = "degraded"
            else:
                checks["disk_space"] = {
                    "status": "ok",
                    "message": f"Disk space: {free_gb:.2f}GB free"
                }
        else:
            checks["disk_space"] = {"status": "ok", "message": "Backup directory not configured"}
    except Exception as e:
        checks["disk_space"] = {"status": "error", "message": f"Disk check error: {str(e)}"}
    
    # 4. 检查外部 API (可选,仅在生产环境)
    if os.getenv("APP_ENV") == "production":
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                    headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY', '')}"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    # 401 表示 API Key 有效但请求格式不对,说明连接正常
                    if resp.status in [401, 400]:
                        checks["external_api"] = {"status": "ok", "message": "DashScope API reachable"}
                    else:
                        checks["external_api"] = {"status": "warning", "message": f"Unexpected response: {resp.status}"}
        except Exception as e:
            checks["external_api"] = {"status": "error", "message": f"External API error: {str(e)}"}
            overall_status = "degraded"
    
    # 如果有任何 error,整体状态为 unhealthy
    if any(check["status"] == "error" for check in checks.values()):
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }