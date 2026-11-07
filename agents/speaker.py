"""语音 Agent：把文案合成为 mp3 语音。"""
import time

from langgraph.types import StreamWriter

from state import AgentState, TaskRecord
from tools import tts_api


def speaker_node(state: AgentState, *, writer: StreamWriter) -> dict:
    writer({"agent": "speaker", "status": "running"})  # 上报"开始执行"，前端卡片置为执行中
    start = time.time()
    try:
        path = tts_api.synthesize(state["copy_text"], filename="copy.mp3")
        record = TaskRecord(
            agent="speaker", status="done",
            summary="已合成语音" if path else "已合成语音（mock，无实际音频）",
            output=path or "(mock 模式)",
            elapsed=round(time.time() - start, 2),
        )
        return {"audio_path": path, "task_log": [record]}
    except Exception as exc:
        record = TaskRecord(
            agent="speaker", status="failed",
            summary="语音合成失败", output=str(exc)[:80],
            elapsed=round(time.time() - start, 2),
        )
        return {"audio_path": "", "task_log": [record]}
