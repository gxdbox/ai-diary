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

# 复用 security.py 中的密钥配置，保证 token 签发和验证一致
from app.core.security import SECRET_KEY, ALGORITHM


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
    """DashScope ASR 实时识别回调

    通过 loop.call_soon_threadsafe() 确保所有队列操作在事件循环线程执行，
    避免 asyncio.Queue 的线程安全问题。
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.loop = loop
        self.connected = False
        self.stopped = False
        self.ready_event = asyncio.Event()

    def on_open(self):
        self.connected = True
        self.loop.call_soon_threadsafe(self.ready_event.set)
        logger.info("ASR 实时连接已建立")

    def on_event(self, result: RecognitionResult):
        try:
            sentence = result.output.get("sentence", {})
            text = sentence.get("text", "")
            if text and text.strip():
                payload = json.dumps({
                    "text": text.strip(),
                    "sentence_id": sentence.get("sentence_id", 0),
                    "sentence_end": sentence.get("sentence_end", False),
                    "begin_time": sentence.get("begin_time", 0),
                    "end_time": sentence.get("end_time", 0),
                }, ensure_ascii=False)
                self.loop.call_soon_threadsafe(self.queue.put_nowait, payload)
        except Exception as e:
            logger.error(f"ASR callback 处理异常: {e}")

    def on_error(self, result: RecognitionResult):
        msg = result.message if hasattr(result, 'message') else str(result)
        logger.error(f"ASR 错误: {msg}")
        self.connected = False
        try:
            error_payload = json.dumps({"type": "asr_error", "error": msg}, ensure_ascii=False)
            self.loop.call_soon_threadsafe(self.queue.put_nowait, error_payload)
        except Exception:
            pass

    def on_close(self):
        self.connected = False
        logger.info("ASR 连接关闭")

    def on_complete(self):
        self.connected = False
        self.stopped = True
        self.loop.call_soon_threadsafe(self.queue.put_nowait, None)
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
    3. 后台启动 DashScope stream_call，等待连接就绪
    4. iOS 发送二进制音频数据（PCM 16kHz 16bit mono）
    5. 服务端转发到 ASR，实时返回识别结果（JSON 文本）
    6. iOS 断开连接 → 结束识别任务
    """
    verify_ws_token(token)
    await ws.accept()
    logger.info("WebSocket 连接已接受")

    loop = asyncio.get_running_loop()
    callback = ASRCallback(loop=loop)
    recognition = None
    recognition_task = None

    try:
        recognition = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=16000,
            callback=callback,
        )

        # start() 是阻塞调用——作为后台任务启动，不 await
        recognition_task = asyncio.create_task(
            asyncio.to_thread(recognition.start)
        )

        # 等待 ASR 连接就绪或超时
        try:
            await asyncio.wait_for(callback.ready_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            await ws.send_text(
                json.dumps({"error": "ASR 服务连接超时"}, ensure_ascii=False)
            )
            return

        if not callback.connected:
            await ws.send_text(
                json.dumps({"error": "ASR 服务连接失败"}, ensure_ascii=False)
            )
            return

        # 通知 iOS 已就绪
        await ws.send_text(json.dumps({"type": "ready"}, ensure_ascii=False))
        logger.info("实时 ASR 已就绪，开始接收音频")

        # 后台任务：将 ASR 结果发送给 iOS
        async def send_asr_results():
            while not callback.stopped:
                try:
                    result_text = await asyncio.wait_for(
                        callback.queue.get(), timeout=0.5
                    )
                    if result_text is None:
                        break
                    await ws.send_text(result_text)
                except asyncio.TimeoutError:
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

        # 停止 ASR
        if not callback.stopped:
            await asyncio.to_thread(recognition.stop)
        await asyncio.wait_for(send_task, timeout=5.0)

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}", exc_info=True)
        try:
            await ws.send_text(
                json.dumps({"error": str(e)}, ensure_ascii=False)
            )
        except Exception:
            pass
    finally:
        if recognition and not callback.stopped:
            try:
                await asyncio.to_thread(recognition.stop)
            except Exception:
                pass
        if recognition_task and not recognition_task.done():
            recognition_task.cancel()
        try:
            await ws.close()
        except Exception:
            pass
