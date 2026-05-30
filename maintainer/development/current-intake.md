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

- slice 1（RuntimeScenarioBundle.suggested_timing 字段）：进行中。
