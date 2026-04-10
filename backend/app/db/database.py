"""
数据库配置和初始化
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_diary.db")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Diary(Base):
    """日记数据模型"""
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False, comment="原始语音转写文本")
    cleaned_text = Column(Text, nullable=True, comment="AI清洗后的文本")
    emotion = Column(String(50), nullable=True, comment="主要情绪类型")
    emotion_score = Column(Float, nullable=True, comment="情绪强度(1-10)")
    emotion_keywords = Column(Text, nullable=True, comment="情绪关键词JSON")
    secondary_emotions = Column(Text, nullable=True, comment="次要情绪JSON")
    emotion_dimension = Column(String(20), nullable=True, comment="情绪维度")
    emotion_confidence = Column(Float, nullable=True, comment="情绪识别信心度")
    topics = Column(Text, nullable=True, comment="主题标签JSON")
    key_events = Column(Text, nullable=True, comment="关键事件JSON")
    recording_duration = Column(Integer, nullable=True, comment="录音时长(秒)")
    word_count = Column(Integer, default=0, comment="字数")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()