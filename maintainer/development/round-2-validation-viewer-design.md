# Round 2 — validation_viewer 设计草稿（已被新方向替代）

> **本文件作为历史参考保留。**
>
> 这一版设计是 **dashboard 风格**（6 面板 + game replay 双 tab），后续在与用户的架构讨论中被**"runtime introspection / 飞机黑盒子"风格**替代。新方向的核心诉求是把单次 turn 的"感知 → 决策 → 动作"链路展开，并把跨 turn 演化呈现为可追溯序列；不再走 metrics dashboard 路线。
>
> 实际落地见：
> - `observation_tools/`（顶层独立工具目录）
> - `maintainer/development/v0-progress.md`（V0 完整 closeout）
>
> 旧设计中仍然有用的部分（Crafter 9×7 grid 渲染、life panel、inventory）已记入 V0-g progress 文档的"V1 候选"列表，作为 plugin 形式重新接入。

---

**状态（历史）**：设计草稿。已跨多轮讨论；用户希望实施前再讨论一次。**未经用户明确批准 V1 scope 之前不要开始实施。**

**配套文档**：
- `.claude/plans/federated-snacking-engelbart.md` — 主计划
- 参考项目：`/Users/mojiawen/Documents/codex/crafter_test`
  （尤其是 `data/reports/crafter_call_visual.html` —— 37k 行静态 HTML，展示像素画游戏状态、彩色 local_view 网格、生命面板、物品栏、按步导航）

---

## 1. 为什么需要 viewer

Round 1 + Phase 1 之后，EVA-Crafter 每次运行会产出 6+ 个 JSONL trace 文件，6h+ 长跑下每个文件会积累数千行：

- `events.jsonl` —— startup / shutdown / errors
- `response_history.jsonl` —— 每个 turn 的 selected_action + deltas + observation
- `deliberation_audit.jsonl` —— 每个 turn 的 L3 决策 + drive_broadcast + signal_batch
- `learning_outcomes.jsonl` —— RPE outcomes
- `habit_bias.jsonl` —— 已 crystallize 的 habits
- `semantic_memory.jsonl` —— semantic patterns
- `llm_advisory_audit.jsonl` —— LLM advisory 调用
- `snapshots/profile-*.json` —— 周期性 stability_metrics profile

直接读原始 JSONL 既无法做实时监控也无法做事后回顾。按用户要求，viewer 需要提供：

- **数据分析仪表盘** —— 指标轨迹、分布、相关性
- **游戏化回放** —— 像 crafter_test 那样按步播放 agent 玩 Crafter，看它"在干什么"

---

## 2. 架构

### 位置

**新增顶层目录**：`validation_viewer/`

理由（先前讨论已定）：
- Schema 同步：viewer 读框架产出的 JSONL；同一仓库防止 schema 漂移
- 同仓库先例：`runners/`、`stability_metrics/`、`inheritance_distillation/` 已经是顶层 peer，再加一个完全合理
- 纯读工具：viewer 不 import 也不修改 agent runtime 代码；`eva/` 删掉也不会影响 viewer（除非没数据可读）
- 不需要新框架依赖：stdlib `http.server` 足够

### 后端（Python）

`validation_viewer/server.py` —— stdlib `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`。**不引入** Flask / FastAPI / Tornado。路由：

| Path | 行为 |
|---|---|
| `GET /` | 返回 `static/index.html` |
| `GET /static/<file>` | 返回静态资源（CSS / JS / images） |
| `GET /api/run_info` | 运行元信息（name、start time、runtime_dir、snapshot_dir） |
| `GET /api/snapshots` | 当前所有 snapshot JSON 文件（体积小，全量返回） |
| `GET /api/response_history?after_idx=N` | 索引 N 之后的增量 response_history 条目 |
| `GET /api/deliberation_audit?after_idx=N` | 同上 |
| `GET /api/learning_outcomes?after_idx=N` | 同上 |
| `GET /api/habit_bias?after_idx=N` | 同上 |
| `GET /api/semantic_memory?after_idx=N` | 同上 |
| `GET /api/llm_advisory?after_idx=N` | 同上 |
| `GET /api/events?after_idx=N` | 同上 |
| `GET /api/local_view?turn_idx=N` | 单个 turn 详情：从 `response_history[N]` 取出 `agent_observation` |

用索引分页（而非时间戳）让轮询既便宜又无歧义。

### 前端（vanilla）

`validation_viewer/static/`：
- `index.html` —— 主页，tab 导航，视口容器
- `style.css` —— dark 主题，等宽字体显示数据，彩色网格
- `app.js` —— fetch + 轮询 + 渲染。无框架。约 600 LOC
- `tile_palette.json` —— Crafter tile name → color hex（JS 可消费）

图表：
- 在 canvas 中用极小 stdlib chart 实现
- 或者 CDN 拉一个 Chart.js / uPlot（决定推迟）
- **V1 默认**：手写 SVG 折线图（无 CDN、无额外依赖，每种图表约 50 LOC，完全可控）

轮询：
- 每 5 秒，fetch 各 `?after_idx=N` 端点
- 增量更新图表
- "Live" 指示器在 60 秒无新数据时变黄

入口：

```bash
python -m validation_viewer \
  --runtime-dir validation-runs/crafter-6h/runtime \
  --snapshot-dir validation-runs/crafter-6h/snapshots \
  --port 8080 \
  --host 127.0.0.1
```

---

## 3. 面板设计

### 双 tab UI

两类视图回答不同问题；保留为两个独立 top-level tab 避免认知超载。

```
┌─────────────────────────────────────────────────────────────┐
│  EVA Crafter Validation Viewer  [Run: crafter-6h] [Live ●]  │
├─────────────────────────────────────────────────────────────┤
│  [📊 Data Dashboard] [🎮 Game Replay]                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  (当前 tab 内容)                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tab A —— Data Dashboard

6 个面板，网格布局。每个面板独立（数据源为空时也能渲染空）。

#### A.1 —— Stability Metrics 轨迹
- **来源**：`snapshots/profile-*.json`
- **渲染**：7 条折线图（每个指标一条），共享 x 轴（`elapsed_since_start`）
- 指标：`constraint_violation_rate`、`continuity_preservation_score`、`useful_progress_under_constraint`、`recovery_success_rate`、`mean_time_to_recovery_sec`、`recovery_path_entropy`、`cost_ratio`
- **Live**：新 snapshot 到达时刷新
- **Tripwire 指示**：在阈值线处画红色横条

#### A.2 —— L3 Profile 分布
- **来源**：`deliberation_audit.jsonl` → `release_decision.release_context.candidate_profile`
- **渲染**：
  - Donut chart：`observe_first` / `stabilize_first` / `escalate_first` 占比
  - Stacked area：profile 分布随时间变化（窗口化，~100 条 audit 一窗）

#### A.3 —— Action 分布
- **来源**：`response_history.jsonl` → `selected_action`
- **渲染**：
  - 水平柱状图：action 频率
  - Stacked area 随时间变化（窗口化）
- 高亮新出现的 action（首次出现：`place_table`、`make_wood_pickaxe` 等）

#### A.4 —— Drive level 轨迹
- **来源**：`deliberation_audit.jsonl` → `deliberation_input.drive_broadcast.drive_levels`
- **渲染**：6 条折线图（`metabolic` / `safety` / `recovery` / `acquisition` / `capability` / `exploration`）
- **高亮**：`exploration` drive（最粗线）
- 标注事件：`top_drive` 切换、threat signal

#### A.5 —— Memory & Learning 积累
- **来源**：`habit_bias.jsonl`、`learning_outcomes.jsonl`、`semantic_memory.jsonl`
- **渲染**：阶梯折线，计数随时间增长
- Tooltip：最新 habit_bias 条目的 `situation_key` + `preferred_action`

#### A.6 —— LLM Advisory + Events
- **来源**：`llm_advisory_audit.jsonl`、`events.jsonl`
- **渲染**：滚动尾部（最近 20 条）
- LLM advisory：outcome / error 分布徽章

### Tab B —— Game Replay

单一复合视图，带步进控制。

```
┌──────────────────────────────────────┬────────────────────┐
│  Local View (9×7 彩色网格)            │  Life Panel        │
│  ┌─┬─┬─┬─┬─┬─┬─┬─┬─┐                 │  Health  ████░ 7  │
│  │T│G│G│G│G│G│G│G│G│                 │  Food    ███░░ 5  │
│  ├─┼─┼─┼─┼─┼─┼─┼─┼─┤                 │  Water   ██░░░ 3  │
│  │G│G│G│G│G│G│G│G│G│                 │  Energy  ████░ 7  │
│  ...                                  │                    │
│  │G│G│G│G│@│G│G│G│G│ ← player        │  Inventory         │
│  ...                                  │  wood × 2          │
│  └─┴─┴─┴─┴─┴─┴─┴─┴─┘                 │  stone × 1         │
│                                       │                    │
│  Selected action: move_left           │  Achievements (1)  │
│  L3 profile: observe_first            │  • collect_wood    │
│  Reason: crafter_minimal_selection    │                    │
├───────────────────────────────────────┴────────────────────┤
│  ⏮ ◀ ⏸ ▶ ⏭   Turn 142 / 2814   Speed: 1× 2× 5× 10× max   │
│  ──●────────────────────────────────────────────────────  │
└────────────────────────────────────────────────────────────┘
```

**来源**：`response_history.jsonl` —— 每条记录都含决策时刻的 agent observation。具体来说，`agent_observation` payload 要么内嵌在 response_history 中，要么可以通过 wrapper 的 `_observation_panels` 提取。

**渲染细节**：

- **9×7 彩色网格**：63 个 CSS grid 单元。每个单元按 tile type 着色（在 `tile_palette.json` 中查找）。单元内显示双字母缩写（沿用 crafter_test 模式：tree=Tr、grass=Gr 等）。玩家中心格特殊高亮
- **Life panel**：4 条水平 bar，按阈值着色 绿 / 黄 / 红
- **Inventory**：列出 `{item, count}` 其中 `count > 0`
- **Achievements**：已解锁成就清单，长则滚动
- **Action / profile / reason 文字**：来自 `selected_action`、`candidate_profile`、`selected_action_reason`

**步进控制**：
- ⏮ 首 turn、◀ 上一个、⏸ 暂停、▶ 播放、⏭ 末 turn
- 速度：1×、2×、5×、10×、max
- Timeline scrubber：可点击 / 拖拽跳转到任意 turn

**Live 模式**：当处于最新 turn 时，随新条目到达（通过轮询）自动前进。

### 跨 tab 联动（V2 nice-to-have）

- Tab A 事件日志条目点击 → 跳转到 Tab B 对应 turn
- Tab A 图表点击 → 跳转到该 turn
- 推迟到 V2

---

## 4. 像素渲染问题（V1 vs V2）

**V1（推荐）**：只做 symbolic grid
- `response_history.jsonl` 已经含 `agent_observation.visible.local_view.cells`
- 无需 runtime 改动捕获数据
- 颜色来自静态 palette
- 视觉效果类似 crafter_test 的 "3. agent 实际收到的 local_view.cells" 面板

**V2（推迟）**：像素渲染
- 需要捕获 Crafter env 每一步的原始 render 输出
- 需要在 `scenarios/crafter/wrapper/env_wrapper.py` 加 hook，把每步 64×64 PNG 存盘（或压缩为视频）
- 文件大小：64×64×3 bytes × ~3000 turns × 6h，量级可控
- 如果用户觉得 symbolic grid 不够用，才考虑

决定推迟到 V1 demo 之后再定。

---

## 5. 实施切片

如果用户批准 V1 scope：

### V1-a —— 后端骨架 + run_info + snapshots 端点
- `server.py` 配 stdlib HTTP server
- 2 个端点：`/api/run_info`、`/api/snapshots`
- 从 `static/` 提供静态文件
- 入口 `python -m validation_viewer ...`
- 测试：端到端 smoke（GET /、GET /api/run_info）

### V1-b —— 增量端点
- 全部 7 个 `?after_idx=N` 端点
- 安全 tail-read JSONL（处理最后一行可能尚未写完）
- 测试：文件缺失返回空；超大 `after_idx` 返回空

### V1-c —— Tab A 后端就绪 + 前端骨架
- `index.html` 带两个 tab 导航
- 空面板占位
- `app.js` 轮询骨架
- 测试：前端可加载，能发起初始 fetch

### V1-d —— Tab A 各面板渲染
- 实现 6 个面板
- 手写 SVG 图表
- 测试：合成数据下每个面板能正确渲染

### V1-e —— Tab B 游戏回放
- 9×7 彩色网格 + life panel + inventory + achievements
- 步进控制 + timeline scrubber
- 测试：步进导航、play/pause、scrubber

### V1-f —— 收尾 + 文档
- `validation_viewer/README.md`
- 更新 `.claude/plans/federated-snacking-engelbart.md`，标记 Phase 2 完成

**工作量预估**：1-2 天。主要时间花在 V1-d（面板图表）和 V1-e（游戏回放）。

---

## 6. 实施前需要讨论的开放设计问题

用户指出这些条目需要在实施前再讨论一次。新会话开始时清晰列出，避免歧义。

### Q1 —— 像素渲染走 V1 还是 V2？
- 当前提案：V1 只做 symbolic grid（不改 runtime）。V2 像素留到后续
- 备选：从一开始就做像素，接受 runtime hook 的额外开销

### Q2 —— Live 轮询间隔？
- 提案：5 秒。够实时感、又便宜
- 备选：长跑实时监控时 1-2 秒

### Q3 —— Tile palette 来源？
- Crafter 约 22 种 tile。需要 `name → color hex` 映射
- 方案 A：预先放在 `tile_palette.json`（参考 crafter_test 选色）
- 方案 B：从 Crafter env 实际纹理的平均色提取（需要 runtime hook，更准）
- 推荐：V1 走 A

### Q4 —— Multi-run 支持？
- V1 提案：一次一个 run（通过 CLI 参数指定）
- 备选：扫描父目录、列出可用 run、让用户在 UI 切换
- 推荐：V1 single-run，V2 multi-run

### Q5 —— 鉴权？
- V1 提案：只绑定 `127.0.0.1`（localhost），无鉴权
- 顾虑：validation run 中 advisory 可能 log 了 key（不太可能，但值得检查）
- 推荐：V1 localhost-only

### Q6 —— 用图表库还是手写？
- V1 提案：手写 SVG（无 CDN、无依赖）
- 备选：通过 CDN 拉 Chart.js 或 uPlot
- 推荐：V1 手写，如果图表能力限制再上 CDN

### Q7 —— 游戏回放 timeline scrubber 技术方案？
- 需要把所有 turn 载入内存供 scrubber 用
- 6h × ~10 turn/min ≈ 3600 turn × ~2KB JSON ≈ 7MB / run
- 浏览器内存可接受
- 24h：约 28MB，仍 OK。7 天：200MB，可能需要 windowing
- V1 假设：全量加载，必要时再 windowing

---

## 7. 本切片**不**做的事

- 不改 `eva/`（不做框架改动）
- 不改 scenario（不做场景改动）
- 不改 trace 文件 schema
- 不引入新框架依赖（仅 stdlib）
- 不打造长期生产仪表盘（只是分析 viewer）
- 不实现跨 run 对比（V2 推迟）
- 不实现像素原始 observation 捕获（V2 推迟）

---

## 8. 边界 / 不变量

- 所有框架 runtime 不变量不动
- Linux + Crafter 场景行为不动
- Viewer 只读，从不写（不会污染 runtime 产物）
- 所有现有测试通过
- 单进程 viewer 不与 runtime 抢资源（独立进程、独立端口）

---

## 9. 架构师 gate

- **G1**（实施前）：用户批准 V1 scope，包含 Q1-Q7 的取舍。**这是当前 gate。在用户签字前停在这里。**
- **G2**（V1-c 之后）：前端骨架能加载，基本轮询循环能跑。在加面板前先演示
- **G3**（V1-e 之后）：完整 V1 用真实 run 数据验证
- **G4**（收尾）：文档 + progress + readme

---

## 10. 参考

- crafter_test 参考 HTML（色板、网格、生命面板布局）：
  `/Users/mojiawen/Documents/codex/crafter_test/data/reports/crafter_call_visual.html`
- crafter_test 源码（semantic local view 结构）：
  `/Users/mojiawen/Documents/codex/crafter_test/src/crafter_test/wrapper/symbolic_observation.py`
- 当前 agent_observation 来源：`scenarios/crafter/wrapper/observation.py`
  + `scenarios/crafter/wrapper/semantic_local_view.py`
- 当前 response_history schema：见
  `scenarios/crafter/actions/compatibility.py:_build_execution_payload`
- 当前 snapshot schema：`runners/longrun_validation.build_longrun_validation_hook`
