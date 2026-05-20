# observation_tools 视觉迭代开发指引

> 这是 **EVA 可视化（黑盒子查看器）独立工作流** 的入口与章程文档。
> 视觉开发与 EVA 主线（`eva/` / `scenarios/` 的能力开发、Crafter 长跑）
> **拆分为两条并行工作流**，各自在独立 worktree + 独立会话推进。
>
> **新会话冷启动只需读这一份文档** 即可接上：它包含开发方式、修改边界、
> 设计理念、当前现状、待办 backlog。

---

## 0. 这份文档怎么用（开发方式）

视觉线的开发方式**有别于 EVA 主线**。主线遵循严格的 intake-first 纪律
（先写 `maintainer/development/current-intake.md`、freeze tests、sync docs）；
视觉线是辅助工具迭代，走**轻量高频迭代**节奏：

1. **不写主线 intake**。视觉线的需求 / 设计 / 进展全部记在本目录
   （`observation_tools/dev/`）内，不写进 `maintainer/development/`。
2. **迭代循环是"改 → 启动 → 截图 → 看 → 再改"**。可视化是高度视觉化的工作，
   靠看真实渲染效果驱动，不靠纯逻辑推导。
3. **每个有意义的小切片自己 commit**。提交信息用中文，说明改了什么视觉/功能。
4. **测试放 `tests/observation_tools/`**，纯逻辑（extractor / chain_builder /
   trace_reader）要有单元测试；纯渲染（CSS / 布局）靠截图验证。
5. **完成一个迭代批次后**，更新本文档的"当前现状"和"backlog"两节，让下一会话
   能接上。

### 与主线的契约边界（重要）

视觉线与主线**只通过 trace 文件解耦通信**：

```
主线：跑 EVA（Crafter / Linux）→ 写 validation-runs/<run>/runtime/*.jsonl
视觉：viewer --runtime-dir <那个 runtime 目录> → 纯读、渲染
```

- **trace schema 归主线 owns**。viewer 只读、不改 schema。若主线改了 trace 输出
  格式，会在主线侧通知；视觉线被动跟进。当前 schema 已稳定。
- **viewer 能实时读主线长跑数据**：用绝对路径 `--runtime-dir` 指向主线 worktree
  的 `validation-runs/<run>/runtime/`，主线长跑写、视觉会话读，互不干扰。
- **跨线任务**：见 §1 "唯一例外"。

---

## 1. 修改边界（硬约束）

### 允许修改

- `observation_tools/**`（全部：core / plugins / static / dev 文档）
- `tests/observation_tools/**`

### 禁止修改

- `eva/**`（kernel / L1 / L2 / L3 / anchor / mediator —— **主逻辑，绝不碰**）
- `scenarios/**`（Crafter / Linux 场景代码）
- `runners/**`、`stability_metrics/**`、`inheritance_distillation/**`、
  `inheritance_distillation/**`
- `maintainer/development/**`（主线的需求 / intake / progress 文档）
- 任何 trace schema（由主线产出，viewer 只读）

> **判定原则**：viewer 是纯读工具。`eva/` 整个删掉，viewer 仍能编译运行
> （只是没数据可读）。任何让 viewer 依赖 `eva/` 代码的改动都越界了。

### 唯一例外（跨线任务，视觉线不自己做）

**9×7 local_view 彩色格子**需要主线在 `scenarios/crafter/wrapper/` 增加
observation 持久化 hook（当前 trace 不含 agent observation 的 grid 数据）。

- 这个 hook 由**主线**实现（碰 runtime 代码）。
- 视觉线**等主线产出 grid 数据后**再做渲染消费，不自己改 runtime。

---

## 2. 文档存放约定

视觉线所有需求 / 设计 / 进展文档**集中在 `observation_tools/dev/`**：

| 文件 | 角色 |
|---|---|
| `observation_tools/dev/dev-guide.md` | **本文件** —— 入口 + 章程 + 现状 + backlog |
| `observation_tools/dev/<feature>.md`（按需新增） | 单个较大特性的设计草稿 |

约定：

- **不写进 `maintainer/development/`**（那是 EVA 主线的需求空间，避免混淆）。
- 视觉线文档随 `observation_tools/` 代码一起 git 版本化（不像 `maintainer/`
  是 gitignored 本地文档）。
- 历史参考：`maintainer/development/v0-progress.md` / `v1-progress.md` 是主线侧
  对视觉线 V0 / V1 产出的 closeout 记录（验收快照），可读但不在此继续维护；
  视觉线的活跃记录以本文件为准。

---

## 3. 背景与设计理念（讨论关键信息）

### 3.1 EVA 是持续运行体，不是任务型 agent

EVA 没有任务型 agent 那种明确的"会话 / 请求 / 返回"边界。它是一个
**持续运行的存在体**：heartbeat 驱动的生命节律，面对环境（场景）不断做出反应。
它的行为记忆按时间顺序归档。

### 3.2 核心比喻：飞机黑盒子

可视化的本职 = **黑盒子**。EVA 面对环境做出的每一次反应（不管快路径 reflex
还是慢路径 deliberation）都应该**可追溯、可审查**。可视化要把 EVA 核心的
**感知 → 决策 → 动作** 链条串起来。

### 3.3 风格：runtime introspection，不是 dashboard

| | dashboard 风格（**不是我们要的**） | runtime introspection（**我们要的**） |
|---|---|---|
| 代表 | LangSmith / Grafana / Phoenix | 黑盒子 / 链路展开 |
| 答的问题 | "系统健康吗" | "机制怎么运作的、为什么这样选" |
| 形态 | 指标卡片 / 聚合图表 | 单 turn 机制全展开 + 跨 turn 机制演化 |

明确**不做**的方向：
- 不是运行时管理后台（OpenClaw / AutoGen Studio 那种多 agent 编排 / 干预）—— EVA
  是单 agent 研究项目，不需要"管理"层
- 不是 LLM trace observability（LangSmith）—— EVA 不是 LLM-centric，LLM 只是
  advisory 旁路
- 不是时序指标聚合（Grafana）—— EVA 绝大部分数据不是时序型

### 3.4 核心诉求表述

> 在任意时间点，把 EVA 的内部机制（heartbeat / sensing / drive 广播 / advisory /
> candidate / anchor restriction / mediator 释放 / outcome）实际发生的过程以可读
> 方式呈现出来，让架构师直接看到"机制如何运作 + 场景如何具体填充机制"。

- **单 turn 全展开**（核心）：signal_batch → drive_broadcast →
  working_memory_context + candidate_assessments → mediator release_decision →
  selected_action → outcome
- **跨 turn 演化**（辅助）：同一段链的历史趋势

### 3.5 归属架构：core（通用）+ plugins（场景特定）

任何 EVA 场景都有约 70-80% 的共性观察需求（lifecycle / drive / L3 / mediator /
advisory / memory），20-30% 是场景特定（Crafter 的生命体征 / 库存 / 视野；Linux
的 command output / disk / process）。

```
observation_tools/                 (顶层独立工具，与 eva / scenarios / runners 平级)
├── core/                          (跨场景通用展示，约 70-80%)
│   ├── trace_reader.py            读 JSONL（容错：缺文件 / 空行 / 末行未完整）
│   ├── chain_builder.py           按 turn 顺序对齐多文件 → ChainView
│   └── static/                    前端 (index.html / style.css / app.js)
└── plugins/                       (场景特定，约 20-30%)
    ├── __init__.py                apply_plugins_to_chain() hook
    └── crafter/                   Crafter extractor（注入 chain["crafter"]）
```

- 主体是 **EVA 工具**（core），场景通过 **plugin** 接入。
- 加新场景 = 写一个 plugin extractor + 前端 renderSection，core 不变。

---

## 4. 当前现状（V0 + V1 已完成）

### V0 — 黑盒子查看器（核心链路）

- **后端**：
  - `core/trace_reader.py` —— `read_jsonl` / `read_jsonl_count`，容错读取
  - `core/chain_builder.py` —— `ChainView` dataclass + `build_chains` +
    `build_timeline_summary`，按 `deliberation_audit.jsonl` 顺序索引为 turn_idx，
    其他文件按序对齐，缺失降级为 None
  - `server.py` —— stdlib `http.server.ThreadingHTTPServer`，端点：
    `GET /`、`/static/<file>`、`/api/run_info`、`/api/turns`、`/api/turn/<n>`、
    `/api/timeline`
- **前端**（`core/static/`，vanilla JS，无 CDN）：
  - 顶部状态条（run 名 / 当前 turn / 生命态 / turns 总数 / Live 指示器）
  - 顶部时间轴 strip（life_state segments + drive_levels 折线，手写 SVG）
  - 左侧 turn 列表（可滚动 / 筛选 / 点击跳转）
  - 右侧链路详情（L1 → L2 → L3 → advisory → 动作 → outcome 各段可折叠）
- **入口**：`python -m observation_tools --runtime-dir <path> --port <port>`

### V1 — Crafter plugin（场景特定）

- **后端**：`plugins/crafter/extractor.py` 的 `extract_crafter_view(deliberation,
  response)` 从 `signal_batch.payload.dimensions` 提取场景数据：
  - `vitals`（health / food / water / energy / threat_count + 3 个 status）
  - `inventory`（items / tools / available_tools / scarce_resources）
  - `local_view`（threat / resource / utility totals + capability_gap）
  - `rate_context`（health / threat 变化方向）
  - `deltas`（achievement / life / inventory delta + visible_threat_count）
  - `statuses`（8 个 dimension status 一览）
  - `plugins/__init__.py` 的 `apply_plugins_to_chain()` 在 `ChainView.to_dict()`
    时注入 `chain["crafter"]`
- **前端**：`app.js` 的 `renderCrafterSection(crafter)`（生命 bar / 库存网格 /
  视野感知表 / deltas / 维度状态徽章），渲染在链路详情**最前**（场景观察先于
  框架机制）；`style.css` 对应样式
- **测试**：`tests/observation_tools/test_crafter_extractor.py`（12 个）

### 数据 schema 关键点（已确认）

- `deliberation_audit.jsonl` 是链路主干：含 `deliberation_input.signal_batch`
  （L1）、`.drive_broadcast`（L2）、`.working_memory_context`（L3）、`candidates`
  + `assessments`、`release_decision`（mediator）
- `response_history.jsonl` 含动作执行结果（`selected_action` / `pressure_outcome`
  / `achievement_delta` / `inventory_delta` / `life_delta` / `visible_threat_count`）
- Crafter 场景数据在 `signal_batch.signals[class=status].payload.dimensions`：
  `avatar_safety` / `avatar_metabolic` / `avatar_recovery` / `inventory_capability`
  / `inventory_acquisition` / `local_view_threat` / `local_view_resource` /
  `local_view_utility`
- **trace 不含 9×7 grid**：EVA runtime 当前没把 agent observation 持久化（仅
  deliberation 内部使用）。这是 9×7 grid 成为跨线任务的原因（见 §1）。
- 末位 off-by-one 常见：`deliberation_audit` 比 `response_history` 多 1 条
  （末次决策完成但 response 未落盘就 shutdown）。chain_builder 容忍此情况。

### 启动 / 验证

```bash
# 启动（端口避开常用端口，如 8080/3000/5000，用 28391 等）
python -m observation_tools \
  --runtime-dir validation-runs/phase1.7-live-smoke/runtime \
  --port 28391
# 浏览器打开 http://127.0.0.1:28391
```

截图验证手段（按可用性优先级）：
1. **Claude Preview MCP**（`.claude/launch.json` 已配 `observation-viewer`）—— 注意
   spawn cwd 受 sandbox 限制，launch.json 用 `python -c` 内联 `os.chdir('/tmp')` +
   `sys.path.insert` 绕开
2. **computer-use MCP**：`request_access(["Google Chrome"])` → `open -a "Google
   Chrome" <url>` → `screenshot`。Chrome 是 **read tier**（只能截图，不能点击 /
   scroll / 输入）。要看下方内容靠调整默认渲染顺序或默认选中的 turn
3. 纯逻辑：`curl /api/turn/<n>` 看 chain dict + 单元测试

> read tier 的限制意味着：**无法在浏览器里点击/滚动**。验证某个 section 渲染时，
> 让它默认出现在视口顶部（如 V1 把 Crafter section 排在链路最前 + 默认选倒数第 2
> 个 turn）。

---

## 5. V2+ Backlog（候选，按"对理解 EVA 运作贡献"排序）

> 优先级会随真实长跑数据反馈调整。等基于一个具体长跑跑起来再定最终顺序。

1. **整体视觉优化**（用户已明确点名"视觉效果不好"）：
   - 生命 bar 对比度低（绿色 fill 在深色背景几乎看不见）
   - 顶部时间轴 drive 折线对比度低、缺 Y 轴刻度
   - 整体信息密度可提升、视觉层次不足
   - turn 列表 life_state 徽章不显眼
2. **9×7 local_view 彩色格子**（跨线，依赖主线产出 observation 数据）：让"agent
   看到什么"具象化
3. **events.jsonl 集成时间轴**：tick / turn / distress / life_state_changed 标记
4. **achievement 解锁标记**：哪些 turn 解锁成就，时间轴点亮
5. **跨 turn 对比视图**：选两个 turn 并排展开链路
6. **跨 turn 趋势页**：原 dashboard 6 面板里真正"必看"的部分（等长跑数据定）
7. **Linux runtime plugin**：第二个场景特定渲染，验证 plugin 架构通用性
8. **多 run 切换**：UI 下拉切换不同 runtime_dir
9. **Game replay 步进控制**：◀ ▶ ⏮ ⏭ + 速度 + scrubber（场景数据更丰富后再做）

---

## 6. 每次迭代结束的收尾清单

- [ ] 新增 / 改动逻辑有 `tests/observation_tools/` 单元测试
- [ ] 截图验证视觉改动符合预期
- [ ] 更新本文件 §4（现状）和 §5（backlog）
- [ ] commit（中文信息，说明视觉 / 功能改了什么）
- [ ] 若 viewer 后台进程还在跑，提醒用户或自行 kill
