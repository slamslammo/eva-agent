# Phase 2 V0 — observation_tools 黑盒子查看器 — 进展记录

**状态**：V0 全部子切片落地，已可在本地运行 viewer
**Intake**：`maintainer/development/current-intake.md`
**Smoke 数据**：`validation-runs/phase1.7-live-smoke/runtime/`（211 turns）

---

## 摘要

按用户在架构讨论中确立的核心定位：**EVA 是持续运行体，需要一个"飞机黑盒子"式的工具把每次 turn 的"感知 → 决策 → 动作"链路展开成可读视图**。V0 实现了最小可用版本：本地浏览器查看 EVA 运行时输出的 trace JSONL，按 turn 展开链路，支持跨 turn drive 折线与生命态变化追溯。

**不属于 EVA 核心理论与工程架构**，作为独立辅助工具存在。删除 `observation_tools/` 不影响任何主线代码。

---

## 落地的子切片

### V0-a — 目录骨架 + intake

- 新增顶层目录 `observation_tools/`（与 `eva/` / `scenarios/` / `runners/` 等平级）
- 子结构：`core/`（跨场景通用展示）+ `plugins/`（场景特定渲染，V0 暂不实现）+ `core/static/`（前端文件）
- 写 intake 到 `current-intake.md` 覆盖 1.7 closeout

### V0-b — `trace_reader` + `chain_builder`

模块：
- `observation_tools/core/trace_reader.py`（~80 LOC）—— 容错读取 JSONL（缺文件 / 末行未完整 / 非法 JSON / 非 dict 顶层）
- `observation_tools/core/chain_builder.py`（~150 LOC）—— `ChainView` dataclass + `build_chains` / `build_timeline_summary` / `runtime_counts`

测试：`tests/observation_tools/test_trace_reader.py`（8 测试）+ `tests/observation_tools/test_chain_builder.py`（11 测试）= **19 测试通过**

### V0-c — HTTP server + API 端点

模块：
- `observation_tools/server.py`（~180 LOC）—— stdlib `ThreadingHTTPServer` + `BaseHTTPRequestHandler`，无第三方依赖
- `observation_tools/__main__.py`（~50 LOC）—— `python -m observation_tools` 入口

端点：
- `GET /`、`GET /static/<file>`
- `GET /api/run_info` / `/api/turns` / `/api/turn/<idx>` / `/api/timeline`
- 安全：`127.0.0.1` 默认绑定，`/static/` 防目录遍历，500 兜底所有未捕获异常

测试：`tests/observation_tools/test_server.py`（12 测试）= **12 测试通过**

### V0-d — 前端骨架 + turn 列表 + 轮询

文件：
- `observation_tools/core/static/index.html`（~50 LOC）—— 顶部 bar + timeline strip + 左右双栏布局
- `observation_tools/core/static/style.css`（~190 LOC）—— GitHub dark 配色，纯 CSS，无 Tailwind / 其他框架
- `observation_tools/core/static/app.js`（V0-d 时 ~240 LOC）—— vanilla JS，无 CDN

特性：
- 5 秒轮询 `/api/run_info`；counts 变化时增量重拉 `/api/turns` + `/api/timeline`
- Turn 列表倒序（最新在顶）+ 按 life_state / advisory outcome 筛选
- Live 指示器：连接 / 等待新数据 / 加载失败 三态

### V0-e — 链路详情视图

`app.js` 增加 6 个 section renderer（~270 LOC 新增）：

| Section | 展示内容 |
|---|---|
| L1 感知 signal_batch | 按 class (threat / pressure / status / background) 分组计数 + 列表 |
| L2 drive_broadcast | top_drive 高亮 + 全部 drive 的 level / trend 表 |
| L3 deliberation | Working Memory 摘要（situation_key、bias / habit / semantic 计数、advisory_context）+ Candidates / Assessments + Mediator release_decision |
| LLM Advisory | provider / model / outcome / fallback 详情；未启用时占位提示 |
| 动作执行 | selected_action / posture / reason、filter 结果、execution_status、pressure_outcome、场景 deltas |
| Outcome / Memory | learning_outcome（含 outcome_vector）+ habit_bias 新增项 |

每段可折叠、附带原始 JSON 展开（`<details>` 折叠）。

### V0-f — 顶部迷你时间轴 + drive 折线

`app.js` 增加 SVG 渲染（~130 LOC 新增）：

- 自适应宽度，高度固定 80px
- 上部 12px：life_state 变化标记带（按相邻段着色，hover 显示 turn 范围）
- 下部 64px：6 条 drive 折线（手挑配色：metabolic 红 / safety 橙 / recovery 绿 / acquisition 蓝 / capability 紫 / exploration 粉橙）
- 0 / 0.5 / 1 水平虚线参考
- 选中 turn 蓝色竖线指示
- **点击跳转**：按 X 坐标推算 turn idx，选中并滚动详情区

### V0-g — Smoke + closeout + commit（本切片）

Smoke 命令：

```bash
python -m observation_tools \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --port 8767
```

API smoke 通过：
- `/api/run_info`：211 deliberations / 211 advisory / 210 response（off-by-one 正常）
- `/api/turn/100`：5 signals、top_drive=acquisition、release_outcome=compatibility_release、selected_action=sleep、advisory_attached（deepseek-v4-flash）、outcome_delta=0.4
- `/api/timeline`：211 turns、6 drives 全有数据、life_state ∈ {STABLE, UNKNOWN}、advisory_outcomes 全部 advisory_attached
- 静态文件全部 200 OK

---

## 改动文件

| 文件 | 改动 |
|---|---|
| `observation_tools/__init__.py` | 新增（顶层模块 docstring） |
| `observation_tools/__main__.py` | 新增（~50 LOC，CLI 入口） |
| `observation_tools/server.py` | 新增（~180 LOC，HTTP server + 路由） |
| `observation_tools/core/__init__.py` | 新增 |
| `observation_tools/core/trace_reader.py` | 新增（~80 LOC） |
| `observation_tools/core/chain_builder.py` | 新增（~150 LOC） |
| `observation_tools/core/static/index.html` | 新增（~50 LOC） |
| `observation_tools/core/static/style.css` | 新增（~190 LOC） |
| `observation_tools/core/static/app.js` | 新增（~740 LOC） |
| `observation_tools/plugins/__init__.py` | 新增（V1+ plugin 占位） |
| `tests/observation_tools/__init__.py` | 新增 |
| `tests/observation_tools/test_trace_reader.py` | 新增（8 测试） |
| `tests/observation_tools/test_chain_builder.py` | 新增（11 测试） |
| `tests/observation_tools/test_server.py` | 新增（12 测试） |
| `docs/implementation-tracking.md` | 新增 observation_tools 行 |
| `docs/implementation-tracking-zh.md` | 中文镜像 |
| `maintainer/development/round-2-validation-viewer-design.md` | 头部加 SUPERSEDED 备注，旧 dashboard 设计仅作历史参考 |
| `maintainer/development/v0-progress.md` | 本文件 |
| `maintainer/development/current-intake.md` | closeout |

---

## 回归

| 阶段 | 测试总数 | 通过 | 失败 | 备注 |
|---|---|---|---|---|
| V0 之前 | 415 | 414 | 1（pre-existing） | Phase 1.7 baseline |
| V0-b | 415 + 19 = 434 | 433 | 1（pre-existing） | trace_reader + chain_builder |
| V0-c | 434 + 12 = 446 | 445 | 1（pre-existing） | server 集成测试 |
| V0-d / e / f / g | 446 | 445 | 1（pre-existing） | 纯前端 / docs 改动 |

`l2_drive.test_drive.test_update_drive_state_accumulates_over_multiple_patrols` 是 `main` 上 pre-existing 失败，与 V0 无关。

---

## 接下来

V0 是 EVA 黑盒子查看器的最小可用版本。V0 跑过几次真实长跑（Phase 3）之后，会暴露出哪些需要补强 / 哪些不实用，再决定 V1 方向。

候选 V1 工作（按可能优先级，待长跑反馈后定）：

1. **Crafter plugin**（`observation_tools/plugins/crafter/`）—— 9×7 colored grid + 生命条 + inventory + achievements；挂在动作执行 section 的"场景观察"那一格
2. **跨 turn 趋势页**—— 类似 dashboard 的指标聚合（L3 profile 分布、action 多样性、habit 积累速率等），不再做完整 6 面板，只放真实运行中"想看"的 2-3 个
3. **Events.jsonl 集成**—— 把 1272 条 events 关联到对应 turn，展开"运行时事件链"（startup / lifestate_changed / patrol_queued 等）
4. **Live 长跑场景优化**—— 增量轮询而非全量重拉、虚拟滚动 turn 列表（万 turn 量级时需要）

无论哪个 V1，都基于"V0 已经跑过几次真实长跑、清楚痛点"的前提。
