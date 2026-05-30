# Current Intake

## Active Item

`framework-scenario-timing-and-advisor-coupling`（APPROVED → B-claude-2）

让场景能**声明**自己的外部生命节律（external-life timing），框架在 CLI 未显式指定时回退到该声明；
同时收口 advisor adapter 的默认耦合（observation 2）。当前 `ExternalLifeConfig` 的 calendar tempo
只能由 CLI / 框架默认硬编码，`RuntimeScenarioBundle` 没有 timing 声明位，导致场景（如 Crafter 的
sec 级节律）无法把"我该多快巡查"写进 bundle，只能在每个 runner / 测试里重复构造 `ExternalLifeConfig`。

Coordination owner: `B-claude-2`
Branch: `framework-scenario-timing-and-advisor-coupling`
（worktree `/Users/mojiawen/Documents/claude_projects/eva-agent-fst`，base 6e26380）

## Change Intake（6 点）

1. **层**：以 **framework** 为主 —— `eva/scenario_bundle.py`（scenario seam）+ `eva/kernel/config.py` /
   `eva/kernel/main.py`（config 接线）；附带 `scenarios/crafter`（场景声明）与 `eva/l3_deliberation`
   adapter 默认（observation 2）。
2. **canonical owner**：
   - `RuntimeScenarioBundle.suggested_timing` → `eva/scenario_bundle.py`
   - timing 数据结构 → `eva/kernel/config.py::ExternalLifeConfig`（复用，不新建）
   - CLI→config 回退接线 → `eva/kernel/main.py::build_runtime_config_from_args`
   - Crafter timing 声明 → `scenarios/crafter/__init__.py`
   - adapter 默认 → `eva/kernel/main.py` / config 默认（observation 2）
3. **stable / transitional / reserved**：scenario seam 与 main.py 接线均为 **stable owner**。
   本轮只做**加法扩展**（新增可选字段、回退分支），不扩大 transitional 职责；adapter 默认调整属
   行为收口（inert→heuristic），范围受限、有回归保护。
4. **slice or feature**：feature slice，拆 5 个子 slice（见下）。
5. **需冻结的 tests**：
   - `tests/scenarios/test_existence_semantics.py`（RuntimeScenarioBundle 必填契约红线 —— 新字段
     必须带默认且排在必填字段之后，不破"缺字段即 TypeError"）
   - Linux 回归：`tests/integration/test_main_runtime.py`、`tests/kernel/test_step_loop.py` 等
     （Linux 默认 timing 不变、CLI 覆盖优先级不变）
   - Crafter：`tests/integration/test_crafter_runtime.py`、`tests/scenarios/crafter/*`
6. **需同步的 docs**：A review（framework 改动）；如落地涉及 timing 语义，回写
   `docs/eva-framework-implementation.md` 的 external-life 节；当前 round progress 文档。

## Slice 大纲（A 的修法）

- **slice 1**：`RuntimeScenarioBundle` 加 `suggested_timing: ExternalLifeConfig | None = None`
  （纯加法，默认 None，向后兼容）。本 slice 不改任何行为。
- **slice 2**：`build_runtime_config_from_args` 在 **CLI 未传** timing 时回退到 active scenario 的
  `suggested_timing`；**CLI 显式传仍优先**。设计点：timing 相关 argparse 默认改 `None` 哨兵以区分
  "显式传"与"未传"，并让该函数能读到 active bundle。**← 真实设计决策，需 A 确认方向。**
- **slice 3**：`scenarios/crafter/__init__.py` 声明 sec 级 `suggested_timing`，去掉测试里重复构造
  `ExternalLifeConfig` 的样板（dedup）。
- **slice 4**（observation 2）：adapter_mode 默认 `inert→heuristic`，避免 default 触发额外 advisor
  LLM 调用；保留 `llm_assisted` 给 dlPFC producer。
- **slice 5**：测试补全 + **Linux 回归**（红线：Linux timing 默认不变 / dlPFC producer 不破 /
  CLI 覆盖优先级保留）。

## 红线

- framework 改动，**A 必须 review** 后才算完成。
- 每个 slice 一个 commit，先测试后实现（TDD）。
- 不改 `value_judgment / selection / contracts` 的打分逻辑（保持纪律）。
- DeepSeek key 只 inline 注入，绝不写 repo/git/board。

## Status

- **slice 1（RuntimeScenarioBundle.suggested_timing 字段）：完成 ✓**
  - commit `427a46a`（`eva/scenario_bundle.py` 加字段 + `tests/scenarios/test_scenario_suggested_timing.py`）
  - commit `5e42dc8`（intake doc，force-add，maintainer/ 在本分支 gitignored）
  - 验证：`test_scenario_suggested_timing.py` + `test_existence_semantics.py` 共 **9 passed**；
    CRAFTER / LINUX 两个 bundle 的 `suggested_timing` 均默认 `None`（纯加法、向后兼容）；
    `git diff --check` clean；工作树 0 脏。
- **slice 2（CLI 未传→回退 scenario.suggested_timing）：设计已定，实现待环境恢复。**

## Slice 2 设计发现（待 A review）

通过 targeted grep 确认（环境 Read 工具降级期间用单行 grep 取证）：

1. **`build_runtime_config_from_args(args)` 不持有 active bundle**：`eva/kernel/main.py` 全文
   `scenario` 出现 **0 次**；该函数签名只收 `args`（已确认 body：line ~847-852 直接取
   `args.shallow_patrol_interval` 等 4 个 timing 字段，再 `build_runtime_config(... external_life=...)`）。
2. **timing argparse 默认是硬编码值**（main.py line 783-786）：`--shallow-patrol-interval` 300.0 /
   `--deep-patrol-interval` 1800.0 / `--full-report-interval` 86400.0 / `--recent-event-window` 1800.0。
   → 无法区分"用户显式传 300"与"未传"。**必须改成 `None` 哨兵默认**才能做回退。
3. **runner 里 config 构造先于 scenario 激活**：`runners/run_crafter.py` —
   `build_runtime_config_from_args` 在 **line 126**，`activate_crafter_scenario` 在 **line 145**
   （config 先、激活后）。`CRAFTER_SCENARIO_BUNDLE` 在 run_crafter 引用 **0 次**（只调
   activate 函数，不直接 import 常量）。
   → **回退不能依赖 `get_active_runtime_scenario()`**（构造 config 时尚未激活）。

**选定设计（Option A，显式传参）**：
- `build_runtime_config_from_args(args, *, suggested_timing: ExternalLifeConfig | None = None)`
  —— 加可选 kw，默认 None，2 个测试调用方（`test_main_runtime.py` / `test_patrol_turn_flow.py`）
  不传仍向后兼容。
- main.py line 783-786 四个 timing argparse 默认 `300.0/1800.0/...` → `None`。
- 函数内回退：`base = suggested_timing or ExternalLifeConfig()`；对 4 个 timing 字段，
  CLI 值非 None 用 CLI、否则用 `base.<field>`；用 `dataclasses.replace(base, **overrides)`
  保留 `ExternalLifeConfig` 的非 timing 字段（disk/continuity/anomaly 阈值）。
  → CLI 显式 > scenario 声明 > `ExternalLifeConfig()` 框架默认。
- 3 个 runner 在调用 `build_runtime_config_from_args` 时传该 scenario 的 `suggested_timing`
  （run_crafter 需 import `CRAFTER_SCENARIO_BUNDLE` 或改用 activate 返回值；具体接线待 Read 恢复后逐个确认 run_eva / run_linux_runtime 的顺序）。

**备选（未选）**：重排 runner 让激活先于 config 构造 → 改动 runner 主流程、有 activation 副作用
（注册 drive preset / persistence / dimension specs）顺序风险，弃用。

## ⚠️ 待修复（slice 4 提交含失败测试）

`9b045eb`（slice 4 adapter 默认翻转）**提交时混入 1 个失败测试**——并行 batch 让 commit 早于
全量验证完成。真实结果是 `1 failed, 785 passed`：
- 失败：`tests/integration/test_main_runtime.py::MainLoopTests::test_cli_accepts_working_memory_backend_flag`
  （line ~782）。第二个 subprocess 用 `llm_assisted` + `client-mode heuristic` 但**没传**
  `--working-memory-adapter-mode`，翻转后默认 heuristic → 构造本地 `HeuristicWorkingMemoryAdapter`
  （trace `['top_drive_curiosity']`），不再走 client-backed shell（trace `model_client_provider_*`）→
  断言失败。这是和已修的 `test_runtime_uses_heuristic_model_client_shell_for_llm_backend` 同一根因的
  第三处（subprocess CLI 测试，没被我的 build_runtime_config grep 命中）。
- **已在工作树修复（未提交、未验证）**：给该 subprocess argv 加 `--working-memory-adapter-mode inert`
  显式 opt-in client-backed shell（intent-preserving）。
- `9b045eb` 未 push，提交信息误称 "765 passed"。修复后应 **amend `9b045eb`** 纳入该 test fix +
  改正提交信息为真实计数。
- 当前未追踪：`tests/integration/test_scenario_timing_linux_regression.py`（slice 5,已写未提交）。

恢复步骤（output pipe 恢复后）：
1. `python -m pytest tests/integration/test_main_runtime.py -q`（写 /tmp 再读）→ 确认 cli 测试绿。
2. `git add tests/integration/test_main_runtime.py && git commit --amend --no-edit`（或改正信息）。
3. 全量 `python -m pytest -q` + `git diff --check` → 786 passed 区间、clean。
4. slice 5：跑 test_scenario_timing_linux_regression.py 绿 → commit。
5. 更新本 doc Status → force-add commit → push → eva-pm G2_REQUESTED + A note。

## 环境状态（2026-05-30）

fst + eva-agent 两 worktree 当前 tool-output 降级：**Read 工具返回空、多行 Bash 输出被吞**
（单行短 echo 与单行 grep 取证仍可用）。文件本身完好（git 树干净、slice 1 已落库）——
坏的是工具输出管道，非文件，`git checkout` 不适用。slice 2 需编辑 main.py + 3 runner，
而 Edit 依赖本会话先成功 Read → **slice 2 实现硬阻塞，待 Read 恢复后继续**。
