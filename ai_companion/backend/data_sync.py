# AI伴侣 - 数据同步模块

import sqlite3
import json
from datetime import datetime
from pathlib import Path

# 数据库路径
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "ai_companion.db"


def init_db():
    """初始化本地数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建日记表（从松果日记同步的数据）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY,
            cleaned_text TEXT NOT NULL,
            emotion TEXT,
            emotion_score REAL,
            topics TEXT,
            created_at TEXT,
            synced_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建对话历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diary_id INTEGER,
            user_input TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            emotion_before TEXT,
            emotion_after TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (diary_id) REFERENCES diaries(id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"✓ 数据库初始化完成: {DB_PATH}")


def import_diaries_from_file(filepath: str):
    """从导出文件导入日记数据"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    imported_count = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 解析数据（格式：id|cleaned_text|emotion|emotion_score|topics|created_at）
            parts = line.split('|')
            if len(parts) >= 6:
                try:
                    diary_id = int(parts[0])
                    cleaned_text = parts[1]
                    emotion = parts[2] if parts[2] else None
                    emotion_score = float(parts[3]) if parts[3] else None
                    topics = parts[4] if parts[4] else None
                    created_at = parts[5] if parts[5] else None

                    # 检查是否已存在
                    cursor.execute("SELECT id FROM diaries WHERE id = ?", (diary_id,))
                    if cursor.fetchone():
                        continue

                    # 插入数据
                    cursor.execute("""
                        INSERT INTO diaries (id, cleaned_text, emotion, emotion_score, topics, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (diary_id, cleaned_text, emotion, emotion_score, topics, created_at))

                    imported_count += 1

                except Exception as e:
                    print(f"导入失败: {line[:50]}... - {e}")

    conn.commit()
    conn.close()

    print(f"✓ 导入完成: {imported_count} 条日记")
    return imported_count


def get_diaries(limit: int = 20, emotion: str = None):
    """获取日记列表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if emotion:
        cursor.execute("""
            SELECT id, cleaned_text, emotion, created_at
            FROM diaries
            WHERE emotion = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (emotion, limit))
    else:
        cursor.execute("""
            SELECT id, cleaned_text, emotion, created_at
            FROM diaries
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "text": row[1],
            "emotion": row[2],
            "created_at": row[3]
        }
        for row in rows
    ]


def get_diary_by_id(diary_id: int):
    """获取单篇日记"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, cleaned_text, emotion, emotion_score, topics, created_at
        FROM diaries WHERE id = ?
    """, (diary_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row[0],
            "text": row[1],
            "emotion": row[2],
            "emotion_score": row[3],
            "topics": row[4],
            "created_at": row[5]
        }
    return None


def save_conversation(diary_id: int, user_input: str, ai_response: str, emotion_before: str = None):
    """保存对话记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conversations (diary_id, user_input, ai_response, emotion_before)
        VALUES (?, ?, ?, ?)
    """, (diary_id, user_input, ai_response, emotion_before))

    conn.commit()
    conn.close()


def get_stats():
    """获取统计信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 总数
    cursor.execute("SELECT COUNT(*) FROM diaries")
    total = cursor.fetchone()[0]

    # 情绪分布
    cursor.execute("""
        SELECT emotion, COUNT(*) as count
        FROM diaries
        WHERE emotion IS NOT NULL
        GROUP BY emotion
        ORDER BY count DESC
    """)
    emotions = cursor.fetchall()

    conn.close()

    return {
        "total": total,
        "emotion_distribution": dict(emotions)
    }


if __name__ == "__main__":
    # 测试导入
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        import_diaries_from_file(filepath)

    # 测试查询
    init_db()
    stats = get_stats()
    print(f"统计: {stats}")

    diaries = get_diaries(5)
    print(f"最近5条日记:")
    for d in diaries:
        print(f"  [{d['id']}] {d['emotion']}: {d['text'][:50]}...")