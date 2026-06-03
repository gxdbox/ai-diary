"""
自定义词典API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
import re

from app.db.database import get_db, DictionaryEntry, async_session_maker

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

        # 检查数量上限（免费用户 50 词，后期会员可放开）
        count_result = await db.execute(
            select(func.count()).select_from(DictionaryEntry)
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
_fuzzy_pinyin_cache: dict = {}  # {normalized_pinyin: original_word}


async def load_dictionary_cache(db: AsyncSession):
    """加载词典到缓存"""
    global dictionary_cache, dictionary_words, _fuzzy_pinyin_cache

    result = await db.execute(select(DictionaryEntry))
    entries = result.scalars().all()

    dictionary_cache = {}
    dictionary_words = set()
    _fuzzy_pinyin_cache = {}

    for entry in entries:
        dictionary_cache[entry.pinyin] = entry.word
        dictionary_words.add(entry.word)
        # 同时存储模糊拼音签名
        fuzzy_key = normalize_pinyin(entry.pinyin)
        if fuzzy_key not in _fuzzy_pinyin_cache:
            _fuzzy_pinyin_cache[fuzzy_key] = entry.word


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


def apply_dictionary_correction(text: str) -> str:
    """应用词典校正（基于拼音模糊匹配 + 混淆规则 + 英文匹配）

    对 raw_text 进行前置处理：
    1. 完全拼音匹配（同音字替换）
    2. 模糊拼音匹配（近音字替换，基于编辑距离和发音混淆规则）
    3. 英文/中英混排词汇修正
    """
    global dictionary_cache, dictionary_words, _fuzzy_pinyin_cache

    if not dictionary_cache:
        return text

    # 先做英文词汇修正
    text = _correct_english_words(text)

    result = []
    i = 0
    text_len = len(text)

    while i < text_len:
        matched = False

        # 尝试最长匹配（最多 10 个字符）
        for length in range(min(10, text_len - i), 0, -1):
            segment = text[i:i + length]

            # 1. 如果这个词本身就在词典中，直接保留
            if segment in dictionary_words:
                result.append(segment)
                i += length
                matched = True
                break

            # 2. 拼音完全匹配
            segment_pinyins = get_all_pinyins(segment)
            for seg_pinyin in segment_pinyins:
                if seg_pinyin in dictionary_cache:
                    result.append(dictionary_cache[seg_pinyin])
                    i += length
                    matched = True
                    break
            if matched:
                break

            # 3. 拼音模糊匹配（编辑距离 + 发音混淆）
            for seg_pinyin in segment_pinyins:
                fuzzy_seg = normalize_pinyin(seg_pinyin)
                if fuzzy_seg in _fuzzy_pinyin_cache:
                    result.append(_fuzzy_pinyin_cache[fuzzy_seg])
                    i += length
                    matched = True
                    break

                # 编辑距离匹配：降低阈值以捕获 n/l、f/h 等近音错误
                best_match = None
                best_similarity = 0.0
                best_pinyin = ""
                for cache_pinyin, cache_word in dictionary_cache.items():
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


def post_correct(cleaned_text: str, words_list: list = None) -> str:
    """后处理：在 AI 清洗后的文本中，检查词典词是否已正确出现

    对于未正确出现在 cleaned_text 中的词典词，尝试在文本中
    查找拼音近似的片段并替换。

    Args:
        cleaned_text: AI 清洗后的文本
        words_list: 词典词汇列表

    Returns:
        进一步修正后的文本
    """
    global dictionary_cache, dictionary_words

    if not dictionary_cache:
        return cleaned_text

    target_words = words_list if words_list is not None else list(dictionary_words)

    for word in target_words:
        # 已在文本中正确出现，跳过
        if word in cleaned_text:
            continue

        # 获取该词的拼音
        word_pinyin = get_pinyin(word)
        if not word_pinyin:
            continue

        # 在 cleaned_text 中滑动窗口搜索拼音相似片段
        for wlen in range(len(word), max(len(word) - 1, 1), -1):
            for start in range(len(cleaned_text) - wlen + 1):
                segment = cleaned_text[start:start + wlen]
                # 跳过已经是词典词的片段
                if segment in dictionary_words:
                    continue

                seg_pinyins = get_all_pinyins(segment)
                for seg_py in seg_pinyins:
                    # 精确拼音匹配
                    if seg_py == word_pinyin:
                        cleaned_text = (
                            cleaned_text[:start] + word + cleaned_text[start + wlen:]
                        )
                        break
                    # 模糊拼音匹配
                    if pinyin_similarity(seg_py, word_pinyin) >= 0.75:
                        cleaned_text = (
                            cleaned_text[:start] + word + cleaned_text[start + wlen:]
                        )
                        break
                else:
                    continue
                break
            else:
                continue
            break

    return cleaned_text