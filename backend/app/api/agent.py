"""
Agent API 路由 - 统一的 AI 对话入口（借鉴 Hermes Agent 的 tool-calling）

替代 assistant.py + companion.py 的双服务架构，提供单一智能 Agent。
Agent 可在对话中主动调用工具（搜日记、跑洞察、查/存记忆），让日记
从"躺在那里"变成"了解自我"的交互途径。

端点：
- POST /api/agent/chat       — Agent 对话（tool-calling loop）
- GET  /api/agent/history    — 对话历史
- GET  /api/agent/capabilities — 返回 Agent 可用工具
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import logging

from app.db.database import get_sync_db
from app.services.ai.agent import DiaryAgent
from app.services.ai.tools import DiaryToolRegistry
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    message: str
    conversation_history: Optional[List[Dict]] = None
    reflect: bool = True  # 是否对话后记忆反思


class AgentChatResponse(BaseModel):
    """Agent 对话响应"""
    response: str
    conversation_id: Optional[int] = None
    tool_usage: List[Dict] = []
    iterations: int = 0
    safe: bool = True


@router.post("/chat", response_model=AgentChatResponse)
async def chat(
    request: AgentChatRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Agent 对话（tool-calling loop）

    AI 会在需要时主动调用工具：搜索日记、获取洞察、查/存记忆。
    这是借鉴 Hermes Agent 的 self-improving loop 理念，让对话能
    主动挖掘日记价值，帮助用户了解自我。
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        # 初始化 Agent
        agent = DiaryAgent(db, vector_store)

        # 执行 Agent 循环
        result = await agent.chat(
            user_input=request.message,
            conversation_history=request.conversation_history,
            reflect=request.reflect,
        )

        # 保存对话记录（mode=agent）
        conv_id = _save_conversation(
            db,
            user_id=1,
            user_input=request.message,
            ai_response=result["response"],
            tool_usage=result.get("tool_usage", []),
        )

        return AgentChatResponse(
            response=result["response"],
            conversation_id=conv_id if conv_id > 0 else None,
            tool_usage=result.get("tool_usage", []),
            iterations=result.get("iterations", 0),
            safe=result.get("safe", True),
        )

    except Exception as e:
        logger.error("Agent 对话失败: %s", e)
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")


@router.get("/history")
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """获取 Agent 对话历史"""
    try:
        result = db.execute(
            text("""
                SELECT id, user_input, ai_response, mode, emotion_before, created_at
                FROM conversations
                WHERE mode = 'agent'
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        rows = result.fetchall()
        return {
            "history": [
                {
                    "id": row[0],
                    "user_input": row[1],
                    "ai_response": row[2],
                    "mode": row[3],
                    "emotion_before": row[4],
                    "created_at": (
                        row[5] if isinstance(row[5], str)
                        else (row[5].isoformat() if row[5] else None)
                    ),
                }
                for row in reversed(rows)
            ]
        }
    except Exception as e:
        logger.error("获取对话历史失败: %s", e)
        return {"history": []}


@router.get("/capabilities")
async def get_capabilities(db: Session = Depends(get_sync_db)):
    """返回 Agent 可用工具列表（供前端展示 Agent 能力）"""
    registry = DiaryToolRegistry(db, vector_store)
    capabilities = []
    for tool in registry.definitions:
        func = tool["function"]
        capabilities.append({
            "name": func["name"],
            "description": func["description"],
            "parameters": list(
                func["parameters"].get("properties", {}).keys()
            ),
        })
    return {"capabilities": capabilities, "agent_enabled": True}


def _save_conversation(
    db: Session,
    user_id: int,
    user_input: str,
    ai_response: str,
    tool_usage: List[Dict] = None,
) -> int:
    """保存 Agent 对话记录到 conversations 表"""
    try:
        # 把工具使用轨迹序列化存入 ai_response 后缀（便于调试）
        full_response = ai_response
        if tool_usage:
            tools_summary = ", ".join(
                t["tool"] for t in tool_usage
            )
            full_response = f"{ai_response}\n\n[工具调用: {tools_summary}]"

        result = db.execute(
            text("""
                INSERT INTO conversations
                (user_id, diary_id, user_input, ai_response, mode, emotion_before, created_at)
                VALUES (:user_id, NULL, :user_input, :ai_response, 'agent', NULL, :created_at)
            """),
            {
                "user_id": user_id,
                "user_input": user_input,
                "ai_response": full_response,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        db.commit()
        return result.lastrowid
    except Exception as e:
        logger.error("保存 Agent 对话记录失败: %s", e)
        db.rollback()
        return -1
