"""
日记助手 API 路由 - 基于 ProactAgent 论文思想

提供智能日记辅助功能：
1. AI 问答（整合三层记忆）
2. 主动检索相关记忆
3. 用户上下文
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List
import json

from app.db.database import get_sync_db, Diary
from app.models.memory import (
    RetrievalRequest, ProactiveRetrievalResponse
)
from app.services.diary_assistant import DiaryAssistantService
from app.services.ai_service import ai_service

router = APIRouter()


@router.post("/ask")
async def ask_question(
    question: str = Query(..., description="用户问题"),
    db: Session = Depends(get_sync_db)
):
    """
    AI 智能问答

    整合 ProactAgent 三层记忆：
    - 事实记忆：用户偏好、情绪模式
    - 情节记忆：相关历史日记
    - 行为技能：写作习惯

    返回：AI 回答 + 相关日记列表
    """
    try:
        assistant = DiaryAssistantService(db)

        # 1. 主动检索相关记忆
        retrieval_response = assistant.retrieval_service.retrieve(
            RetrievalRequest(
                current_context=question,
                max_results=5,
                min_importance=0.3
            )
        )

        # 2. 获取用户上下文（偏好、情绪模式）
        user_context = assistant.get_user_context()

        # 3. 构建上下文内容
        context_parts = []
        related_diaries = []

        # 添加情节记忆（相关日记）
        for result in retrieval_response.results[:3]:
            if result.memory.memory_type.value == "episodic" and result.memory.source_diary_id:
                diary_result = db.execute(
                    select(Diary).where(Diary.id == result.memory.source_diary_id)
                )
                diary = diary_result.scalar_one_or_none()
                if diary:
                    context_parts.append(
                        f"[{diary.created_at.strftime('%Y-%m-%d')}]\n{diary.cleaned_text[:300]}"
                    )
                    related_diaries.append({
                        "id": diary.id,
                        "text": diary.cleaned_text[:100] + "..." if len(diary.cleaned_text) > 100 else diary.cleaned_text,
                        "date": diary.created_at.strftime('%Y-%m-%d'),
                        "emotion": diary.emotion
                    })

        # 添加用户上下文信息
        if user_context.get("common_topics"):
            context_parts.append(
                f"[用户偏好]\n常写主题：{', '.join(user_context['common_topics'][:5])}"
            )

        if user_context.get("emotion_distribution"):
            top_emotions = sorted(
                user_context["emotion_distribution"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            context_parts.append(
                f"[情绪模式]\n常见情绪：{', '.join([e[0] for e in top_emotions])}"
            )

        context = "\n\n---\n\n".join(context_parts) if context_parts else "暂无相关记忆"

        # 4. 调用 AI 生成回答
        answer = await ai_service.answer_question(question, context)

        return {
            "answer": answer,
            "related_diaries": related_diaries,
            "context_used": len(context_parts),
            "retrieval_trigger": retrieval_response.retrieval_trigger
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")


@router.post("/retrieve", response_model=ProactiveRetrievalResponse)
async def proactive_retrieve(
    request: RetrievalRequest,
    db: Session = Depends(get_sync_db)
):
    """
    主动检索记忆

    返回是否需要检索、检索原因、相关记忆
    """
    try:
        from app.services.proactive_retrieval import ProactiveRetrievalService
        retrieval = ProactiveRetrievalService(db)
        response = retrieval.retrieve(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/context")
async def get_user_context(db: Session = Depends(get_sync_db)):
    """
    获取用户上下文

    返回用户的偏好、常用主题、情绪分布、写作习惯
    """
    try:
        assistant = DiaryAssistantService(db)
        context = assistant.get_user_context()
        return context
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取上下文失败: {str(e)}")


@router.post("/learn/{diary_id}")
async def learn_from_diary(
    diary_id: int,
    diary_data: Dict,
    db: Session = Depends(get_sync_db)
):
    """
    从日记学习

    写完日记后调用，自动提取并存储记忆
    """
    try:
        diary_data["id"] = diary_id
        assistant = DiaryAssistantService(db)
        assistant.learn_from_diary(diary_id, diary_data)
        return {"success": True, "message": "学习完成"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"学习失败: {str(e)}")


@router.post("/feedback/{diary_id}")
async def record_feedback(
    diary_id: int,
    memory_id: int,
    was_helpful: bool,
    db: Session = Depends(get_sync_db)
):
    """
    记录反馈并学习

    用户反馈检索结果是否有帮助
    ProactAgent 核心：通过反馈改进检索策略
    """
    try:
        assistant = DiaryAssistantService(db)
        assistant.record_feedback(diary_id, memory_id, was_helpful)
        return {
            "success": True,
            "message": f"反馈已记录：{'有帮助' if was_helpful else '无帮助'}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录反馈失败: {str(e)}")


@router.get("/memories")
async def get_all_memories(db: Session = Depends(get_sync_db)):
    """
    获取所有记忆

    查看两种类型的记忆内容
    """
    try:
        from app.services.memory_service import MemoryService
        from app.models.memory import MemoryType

        memory_service = MemoryService(db)
        memories = memory_service.get_all_memories()

        return {
            "factual": [
                {
                    "id": m.id,
                    "content": m.content,
                    "keywords": m.keywords,
                    "importance": m.importance_score
                }
                for m in memories.get(MemoryType.FACTUAL, [])
            ],
            "episodic": [
                {
                    "id": m.id,
                    "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                    "keywords": m.keywords,
                    "source_diary_id": m.source_diary_id,
                    "importance": m.importance_score
                }
                for m in memories.get(MemoryType.EPISODIC, [])[:20]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆失败: {str(e)}")