"""
虚拟世界 API 路由

提供人物关系图谱、地点、统计信息等接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db, Diary, Character, Relationship, Location
from app.models.diary import (
    CharacterResponse,
    RelationshipResponse,
    LocationResponse,
    WorldStatsResponse,
    DiaryResponse
)

router = APIRouter(prefix="/api/world", tags=["虚拟世界"])


def _character_to_response(char: Character) -> CharacterResponse:
    """转换 Character ORM 对象为响应模型"""
    return CharacterResponse(
        id=char.id,
        name=char.name,
        appearance_count=char.appearance_count,
        avatar_color=char.avatar_color,
        first_appearance=char.first_appearance,
        last_appearance=char.last_appearance
    )


def _relationship_to_response(rel: Relationship, char_a: Character = None, char_b: Character = None) -> RelationshipResponse:
    """转换 Relationship ORM 对象为响应模型"""
    return RelationshipResponse(
        id=rel.id,
        character_a_id=rel.character_a_id,
        character_b_id=rel.character_b_id,
        character_a_name=char_a.name if char_a else None,
        character_b_name=char_b.name if char_b else None,
        relationship_type=rel.relationship_type,
        strength=rel.strength,
        last_interaction=rel.last_interaction
    )


@router.get("/characters", response_model=List[CharacterResponse])
async def get_characters(
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    sort_by: str = Query("appearance_count", description="排序字段: appearance_count/last_appearance/name"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有人物列表

    按出现次数、最后出现时间或名称排序
    """
    try:
        # 构建排序
        if sort_by == "last_appearance":
            order_by = desc(Character.last_appearance)
        elif sort_by == "name":
            order_by = Character.name
        else:
            order_by = desc(Character.appearance_count)

        result = await db.execute(
            select(Character)
            .order_by(order_by)
            .limit(limit)
        )
        characters = result.scalars().all()

        return [_character_to_response(char) for char in characters]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人物列表失败: {str(e)}")


@router.get("/relationships", response_model=List[RelationshipResponse])
async def get_relationships(
    min_strength: float = Query(0.0, ge=0, le=1, description="最小关系强度"),
    limit: int = Query(200, ge=1, le=1000, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取人物关系图谱

    可选过滤最低关系强度
    """
    try:
        query = select(Relationship).where(Relationship.strength >= min_strength)

        result = await db.execute(
            query.order_by(desc(Relationship.strength)).limit(limit)
        )
        relationships = result.scalars().all()

        # 批量加载关联的人物信息
        response_list = []
        for rel in relationships:
            char_a_result = await db.execute(
                select(Character).where(Character.id == rel.character_a_id)
            )
            char_a = char_a_result.scalar_one_or_none()

            char_b_result = await db.execute(
                select(Character).where(Character.id == rel.character_b_id)
            )
            char_b = char_b_result.scalar_one_or_none()

            response_list.append(_relationship_to_response(rel, char_a, char_b))

        return response_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取关系图谱失败: {str(e)}")


@router.get("/locations", response_model=List[LocationResponse])
async def get_locations(
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有地点列表
    """
    try:
        result = await db.execute(
            select(Location)
            .order_by(desc(Location.visit_count))
            .limit(limit)
        )
        locations = result.scalars().all()

        return [
            LocationResponse(
                id=loc.id,
                name=loc.name,
                visit_count=loc.visit_count,
                last_visit=loc.last_visit
            )
            for loc in locations
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取地点列表失败: {str(e)}")


@router.get("/timeline/{character_name}")
async def get_character_timeline(
    character_name: str,
    limit: int = Query(50, ge=1, le=200, description="返回日记数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取某个人物的时间轴（相关日记）

    返回包含该人物的所有日记，按时间倒序排列
    """
    try:
        # 先找到人物
        result = await db.execute(
            select(Character).where(Character.name == character_name)
        )
        character = result.scalar_one_or_none()

        if not character:
            raise HTTPException(status_code=404, detail=f"人物 '{character_name}' 不存在")

        # 查找包含该人物名称的日记（简单文本匹配）
        # 注意：这是一个简化的实现，更精确的方式需要建立 diary-character 关联表
        from sqlalchemy import text as sql_text

        diary_result = await db.execute(
            sql_text("""
                SELECT * FROM diaries
                WHERE cleaned_text LIKE :pattern
                   OR raw_text LIKE :pattern
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"pattern": f"%{character_name}%", "limit": limit}
        )
        rows = diary_result.fetchall()

        # 转换为 DiaryResponse
        diaries = []
        for row in rows:
            # 解析 JSON 字段
            import json
            emotion_keywords = json.loads(row.emotion_keywords) if row.emotion_keywords else []
            secondary_emotions = json.loads(row.secondary_emotions) if row.secondary_emotions else []
            topics = json.loads(row.topics) if row.topics else []
            key_events = json.loads(row.key_events) if row.key_events else []
            weather = json.loads(row.weather) if row.weather else None
            images = json.loads(row.images) if row.images else []

            diaries.append(DiaryResponse(
                id=row.id,
                raw_text=row.raw_text,
                title=row.title,
                cleaned_text=row.cleaned_text,
                emotion=row.emotion,
                emotion_score=row.emotion_score,
                emotion_energy=row.emotion_energy,
                emotion_intensity=row.emotion_intensity,
                emotion_keywords=emotion_keywords,
                secondary_emotions=secondary_emotions,
                emotion_dimension=row.emotion_dimension,
                emotion_confidence=row.emotion_confidence,
                topics=topics,
                key_events=key_events,
                recording_duration=row.recording_duration,
                audio_url=row.audio_url,
                word_count=row.word_count,
                weather=weather,
                images=images,
                created_at=row.created_at,
                updated_at=row.updated_at
            ))

        return {
            "character": _character_to_response(character),
            "diaries": diaries,
            "total": len(diaries)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取人物时间轴失败: {str(e)}")


@router.get("/stats", response_model=WorldStatsResponse)
async def get_world_stats(db: AsyncSession = Depends(get_db)):
    """
    获取虚拟世界统计信息

    包括人物总数、关系总数、最活跃人物、最强关系等
    """
    try:
        # 统计总数
        char_count_result = await db.execute(select(func.count()).select_from(Character))
        total_characters = char_count_result.scalar()

        rel_count_result = await db.execute(select(func.count()).select_from(Relationship))
        total_relationships = rel_count_result.scalar()

        loc_count_result = await db.execute(select(func.count()).select_from(Location))
        total_locations = loc_count_result.scalar()

        # 最活跃人物（出现次数最多）
        most_active_result = await db.execute(
            select(Character)
            .order_by(desc(Character.appearance_count))
            .limit(1)
        )
        most_active_char = most_active_result.scalar_one_or_none()

        # 最强关系
        strongest_rel_result = await db.execute(
            select(Relationship)
            .order_by(desc(Relationship.strength))
            .limit(1)
        )
        strongest_rel = strongest_rel_result.scalar_one_or_none()

        # 构建响应
        most_active_character = None
        if most_active_char:
            most_active_character = _character_to_response(most_active_char)

        strongest_relationship = None
        if strongest_rel:
            # 加载关联人物
            char_a_result = await db.execute(
                select(Character).where(Character.id == strongest_rel.character_a_id)
            )
            char_a = char_a_result.scalar_one_or_none()

            char_b_result = await db.execute(
                select(Character).where(Character.id == strongest_rel.character_b_id)
            )
            char_b = char_b_result.scalar_one_or_none()

            strongest_relationship = _relationship_to_response(strongest_rel, char_a, char_b)

        return WorldStatsResponse(
            total_characters=total_characters or 0,
            total_relationships=total_relationships or 0,
            total_locations=total_locations or 0,
            most_active_character=most_active_character,
            strongest_relationship=strongest_relationship
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/search/character")
async def search_characters(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    搜索人物

    支持模糊匹配人物名称
    """
    try:
        from sqlalchemy import text as sql_text

        result = await db.execute(
            sql_text("""
                SELECT * FROM characters
                WHERE name LIKE :pattern
                ORDER BY appearance_count DESC
                LIMIT :limit
            """),
            {"pattern": f"%{query}%", "limit": limit}
        )
        rows = result.fetchall()

        # 手动构建 CharacterResponse
        characters = []
        for row in rows:
            characters.append(CharacterResponse(
                id=row.id,
                name=row.name,
                appearance_count=row.appearance_count,
                avatar_color=row.avatar_color,
                first_appearance=row.first_appearance,
                last_appearance=row.last_appearance
            ))

        return characters

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索人物失败: {str(e)}")
