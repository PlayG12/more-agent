"""主题规划 Agent：把用户的一句话需求提炼为创作主题与大纲。"""
import time

from langgraph.types import StreamWriter

from state import AgentState, TaskRecord
from tools import llm

SYSTEM_PROMPT = (
    "你是内容策划专家。把用户的一句话需求提炼成明确的创作主题"
    "和不超过 3 点的大纲，输出精炼中文。"
)


def planner_node(state: AgentState, *, writer: StreamWriter) -> dict:
    writer({"agent": "planner", "status": "running"})  # 上报"开始执行"
    start = time.time()
    try:
        theme = llm.chat(SYSTEM_PROMPT, state["user_input"])
        record = TaskRecord(
            agent="planner", status="done",
            summary="已提炼主题与大纲", output=theme[:60],
            elapsed=round(time.time() - start, 2),
        )
        return {"theme": theme, "task_log": [record]}
    except Exception as exc:  # 外部 API 属于系统边界，失败也要可见
        record = TaskRecord(
            agent="planner", status="failed",
            summary="主题提炼失败", output=str(exc)[:80],
            elapsed=round(time.time() - start, 2),
        )
        return {"theme": state["user_input"], "task_log": [record]}
