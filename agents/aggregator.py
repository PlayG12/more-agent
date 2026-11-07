"""汇总 Agent：汇集各 Agent 的产物，形成最终结果说明。"""
import time

from langgraph.types import StreamWriter

from state import AgentState, TaskRecord


def aggregator_node(state: AgentState, *, writer: StreamWriter) -> dict:
    writer({"agent": "aggregator", "status": "running"})  # 上报"开始执行"，前端卡片置为执行中
    start = time.time()
    summary = "；".join([
        f"主题：{state.get('theme', '')[:30]}",
        f"文案：{len(state.get('copy_text', ''))} 字",
        f"图片：{'已生成' if state.get('image_url') else '无'}",
        f"音频：{'已生成' if state.get('audio_path') else '无'}",
    ])
    record = TaskRecord(
        agent="aggregator", status="done",
        summary="产物汇总完成", output=summary,
        elapsed=round(time.time() - start, 2),
    )
    return {"task_log": [record]}
