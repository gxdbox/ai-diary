"""
向量存储服务 - 使用Chroma进行语义搜索
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Chroma持久化目录
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")


class VectorStore:
    """向量存储服务"""

    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False

    def init(self):
        """初始化向量数据库"""
        if self._initialized:
            return

        try:
            # 确保目录存在
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

            # 创建Chroma客户端
            self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="diaries",
                metadata={"description": "日记向量存储"}
            )

            self._initialized = True
            logger.info(f"向量数据库初始化成功: {CHROMA_PERSIST_DIR}")

        except Exception as e:
            logger.error(f"向量数据库初始化失败: {str(e)}")
            raise

    def add_diary(self, diary_id: int, text: str, metadata: Dict = None):
        """添加日记到向量存储"""
        if not self._initialized:
            self.init()

        try:
            self.collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[str(diary_id)]
            )
            logger.info(f"添加日记向量: id={diary_id}")
        except Exception as e:
            logger.error(f"添加日记向量失败: {str(e)}")

    def update_diary(self, diary_id: int, text: str, metadata: Dict = None):
        """更新日记向量"""
        if not self._initialized:
            self.init()

        try:
            self.collection.upsert(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[str(diary_id)]
            )
            logger.info(f"更新日记向量: id={diary_id}")
        except Exception as e:
            logger.error(f"更新日记向量失败: {str(e)}")

    def delete_diary(self, diary_id: int):
        """删除日记向量"""
        if not self._initialized:
            self.init()

        try:
            self.collection.delete(ids=[str(diary_id)])
            logger.info(f"删除日记向量: id={diary_id}")
        except Exception as e:
            logger.error(f"删除日记向量失败: {str(e)}")

    def search(self, query: str, n_results: int = 10) -> List[Dict]:
        """语义搜索"""
        if not self._initialized:
            self.init()

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )

            # 格式化结果
            formatted_results = []
            if results and results.get('ids'):
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted_results.append({
                        'id': int(doc_id),
                        'text': results['documents'][0][i] if results.get('documents') else '',
                        'score': 1 - results['distances'][0][i] if results.get('distances') else 0,
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {}
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    def get_stats(self) -> Dict:
        """获取向量存储统计"""
        if not self._initialized:
            self.init()

        try:
            count = self.collection.count()
            return {
                "total_vectors": count,
                "collection_name": "diaries"
            }
        except Exception as e:
            logger.error(f"获取统计失败: {str(e)}")
            return {"total_vectors": 0, "collection_name": "diaries"}


# 全局向量存储实例
vector_store = VectorStore()