# AI伴侣 - FastAPI 入口

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.chat import router as chat_router
from backend.routers.diary import router as diary_router

app = FastAPI(
    title="AI伴侣",
    description="情感陪伴助手 - 基于DeepSeek API",
    version="0.1.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")
app.include_router(diary_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "AI伴侣服务运行中", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}