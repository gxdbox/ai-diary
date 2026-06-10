"""
数据库配置和初始化
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, create_engine, text as sa_text
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_diary.db")
SYNC_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_diary.db").replace("+aiosqlite", "")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 同步引擎（用于后台任务）
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)

Base = declarative_base()


class Diary(Base):
    """日记数据模型"""
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, index=True)
    raw_text = Column(Text, nullable=False, comment="原始语音转写文本")
    title = Column(String(100), nullable=True, comment="日记标题")
    cleaned_text = Column(Text, nullable=True, comment="AI清洗后的文本")
    emotion = Column(String(50), nullable=True, comment="主要情绪类型")
    emotion_score = Column(Float, nullable=True, comment="情绪强度(1-10)")
    emotion_keywords = Column(Text, nullable=True, comment="情绪关键词JSON")
    secondary_emotions = Column(Text, nullable=True, comment="次要情绪JSON")
    emotion_dimension = Column(String(20), nullable=True, comment="情绪维度")
    emotion_confidence = Column(Float, nullable=True, comment="情绪识别信心度")
    emotion_energy = Column(Float, nullable=True, comment="情绪能量值(-10到+10)")
    emotion_intensity = Column(Float, nullable=True, comment="情绪强度(1-10)")
    topics = Column(Text, nullable=True, comment="主题标签JSON")
    key_events = Column(Text, nullable=True, comment="关键事件JSON")
    recording_duration = Column(Integer, nullable=True, comment="录音时长(秒)")
    audio_url = Column(String(500), nullable=True, comment="音频文件OSS URL")
    word_count = Column(Integer, default=0, comment="字数")
    weather = Column(Text, nullable=True, comment="天气信息JSON")
    images = Column(Text, nullable=True, comment="图片OSS key列表JSON")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class DictionaryEntry(Base):
    """自定义词典模型"""
    __tablename__ = "dictionary"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(100), nullable=False, comment="正确词")
    pinyin = Column(String(200), nullable=False, comment="拼音（用于同音词匹配）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class Conversation(Base):
    """对话记录表 - 统一存储 companion 和 assistant 的对话"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=1, comment="用户 ID")
    diary_id = Column(Integer, nullable=True, comment="关联的日记 ID")
    user_input = Column(Text, nullable=False, comment="用户输入")
    ai_response = Column(Text, nullable=False, comment="AI 回复")
    mode = Column(String(20), default="companion", comment="对话模式: companion/assistant")
    emotion_before = Column(String(50), nullable=True, comment="对话前情绪")
    emotion_after = Column(String(50), nullable=True, comment="对话后情绪")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class Character(Base):
    """日记人物实体"""
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="人物名称")
    first_appearance = Column(DateTime, nullable=False, comment="首次出现时间")
    last_appearance = Column(DateTime, nullable=False, comment="最后出现时间")
    appearance_count = Column(Integer, default=0, comment="出现次数")
    avatar_color = Column(String(20), default="#4A90E2", comment="头像颜色（十六进制）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class Relationship(Base):
    """人物关系"""
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, index=True)
    character_a_id = Column(Integer, nullable=False, comment="人物A ID")
    character_b_id = Column(Integer, nullable=False, comment="人物B ID")
    relationship_type = Column(String(50), default="unknown", comment="关系类型：朋友/家人/同事等")
    strength = Column(Float, default=0.5, comment="关系强度 0-1")
    last_interaction = Column(DateTime, nullable=True, comment="最后互动时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class CharacterAlias(Base):
    """人物别名表"""
    __tablename__ = "character_aliases"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, nullable=False, index=True, comment="关联人物 ID")
    alias = Column(String(100), nullable=False, comment="别名")
    source = Column(String(50), default="auto", comment="来源: auto/llm/manual")
    confidence = Column(Float, default=1.0, comment="匹配置信度 0-1")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


class Location(Base):
    """地点实体"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, comment="地点名称")
    visit_count = Column(Integer, default=0, comment="访问次数")
    last_visit = Column(DateTime, nullable=True, comment="最后访问时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 安全迁移：为旧数据库添加 images 列
        try:
            def add_images_column(connection):
                result = connection.execute(
                    sa_text("PRAGMA table_info(diaries)")
                )
                columns = [row[1] for row in result]
                if "images" not in columns:
                    connection.execute(
                        sa_text("ALTER TABLE diaries ADD COLUMN images TEXT")
                    )
            await conn.run_sync(add_images_column)
        except Exception as e:
            print(f"[DB Migration] images column migration: {e}")
        # 安全迁移：为旧数据库添加 title 列
        try:
            def add_title_column(connection):
                result = connection.execute(
                    sa_text("PRAGMA table_info(diaries)")
                )
                columns = [row[1] for row in result]
                if "title" not in columns:
                    connection.execute(
                        sa_text("ALTER TABLE diaries ADD COLUMN title VARCHAR(100)")
                    )
            await conn.run_sync(add_title_column)
        except Exception as e:
            print(f"[DB Migration] title column migration: {e}")
        # 安全迁移：为旧数据库添加 audio_url 列
        try:
            def add_audio_url_column(connection):
                result = connection.execute(
                    sa_text("PRAGMA table_info(diaries)")
                )
                columns = [row[1] for row in result]
                if "audio_url" not in columns:
                    connection.execute(
                        sa_text("ALTER TABLE diaries ADD COLUMN audio_url VARCHAR(500)")
                    )
            await conn.run_sync(add_audio_url_column)
        except Exception as e:
            print(f"[DB Migration] audio_url column migration: {e}")
        # 新增：为 relationships 表添加索引
        try:
            def add_relationship_indexes(connection):
                # 检查索引是否存在
                result = connection.execute(
                    sa_text("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_relationship_char_a'")
                )
                if not result.fetchone():
                    connection.execute(sa_text("CREATE INDEX idx_relationship_char_a ON relationships(character_a_id)"))
                    connection.execute(sa_text("CREATE INDEX idx_relationship_char_b ON relationships(character_b_id)"))
            await conn.run_sync(add_relationship_indexes)
        except Exception as e:
            print(f"[DB Migration] relationship indexes migration: {e}")
        # 安全迁移：创建 character_aliases 表
        try:
            def add_character_aliases_table(connection):
                result = connection.execute(
                    sa_text("SELECT name FROM sqlite_master WHERE type='table' AND name='character_aliases'")
                )
                if not result.fetchone():
                    connection.execute(sa_text("""
                        CREATE TABLE character_aliases (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            character_id INTEGER NOT NULL,
                            alias VARCHAR(100) NOT NULL,
                            source VARCHAR(50) DEFAULT 'auto',
                            confidence FLOAT DEFAULT 1.0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    connection.execute(sa_text("CREATE INDEX idx_alias_character_id ON character_aliases(character_id)"))
                    connection.execute(sa_text("CREATE INDEX idx_alias_name ON character_aliases(alias)"))
            await conn.run_sync(add_character_aliases_table)
        except Exception as e:
            print(f"[DB Migration] character_aliases table migration: {e}")


async def get_db():
    """获取数据库会话（异步）"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """获取数据库会话（同步，用于后台任务）"""
    session = Session(bind=sync_engine)
    try:
        yield session
    finally:
        session.close()