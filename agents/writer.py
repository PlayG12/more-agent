"""文案 Agent：根据主题写一段适合配图与朗读的宣传文案。"""
import time

from langgraph.types import StreamWriter

from state import AgentState, TaskRecord
from tools import llm

SYSTEM_PROMPT = (
    "你是文案写手。根据给定主题写一段 150 字以内的中文宣传文案，"
    "语言生动、适合朗读，只输出文案正文。"
)


def writer_node(state: AgentState, *, writer: StreamWriter) -> dict:
    writer({"agent": "writer", "status": "running"})  # 上报"开始执行"，前端卡片置为执行中
    start = time.time()
    try:
        copy = llm.chat(
            SYSTEM_PROMPT,
            f"创作主题：{state['theme']}\n原始需求：{state['user_input']}",
        )
        record = TaskRecord(
            agent="writer", status="done",
            summary=f"已生成 {len(copy)} 字文案", output=copy[:60],
            elapsed=round(time.time() - start, 2),
        )
        return {"copy_text": copy, "task_log": [record]}
    except Exception as exc:
        record = TaskRecord(
            agent="writer", status="failed",
            summary="文案生成失败", output=str(exc)[:80],
            elapsed=round(time.time() - start, 2),
        )
        return {"copy_text": "", "task_log": [record]}
