"""
分析相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import List, Optional
import json

from app.db.database import get_db, Diary
from app.models.diary import AnalyzeRequest, AnalyzeResponse, EmotionResult
from app.models.insight import DeepInsightResponse
from app.services.ai_service import ai_service
from app.services.analyzer import analyzer
from app.services.insight_analyzer import insight_analyzer

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    """
    分析文本
    返回情绪、主题、关键事件
    """
    try:
        analysis = await analyzer.analyze(request.text)

        return AnalyzeResponse(
            emotion=EmotionResult(
                emotion=analysis["emotion"].get("emotion", "平静"),
                score=analysis["emotion"].get("score", 5.0),
                keywords=analysis["emotion"].get("keywords", [])
            ),
            topics=analysis.get("topics", []),
            key_events=analysis.get("key_events", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/emotion/trend")
async def get_emotion_trend(
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取情绪趋势
    返回最近N天的情绪能量变化
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Diary)
            .where(Diary.created_at >= start_date)
            .order_by(Diary.created_at)
        )
        diaries = result.scalars().all()

        # 按日期分组统计
        daily_data = {}
        for diary in diaries:
            date_str = diary.created_at.strftime("%Y-%m-%d")
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "energies": [],
                    "intensities": [],
                    "emotions": []
                }
            # 使用 emotion_energy（兼容旧数据）
            energy = diary.emotion_energy if diary.emotion_energy is not None else _convert_old_score(diary)
            if energy is not None:
                daily_data[date_str]["energies"].append(energy)
            if diary.emotion_intensity:
                daily_data[date_str]["intensities"].append(diary.emotion_intensity)
            if diary.emotion:
                daily_data[date_str]["emotions"].append(diary.emotion)

        # 计算每日平均
        trend = []
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            avg_energy = sum(data["energies"]) / len(data["energies"]) if data["energies"] else 0
            avg_intensity = sum(data["intensities"]) / len(data["intensities"]) if data["intensities"] else 0
            trend.append({
                "date": date_str,
                "average_energy": round(avg_energy, 2),
                "average_intensity": round(avg_intensity, 2),
                "diary_count": len(data["energies"])
            })

        return {
            "trend": trend,
            "days": days
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取情绪趋势失败: {str(e)}")


@router.get("/topics/distribution")
async def get_topic_distribution(
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取主题分布
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Diary)
            .where(Diary.created_at >= start_date)
        )
        diaries = result.scalars().all()

        # 统计主题
        summary = analyzer.get_topic_summary([{
            "topics": json.loads(d.topics) if d.topics else []
        } for d in diaries])

        return {
            "top_topics": summary["top_topics"],
            "total_topics": summary["total_topics"],
            "days": days
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取主题分布失败: {str(e)}")


@router.get("/emotion/distribution")
async def get_emotion_distribution(
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取情绪分布
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Diary)
            .where(Diary.created_at >= start_date)
        )
        diaries = result.scalars().all()

        # 统计情绪
        energies = []
        emotions = []
        for d in diaries:
            energy = d.emotion_energy if d.emotion_energy is not None else _convert_old_score(d)
            if energy is not None:
                energies.append(energy)
            if d.emotion:
                emotions.append(d.emotion)

        # 情绪分布
        distribution = {}
        for emotion in emotions:
            distribution[emotion] = distribution.get(emotion, 0) + 1

        return {
            "average_energy": round(sum(energies) / len(energies), 2) if energies else 0,
            "distribution": distribution,
            "total_count": len(diaries),
            "days": days
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取情绪分布失败: {str(e)}")


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    获取总体统计
    """
    try:
        # 总日记数
        total_result = await db.execute(select(func.count()).select_from(Diary))
        total_count = total_result.scalar()

        # 总字数
        words_result = await db.execute(select(func.sum(Diary.word_count)))
        total_words = words_result.scalar() or 0

        # 连续记录天数
        streak = await _calculate_streak(db)

        # 平均情绪能量（兼容旧数据）
        result = await db.execute(select(Diary))
        diaries = result.scalars().all()

        energies = []
        intensities = []
        for d in diaries:
            energy = d.emotion_energy if d.emotion_energy is not None else _convert_old_score(d)
            if energy is not None:
                energies.append(energy)
            if d.emotion_intensity:
                intensities.append(d.emotion_intensity)

        avg_energy = sum(energies) / len(energies) if energies else 0
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0

        return {
            "total_diaries": total_count,
            "total_words": total_words,
            "streak_days": streak,
            "average_emotion_energy": round(avg_energy, 2),
            "average_emotion_intensity": round(avg_intensity, 2)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/insights")
async def get_insights(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    获取AI洞察
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Diary)
            .where(Diary.created_at >= start_date)
            .order_by(desc(Diary.created_at))
            .limit(50)
        )
        diaries = result.scalars().all()

        if not diaries:
            return {"insights": []}

        insights = []

        # 情绪洞察
        emotions = [d.emotion for d in diaries if d.emotion]
        if emotions:
            distribution = {}
            for emotion in emotions:
                distribution[emotion] = distribution.get(emotion, 0) + 1
            top_emotion = max(distribution.items(), key=lambda x: x[1])
            insights.append({
                "type": "emotion",
                "insight": f"最近{days}天，你最常出现的情绪是「{top_emotion[0]}」，共{top_emotion[1]}次"
            })

        # 主题洞察
        topic_summary = analyzer.get_topic_summary([{
            "topics": json.loads(d.topics) if d.topics else []
        } for d in diaries])

        if topic_summary["top_topics"]:
            top_topic = topic_summary["top_topics"][0]
            insights.append({
                "type": "topic",
                "insight": f"你最关注「{top_topic[0]}」相关的内容，共提到{top_topic[1]}次"
            })

        # 记录时间洞察
        insights.append({
            "type": "habit",
            "insight": f"最近{days}天你共记录了{len(diaries)}篇日记，继续保持！"
        })

        return {"insights": insights}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取洞察失败: {str(e)}")


@router.get("/deep-insights", response_model=DeepInsightResponse)
async def get_deep_insights(
    days: int = Query(90, ge=7, le=365, description="分析周期天数"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取深度洞察

    返回四大分类的深度洞察：
    - 自我认知：天赋、写作人格、价值观
    - 生活状态：情绪健康、生活平衡、人际关系
    - 风险预警：危机信号、方向偏差、能量黑洞
    - 成长激励：积极变化、希望方向、盲点提示

    分析原理：从日记数据中提取模式，帮助用户真正认识自己
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(Diary)
            .where(Diary.created_at >= start_date)
            .order_by(desc(Diary.created_at))
            .limit(200)
        )
        diaries = result.scalars().all()

        if not diaries:
            return insight_analyzer._empty_response(days)

        # 转换为分析服务需要的格式
        diary_data = []
        for d in diaries:
            energy = d.emotion_energy if d.emotion_energy is not None else _convert_old_score(d)
            diary_data.append({
                "id": d.id,
                "created_at": d.created_at,
                "emotion": d.emotion,
                "emotion_energy": energy,
                "emotion_intensity": d.emotion_intensity,
                "topics": json.loads(d.topics) if d.topics else [],
                "cleaned_text": d.cleaned_text,
                "raw_text": d.raw_text
            })

        # 执行深度分析
        insights = insight_analyzer.analyze(diary_data, days)

        return insights

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取深度洞察失败: {str(e)}")


def _convert_old_score(diary: Diary) -> Optional[float]:
    """兼容旧数据：将 emotion_score 转换为 emotion_energy"""
    if diary.emotion_score is None:
        return None

    # 根据 emotion_dimension 转换
    # positive → 正值, negative → 负值, mixed → 0
    score = diary.emotion_score

    if diary.emotion_dimension == "positive":
        return score * 0.6  # 正向能量
    elif diary.emotion_dimension == "negative":
        return -score * 0.9  # 负向能量
    else:
        return 0  # mixed 或未知


async def _calculate_streak(db: AsyncSession) -> int:
    """计算连续记录天数"""
    # 获取所有日记日期
    result = await db.execute(
        select(Diary.created_at)
        .order_by(desc(Diary.created_at))
    )
    all_dates = [row[0].date() for row in result.fetchall()]

    if not all_dates:
        return 0

    # 去重：同一天多篇日记只算一天
    unique_dates = sorted(set(all_dates), reverse=True)

    # 用服务器本地时间判断"今天"
    today = datetime.now().date()

    # 检查最近一天是否是今天或昨天（没有日记就不算 streak）
    if unique_dates[0] not in [today, today - timedelta(days=1)]:
        return 0

    # 从最近一天开始，严格检查连续性
    streak = 1
    for i in range(1, len(unique_dates)):
        # 后一天必须比前一天少 1 天（严格连续）
        if unique_dates[i] == unique_dates[i-1] - timedelta(days=1):
            streak += 1
        else:
            break

    return streak