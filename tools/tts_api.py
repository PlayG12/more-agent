"""文字转语音接口（edge-tts，免费、无需 API key）。

音色可在 .env 的 TTS_VOICE 配置，例如：
zh-CN-XiaoxiaoNeural（晓晓，女）/ zh-CN-YunjianNeural（云健，男）
"""
import asyncio
import os
import time

import edge_tts

import config


def synthesize(text: str, filename: str = "copy.mp3") -> str:
    """文本 -> mp3 文件，返回文件路径。TTS_MOCK=1 时返回空串。

    edge-tts 走的是公共服务，偶发网络抖动，失败时重试。
    """
    if config.TTS_MOCK:
        return ""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(config.OUTPUT_DIR, filename)
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            asyncio.run(_run(text, out_path))
            return out_path
        except Exception as exc:
            last_exc = exc
            time.sleep(2)
    raise last_exc


async def _run(text: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text, voice=config.TTS_VOICE)
    await communicate.save(out_path)
