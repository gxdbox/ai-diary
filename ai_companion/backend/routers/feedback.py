# AI伴侣 - 反馈路由

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.database import FeedbackDB

router = APIRouter(prefix="/api", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """反馈请求"""
    conversation_id: Optional[int] = None
    rating: int  # 1-5分
    feedback_type: Optional[str] = None  # "好"/"一般"/"不好"/"有害"
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    feedback_id: int
    message: str


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """提交用户反馈"""
    # 验证评分范围
    if request.rating < 1 or request.rating > 5:
        raise HTTPException(status_code=400, detail="评分必须在1-5之间")

    feedback_id = FeedbackDB.save_feedback(
        conversation_id=request.conversation_id,
        rating=request.rating,
        feedback_type=request.feedback_type,
        comment=request.comment
    )

    return FeedbackResponse(
        success=True,
        feedback_id=feedback_id,
        message="感谢您的反馈！我们会持续改进。😊"
    )


@router.get("/feedback/stats")
async def get_feedback_stats():
    """获取反馈统计"""
    stats = FeedbackDB.get_feedback_stats()
    return stats