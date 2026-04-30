# AI伴侣 - FastAPI 入口

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.chat import router as chat_router
from backend.routers.diary import router as diary_router
from backend.routers.feedback import router as feedback_router

app = FastAPI(
    title="AI伴侣",
    description="情感陪伴助手 - 支持对话记忆、情绪匹配、用户反馈",
    version="1.0.0"
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
app.include_router(chat_router)
app.include_router(diary_router)
app.include_router(feedback_router)


@app.get("/")
async def root():
    return {
        "message": "AI伴侣服务运行中",
        "version": "1.0.0",
        "features": ["对话记忆", "情绪匹配", "用户反馈", "Prompt版本管理"]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}