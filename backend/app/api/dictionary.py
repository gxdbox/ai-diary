"""
自定义词典API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
import re

from app.db.database import get_db, DictionaryEntry, async_session_maker, User
from app.core.security import get_current_user

router = APIRouter()

# 免费用户自定义词典词数上限（后期可改为会员配置）
MAX_DICTIONARY_WORDS = 50

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


# ============ 拼音模糊匹配工具 ============

def levenshtein(a: str, b: str) -> int:
    """计算两个字符串的 Levenshtein 编辑距离"""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m

    # 只用两行来节省内存
    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev

    return prev[n]


def pinyin_similarity(a: str, b: str) -> float:
    """基于编辑距离的拼音相似度（0.0 ~ 1.0）"""
    if a == b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    dist = levenshtein(a, b)
    return 1.0 - dist / max_len


# 拼音归一化规则 — 仅归一化平翘舌（最常见混淆），其他通过编辑距离兜底
_NORMALIZE_RULES = [
    ('zh', 'z'), ('ch', 'c'), ('sh', 's'),
]


def normalize_pinyin(py: str) -> str:
    """生成拼音的模糊归一化签名

    平翘舌归一化：zh→z, ch→c, sh→s。
    n/l、f/h、前后鼻音等近音混淆通过编辑距离（Levenshtein）兜底。
    """
    result = py
    for pattern, replacement in _NORMALIZE_RULES:
        result = result.replace(pattern, replacement)
    return result


def is_english_word(word: str) -> bool:
    """判断是否包含非中文字符（英文、数字、混合）"""
    for c in word:
        if c.isascii() and c.isalpha():
            return True
    return False


# ============ 拼音模糊匹配工具结束 ============


class DictionaryEntryCreate(BaseModel):
    word: str  # 正确词


class DictionaryEntryResponse(BaseModel):
    id: int
    word: str
    pinyin: str
    source: str = "manual"
    correction_count: int = 0

    class Config:
        from_attributes = True


class DictionaryListResponse(BaseModel):
    entries: List[DictionaryEntryResponse]
    total: int


@router.get("/list", response_model=DictionaryListResponse)
async def list_dictionary(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取所有词典条目（按校正次数降序排列，高频词优先）"""
    try:
        result = await db.execute(
            select(DictionaryEntry)
            .where(DictionaryEntry.user_id == current_user.id)
            .order_by(DictionaryEntry.correction_count.desc(), DictionaryEntry.created_at.desc())
        )
        entries = result.scalars().all()

        return DictionaryListResponse(
            entries=[
                DictionaryEntryResponse(
                    id=e.id,
                    word=e.word,
                    pinyin=e.pinyin,
                    source=e.source if e.source else "manual",
                    correction_count=e.correction_count if e.correction_count else 0
                ) for e in entries
            ],
            total=len(entries)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取词典失败: {str(e)}")


@router.post("/add", response_model=DictionaryEntryResponse)
async def add_dictionary_entry(
    entry: DictionaryEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加词典条目（只需输入正确词，系统自动生成拼音）"""
    try:
        # 检查是否已存在
        result = await db.execute(
            select(DictionaryEntry).where(DictionaryEntry.word == entry.word, DictionaryEntry.user_id == current_user.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return DictionaryEntryResponse(
                id=existing.id,
                word=existing.word,
                pinyin=existing.pinyin,
                source=existing.source if existing.source else "manual",
                correction_count=existing.correction_count if existing.correction_count else 0
            )

        # 检查数量上限（免费用户 50 词，后期会员可放开）
        count_result = await db.execute(
            select(func.count()).select_from(DictionaryEntry).where(DictionaryEntry.user_id == current_user.id)
        )
        current_count = count_result.scalar()
        if current_count >= MAX_DICTIONARY_WORDS:
            raise HTTPException(
                status_code=400,
                detail=f"自定义词典已达到 {MAX_DICTIONARY_WORDS} 词上限，开通会员可无限添加"
            )

        # 自动生成拼音
        pinyin_str = get_pinyin(entry.word)

        # 创建新条目
        new_entry = DictionaryEntry(
            user_id=current_user.id,
            word=entry.word,
            pinyin=pinyin_str,
            source='manual'
        )
        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)

        # 更新缓存
        await update_dictionary_cache()

        return DictionaryEntryResponse(
            id=new_entry.id,
            word=new_entry.word,
            pinyin=new_entry.pinyin,
            source='manual',
            correction_count=0
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"添加词典失败: {str(e)}")


@router.put("/{entry_id}", response_model=DictionaryEntryResponse)
async def update_dictionary_entry(
    entry_id: int,
    entry: DictionaryEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新词典条目"""
    try:
        result = await db.execute(
            select(DictionaryEntry).where(DictionaryEntry.id == entry_id, DictionaryEntry.user_id == current_user.id)
        )
        dictionary_entry = result.scalar_one_or_none()

        if not dictionary_entry:
            raise HTTPException(status_code=404, detail="词典条目不存在")

        # 检查新词是否已存在（排除当前条目）
        result = await db.execute(
            select(DictionaryEntry).where(
                DictionaryEntry.word == entry.word,
                DictionaryEntry.id != entry_id,
                DictionaryEntry.user_id == current_user.id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return DictionaryEntryResponse(
                id=existing.id,
                word=existing.word,
                pinyin=existing.pinyin,
                source=existing.source if existing.source else "manual",
                correction_count=existing.correction_count if existing.correction_count else 0
            )

        dictionary_entry.word = entry.word
        dictionary_entry.pinyin = get_pinyin(entry.word)
        
        await db.commit()
        await db.refresh(dictionary_entry)
        await update_dictionary_cache()

        return DictionaryEntryResponse(
            id=dictionary_entry.id,
            word=dictionary_entry.word,
            pinyin=dictionary_entry.pinyin,
            source=dictionary_entry.source if dictionary_entry.source else "manual",
            correction_count=dictionary_entry.correction_count if dictionary_entry.correction_count else 0
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新词典失败：{str(e)}")


@router.delete("/{entry_id}")
async def delete_dictionary_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除词典条目"""
    try:
        result = await db.execute(
            select(DictionaryEntry).where(DictionaryEntry.id == entry_id, DictionaryEntry.user_id == current_user.id)
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


@router.post("/{entry_id}/confirm", response_model=DictionaryEntryResponse)
async def confirm_dictionary_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """确认 auto 来源的词典词，提升为 confirmed（权重更高）

    用户在词典页面确认自动学习的词汇后，该词的 source 从 'auto' 变为 'confirmed'，
    表示用户认可该词，后续清洗时优先级更高。
    """
    try:
        result = await db.execute(
            select(DictionaryEntry).where(
                DictionaryEntry.id == entry_id,
                DictionaryEntry.user_id == current_user.id
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise HTTPException(status_code=404, detail="词典条目不存在")

        entry.source = 'confirmed'
        await db.commit()
        await db.refresh(entry)
        await update_dictionary_cache()

        return DictionaryEntryResponse(
            id=entry.id,
            word=entry.word,
            pinyin=entry.pinyin,
            source=entry.source,
            correction_count=entry.correction_count if entry.correction_count else 0
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"确认词典失败: {str(e)}")


# ============ 词典缓存与校正 ============

# 按用户隔离的缓存结构
_dictionary_cache_by_user: dict = {}  # {user_id: {pinyin: word}}
_dictionary_words_by_user: dict = {}  # {user_id: set(words)}
_fuzzy_pinyin_cache_by_user: dict = {}  # {user_id: {normalized_pinyin: original_word}}

# 兼容旧的全局缓存（用于单用户场景，默认用户 ID 为 None）
dictionary_cache: dict = {}
dictionary_words: set = set()
_fuzzy_pinyin_cache: dict = {}


def get_user_cache(user_id: int = None) -> tuple:
    """获取指定用户的缓存，如果 user_id 为 None 则使用全局缓存"""
    if user_id is None:
        return dictionary_cache, dictionary_words, _fuzzy_pinyin_cache
    return (
        _dictionary_cache_by_user.get(user_id, {}),
        _dictionary_words_by_user.get(user_id, set()),
        _fuzzy_pinyin_cache_by_user.get(user_id, {})
    )


async def load_dictionary_cache(db: AsyncSession, user_id: int = None):
    """加载词典到缓存

    Args:
        db: 数据库会话
        user_id: 如果提供，只加载该用户的词典；否则加载全部（兼容旧逻辑）
    """
    global dictionary_cache, dictionary_words, _fuzzy_pinyin_cache
    global _dictionary_cache_by_user, _dictionary_words_by_user, _fuzzy_pinyin_cache_by_user

    query = select(DictionaryEntry)
    if user_id is not None:
        query = query.where(DictionaryEntry.user_id == user_id)

    result = await db.execute(query)
    entries = result.scalars().all()

    # 初始化缓存
    cache_dict = {}
    words_set = set()
    fuzzy_dict = {}

    for entry in entries:
        cache_dict[entry.pinyin] = entry.word
        words_set.add(entry.word)
        fuzzy_key = normalize_pinyin(entry.pinyin)
        if fuzzy_key not in fuzzy_dict:
            fuzzy_dict[fuzzy_key] = entry.word

    if user_id is not None:
        # 更新用户特定缓存
        _dictionary_cache_by_user[user_id] = cache_dict
        _dictionary_words_by_user[user_id] = words_set
        _fuzzy_pinyin_cache_by_user[user_id] = fuzzy_dict
    else:
        # 更新全局缓存（兼容旧逻辑）
        dictionary_cache = cache_dict
        dictionary_words = words_set
        _fuzzy_pinyin_cache = fuzzy_dict


async def update_dictionary_cache():
    """更新词典缓存"""
    async with async_session_maker() as db:
        await load_dictionary_cache(db)


def _correct_english_words(text: str) -> str:
    """修正中英混排词汇（词典中的英文词汇在文本中的变体）"""
    global dictionary_words

    if not dictionary_words:
        return text

    for word in dictionary_words:
        if not is_english_word(word):
            continue

        # 提取英文部分进行模糊匹配
        english_parts = re.findall(r'[a-zA-Z]+', word)
        for en_part in english_parts:
            if len(en_part) < 3:
                continue
            # 在文本中查找相似的英文片段（大小写不敏感）
            pattern = re.compile(re.escape(en_part), re.IGNORECASE)
            found = pattern.findall(text)
            if found and found[0] != en_part:
                # 文本中的英文拼写与词典不一致，修正为正确形式
                # 只修正已存在的英文词，不插入新词
                pass

    return text


def apply_dictionary_correction(text: str, user_id: int = None) -> str:
    """应用词典校正（基于拼音模糊匹配 + 混淆规则 + 英文匹配）

    对 raw_text 进行前置处理：
    1. 完全拼音匹配（同音字替换）
    2. 模糊拼音匹配（近音字替换，基于编辑距离和发音混淆规则）
    3. 英文/中英混排词汇修正

    Args:
        text: 待校正的文本
        user_id: 用户 ID，用于获取用户特定的词典缓存；如果为 None 则使用全局缓存
    """
    cache, words, fuzzy_cache = get_user_cache(user_id)

    if not cache:
        return text

    # 英文词汇修正（使用相同缓存）
    if words:
        for word in words:
            if not is_english_word(word):
                continue
            english_parts = re.findall(r'[a-zA-Z]+', word)
            for en_part in english_parts:
                if len(en_part) < 3:
                    continue
                pattern = re.compile(re.escape(en_part), re.IGNORECASE)
                found = pattern.findall(text)
                if found and found[0] != en_part:
                    text = pattern.sub(en_part, text)

    result = []
    i = 0
    text_len = len(text)

    while i < text_len:
        matched = False

        # 尝试最长匹配（最多 10 个字符）
        for length in range(min(10, text_len - i), 0, -1):
            segment = text[i:i + length]

            # 1. 如果这个词本身就在词典中，直接保留
            if segment in words:
                result.append(segment)
                i += length
                matched = True
                break

            # 2. 拼音完全匹配
            segment_pinyins = get_all_pinyins(segment)
            for seg_pinyin in segment_pinyins:
                if seg_pinyin in cache:
                    result.append(cache[seg_pinyin])
                    i += length
                    matched = True
                    break
            if matched:
                break

            # 3. 拼音模糊匹配（编辑距离 + 发音混淆）
            for seg_pinyin in segment_pinyins:
                fuzzy_seg = normalize_pinyin(seg_pinyin)
                if fuzzy_seg in fuzzy_cache:
                    result.append(fuzzy_cache[fuzzy_seg])
                    i += length
                    matched = True
                    break

                # 编辑距离匹配：降低阈值以捕获 n/l、f/h 等近音错误
                best_match = None
                best_similarity = 0.0
                best_pinyin = ""
                for cache_pinyin, cache_word in cache.items():
                    sim = pinyin_similarity(seg_pinyin, cache_pinyin)
                    if sim >= 0.6 and sim > best_similarity:
                        best_similarity = sim
                        best_match = cache_word
                        best_pinyin = cache_pinyin

                if best_match and best_similarity >= 0.6:
                    # 额外长度约束：拼音长度比 >= 0.75，避免短词误匹配长片段
                    len_ratio = min(len(seg_pinyin), len(best_pinyin)) / max(len(seg_pinyin), len(best_pinyin))
                    if len_ratio < 0.75:
                        continue
                    result.append(best_match)
                    i += length
                    matched = True
                    break
            if matched:
                break

        if not matched:
            result.append(text[i])
            i += 1

    return ''.join(result)


# post_correct() 已移除：不再对 AI 输出进行强制替换，避免破坏原文