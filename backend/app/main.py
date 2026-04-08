"""
AI智能日记App - FastAPI后端
"""
# 首先加载环境变量
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import diary, analysis, search
from app.db.database import init_db

app = FastAPI(
    title="AI日记API",
    description="AI智能日记App后端服务",
    version="1.0.0"
)

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


@app.on_event("startup")
async def startup():
    """应用启动时初始化数据库"""
    await init_db()


@app.get("/")
async def root():
    return {"message": "AI日记API服务运行中", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}