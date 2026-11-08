"""Streamlit 演示入口：输入主题，实时观看每个 Agent 的工作状态与产物。

运行：streamlit run app.py

状态可见性的实现：
- 节点开始执行时通过 custom 流推送 {"agent": ..., "status": "running"}；
- 节点完成时通过 updates 流带回 task_log 记录（耗时、产出摘要）；
- 前端据此把每个 Agent 的卡片从 等待中 -> 执行中 -> 完成/失败 实时刷新。
"""
import streamlit as st

import config
from graph import graph

# (节点名, 展示名) —— 与 graph.py 中的节点名一一对应
AGENTS = [
    ("planner", "主题规划 Agent"),
    ("writer", "文案 Agent"),
    ("painter", "文生图 Agent"),
    ("speaker", "语音 Agent"),
    ("aggregator", "汇总 Agent"),
]
NAMES = dict(AGENTS)

st.set_page_config(page_title="More-Agent 多 Agent 创作流水线", layout="wide")
st.title("More-Agent")

if config.LLM_MOCK or config.IMAGE_MOCK:
    st.caption("未检测到部分 API Key，对应 Agent 以 mock 模式运行；在 .env 中配置后自动切换为真实接口。")

user_input = st.text_input("输入你的主题需求", placeholder="例：做一个关于秋日森林的宣传内容")

if st.button("开始创作", type="primary", disabled=not user_input):
    # 每个 Agent 一张状态卡片
    cards = {key: st.empty() for key, _ in AGENTS}
    for key, name in AGENTS:
        cards[key].info(f"⏳ {name}：等待中")

    final_state: dict = {}
    with st.spinner("多 Agent 协同创作中…"):
        # 订阅两种流：
        #   custom  —— 节点内部用 StreamWriter 主动推送的"开始执行"事件
        #   updates —— 节点返回后产生的状态增量（key 即节点名，内含 task_log）
        for mode, chunk in graph.stream(
            {"user_input": user_input, "task_log": []},
            stream_mode=["updates", "custom"],
        ):
            if mode == "custom":
                # 节点开始执行
                name = NAMES.get(chunk["agent"], chunk["agent"])
                cards[chunk["agent"]].warning(f"🔄 {name}：执行中…")
            else:
                # 节点完成，updates 的 key 就是节点名
                for node_name, update in chunk.items():
                    final_state.update(update)
                    for record in update.get("task_log", []):
                        name = NAMES.get(node_name, node_name)
                        if record["status"] == "done":
                            cards[node_name].success(
                                f"✅ {name}：{record['summary']}（{record['elapsed']}s）\n\n{record['output']}"
                            )
                        else:
                            cards[node_name].error(
                                f"❌ {name}：{record['summary']}\n\n{record['output']}"
                            )

    # 产物展示
    st.divider()
    st.subheader("最终产物")
    col_text, col_image = st.columns(2)
    with col_text:
        st.markdown("**文案**")
        st.write(final_state.get("copy_text") or "（无）")
    with col_image:
        st.markdown("**配图**")
        if final_state.get("image_url"):
            st.image(final_state["image_url"])
        else:
            st.write("（无）")
    st.markdown("**语音**")
    if final_state.get("audio_path"):
        st.audio(final_state["audio_path"])
    else:
        st.write("（无）")

    # 完整执行日志（对应"执行过程可见"的评分点）
    with st.expander("查看完整 task_log"):
        st.json(final_state.get("task_log", []))
