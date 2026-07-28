"""
实时语音识别 WebSocket 端点

iOS 端通过 WebSocket 发送实时音频流，后端转发到 DashScope Paraformer 实时 ASR，
识别结果实时返回给 iOS 端展示。

架构：iOS PCM 流 → 后端 WebSocket → DashScope Recognition SDK → 实时文本返回
"""
import os
import json
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from jose import jwt, JWTError

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

logger = logging.getLogger(__name__)

router = APIRouter()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
dashscope.api_key = DASHSCOPE_API_KEY

# JWT 密钥（与 auth 模块保持一致）
SECRET_KEY = os.getenv("SECRET_KEY", "please-change-this-to-a-random-secret-key-at-least-32-chars")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def verify_ws_token(token: str) -> int:
    """验证 WebSocket 请求中的 JWT token，返回 user_id"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


class ASRCallback(RecognitionCallback):
    """DashScope ASR 实时识别回调 — 将结果通过 asyncio.Queue 发送给 WebSocket"""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.connected = False
        self.stopped = False

    def on_open(self):
        self.connected = True
        logger.info("ASR 实时连接已建立")

    def on_event(self, result: RecognitionResult):
        try:
            sentence = result.output.get("sentence", {})
            text = sentence.get("text", "")
            if text and text.strip():
                self.queue.put_nowait(json.dumps({
                    "text": text.strip(),
                    "sentence_id": sentence.get("sentence_id", 0),
                    "sentence_end": sentence.get("sentence_end", False),
                    "begin_time": sentence.get("begin_time", 0),
                    "end_time": sentence.get("end_time", 0),
                }, ensure_ascii=False))
        except Exception as e:
            logger.error(f"ASR callback 处理异常: {e}")

    def on_error(self, result: RecognitionResult):
        logger.error(f"ASR 错误: {result.message if hasattr(result, 'message') else str(result)}")

    def on_close(self):
        self.connected = False
        logger.info("ASR 连接关闭")

    def on_complete(self):
        self.connected = False
        self.stopped = True
        self.queue.put_nowait(None)  # 发送结束信号
        logger.info("ASR 识别完成")


@router.websocket("/ws/asr")
async def asr_realtime_websocket(
    ws: WebSocket,
    token: str = Query(None, description="JWT 认证 token"),
):
    """实时语音识别 WebSocket

    流程：
    1. iOS 连接 wss://server/ws/asr?token=xxx
    2. 验证 JWT token
    3. 服务端建立 DashScope 实时 ASR 连接
    4. iOS 发送二进制音频数据（PCM 16kHz 16bit mono）
    5. 服务端转发到 ASR，实时返回识别结果（JSON 文本）
    6. iOS 断开连接 → 结束识别任务

    支持的音频格式：PCM 16kHz 16bit mono（与 iOS SFSpeech 一致）
    """
    # 验证 token
    verify_ws_token(token)

    await ws.accept()
    logger.info("WebSocket 连接已接受")

    callback = ASRCallback()
    recognition = None

    try:
        # 创建 DashScope 实时识别器
        recognition = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=16000,
            callback=callback,
        )

        # 在线程池中启动 stream_call（它内部会建立 WebSocket）
        await asyncio.to_thread(recognition.stream_call)

        if not callback.connected:
            await ws.send_text(json.dumps({"error": "ASR 服务连接失败"}, ensure_ascii=False))
            return

        # 通知 iOS 已就绪
        await ws.send_text(json.dumps({"type": "ready"}, ensure_ascii=False))
        logger.info("实时 ASR 已就绪，开始接收音频")

        # 后台任务：将 ASR 结果发送给 iOS
        async def send_asr_results():
            while not callback.stopped:
                try:
                    result_text = await asyncio.wait_for(callback.queue.get(), timeout=0.5)
                    if result_text is None:
                        break
                    await ws.send_text(result_text)
                except asyncio.TimeoutError:
                    # 心跳检查
                    if callback.stopped:
                        break
                    continue
                except Exception as e:
                    if not callback.stopped:
                        logger.error(f"发送 ASR 结果失败: {e}")
                    break

        send_task = asyncio.create_task(send_asr_results())

        # 主循环：接收 iOS 音频数据
        try:
            while True:
                data = await ws.receive_bytes()
                if data and recognition and callback.connected:
                    recognition.send_audio_frame(data)
        except WebSocketDisconnect:
            logger.info("iOS 客户端断开连接")

        # 等待 send_task 完成
        if not callback.stopped:
            await asyncio.to_thread(recognition.stop)
        await asyncio.wait_for(send_task, timeout=5.0)

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}", exc_info=True)
        try:
            await ws.send_text(json.dumps({"error": str(e)}, ensure_ascii=False))
        except Exception:
            pass
    finally:
        if recognition:
            try:
                if not callback.stopped:
                    await asyncio.to_thread(recognition.stop)
            except Exception:
                pass
        try:
            await ws.close()
        except Exception:
            pass
