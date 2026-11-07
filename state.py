"""多 Agent 共享状态定义。

task_log 是"每个 Agent 工作状态可见"的核心载体：
每个节点执行完都会 append 一条记录，前端只需渲染这个列表。
"""
import operator
from typing import Annotated, Literal, TypedDict


class TaskRecord(TypedDict):
    agent: str                          # 节点（Agent）名
    status: Literal["done", "failed"]   # 完成状态
    summary: str                        # 该 Agent 做了什么
    output: str                         # 产出摘要
    elapsed: float                      # 耗时（秒）


# total=False：每个节点只需返回自己要更新的少数字段，
# LangGraph 会把返回值自动合并进全局状态，不要求一次给全
class AgentState(TypedDict, total=False):
    user_input: str    # 用户原始输入
    theme: str         # 主题规划 Agent 产出
    copy_text: str     # 文案 Agent 产出
    image_url: str     # 文生图 Agent 产出
    audio_path: str    # 语音 Agent 产出
    # Annotated[..., operator.add] 是 LangGraph 的 reducer：
    # 多个（并行）节点同轮返回 task_log 时，列表做加法拼接而不是互相覆盖
    task_log: Annotated[list[TaskRecord], operator.add]
