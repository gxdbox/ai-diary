"""
日记相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List
import json

from app.db.database import get_db, Diary
from app.models.diary import (
    DiaryCreate, DiaryResponse, DiaryListResponse,
    CleanTextRequest, CleanTextResponse
)
from app.services.ai_service import ai_service
from app.services.text_cleaner import text_cleaner
from app.services.vector_store import vector_store

router = APIRouter()


@router.post("/clean", response_model=CleanTextResponse)
async def clean_text(request: CleanTextRequest):
    """
    清洗语音转写文本
    使用AI进行智能清洗
    """
    try:
        # 使用AI清洗
        cleaned = await ai_service.clean_text(request.raw_text)

        return CleanTextResponse(
            cleaned_text=cleaned,
            original_length=len(request.raw_text),
            cleaned_length=len(cleaned)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本清洗失败: {str(e)}")


@router.post("/create", response_model=DiaryResponse)
async def create_diary(
    request: DiaryCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新日记
    1. AI清洗文本
    2. AI分析情绪和主题
    3. 保存到数据库
    4. 添加到向量存储
    """
    try:
        # AI清洗文本
        cleaned_text = await ai_service.clean_text(request.raw_text)

        # AI分析
        analysis = await ai_service.full_analysis(cleaned_text)

        # 创建日记记录
        diary = Diary(
            raw_text=request.raw_text,
            cleaned_text=cleaned_text,
            emotion=analysis["emotion"].get("emotion"),
            emotion_score=analysis["emotion"].get("score"),
            emotion_keywords=json.dumps(analysis["emotion"].get("keywords", []), ensure_ascii=False),
            topics=json.dumps(analysis["topics"], ensure_ascii=False),
            key_events=json.dumps(analysis["key_events"], ensure_ascii=False),
            recording_duration=request.recording_duration,
            word_count=len(cleaned_text)
        )

        db.add(diary)
        await db.commit()
        await db.refresh(diary)

        # 添加到向量存储
        vector_store.add_diary(
            diary_id=diary.id,
            text=cleaned_text,
            metadata={
                "emotion": diary.emotion,
                "created_at": diary.created_at.isoformat()
            }
        )

        return _diary_to_response(diary)

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建日记失败: {str(e)}")


@router.get("/list", response_model=DiaryListResponse)
async def list_diaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    emotion: str = Query(None, description="按情绪筛选"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取日记列表
    支持分页和情绪筛选
    """
    try:
        # 构建查询
        query = select(Diary)

        if emotion:
            query = query.where(Diary.emotion == emotion)

        # 计算总数
        count_query = select(func.count()).select_from(Diary)
        if emotion:
            count_query = count_query.where(Diary.emotion == emotion)

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页查询
        query = query.order_by(desc(Diary.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        diaries = result.scalars().all()

        return DiaryListResponse(
            items=[_diary_to_response(d) for d in diaries],
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记列表失败: {str(e)}")


@router.get("/{diary_id}", response_model=DiaryResponse)
async def get_diary(
    diary_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单篇日记详情
    """
    try:
        result = await db.execute(
            select(Diary).where(Diary.id == diary_id)
        )
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        return _diary_to_response(diary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记失败: {str(e)}")


@router.delete("/{diary_id}")
async def delete_diary(
    diary_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除日记
    """
    try:
        result = await db.execute(
            select(Diary).where(Diary.id == diary_id)
        )
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        await db.delete(diary)
        await db.commit()

        # 从向量存储删除
        vector_store.delete_diary(diary_id)

        return {"message": "删除成功", "id": diary_id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除日记失败: {str(e)}")


@router.put("/{diary_id}", response_model=DiaryResponse)
async def update_diary(
    diary_id: int,
    cleaned_text: str = Query(..., description="修改后的文本"),
    db: AsyncSession = Depends(get_db)
):
    """
    更新日记内容
    """
    try:
        result = await db.execute(
            select(Diary).where(Diary.id == diary_id)
        )
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        # 更新文本
        diary.cleaned_text = cleaned_text
        diary.word_count = len(cleaned_text)

        # 重新分析
        analysis = await ai_service.full_analysis(cleaned_text)
        diary.emotion = analysis["emotion"].get("emotion")
        diary.emotion_score = analysis["emotion"].get("score")
        diary.emotion_keywords = json.dumps(analysis["emotion"].get("keywords", []), ensure_ascii=False)
        diary.topics = json.dumps(analysis["topics"], ensure_ascii=False)
        diary.key_events = json.dumps(analysis["key_events"], ensure_ascii=False)

        await db.commit()
        await db.refresh(diary)

        # 更新向量存储
        vector_store.update_diary(
            diary_id=diary.id,
            text=cleaned_text,
            metadata={
                "emotion": diary.emotion,
                "created_at": diary.created_at.isoformat()
            }
        )

        return _diary_to_response(diary)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新日记失败: {str(e)}")


def _diary_to_response(diary: Diary) -> DiaryResponse:
    """将数据库模型转换为响应模型"""
    return DiaryResponse(
        id=diary.id,
        raw_text=diary.raw_text,
        cleaned_text=diary.cleaned_text,
        emotion=diary.emotion,
        emotion_score=diary.emotion_score,
        emotion_keywords=json.loads(diary.emotion_keywords) if diary.emotion_keywords else [],
        topics=json.loads(diary.topics) if diary.topics else [],
        key_events=json.loads(diary.key_events) if diary.key_events else [],
        recording_duration=diary.recording_duration,
        word_count=diary.word_count,
        created_at=diary.created_at,
        updated_at=diary.updated_at
    )