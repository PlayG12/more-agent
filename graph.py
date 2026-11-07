"""LangGraph 任务编排。

流程：
    planner -> writer -> painter ┐
                      -> speaker ┴-> aggregator -> END
writer 之后扇出（fan-out）：文生图与语音合成互不依赖，并行执行；
aggregator 作为屏障（barrier），等两者都完成后再汇总。
"""
from langgraph.graph import END, START, StateGraph

from agents import aggregator, painter, planner, speaker, writer
from state import AgentState


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("planner", planner.planner_node)
    g.add_node("writer", writer.writer_node)
    g.add_node("painter", painter.painter_node)
    g.add_node("speaker", speaker.speaker_node)
    g.add_node("aggregator", aggregator.aggregator_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "writer")
    g.add_edge("writer", "painter")   # 扇出：并行分支 1
    g.add_edge("writer", "speaker")   # 扇出：并行分支 2
    # aggregator 有两条入边，天然形成屏障（barrier）：
    # 必须 painter 和 speaker 都完成，aggregator 才会执行
    g.add_edge("painter", "aggregator")
    g.add_edge("speaker", "aggregator")
    g.add_edge("aggregator", END)

    # compile 后才得到可调用的图，之后用 graph.stream / graph.invoke 驱动
    return g.compile()


graph = build_graph()
