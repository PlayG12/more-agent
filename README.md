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
├── app.py            # 第一版入口：状态卡片 + 产物展示
├── start.py          # 一键启动两版网页（自动打开 8501 / 8502）
├── app_v2.py         # 第二版入口：notebook 风格「执行情况」页（不影响第一版）
├── result_server.py  # 第二版的结果标签页服务（端口 8800，关闭标签页自动清理）
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

## 两个前端页面

| 页面 | 文件 | 呈现方式 |
|---|---|---|
| 第一版 | `app.py` | 每个 Agent 一张状态卡片（等待中/执行中/完成），底部展示文案、配图、语音 |
| 第二版 | `app_v2.py` | notebook 讲义风格：`[n]` 代码格展示 Agent 真实源码，输出格展示 Thought / Action / Observation / Final，执行中实时刷新；生成完成后自动打开结果标签页，关闭标签页后内容自动删除 |

两版共用同一张 `graph` 与同一套 Agent，仅呈现方式不同；第二版为独立入口，不修改第一版。

第二版的结果标签页由 [result_server.py](result_server.py) 提供（本地端口 8800）：执行开始时先打开「生成中」页面，完成后自动刷新出文案、配图、语音；关闭该标签页会通知服务清理页面内容与音频副本（刷新页面不会误删）。

## 快速开始

### 首次安装（只做一次）

```powershell
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env            # 填入你的 key（也可不填，先跑 mock）
```

### 启动方式（每次使用，一条命令启动两版）

在项目根目录执行：

```powershell
.venv\Scripts\python.exe start.py
```

脚本会同时启动两版网页，并约 8 秒后自动在浏览器打开两个标签页：

- 第一版：http://localhost:8501 （输入主题，点击「开始创作」）
- 第二版：http://localhost:8502 （输入主题，点击「开始执行」）

停止全部服务：在该终端按 `Ctrl + C`。

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
- **第二版没有自动弹出结果页**：浏览器拦截了弹窗，点页面底部的「打开结果页」按钮即可；也可在浏览器地址栏允许本站弹窗。

## 作者

黄宇鑫 20214225038
