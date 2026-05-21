"""
情感陪伴 API 路由

替代 ai_companion 的所有对话端点：
- POST /api/companion/chat  — 情感陪伴对话
- GET  /api/companion/history — 对话历史
- POST /api/companion/diary-respond — 对日记进行情感回应
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict

from app.db.database import get_sync_db
from app.services.companion import CompanionService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict]] = None
    diary_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[int] = None
    emotion_detected: Optional[str] = None
    safe: bool = True


class DiaryRespondRequest(BaseModel):
    diary_id: int


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_sync_db),
):
    """情感陪伴对话"""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    service = CompanionService(db)
    try:
        result = await service.chat(
            user_input=request.message,
            conversation_history=request.conversation_history,
            diary_id=request.diary_id,
        )
        return ChatResponse(
            response=result["response"],
            conversation_id=result.get("conversation_id"),
            emotion_detected=result.get("emotion_detected"),
            safe=result.get("safe", True),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")


@router.get("/history")
async def get_history(
    limit: int = Query(10, ge=1, le=100),
    mode: Optional[str] = Query(None, description="过滤模式: companion/assistant"),
    db: Session = Depends(get_sync_db),
):
    """获取对话历史"""
    service = CompanionService(db)
    history = service.get_conversation_history(limit=limit, mode=mode)
    return {"conversations": history, "count": len(history)}


@router.post("/diary-respond")
async def respond_to_diary(
    request: DiaryRespondRequest,
    db: Session = Depends(get_sync_db),
):
    """AI 对日记内容进行情感回应"""
    from sqlalchemy import select, text as sql_text
    from app.db.database import Diary

    diary_result = db.execute(
        sql_text("SELECT id, cleaned_text, emotion FROM diaries WHERE id = :id"),
        {"id": request.diary_id},
    )
    row = diary_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="日记不存在")

    diary_text = row[1] or ""
    diary_emotion = row[2]

    service = CompanionService(db)
    try:
        result = await service.chat(
            user_input=f"我今天写了一篇日记：{diary_text}",
            diary_id=request.diary_id,
        )
        return {
            "diary_id": request.diary_id,
            "diary_emotion": diary_emotion or "未知",
            "ai_response": result["response"],
            "conversation_id": result.get("conversation_id"),
            "safe": result.get("safe", True),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回应失败: {str(e)}")
