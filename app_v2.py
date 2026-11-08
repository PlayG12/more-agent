"""第二版网页：讲义 notebook 风格的 Agent「执行情况」页面。

独立于第一版 app.py，不修改任何原文件：
    streamlit run app_v2.py --server.port 8502

流程与第一版完全一致（同一张 graph、同一批 Agent），
区别只在呈现方式：按 notebook 版式逐格展示——
[n] 代码格放真实源码，下方输出格展示 Thought / Action / Observation / Final，
执行中实时刷新状态。
"""
import html
import inspect
import os
import re

import streamlit as st
import streamlit.components.v1 as components

import result_server
from agents import aggregator, painter, planner, speaker, writer
from graph import build_graph, graph

# (节点名, 展示名)——与 graph.py 的节点名一一对应
AGENTS = [
    ("planner", "主题规划 Agent"),
    ("writer", "文案 Agent"),
    ("painter", "文生图 Agent"),
    ("speaker", "语音 Agent"),
    ("aggregator", "汇总 Agent"),
]
NAMES = dict(AGENTS)
# 节点名 -> 代码格编号（[1] 是编排格，Agent 从 [2] 开始）
CELL_IDX = {key: i + 2 for i, (key, _) in enumerate(AGENTS)}

# 每个 Agent 执行前的"思考"，用于 Thought 行
THOUGHTS = {
    "planner": "用户只给了一句话需求，先提炼出明确的创作主题与不超过 3 点的大纲，才能交给下游。",
    "writer": "主题已就绪，据此写一段 150 字以内、语言生动、适合朗读的宣传文案。",
    "painter": "文案已就绪，据此生成主题插画；本步骤与语音合成互不依赖，可以并行。",
    "speaker": "文案已就绪，把它合成为 mp3 语音；与文生图并行执行，互不阻塞。",
    "aggregator": "两条并行分支都已返回，汇总各 Agent 产物，检查完整性并给出结果说明。",
}

# 各 Agent 节点函数的真实源码，作为代码格内容
SRC = {
    "planner": inspect.getsource(planner.planner_node),
    "writer": inspect.getsource(writer.writer_node),
    "painter": inspect.getsource(painter.painter_node),
    "speaker": inspect.getsource(speaker.speaker_node),
    "aggregator": inspect.getsource(aggregator.aggregator_node),
}
SRC_GRAPH = inspect.getsource(build_graph)

# ---------- 语法高亮 ----------
_TOKENS = re.compile(
    r"(?P<comment>#[^\n]*)"
    r"|(?P<string>\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"\n]*\"|'[^'\n]*')"
    r"|(?P<kw>\b(?:from|import|def|return|class|if|elif|else|for|while|in|not|and|or"
    r"|try|except|finally|with|as|lambda|None|True|False|raise|pass|yield|is)\b)"
    r"|(?P<num>\b\d+(?:\.\d+)?\b)"
    r"|(?P<bi>\b(?:print|len|str|dict|list|tuple|round|int|float|bool|type|range|enumerate)\b)"
)
_CLASS = {"comment": "tk-c", "string": "tk-s", "kw": "tk-k", "num": "tk-n", "bi": "tk-b"}

TAG_CLASS = {
    "Pending": "t-pd",
    "Thought": "t-th",
    "Action": "t-ac",
    "Observation": "t-ob",
    "Running": "t-ru",
    "Final": "t-fi",
    "Error": "t-er",
}


def _hl(line: str) -> str:
    """单行 Python 高亮，返回已转义的 HTML。"""
    buf, pos = [], 0
    for m in _TOKENS.finditer(line):
        buf.append(html.escape(line[pos:m.start()]))
        buf.append(f'<span class="{_CLASS[m.lastgroup]}">{html.escape(m.group())}</span>')
        pos = m.end()
    buf.append(html.escape(line[pos:]))
    return "".join(buf)


def _cell(cell: dict) -> str:
    """一个 [n] 代码格 + 对应输出格。"""
    lines = cell["src"].rstrip("\n").split("\n")
    rows = "".join(
        f'<div class="row"><span class="ln">{i + 1}</span>'
        f'<span class="src">{_hl(line) or "&nbsp;"}</span></div>'
        for i, line in enumerate(lines)
    )
    out = "".join(
        f'<div class="oline"><span class="tag {TAG_CLASS[tag]}">{tag}:</span>'
        f'<span class="otxt">{html.escape(text)}</span></div>'
        for tag, text in cell["entries"]
    )
    pulse = '<span class="pulse"></span>' if cell["status"] == "running" else ""
    return (
        f'<div class="cell"><div class="cidx">[{cell["idx"]}]</div>'
        f'<div class="rows">{rows}</div></div>'
        f'<div class="out">{out}{pulse}</div>'
    )


def _doc(cells: list[dict]) -> str:
    done = sum(1 for c in cells if c["idx"] > 1 and c["status"] in ("done", "failed"))
    body = "".join(_cell(c) for c in cells)
    return f"""
<div id="top"></div>
<div class="doc">
  <div class="doc-bar">
    <span class="doc-back">‹</span>
    <span class="doc-title">多 Agent 协同创作</span>
    <span class="doc-menu">⋯</span>
  </div>
  <div class="sec">
    <span class="chev">‹</span>
    <h2>H（执行情况）</h2>
    <span class="exp">⌄</span>
  </div>
  <div class="meta">Python · LangGraph StateGraph · 5 个 Agent · 已完成 {done}/5</div>
  <div class="body">{body}</div>
</div>
<a class="totop" href="#top">↑ 回到顶部</a>
"""


def _pending_cells() -> list[dict]:
    """页面初始骨架：所有 Agent 等待调度（同时展示 notebook 版式）。"""
    cells = [{
        "idx": 1, "src": SRC_GRAPH, "status": "pending",
        "entries": [("Pending", "等待执行")],
    }]
    for i, (key, name) in enumerate(AGENTS, start=2):
        cells.append({
            "idx": i, "src": SRC[key], "status": "pending",
            "entries": [("Pending", f"{name} 等待调度")],
        })
    return cells


CSS = """
<style>
#MainMenu, header[data-testid="stHeader"], footer {display:none !important;}
.stApp {background:#f4f5f7;}
.block-container {padding-top:1.4rem; padding-bottom:5rem; max-width:880px;}
.stTextInput input {
  border:1px solid #d8dde3 !important; border-radius:8px !important;
  background:#fff !important; font-size:14px; padding:.55rem .8rem !important;
  color:#1f2328 !important; -webkit-text-fill-color:#1f2328 !important;
  caret-color:#1f2328;
}
.stTextInput input::placeholder {
  color:#9aa3ad !important; -webkit-text-fill-color:#9aa3ad !important;
}
.stButton button {height:40px; border-radius:8px; font-size:14px;}
.stButton button[kind="primary"] {background:#0f766e; border:none; color:#fff;}
.doc {background:#fff; border:1px solid #e3e6ea; border-radius:4px;
  box-shadow:0 1px 2px rgba(0,0,0,.04); overflow:hidden;}
.doc-bar {display:flex; align-items:center; padding:14px 18px;
  border-bottom:1px solid #e6e8eb;}
.doc-back {color:#b6bcc5; font-size:15px; width:24px;}
.doc-title {flex:1; text-align:center; font-size:15px; font-weight:600; color:#1f2328;}
.doc-menu {color:#b6bcc5; font-size:18px; letter-spacing:2px; width:24px; text-align:right;}
.sec {display:flex; align-items:center; gap:8px; padding:16px 18px 4px;}
.sec h2 {font-size:19px; font-weight:700; margin:0; color:#1f2328;}
.chev, .exp {color:#9aa3ad; font-size:14px;}
.exp {margin-left:auto;}
.meta {padding:0 18px 10px; color:#98a1ab; font-size:12px;
  border-bottom:1px solid #eef0f2;}
.body {padding:6px 18px 20px;}
.cell {display:flex; margin:14px 0 0; background:#f7f8fa;
  border:1px solid #edeff2; border-radius:6px; overflow:hidden;}
.cidx {flex:0 0 46px; padding:10px 0 0 12px; color:#a7aeb8;
  font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
.rows {flex:1; min-width:0; padding:8px 12px 8px 0; overflow-x:auto;}
.row {display:flex; white-space:pre;
  font:12.5px/1.7 ui-monospace,SFMono-Regular,Menlo,Consolas,"Cascadia Mono",monospace;}
.ln {flex:0 0 28px; text-align:right; padding-right:12px;
  color:#c2c7cf; user-select:none;}
.src {flex:1; color:#24292f;}
.tk-k {color:#0550ae;} .tk-s {color:#0a7d4f;} .tk-c {color:#8b949e; font-style:italic;}
.tk-n {color:#a15b00;} .tk-b {color:#8250df;}
.out {margin:6px 0 0 62px; padding:2px 0 2px 14px; border-left:2px solid #f0f2f5;}
.oline {font:13px/1.75 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  white-space:pre-wrap; word-break:break-word; color:#24292f;}
.tag {font-weight:600; margin-right:6px;}
.t-pd {color:#9aa3ad;} .t-th {color:#0a66c2;} .t-ac {color:#8250df;}
.t-ob {color:#1a7f37;} .t-ru {color:#b26b00;} .t-fi {color:#0f766e;} .t-er {color:#c0392b;}
.pulse {display:inline-block; width:7px; height:7px; border-radius:50%;
  background:#d97706; margin-left:8px; animation:pulse 1.1s infinite;}
@keyframes pulse {0%,100%{opacity:.2;} 50%{opacity:1;}}
.totop {position:fixed; right:26px; bottom:28px; display:inline-flex; align-items:center;
  gap:8px; padding:10px 16px; border-radius:999px; background:#fff;
  border:1px solid #e1e4e8; box-shadow:0 6px 18px rgba(0,0,0,.12);
  color:#3c4149 !important; font-size:13px; text-decoration:none !important; z-index:999;}
@media (max-width:640px) {
  .block-container {padding-left:.75rem; padding-right:.75rem;}
  .cidx {flex-basis:36px;} .out {margin-left:52px;}
}
</style>
"""

st.set_page_config(page_title="More-Agent 执行情况", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

# 输入区（与第一版相同的入口流程）
col_input, col_btn = st.columns([4, 1])
with col_input:
    user_input = st.text_input(
        "主题需求", label_visibility="collapsed",
        placeholder="输入你的主题需求，例：做一个关于秋日森林的宣传内容",
    )
with col_btn:
    run = st.button("开始执行", type="primary", disabled=not user_input)

ph = st.empty()

if not run:
    # 未执行时也渲染完整版式，方便预览样式
    ph.markdown(_doc(_pending_cells()), unsafe_allow_html=True)
else:
    # 结果标签页：先生成 token 并立刻打开页面（此时仍在点击后的手势窗口内，
    # 浏览器更容易放行弹窗），页面处于"生成中"，完成后自动刷新出内容。
    token = result_server.create_result()
    page_url = result_server.result_url(token)
    components.html(
        f"""<script>
        (function () {{
          var url = "{page_url}";
          var w = null;
          try {{ w = window.open(url, "_blank"); }} catch (e) {{}}
          if (!w) {{ try {{ w = window.parent.open(url, "_blank"); }} catch (e) {{}} }}
        }})();
        </script>""",
        height=0,
    )

    cells = _pending_cells()
    # [1] 编排格：图在 import 时已构建完成
    cells[0]["status"] = "done"
    cells[0]["entries"] = [
        ("Thought", "五个 Agent 已就绪，需要先把它们编排成一条可执行的任务流。"),
        ("Action", "build_graph()"),
        ("Observation", "START → planner → writer → {painter ∥ speaker} → aggregator → END"),
        ("Final", "编排完成：串行主线 + 扇出并行 + 屏障汇总。"),
    ]
    ph.markdown(_doc(cells), unsafe_allow_html=True)

    final_state: dict = {}
    for mode, chunk in graph.stream(
        {"user_input": user_input, "task_log": []},
        stream_mode=["updates", "custom"],
    ):
        if mode == "custom":
            # 节点开始执行：Thought + Action
            key = chunk["agent"]
            cell = next(c for c in cells if c["idx"] == CELL_IDX[key])
            cell["status"] = "running"
            cell["entries"] = [
                ("Thought", THOUGHTS[key]),
                ("Running", f"{key}_node(state)"),
            ]
        else:
            # 节点完成：补上 Observation / Error
            for node_name, update in chunk.items():
                final_state.update(update)
                for record in update.get("task_log", []):
                    cell = next(c for c in cells if c["idx"] == CELL_IDX[node_name])
                    if record["status"] == "done":
                        cell["status"] = "done"
                        cell["entries"] = [
                            ("Thought", THOUGHTS[node_name]),
                            ("Action", f"{node_name}_node(state)"),
                            ("Observation", f"{record['summary']}，耗时 {record['elapsed']}s"),
                        ]
                    else:
                        cell["status"] = "failed"
                        cell["entries"] = [
                            ("Thought", THOUGHTS[node_name]),
                            ("Action", f"{node_name}_node(state)"),
                            ("Error", record["output"]),
                        ]
        ph.markdown(_doc(cells), unsafe_allow_html=True)

    # 全部完成后给出 Final 行（对应第一版"流程一致"的收尾）
    # 产物地址：图片是远程 URL，语音是本地文件（转绝对路径便于复制打开）
    image_addr = final_state.get("image_url") or "（无）"
    audio_path = final_state.get("audio_path") or ""
    audio_addr = os.path.abspath(audio_path) if audio_path else "（无）"
    copy_text = final_state.get("copy_text") or ""

    final = next(c for c in cells if c["idx"] == 6)
    final["entries"].append(
        ("Final", f"5 个 Agent 全部完成，任务编排执行结束。主题需求：{user_input}")
    )
    final["entries"].append(("Final", f"文案：{copy_text}"))
    final["entries"].append(("Final", f"图片地址：{image_addr}"))
    final["entries"].append(("Final", f"语音地址：{audio_addr}"))
    ph.markdown(_doc(cells), unsafe_allow_html=True)

    # 发布到结果标签页（页面轮询到 ready 后自动刷新出图文语音）
    result_server.publish_result(token, final_state)
    st.link_button("打开结果页", page_url)
    st.caption("若浏览器拦截了自动弹窗，可点上方按钮手动打开；关闭结果标签页后，内容会自动删除。")
