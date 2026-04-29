# AI伴侣 - 聊天 API

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.modules.llm.core.llm_core import get_engine

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    status: str = "ok"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    engine = get_engine()

    try:
        response = engine.chat(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成回应失败: {str(e)}")