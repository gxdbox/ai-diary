"""
自定义词典API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel
import re

from app.db.database import get_db, DictionaryEntry, async_session_maker

router = APIRouter()

# 拼音转换
from pypinyin import pinyin, Style
import itertools


def get_pinyin(text: str) -> str:
    """获取文本拼音（不带声调，只取第一读音）"""
    result = pinyin(text, style=Style.NORMAL)
    return ''.join([item[0] for item in result])


def get_all_pinyins(text: str) -> list:
    """获取文本所有可能的拼音组合（考虑多音字）"""
    # heteronym=True 会返回多音字的所有读音
    result = pinyin(text, style=Style.NORMAL, heteronym=True)

    # 生成所有拼音组合
    pinyin_combinations = []
    for item in result:
        if isinstance(item, list):
            pinyin_combinations.append(item)
        else:
            pinyin_combinations.append([item])

    # 计算所有组合（笛卡尔积）
    all_combinations = list(itertools.product(*pinyin_combinations))
    return [''.join(combo) for combo in all_combinations]


class DictionaryEntryCreate(BaseModel):
    word: str  # 正确词


class DictionaryEntryResponse(BaseModel):
    id: int
    word: str
    pinyin: str

    class Config:
        from_attributes = True


class DictionaryListResponse(BaseModel):
    entries: List[DictionaryEntryResponse]
    total: int


@router.get("/list", response_model=DictionaryListResponse)
async def list_dictionary(db: AsyncSession = Depends(get_db)):
    """获取所有词典条目"""
    try:
        result = await db.execute(select(DictionaryEntry).order_by(DictionaryEntry.created_at.desc()))
        entries = result.scalars().all()

        return DictionaryListResponse(
            entries=[
                DictionaryEntryResponse(
                    id=e.id,
                    word=e.word,
                    pinyin=e.pinyin
                ) for e in entries
            ],
            total=len(entries)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取词典失败: {str(e)}")


@router.post("/add", response_model=DictionaryEntryResponse)
async def add_dictionary_entry(
    entry: DictionaryEntryCreate,
    db: AsyncSession = Depends(get_db)
):
    """添加词典条目（只需输入正确词，系统自动生成拼音）"""
    try:
        # 检查是否已存在
        result = await db.execute(
            select(DictionaryEntry).where(DictionaryEntry.word == entry.word)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return DictionaryEntryResponse(
                id=existing.id,
                word=existing.word,
                pinyin=existing.pinyin
            )

        # 自动生成拼音
        pinyin_str = get_pinyin(entry.word)

        # 创建新条目
        new_entry = DictionaryEntry(
            word=entry.word,
            pinyin=pinyin_str
        )
        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)

        # 更新缓存
        await update_dictionary_cache()

        return DictionaryEntryResponse(
            id=new_entry.id,
            word=new_entry.word,
            pinyin=new_entry.pinyin
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"添加词典失败: {str(e)}")


@router.put("/{entry_id}", response_model=DictionaryEntryResponse)
async def update_dictionary_entry(
    entry_id: int,
    entry: DictionaryEntryCreate,
    db: AsyncSession = Depends(get_db)
):
    """更新词典条目"""
    try:
        result = await db.execute(
            select(DictionaryEntry).where(DictionaryEntry.id == entry_id)
        )
        dictionary_entry = result.scalar_one_or_none()

        if not dictionary_entry:
            raise HTTPException(status_code=404, detail="词典条目不存在")

        # 检查新词是否已存在（排除当前条目）
        result = await db.execute(
            select(DictionaryEntry).where(
                DictionaryEntry.word == entry.word,
                DictionaryEntry.id != entry_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return DictionaryEntryResponse(
                id=existing.id,
                word=existing.word,
                pinyin=existing.pinyin
            )

        dictionary_entry.word = entry.word
        dictionary_entry.pinyin = get_pinyin(entry.word)
        
        await db.commit()
        await db.refresh(dictionary_entry)
        await update_dictionary_cache()

        return DictionaryEntryResponse(
            id=dictionary_entry.id,
            word=dictionary_entry.word,
            pinyin=dictionary_entry.pinyin
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新词典失败：{str(e)}")


@router.delete("/{entry_id}")
async def delete_dictionary_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除词典条目"""
    try:
        result = await db.execute(
            select(DictionaryEntry).where(DictionaryEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise HTTPException(status_code=404, detail="词典条目不存在")

        await db.delete(entry)
        await db.commit()

        # 更新缓存
        await update_dictionary_cache()

        return {"message": "删除成功", "id": entry_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除词典失败: {str(e)}")


# ============ 词典缓存与校正 ============

# 全局缓存
dictionary_cache: dict = {}  # {pinyin: word}
dictionary_words: set = set()  # 所有词典词（用于快速检查）


async def load_dictionary_cache(db: AsyncSession):
    """加载词典到缓存"""
    global dictionary_cache, dictionary_words

    result = await db.execute(select(DictionaryEntry))
    entries = result.scalars().all()

    dictionary_cache = {}
    dictionary_words = set()

    for entry in entries:
        dictionary_cache[entry.pinyin] = entry.word
        dictionary_words.add(entry.word)


async def update_dictionary_cache():
    """更新词典缓存"""
    async with async_session_maker() as db:
        await load_dictionary_cache(db)


def apply_dictionary_correction(text: str) -> str:
    """应用词典校正（基于拼音匹配，考虑多音字）"""
    global dictionary_cache, dictionary_words

    if not dictionary_cache:
        return text

    # 分词处理：按字符逐个匹配
    result = []
    i = 0
    text_len = len(text)

    while i < text_len:
        # 尝试最长匹配（最多10个字符）
        matched = False
        for length in range(min(10, text_len - i), 0, -1):
            segment = text[i:i+length]

            # 如果这个词本身就在词典中，直接保留
            if segment in dictionary_words:
                result.append(segment)
                i += length
                matched = True
                break

            # 获取该片段所有可能的拼音组合（考虑多音字）
            segment_pinyins = get_all_pinyins(segment)

            # 检查是否有任何一个拼音匹配词典
            for seg_pinyin in segment_pinyins:
                if seg_pinyin in dictionary_cache:
                    # 替换为正确词
                    result.append(dictionary_cache[seg_pinyin])
                    i += length
                    matched = True
                    break

            if matched:
                break

        if not matched:
            result.append(text[i])
            i += 1

    return ''.join(result)