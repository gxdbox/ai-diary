"""
日记助手 API 路由 - 基于 ProactAgent 论文思想 + 上下文管理技巧

提供智能日记辅助功能：
1. AI 问答（整合三层记忆 + 上下文管理）
2. 主动检索相关记忆
3. 用户上下文
4. 隐性记忆表达（避免监控感）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, List, Optional
import json

from app.db.database import get_sync_db, Diary
from app.models.memory import (
    RetrievalRequest, ProactiveRetrievalResponse
)
from app.models.context import ContextBudget, AssembledContext
from app.services.diary_assistant import DiaryAssistantService
from app.services.context_service import ContextService
from app.services.ai_service import ai_service
from app.services.vector_store import vector_store
from app.prompts import build_messages_prompt, DIARY_COMPANION_SYSTEM

router = APIRouter()


@router.post("/ask")
async def ask_question(
    question: str = Query(..., description="用户问题"),
    conversation_history: Optional[List[Dict]] = Body(default=None, description="对话历史"),
    db: Session = Depends(get_sync_db)
):
    """
    AI 智能问答（升级版 - 整合上下文管理）

    核心升级：
    1. 使用 ContextService 组装完整上下文
    2. 应用时间衰减算法
    3. 隐性记忆表达（避免监控感）
    4. 智能上下文裁剪

    返回：AI 回答 + 相关日记列表 + 上下文信息
    """
    try:
        # 1. 初始化上下文服务
        context_service = ContextService(db, vector_store)

        # 2. 构建完整上下文
        context = context_service.build_context(
            user_input=question,
            user_id=1,
            conversation_history=conversation_history or [],
            budget=ContextBudget()
        )

        # 3. 构建消息格式（隐性记忆表达）
        messages = build_messages_prompt(
            user_input=question,
            user_profile=context.user_profile,
            memories=context.relevant_memories,
            conversation_history=context.conversation_history,
            system_prompt=DIARY_COMPANION_SYSTEM
        )

        # 4. 调用 AI（使用新的消息格式）
        answer = await ai_service.call_llm_with_messages(messages)

        # 5. 构建返回的相关日记列表
        related_diaries = []
        for memory in context.relevant_memories[:3]:
            source_id = memory.get('source_diary_id') or memory.get('metadata', {}).get('source_diary_id')
            if source_id:
                diary_result = db.execute(
                    select(Diary).where(Diary.id == source_id)
                )
                diary = diary_result.scalar_one_or_none()
                if diary:
                    related_diaries.append({
                        "id": diary.id,
                        "text": diary.cleaned_text[:100] + "..." if len(diary.cleaned_text) > 100 else diary.cleaned_text,
                        "date": diary.created_at.strftime('%Y-%m-%d'),
                        "emotion": diary.emotion
                    })

        # 6. 收集 memory_ids 用于反馈
        memory_ids = [m.get('id') for m in context.relevant_memories if m.get('id')]

        return {
            "answer": answer,
            "related_diaries": related_diaries,
            "memory_ids": memory_ids,
            "context_tokens": context.total_tokens,
            "memories_used": len(context.relevant_memories)
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


@router.post("/feedback")
async def record_session_feedback(
    memory_ids: List[int] = Body(..., embed=True),
    was_helpful: bool = Body(..., embed=True),
    db: Session = Depends(get_sync_db)
):
    """
    记录反馈并学习（简化版）

    用户对整个回答反馈是否有帮助
    根据反馈批量调整所有检索到的记忆的重要性
    """
    try:
        assistant = DiaryAssistantService(db)

        delta = 0.15 if was_helpful else -0.1

        for memory_id in memory_ids:
            assistant.memory_service.update_importance(memory_id, delta=delta)

        return {
            "success": True,
            "message": f"反馈已记录：{'有帮助' if was_helpful else '无帮助'}",
            "updated_count": len(memory_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录反馈失败: {str(e)}")


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