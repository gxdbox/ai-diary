"""
搜索相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import json

from app.db.database import get_db, Diary
from app.models.diary import SearchRequest, SearchResponse, SearchResult
from app.services.vector_store import vector_store
from app.services.ai_service import ai_service

router = APIRouter()


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    语义搜索
    使用向量相似度进行搜索
    """
    try:
        # 向量搜索
        results = vector_store.search(request.query, request.limit)

        # 获取完整日记信息
        search_results = []
        for r in results:
            result = await db.execute(
                select(Diary).where(Diary.id == r["id"])
            )
            diary = result.scalar_one_or_none()

            if diary:
                search_results.append(SearchResult(
                    id=diary.id,
                    text=diary.cleaned_text[:200] + "..." if len(diary.cleaned_text) > 200 else diary.cleaned_text,
                    score=r["score"],
                    created_at=diary.created_at
                ))

        return SearchResponse(
            results=search_results,
            query=request.query,
            total=len(search_results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/keyword")
async def keyword_search(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    关键词搜索
    使用SQL LIKE进行简单搜索
    """
    try:
        result = await db.execute(
            select(Diary)
            .where(Diary.cleaned_text.contains(keyword))
            .limit(limit)
        )
        diaries = result.scalars().all()

        return {
            "results": [{
                "id": d.id,
                "text": d.cleaned_text[:200] + "..." if len(d.cleaned_text) > 200 else d.cleaned_text,
                "created_at": d.created_at.isoformat()
            } for d in diaries],
            "query": keyword,
            "total": len(diaries)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/ask")
async def ask_question(
    question: str = Query(..., description="用户问题"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI问答
    基于日记内容回答问题
    """
    try:
        # 先搜索相关日记
        results = vector_store.search(question, n_results=5)

        if not results:
            return {
                "answer": "抱歉，我在你的日记中没有找到相关信息。",
                "sources": []
            }

        # 构建上下文
        context_parts = []
        source_ids = []

        for r in results:
            result = await db.execute(
                select(Diary).where(Diary.id == r["id"])
            )
            diary = result.scalar_one_or_none()

            if diary:
                context_parts.append(f"[{diary.created_at.strftime('%Y-%m-%d')}]\n{diary.cleaned_text}")
                source_ids.append(diary.id)

        context = "\n\n---\n\n".join(context_parts)

        # 调用AI回答
        answer = await ai_service.answer_question(question, context)

        return {
            "answer": answer,
            "sources": source_ids,
            "context_count": len(context_parts)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@router.get("/suggestions")
async def get_search_suggestions():
    """
    获取搜索建议（快捷问题）
    """
    suggestions = [
        "最近在焦虑什么？",
        "本月开心的事",
        "去年的今天",
        "关于工作的日记",
        "情绪低落的日子",
        "和家人在一起",
        "周末做了什么",
        "我的健康记录"
    ]

    return {"suggestions": suggestions}