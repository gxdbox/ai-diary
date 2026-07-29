"""
日记相关API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, Form, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List
from datetime import datetime
import json
import asyncio
import importlib
import logging

logger = logging.getLogger(__name__)

from app.db.database import get_db, Diary, User, DictionaryEntry
from app.core.security import get_current_user
from app.models.diary import (
    DiaryCreate, DiaryResponse, DiaryListResponse,
    CleanTextRequest, CleanTextResponse, WeatherRequest,
    ImageUploadResponse, ImageDeleteRequest, TranscribeResponse
)
from app.services.ai_service import ai_service
from app.services.text_cleaner import text_cleaner
from app.services.vector_store import vector_store
from app.services.entity_extractor import EntityExtractor
from app.services import oss_service
from app.services.oss_service import OSSService
from app.services.asr_service import asr_service

router = APIRouter()


async def _get_context_summary(db: AsyncSession, user_id: int) -> str:
    """获取用户近期日记上下文摘要，用于同音词消歧

    从最近 5 篇日记中提取文本片段作为上下文，帮助 LLM 在清洗时
    根据用户习惯用语消歧同音词。
    """
    try:
        result = await db.execute(
            select(Diary.cleaned_text)
            .where(Diary.user_id == user_id, Diary.cleaned_text.isnot(None))
            .order_by(desc(Diary.created_at))
            .limit(5)
        )
        texts = result.scalars().all()
        if not texts:
            return ""
        summaries = [t[:80] for t in texts if t]
        return "；".join(summaries)
    except Exception as e:
        logger.warning(f"获取上下文摘要失败: {e}")
        return ""


def _async_learn_from_diary(diary_id: int, diary_data: dict):
    """
    异步学习日记内容（后台任务）

    安全隔离设计：
    - 在后台线程执行，不阻塞主链路
    - 错误只记录日志，不影响用户体验
    - 使用动态导入避免循环导入问题
    """
    try:
        # 动态导入避免循环导入
        diary_assistant_module = importlib.import_module('app.services.diary_assistant')
        database_module = importlib.import_module('app.db.database')

        # 使用同步数据库连接（后台任务）
        db = next(database_module.get_sync_db())
        DiaryAssistantService = diary_assistant_module.DiaryAssistantService
        assistant = DiaryAssistantService(db)
        assistant.learn_from_diary(diary_id, diary_data)
        db.close()

    except Exception as e:
        # 失败只记录日志，不影响用户
        print(f"[Memory Learning Error] diary_id={diary_id}: {e}")


def _async_extract_entities(diary_id: int, cleaned_text: str, created_at: datetime):
    """
    异步提取日记中的实体（后台任务）

    从日记文本中提取人物、地点、关系等信息并保存到数据库
    """
    try:
        # 动态导入避免循环导入
        database_module = importlib.import_module('app.db.database')
        entity_extractor_module = importlib.import_module('app.services.entity_extractor')
        normalizer_module = importlib.import_module('app.services.entity_normalizer')

        # 使用同步数据库连接（后台任务）
        db = next(database_module.get_sync_db())
        EntityExtractor = entity_extractor_module.EntityExtractor
        EntityNormalizer = normalizer_module.EntityNormalizer
        extractor = EntityExtractor(db)

        # 构建已知实体上下文用于别名归一化
        normalizer = EntityNormalizer(db)
        context = normalizer.build_context()

        # 提取实体
        import asyncio
        entities = asyncio.run(extractor.extract_entities(cleaned_text, context))

        # 保存实体
        asyncio.run(extractor.save_entities(entities, diary_id, created_at))

        db.close()

    except Exception as e:
        # 失败只记录日志，不影响用户
        print(f"[Entity Extraction Error] diary_id={diary_id}: {e}")


def _async_auto_learn_dictionary(raw_text: str, cleaned_text: str, user_id: int):
    """异步学习日记中的专有名词，自动添加到用户词典

    同时统计词典词的校正次数，用于权重系统。
    后台提取专有名词并添加到词典，标记 source='auto'。
    """
    try:
        database_module = importlib.import_module('app.db.database')
        ai_service_module = importlib.import_module('app.services.ai_service')
        dictionary_module = importlib.import_module('app.api.dictionary')

        db = next(database_module.get_sync_db())
        DictionaryEntry = database_module.DictionaryEntry
        AIService = ai_service_module.AIService
        ai = AIService()

        # 提取专有名词
        nouns = asyncio.run(ai.extract_proper_nouns(cleaned_text))

        # 获取已有词典词
        from sqlalchemy import select as sa_select
        from sqlalchemy import update as sa_update
        existing_entries = db.execute(
            sa_select(DictionaryEntry.word, DictionaryEntry.correction_count)
            .where(DictionaryEntry.user_id == user_id)
        ).all()
        existing_words = {row[0]: row[1] or 0 for row in existing_entries}
        existing_count = len(existing_words)

        # 统计词典词的校正次数（比较 raw_text 和 cleaned_text）
        for word in existing_words:
            raw_count = raw_text.count(word)
            cleaned_count = cleaned_text.count(word)
            if cleaned_count > raw_count:
                # 该词在清洗后出现次数增加，说明被校正了
                delta = cleaned_count - raw_count
                db.execute(
                    sa_update(DictionaryEntry)
                    .where(DictionaryEntry.word == word, DictionaryEntry.user_id == user_id)
                    .values(correction_count=DictionaryEntry.correction_count + delta)
                )

        # 添加新词
        get_pinyin = dictionary_module.get_pinyin
        MAX_WORDS = dictionary_module.MAX_DICTIONARY_WORDS
        added = 0
        for noun in nouns:
            if noun in existing_words:
                continue
            if existing_count + added >= MAX_WORDS:
                break
            new_entry = DictionaryEntry(
                user_id=user_id,
                word=noun,
                pinyin=get_pinyin(noun),
                source='auto'
            )
            db.add(new_entry)
            added += 1
            existing_words[noun] = 0

        # 统一提交
        if added > 0:
            db.commit()
            asyncio.run(dictionary_module.update_dictionary_cache())
            print(f"[Dictionary Auto-Learn] Added {added} new words: {nouns[:added]}")
        else:
            db.commit()  # 仅提交权重更新

        db.close()
    except Exception as e:
        print(f"[Dictionary Auto-Learn Error]: {e}")


@router.post("/clean", response_model=CleanTextResponse)
async def clean_text(request: CleanTextRequest, current_user: User = Depends(get_current_user)):
    """
    清洗语音转写文本
    使用AI进行智能清洗
    """
    try:
        # 使用AI清洗
        cleaned = await ai_service.clean_text(request.raw_text)

        return CleanTextResponse(
            cleaned_text=cleaned,
            original_length=len(request.raw_text),
            cleaned_length=len(cleaned)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文本清洗失败: {str(e)}")


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    音频转写 — 上传音频文件，使用云端 ASR 转写

    1. 上传音频到 OSS
    2. 从当前用户词典查询热词
    3. 调用 DashScope Paraformer-v2 转写（带热词）
    4. 返回带标点的转写文本（不经过 LLM 清洗，供前端预览）
    """
    try:
        # 上传音频到 OSS
        audio_oss_service = OSSService()
        oss_url = await audio_oss_service.upload(audio_file)

        # 生成签名 URL 供 ASR 服务访问（私有 Bucket 需要签名）
        signed_url = audio_oss_service.get_signed_url(oss_url)

        # 从数据库查询当前用户词典词作为热词（按用户隔离，带权重）
        dict_result = await db.execute(
            select(
                DictionaryEntry.word,
                DictionaryEntry.correction_count,
                DictionaryEntry.source
            ).where(DictionaryEntry.user_id == current_user.id)
            .order_by(DictionaryEntry.correction_count.desc())
        )
        entries = dict_result.all()

        # 构建带权重的热词字典（基于 correction_count 和 source）
        hot_words = {}
        for word, count, source in entries[:50]:
            if source == 'confirmed':
                weight = 90  # 用户确认的词权重最高
            elif count and count > 5:
                weight = min(80, 50 + count * 3)  # 高频词权重较高
            else:
                weight = 50 + (count or 0) * 2  # 基于校正次数调整
            hot_words[word] = weight

        # 调用云端 ASR 转写
        raw_text = await asr_service.transcribe(signed_url, hot_words)
        used_cloud_asr = bool(raw_text)

        if not used_cloud_asr:
            logger.warning("云端 ASR 不可用或转写失败，返回空文本")

        return TranscribeResponse(
            raw_text=raw_text,
            audio_url=oss_url,
            used_cloud_asr=used_cloud_asr
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音频转写失败: {str(e)}")


@router.post("/create", response_model=DiaryResponse)
async def create_diary(
    request: DiaryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新日记
    1. AI清洗文本
    2. AI分析情绪和主题
    3. 保存到数据库
    4. 添加到向量存储
    5. [异步后台] 学习日记内容，更新记忆
    """
    try:
        # 加载用户词典缓存（用于拼音校正）
        from app.api.dictionary import load_dictionary_cache
        await load_dictionary_cache(db, user_id=current_user.id)

        # 获取用户近期上下文摘要（用于同音词消歧）
        context_summary = await _get_context_summary(db, current_user.id)

        # AI清洗文本（两遍清洗 + 上下文消歧 + 用户词典）
        # 如果 used_cloud_asr=True，说明 raw_text 来自离线ASR（已带热词、语气词过滤），跳过规则清洗
        skip_rule_clean = bool(request.used_cloud_asr)
        cleaned_text = await ai_service.clean_text(
            request.raw_text, 
            context_summary=context_summary, 
            user_id=current_user.id,
            skip_rule_clean=skip_rule_clean
        )

        # AI分析
        analysis = await ai_service.full_analysis(cleaned_text)

        # 创建日记记录
        diary = Diary(
            user_id=current_user.id,
            raw_text=request.raw_text,
            title=analysis.get("title"),
            cleaned_text=cleaned_text,
            emotion=analysis["emotion"].get("emotion"),
            emotion_score=analysis["emotion"].get("intensity"),  # 兼容：用 intensity 作为旧 score
            emotion_energy=analysis["emotion"].get("energy"),
            emotion_intensity=analysis["emotion"].get("intensity"),
            emotion_keywords=json.dumps(analysis["emotion"].get("keywords", []), ensure_ascii=False),
            secondary_emotions=json.dumps(analysis["emotion"].get("secondary_emotions", []), ensure_ascii=False),
            emotion_dimension=None,  # 废弃
            emotion_confidence=analysis["emotion"].get("confidence"),
            topics=json.dumps(analysis["topics"], ensure_ascii=False),
            key_events=json.dumps(analysis["key_events"], ensure_ascii=False),
            recording_duration=request.recording_duration,
            audio_url=request.audio_url,
            word_count=len(cleaned_text)
        )

        db.add(diary)
        await db.commit()
        await db.refresh(diary)

        # 添加到向量存储
        vector_store.add_diary(
            diary_id=diary.id,
            text=cleaned_text,
            metadata={
                "user_id": current_user.id,
                "emotion": diary.emotion,
                "created_at": diary.created_at.isoformat()
            }
        )

        # [异步后台] 学习日记内容 - 不阻塞主链路
        diary_data = {
            "id": diary.id,
            "cleaned_text": cleaned_text,
            "emotion": analysis["emotion"].get("emotion"),
            "topics": analysis["topics"],
            "key_events": analysis["key_events"]
        }
        background_tasks.add_task(_async_learn_from_diary, diary.id, diary_data)

        # [真正异步] 使用独立线程提取实体，完全不阻塞主流程
        import threading
        thread = threading.Thread(
            target=_async_extract_entities,
            args=(diary.id, cleaned_text, diary.created_at),
            daemon=True  # 守护线程，主程序退出时自动结束
        )
        thread.start()

        # [真正异步] 自动学习词典词汇 + 权重统计
        dict_thread = threading.Thread(
            target=_async_auto_learn_dictionary,
            args=(request.raw_text, cleaned_text, current_user.id),
            daemon=True
        )
        dict_thread.start()

        return _diary_to_response(diary)

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"创建日记失败: {str(e)}")


@router.get("/list", response_model=DiaryListResponse)
async def list_diaries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    emotion: str = Query(None, description="按情绪筛选"),
    topic: str = Query(None, description="按主题筛选"),
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取日记列表
    支持分页、情绪筛选、主题筛选和时间筛选
    """
    try:
        from datetime import datetime

        # 构建查询
        query = select(Diary).where(Diary.user_id == current_user.id)

        if emotion:
            query = query.where(Diary.emotion == emotion)

        if topic:
            # 主题存储在 JSON 数组中，使用 LIKE 查询
            query = query.where(Diary.topics.like(f'%"{topic}"%'))

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.where(Diary.created_at >= start_dt)
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                # 包含结束日期的全天
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                query = query.where(Diary.created_at <= end_dt)
            except ValueError:
                pass

        # 计算总数
        count_query = select(func.count()).select_from(Diary).where(Diary.user_id == current_user.id)
        if emotion:
            count_query = count_query.where(Diary.emotion == emotion)
        if topic:
            count_query = count_query.where(Diary.topics.like(f'%"{topic}"%'))
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                count_query = count_query.where(Diary.created_at >= start_dt)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
                count_query = count_query.where(Diary.created_at <= end_dt)
            except ValueError:
                pass

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # 分页查询
        query = query.order_by(desc(Diary.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        diaries = result.scalars().all()

        return DiaryListResponse(
            items=[_diary_to_response(d) for d in diaries],
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记列表失败: {str(e)}")


@router.get("/filters")
async def get_filters(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    获取可用的筛选选项
    返回所有情绪和主题列表
    """
    try:
        # 获取所有情绪
        emotion_query = select(Diary.emotion).where(Diary.emotion.isnot(None), Diary.user_id == current_user.id).distinct()
        emotion_result = await db.execute(emotion_query)
        emotions = sorted([e for e in emotion_result.scalars().all() if e])

        # 获取所有主题（从 JSON 数组中提取）
        topic_query = select(Diary.topics).where(Diary.topics.isnot(None), Diary.user_id == current_user.id)
        topic_result = await db.execute(topic_query)
        topics_set = set()
        for topics_json in topic_result.scalars().all():
            try:
                topics_list = json.loads(topics_json)
                topics_set.update(topics_list)
            except:
                pass
        topics = sorted(list(topics_set))

        return {
            "emotions": emotions,
            "topics": topics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取筛选选项失败: {str(e)}")


@router.get("/{diary_id}", response_model=DiaryResponse)
async def get_diary(
    diary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取单篇日记详情
    """
    try:
        result = await db.execute(
            select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id)
        )
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        return _diary_to_response(diary)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日记失败: {str(e)}")


@router.delete("/{diary_id}")
async def delete_diary(
    diary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除日记
    """
    # 先读取 oss keys 和 audio_url（在 DB 删除前读取）
    oss_keys = None
    audio_url = None
    try:
        result = await db.execute(
            select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id)
        )
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        # 保存 OSS keys 用于事务外清理
        if diary.images:
            try:
                oss_keys = json.loads(diary.images)
            except:
                pass

        # 保存音频URL用于事务外清理
        audio_url = diary.audio_url

        await db.delete(diary)
        await db.commit()

        # 从向量存储删除
        vector_store.delete_diary(diary_id)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除日记失败: {str(e)}")

    # OSS 清理在事务外，独立 try/except，不影响删除结果
    if oss_keys:
        try:
            oss_service.batch_delete(oss_keys)
        except Exception as e:
            print(f"[OSS] cleanup failed for diary {diary_id}: {e}")

    # 删除音频文件
    if audio_url:
        try:
            oss_service.delete(audio_url)
        except Exception as e:
            print(f"[OSS] audio cleanup failed for diary {diary_id}: {e}")

    return {"message": "删除成功", "id": diary_id}


@router.put("/{diary_id}", response_model=DiaryResponse)
async def update_diary(
    diary_id: int,
    cleaned_text: str = Query(..., description="修改后的文本"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新日记内容
    """
    try:
        result = await db.execute(
            select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id)
        )
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        # 更新文本
        diary.cleaned_text = cleaned_text
        diary.word_count = len(cleaned_text)

        # 重新分析
        analysis = await ai_service.full_analysis(cleaned_text)
        diary.title = analysis.get("title")
        diary.emotion = analysis["emotion"].get("emotion")
        diary.emotion_score = analysis["emotion"].get("intensity")  # 兼容
        diary.emotion_energy = analysis["emotion"].get("energy")
        diary.emotion_intensity = analysis["emotion"].get("intensity")
        diary.emotion_keywords = json.dumps(analysis["emotion"].get("keywords", []), ensure_ascii=False)
        diary.secondary_emotions = json.dumps(analysis["emotion"].get("secondary_emotions", []), ensure_ascii=False)
        diary.emotion_dimension = None  # 废弃
        diary.emotion_confidence = analysis["emotion"].get("confidence")
        diary.topics = json.dumps(analysis["topics"], ensure_ascii=False)
        diary.key_events = json.dumps(analysis["key_events"], ensure_ascii=False)

        await db.commit()
        await db.refresh(diary)

        # 更新向量存储
        vector_store.update_diary(
            diary_id=diary.id,
            text=cleaned_text,
            metadata={
                "user_id": current_user.id,
                "emotion": diary.emotion,
                "created_at": diary.created_at.isoformat()
            }
        )

        return _diary_to_response(diary)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新日记失败: {str(e)}")


def _diary_to_response(diary: Diary) -> DiaryResponse:
    """将数据库模型转换为响应模型"""
    # 将 OSS key 列表转换为签名 URL 列表（安全降级：失败不影响其他字段）
    image_urls = []
    if diary.images:
        try:
            keys = json.loads(diary.images)
            for key in keys:
                try:
                    image_urls.append(oss_service.sign_url(key))
                except Exception as e:
                    print(f"[OSS] sign_url failed for {key}: {e}")
                    image_urls.append("")
        except json.JSONDecodeError:
            pass

    return DiaryResponse(
        id=diary.id,
        raw_text=diary.raw_text,
        title=diary.title,
        cleaned_text=diary.cleaned_text,
        emotion=diary.emotion,
        emotion_score=diary.emotion_score,
        emotion_energy=diary.emotion_energy,
        emotion_intensity=diary.emotion_intensity,
        emotion_keywords=json.loads(diary.emotion_keywords) if diary.emotion_keywords else [],
        secondary_emotions=json.loads(diary.secondary_emotions) if diary.secondary_emotions else [],
        emotion_dimension=diary.emotion_dimension,
        emotion_confidence=diary.emotion_confidence,
        topics=json.loads(diary.topics) if diary.topics else [],
        key_events=json.loads(diary.key_events) if diary.key_events else [],
        recording_duration=diary.recording_duration,
        audio_url=diary.audio_url,
        word_count=diary.word_count,
        weather=json.loads(diary.weather) if diary.weather else None,
        images=image_urls,
        created_at=diary.created_at,
        updated_at=diary.updated_at
    )


# ============ 图片相关端点 ============

@router.post("/images/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    diary_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传单张图片到日记

    1. 校验文件格式和大小
    2. 上传到 OSS
    3. 更新日记的 images 字段
    """
    try:
        # 读取文件内容
        file_data = await file.read()

        # 提取扩展名
        if file.filename and "." in file.filename:
            ext = file.filename.rsplit(".", 1)[-1]
        else:
            ext = "jpg"

        # 上传到 OSS
        key = oss_service.upload_image(file_data, ext)

        # 查询日记
        result = await db.execute(select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id))
        diary = result.scalar_one_or_none()
        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        # 读取已有图片列表
        images = []
        if diary.images:
            try:
                images = json.loads(diary.images)
            except json.JSONDecodeError:
                pass

        # 检查数量上限
        if len(images) >= 3:
            raise HTTPException(status_code=400, detail="每篇日记最多添加 3 张图片")

        # 追加新 key
        images.append(key)
        diary.images = json.dumps(images, ensure_ascii=False)
        diary.updated_at = datetime.utcnow()
        await db.commit()

        # 生成签名 URL
        url = oss_service.sign_url(key)

        return ImageUploadResponse(
            key=key,
            url=url,
            size=len(file_data)
        )

    except (HTTPException, ValueError):
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片上传失败: {str(e)}")


@router.delete("/images")
async def delete_image(
    request: ImageDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除日记中的单张图片
    """
    try:
        result = await db.execute(select(Diary).where(Diary.id == request.diary_id, Diary.user_id == current_user.id))
        diary = result.scalar_one_or_none()
        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        # 从列表中移除
        images = []
        if diary.images:
            try:
                images = json.loads(diary.images)
            except json.JSONDecodeError:
                pass

        if request.image_key not in images:
            raise HTTPException(status_code=404, detail="图片不存在")

        images.remove(request.image_key)
        diary.images = json.dumps(images, ensure_ascii=False) if images else None
        diary.updated_at = datetime.utcnow()
        await db.commit()

        # 从 OSS 删除（事务外，不影响响应结果）
        try:
            oss_service.delete_image(request.image_key)
        except Exception as e:
            print(f"[OSS] delete_image failed for {request.image_key}: {e}")

        return {"success": True, "diary_id": request.diary_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片删除失败: {str(e)}")


@router.post("/weather")
async def update_weather(
    request: WeatherRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新日记天气信息（异步调用）
    """
    try:
        result = await db.execute(select(Diary).where(Diary.id == request.diary_id, Diary.user_id == current_user.id))
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        diary.weather = json.dumps(request.weather.model_dump())
        diary.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(diary)

        return {"success": True, "diary_id": diary.id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新天气失败: {str(e)}")


# ============ 音频相关端点 ============

@router.post("/{diary_id}/audio", response_model=DiaryResponse)
async def upload_diary_audio(
    diary_id: int,
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传日记音频文件到OSS

    1. 查询日记
    2. 验证并上传音频到OSS
    3. 保存音频URL到数据库
    4. 返回更新后的日记
    """
    try:
        # 查询日记
        result = await db.execute(select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id))
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        # 上传音频到OSS（使用OSSService类）
        audio_oss_service = OSSService()
        oss_url = await audio_oss_service.upload(audio_file)

        # 保存音频URL到数据库
        diary.audio_url = oss_url
        diary.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(diary)

        return _diary_to_response(diary)

    except (HTTPException, ValueError, RuntimeError):
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"音频上传失败: {str(e)}")


@router.get("/{diary_id}/audio-url")
async def get_diary_audio_url(
    diary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取日记音频的签名URL

    1. 查询日记获取audio_url
    2. 生成签名URL（1小时有效）
    3. 返回签名URL
    """
    try:
        result = await db.execute(select(Diary).where(Diary.id == diary_id, Diary.user_id == current_user.id))
        diary = result.scalar_one_or_none()

        if not diary:
            raise HTTPException(status_code=404, detail="日记不存在")

        if not diary.audio_url:
            raise HTTPException(status_code=404, detail="该日记没有关联音频")

        # 生成签名URL（使用OSSService类）
        audio_oss_service = OSSService()
        signed_url = audio_oss_service.get_signed_url(diary.audio_url)

        return {"audio_url": signed_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取音频URL失败: {str(e)}")
