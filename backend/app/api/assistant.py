"""
日记助手 API 路由 - 基于 ProactAgent 论文思想

提供智能日记辅助功能：
1. 主动检索相关记忆
2. 写作建议
3. 相似历史日记
4. 用户上下文
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from app.db.database import get_sync_db
from app.models.memory import (
    DiaryAssistRequest, DiaryAssistResponse,
    RetrievalRequest, ProactiveRetrievalResponse
)
from app.services.diary_assistant import DiaryAssistantService

router = APIRouter()


@router.post("/assist", response_model=DiaryAssistResponse)
async def assist_writing(
    request: DiaryAssistRequest,
    db: Session = Depends(get_sync_db)
):
    """
    智能辅助日记写作

    ProactAgent 核心功能：
    - 分析当前内容
    - 主动检索相关记忆
    - 提供个性化建议
    """
    try:
        assistant = DiaryAssistantService(db)
        response = assistant.assist_writing(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"辅助失败: {str(e)}")


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

    查看三种类型的记忆内容
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
            ],
            "behavioral": [
                {
                    "id": m.id,
                    "content": m.content,
                    "keywords": m.keywords,
                    "access_count": m.access_count
                }
                for m in memories.get(MemoryType.BEHAVIORAL, [])
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆失败: {str(e)}")