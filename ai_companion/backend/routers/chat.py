# AI伴侣 - 聊天 API（支持对话记忆+情绪匹配）

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.llm.core.llm_core import get_engine

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    emotion: Optional[str] = None  # 可选的情绪标签
    diary_id: Optional[int] = None  # 关联的日记ID


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str
    conversation_id: Optional[int] = None
    emotion_detected: Optional[str] = None
    prompt_version: Optional[str] = None
    status: str = "ok"


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口 - 支持对话记忆"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    engine = get_engine()

    try:
        result = engine.chat(
            user_input=request.message,
            emotion=request.emotion,
            diary_id=request.diary_id
        )
        return ChatResponse(
            response=result["response"],
            conversation_id=result.get("conversation_id"),
            emotion_detected=result.get("emotion_detected"),
            prompt_version=result.get("prompt_version"),
            status="ok"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成回应失败: {str(e)}")


@router.get("/api/chat/history")
async def get_chat_history(limit: int = 10):
    """获取对话历史"""
    from backend.database import ConversationDB
    history = ConversationDB.get_recent_conversations(limit)
    return {"conversations": history, "count": len(history)}