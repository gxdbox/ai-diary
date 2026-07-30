"""
云端 ASR 服务 - 基于 DashScope Paraformer

提供高准确率中文语音转文字，支持：
- 语义断句自动标点（enable_semantic_sentence_detection）
- 热词提升专有名词识别率（hotwords）
- 口语填充词自动去除（disfluency_removal）

API 文档: https://help.aliyun.com/zh/dashscope/developer-reference/paraformer-file-audio-to-text
"""
import os
import asyncio
import logging
from typing import Optional, List

import dashscope
from dashscope.audio.asr import Transcription

logger = logging.getLogger(__name__)

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
# 初始化 DashScope API Key
dashscope.api_key = DASHSCOPE_API_KEY


class ASRService:
    """云端 ASR 服务 — DashScope Paraformer-v2"""

    def __init__(self):
        self.enabled = bool(DASHSCOPE_API_KEY)

    async def transcribe(self, audio_url: str, hot_words=None) -> str:
        """转写音频文件

        Args:
            audio_url: 音频文件的公网可访问 URL（OSS 签名 URL）
            hot_words: 热词，支持两种格式：
                - List[str]: 简单词列表，所有词权重 50
                - Dict[str, int]: 词到权重的映射，权重范围 1-100

        Returns:
            转写文本（带标点），失败时返回空字符串
        """
        if not self.enabled:
            logger.warning("DASHSCOPE_API_KEY 未配置，云端 ASR 不可用")
            return ""

        try:
            text = await asyncio.to_thread(
                self._transcribe_sync, audio_url, hot_words
            )
            return text
        except Exception as e:
            logger.error(f"ASR 转写异常: {e}")
            return ""

    def _transcribe_sync(self, audio_url: str, hot_words=None) -> str:
        """同步转写（在线程池中执行）"""
        parameters = {
            "language_hints": ["zh"],
            "enable_semantic_sentence_detection": True,
            "disfluency_removal": True,
        }
        if hot_words:
            # DashScope 热词格式：{word: weight}，weight 范围 1-100
            if isinstance(hot_words, dict):
                # 已经是带权重的字典格式，直接使用（限制最多 50 个）
                parameters["hotwords"] = dict(list(hot_words.items())[:50])
            else:
                # 列表格式，所有词使用默认权重 50
                parameters["hotwords"] = {word: 50 for word in hot_words[:50]}

        # 提交转写任务
        task = Transcription.call(
            model="paraformer-v2",
            file_urls=[audio_url],
            parameters=parameters,
        )

        if task.status_code != 200:
            logger.error(f"ASR 提交失败: {task.status_code} - {task.message}")
            return ""

        task_id = task.output.get("task_id")
        if not task_id:
            logger.error("ASR 提交失败：无 task_id")
            return ""

        # 等待任务完成（SDK 内部轮询）
        result = Transcription.wait(task_id)

        if result.status_code != 200:
            logger.error(f"ASR 任务失败: {result.status_code} - {result.message}")
            return ""

        # 提取转写结果 URL
        results = result.output.get("results", [])
        if not results:
            logger.warning("ASR 任务完成但无结果")
            return ""

        transcription_url = results[0].get("transcription_url")
        if not transcription_url:
            return ""

        return self._download_transcript(transcription_url)

    def _download_transcript(self, url: str) -> str:
        """下载转写结果并提取文本

        DashScope 返回 JSON 格式：
        {
            "file_url": "oss://...",
            "transcripts": [{"text": "转写文本", "channel_id": [0], ...}],
            "subtask_status": "SUCCEEDED"
        }
        """
        import httpx

        try:
            response = httpx.get(url, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                transcripts = data.get("transcripts", [])
                if transcripts:
                    # 拼接所有 transcript 的文本
                    return " ".join(t.get("text", "") for t in transcripts).strip()
                # 兼容：可能是纯文本
                return response.text.strip()
            else:
                logger.error(f"下载转写结果失败: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"下载转写结果异常: {e}")
            return ""

    def get_hot_words(self) -> List[str]:
        """从词典缓存获取热词列表"""
        try:
            from app.api.dictionary import dictionary_words
            return list(dictionary_words)[:50]
        except Exception:
            return []


asr_service = ASRService()
