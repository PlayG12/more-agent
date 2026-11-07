"""文生图 Agent：根据主题生成配图。"""
import time

from langgraph.types import StreamWriter

from state import AgentState, TaskRecord
from tools import image_api


def painter_node(state: AgentState, *, writer: StreamWriter) -> dict:
    writer({"agent": "painter", "status": "running"})  # 上报"开始执行"，前端卡片置为执行中
    start = time.time()
    # 提示词直接由主题拼接而成；后续可升级为让 LLM 先润色成英文提示词
    prompt = f"{state['theme']}，主题宣传插画，高清"
    try:
        url = image_api.generate_image(prompt)
        record = TaskRecord(
            agent="painter", status="done",
            summary="已生成配图" if url else "已生成配图（mock，无实际图片）",
            output=url[:80] if url else "(mock 模式)",
            elapsed=round(time.time() - start, 2),
        )
        return {"image_url": url, "task_log": [record]}
    except Exception as exc:
        record = TaskRecord(
            agent="painter", status="failed",
            summary="图片生成失败", output=str(exc)[:80],
            elapsed=round(time.time() - start, 2),
        )
        return {"image_url": "", "task_log": [record]}
