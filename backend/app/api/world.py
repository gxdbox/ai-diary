"""
虚拟世界 API 路由

提供人物关系图谱、地点、统计信息等接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db, Diary, Character, Relationship, Location, CharacterAlias
from app.models.diary import (
    AliasResponse,
    CharacterResponse,
    RelationshipResponse,
    LocationResponse,
    WorldStatsResponse,
    DiaryResponse
)

router = APIRouter(prefix="/api/world", tags=["虚拟世界"])


async def _load_aliases(db: AsyncSession, character_id: int) -> List[AliasResponse]:
    """加载人物别名列表"""
    result = await db.execute(
        select(CharacterAlias)
        .where(CharacterAlias.character_id == character_id)
        .order_by(CharacterAlias.confidence.desc())
    )
    aliases = result.scalars().all()
    return [
        AliasResponse(
            id=a.id,
            alias=a.alias,
            source=a.source,
            confidence=a.confidence,
            created_at=a.created_at
        )
        for a in aliases
    ]


def _character_to_response(char: Character, aliases: List[AliasResponse] = None) -> CharacterResponse:
    """转换 Character ORM 对象为响应模型"""
    return CharacterResponse(
        id=char.id,
        name=char.name,
        appearance_count=char.appearance_count,
        avatar_color=char.avatar_color,
        first_appearance=char.first_appearance,
        last_appearance=char.last_appearance,
        aliases=aliases or []
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

    按出现次数、最后出现时间或名称排序，附带别名信息
    """
    try:
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

        response_list = []
        for char in characters:
            aliases = await _load_aliases(db, char.id)
            response_list.append(_character_to_response(char, aliases))

        return response_list

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

    返回包含该人物及其所有别名的日记，按时间倒序排列
    """
    try:
        result = await db.execute(
            select(Character).where(Character.name == character_name)
        )
        character = result.scalar_one_or_none()

        if not character:
            raise HTTPException(status_code=404, detail=f"人物 '{character_name}' 不存在")

        aliases = await _load_aliases(db, character.id)
        alias_names = [a.alias for a in aliases]

        search_terms = [character_name] + alias_names

        from sqlalchemy import text as sql_text

        conditions = " OR ".join(["(cleaned_text LIKE :p{0} OR raw_text LIKE :p{0})".format(i)
                                  for i in range(len(search_terms))])
        params = {f"p{i}": f"%{term}%" for i, term in enumerate(search_terms)}
        params["limit"] = limit

        diary_result = await db.execute(
            sql_text(f"""
                SELECT * FROM diaries
                WHERE {conditions}
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            params
        )
        rows = diary_result.fetchall()

        import json
        diaries = []
        for row in rows:
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

        char_aliases = await _load_aliases(db, character.id)

        return {
            "character": _character_to_response(character, char_aliases),
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
        char_count_result = await db.execute(select(func.count()).select_from(Character))
        total_characters = char_count_result.scalar()

        rel_count_result = await db.execute(select(func.count()).select_from(Relationship))
        total_relationships = rel_count_result.scalar()

        loc_count_result = await db.execute(select(func.count()).select_from(Location))
        total_locations = loc_count_result.scalar()

        most_active_result = await db.execute(
            select(Character)
            .order_by(desc(Character.appearance_count))
            .limit(1)
        )
        most_active_char = most_active_result.scalar_one_or_none()

        strongest_rel_result = await db.execute(
            select(Relationship)
            .order_by(desc(Relationship.strength))
            .limit(1)
        )
        strongest_rel = strongest_rel_result.scalar_one_or_none()

        most_active_character = None
        if most_active_char:
            aliases = await _load_aliases(db, most_active_char.id)
            most_active_character = _character_to_response(most_active_char, aliases)

        strongest_relationship = None
        if strongest_rel:
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

    支持模糊匹配人物名称和别名
    """
    try:
        from sqlalchemy import text as sql_text

        result = await db.execute(
            sql_text("""
                SELECT DISTINCT c.* FROM characters c
                LEFT JOIN character_aliases ca ON ca.character_id = c.id
                WHERE c.name LIKE :pattern
                   OR ca.alias LIKE :pattern
                ORDER BY c.appearance_count DESC
                LIMIT :limit
            """),
            {"pattern": f"%{query}%", "limit": limit}
        )
        rows = result.fetchall()

        characters = []
        for row in rows:
            char = Character(
                id=row.id, name=row.name,
                appearance_count=row.appearance_count,
                avatar_color=row.avatar_color,
                first_appearance=row.first_appearance,
                last_appearance=row.last_appearance,
                created_at=row.created_at, updated_at=row.updated_at
            )
            aliases = await _load_aliases(db, char.id)
            characters.append(_character_to_response(char, aliases))

        return characters

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索人物失败: {str(e)}")


@router.get("/aliases/{character_id}", response_model=List[AliasResponse])
async def get_character_aliases(
    character_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取某个人物的所有别名
    """
    try:
        aliases = await _load_aliases(db, character_id)
        return aliases
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取别名失败: {str(e)}")
