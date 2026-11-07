# More-Agent：多 Agent 协同内容创作流水线

基于 **LangGraph** 的多 Agent 协同项目：输入一句话主题，系统自动完成
「主题规划 → 文案撰写 → 文生图 → 语音合成 → 汇总输出」，
每个 Agent 的工作状态与执行过程实时可见。

## 功能特性（与作业要求对应）

| 作业要求 | 实现方式 |
|---|---|
| 基于 LangGraph 多 Agent 协同 | 5 个独立 Agent 节点 + `StateGraph` 编排，共享 `AgentState` |
| 文生图 Agent | `agents/painter.py`，智谱 CogView |
| 文生语音 Agent | `agents/speaker.py`，edge-tts |
| 根据用户输入生成主题 | `agents/planner.py` + `agents/writer.py`（DeepSeek） |
| 任务编排 | `graph.py`：串行主线 + writer 后扇出并行 + barrier 汇总 |
| 工作状态/过程可见 | `task_log` 状态记录 + `stream(custom/updates)` 实时事件 + 前端状态卡片 |

## 架构

```
用户输入 -> planner(主题规划) -> writer(文案) -+-> painter(文生图) -+
                                              +-> speaker(语音)   +-> aggregator(汇总) -> END
```

- `writer` 之后**扇出（fan-out）**：文生图与语音合成互不依赖，并行执行
- `aggregator` 有两条入边，形成**屏障（barrier）**：两个分支都完成才汇总
- 共享状态 `AgentState`（见 [state.py](state.py)）：`task_log` 用 reducer 合并，记录每个 Agent 的状态/耗时/产出摘要
- 状态可见性：节点内 `StreamWriter` 推送"开始执行"（custom 流），节点返回产生"完成"（updates 流），前端据此实时刷新卡片

## 目录结构

```
├── app.py            # Streamlit 入口：输入 + 实时状态面板 + 产物展示
├── graph.py          # StateGraph 编排（fan-out 并行 + barrier 汇总）
├── state.py          # AgentState / TaskRecord 定义
├── config.py         # .env 配置读取；缺 key 自动进入 mock 模式
├── agents/           # 五个 Agent 节点
│   ├── planner.py        # 主题规划（DeepSeek）
│   ├── writer.py         # 文案生成（DeepSeek）
│   ├── painter.py        # 文生图（智谱 CogView）
│   ├── speaker.py        # 语音合成（edge-tts）
│   └── aggregator.py     # 汇总
└── tools/            # 外部能力封装（换厂商只改 .env，业务不动）
    ├── llm.py            # DeepSeek，OpenAI 兼容
    ├── image_api.py      # 智谱 bigmodel images API
    └── tts_api.py        # edge-tts，免费无需 key，带重试
```

## 快速开始

### 首次安装（只做一次）

```powershell
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env            # 填入你的 key（也可不填，先跑 mock）
```

### 启动方式（每次使用）

方式一（推荐，免激活环境）：

```powershell
.venv\Scripts\streamlit.exe run app.py
```

方式二（先激活虚拟环境）：

```powershell
.venv\Scripts\activate
streamlit run app.py
```

启动后浏览器打开 http://localhost:8501 ，输入主题，点击「开始创作」。
停止服务：在终端按 `Ctrl + C`。

> 首次运行 Streamlit 会提示输入邮箱（Welcome to Streamlit），**直接回车跳过**即可。

未配置任何 key 时为 **mock 模式**：完整跑通编排与状态展示，但不产出真实内容。

## API 配置（.env）

| 用途 | 平台 | 配置项 | 费用 |
|---|---|---|---|
| 主题规划 / 文案 | DeepSeek | `DEEPSEEK_API_KEY` | 极低 |
| 文生图 | 智谱 bigmodel | `IMAGE_API_KEY`，模型 `cogview-3-flash` | 免费 |
| 语音合成 | edge-tts | 无需 key，仅配 `TTS_VOICE` 音色 | 免费 |

## 常见问题

- **语音合成偶发失败**：edge-tts 走公共服务，网络抖动时自动重试 3 次（见 `tools/tts_api.py`）。
- **想换模型/厂商**：三个接口都是 OpenAI 兼容或独立封装，改 `.env` 里的 `BASE_URL` / `MODEL` 即可，业务代码不用动。

## 作者

黄宇鑫 20214225038
