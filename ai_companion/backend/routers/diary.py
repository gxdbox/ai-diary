# AI伴侣 - 日记回应 API（支持情绪匹配+对话记忆）

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from backend.modules.llm.core.llm_core import get_engine
from backend.database import ConversationDB
from backend.data_sync import get_diaries, get_diary_by_id, get_stats

router = APIRouter(tags=["diary"])


class DiaryListResponse(BaseModel):
    diaries: List[dict]
    stats: dict


class DiaryRespondRequest(BaseModel):
    diary_id: int
    user_id: Optional[str] = None


class DiaryRespondResponse(BaseModel):
    diary_id: int
    diary_text: str
    diary_emotion: str
    ai_response: str
    conversation_id: Optional[int] = None
    prompt_version: Optional[str] = None
    status: str = "ok"


@router.get("/api/diaries", response_model=DiaryListResponse)
async def list_diaries(limit: int = 20, emotion: Optional[str] = None):
    """获取日记列表"""
    diaries = get_diaries(limit, emotion)
    stats = get_stats()
    return DiaryListResponse(diaries=diaries, stats=stats)


@router.post("/api/diary/respond", response_model=DiaryRespondResponse)
async def respond_to_diary(request: DiaryRespondRequest):
    """AI对日记内容进行情感回应 - 支持情绪匹配"""
    # 获取日记
    diary = get_diary_by_id(request.diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    # 获取AI回应（使用情绪匹配）
    engine = get_engine()
    result = engine.chat(
        user_input=f"我今天写了一篇日记：{diary['text']}",
        emotion=diary['emotion'],  # 情绪标签匹配
        diary_id=request.diary_id
    )

    return DiaryRespondResponse(
        diary_id=request.diary_id,
        diary_text=diary['text'],
        diary_emotion=diary['emotion'] or '未知',
        ai_response=result["response"],
        conversation_id=result.get("conversation_id"),
        prompt_version=result.get("prompt_version")
    )


@router.get("/api/diary/{diary_id}")
async def get_diary(diary_id: int):
    """获取单篇日记详情"""
    diary = get_diary_by_id(diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    return diary