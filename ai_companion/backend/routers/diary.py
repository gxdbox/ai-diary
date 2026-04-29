# AI伴侣 - 日记回应 API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from backend.modules.llm.core.llm_core import get_engine
from backend.data_sync import get_diaries, get_diary_by_id, get_stats, save_conversation

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
    status: str = "ok"


@router.get("/diaries", response_model=DiaryListResponse)
async def list_diaries(limit: int = 20, emotion: Optional[str] = None):
    """获取日记列表"""
    diaries = get_diaries(limit, emotion)
    stats = get_stats()
    return DiaryListResponse(diaries=diaries, stats=stats)


@router.post("/diary/respond", response_model=DiaryRespondResponse)
async def respond_to_diary(request: DiaryRespondRequest):
    """AI对日记内容进行情感回应"""
    # 获取日记
    diary = get_diary_by_id(request.diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    # 构建输入：让AI知道这是一篇日记，需要给予情感回应
    prompt = f"""用户今天写了一篇日记，内容如下：

---
{diary['text']}
---

日记中记录的情绪是：{diary['emotion'] or '未知'}

请阅读这篇日记，给予用户温暖的情感回应。记住：
1. 先表达你理解他们的感受和经历
2. 温和地引导他们思考或倾诉更多
3. 给予真诚的鼓励和支持
4. 像朋友一样自然对话，不要太长"""

    # 获取AI回应
    engine = get_engine()
    ai_response = engine.chat(prompt)

    # 保存对话记录
    save_conversation(
        diary_id=request.diary_id,
        user_input=diary['text'],
        ai_response=ai_response,
        emotion_before=diary['emotion']
    )

    return DiaryRespondResponse(
        diary_id=request.diary_id,
        diary_text=diary['text'],
        diary_emotion=diary['emotion'] or '未知',
        ai_response=ai_response
    )


@router.get("/diary/{diary_id}")
async def get_diary(diary_id: int):
    """获取单篇日记详情"""
    diary = get_diary_by_id(diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    return diary