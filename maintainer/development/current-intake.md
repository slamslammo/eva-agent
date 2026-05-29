# Current Intake

## Active Item

`scenario-time-model-pr-s1` — kernel 消费 clock_source + 双计数 + heartbeat 不冻结 + bridge deferred + transcript v1.2

Coordination owner: `B-claude-2`
Branch: `scenario-time-model-pr-s1`
Plan source: `/Users/mojiawen/Documents/claude_projects/eva-coordination/plans/scenario-time-model-and-step-driven-execution-plan.md` §3 + §6 红线

## Slice plan (TDD)

| # | Slice | Touches | Notes |
|---:|---|---|---|
| 1 | ResponseSelection 加 is_deferred + deferred_reason | tool_registry.py | 纯加法 default False/None |
| 2 | select_response_action / select_integrity_response defer-path 出 is_deferred=True + deferred_reason | crafter compatibility.py | 改返回值结构 |
| 3 | execute_crafter_action 在 is_deferred 时不调 env.step | crafter compatibility.py | bridge fallback 分支 |
| 4 | Lifecycle 双计数器 (attempt_index / scenario_step_index) | lifecycle.py + main.py | clock_source 消费核心 |
| 5 | Consecutive deferred 防护 → NEEDS_HUMAN at MAX=10 | lifecycle.py | R8 |
| 6 | response_history 加 env_step_invoked / clock_source / 双计数 字段 | lifecycle.py response_summary | telemetry |
| 7 | Transcript schema v1.1→v1.2: 加 env_step_invoked / attempt_index / scenario_step_index | llm_transcript.py | R12 |
| 8 | run_meta 分离 counts (llm_success/fail/mediated_release/env_step_invoked) | main.py | R6 telemetry |
| 9 | dlPFC role contract 加 clock_source="step" 段 | crafter_dlpfc_role_contract.py | R11 |
| 10 | Heartbeat-during-deferred 测试 + Linux 回归验证 | tests | **R5 + R2 关键** |

## §6 红线对照（执行全程）

1. Linux 默认 wall_clock 行为不变（noop fallback 沿用）
2. **Linux 回归全绿 explicit 测试**
3. clock_source 字段已存在，不改定义
4. clock_source="step" 时 deferred 不调 env.step（**核心契约**）
5. **⭐ heartbeat/lease/liveness 不受 scenario time freeze 影响**——不冻结，否则重引卡死 bug。**必须有 deferred 期间 heartbeat 持续测试**
6. **scenario step 推进绑 mediated release 不绑 LLM**
7. 失败 attempt 要可见 (attempt_index 照常 +1)
8. consecutive_deferred ≥ 10 → NEEDS_HUMAN
9. 不动 eva-theory
10. 不动 blueprint
11. dlPFC role contract 注入 clock_source 语义
12. transcript schema v1.1→v1.2

## Acceptance (§7 验证)

| 验收指标 | 期望值 |
|---|---|
| env_step_invoked_count | == mediated_release_count |
| scenario_step_index 终值 | == env_step_invoked_count |
| deferred attempt 数 | == 链路 fail 数 |
| attempt_index 终值 | == scenario_step_index + deferred |
| heartbeat 在 deferred 期间 | 持续跳动 |
| Linux 回归 | 全绿 |
| consecutive_deferred ≥10 | NEEDS_HUMAN |

PR-S2（文档）+ Run（验证）链式排在 PR-S1 之后。

## Status: 编码完成，准备 commit + G2_REQUESTED

### Implementation Result

| Slice | Status | Notes |
|---:|---|---|
| 1 ResponseSelection + is_deferred/deferred_reason | ✅ | 3 tests |
| 2 select_response_action defer signal | ✅ | 4 tests |
| 3 execute_crafter_action skip env.step + payload | ✅ | 3 tests; +`_deferred_execution_payload` |
| 4 Lifecycle 双计数器 (attempt/scenario_step) | ✅ | 3 tests; lifecycle.py +12 |
| 5 consecutive_deferred ≥10 → needs_human exit | ✅ | 2 tests; main.py MAX=10 |
| 6 response_history fields (env_step_invoked / is_deferred / deferred_reason) | ✅ | history.py serialization + summary |
| 7 Transcript schema v1.1→v1.2 (env_step_invoked + 双计数) | ✅ | 4 tests + 5 hardcoded test updates |
| 8 RunSummary attempt/scenario_step counts | ✅ | main.py 2 fields |
| 9 dlPFC role contract clock_source 段 | ✅ | 3 tests, plan §3.6 1:1 |
| 10 ⭐ heartbeat-during-deferred (R5 CRITICAL) | ✅ | 1 test verifies exit clean via R8 not R5 violation |

**Files modified** (production):
- `eva/l3_deliberation/tool_edge/tool_registry.py` ResponseSelection +2 optional fields
- `eva/l3_deliberation/tool_edge/history.py` payload + summary 加 env_step_invoked / is_deferred / deferred_reason
- `eva/l3_deliberation/llm_transcript.py` SCHEMA_VERSION v1.1→v1.2 + 3 optional kwargs
- `scenarios/crafter/actions/compatibility.py` defer signal + execute skip env.step + `_deferred_execution_payload`
- `scenarios/crafter/ontology/crafter_dlpfc_role_contract.py` clock_source="step" 段
- `eva/kernel/lifecycle.py` +5 attrs (`_attempt_index` / `_scenario_step_index` / `_consecutive_deferred`) + counter logic in response handler
- `eva/kernel/main.py` `MAX_CONSECUTIVE_DEFERRED=10` constant + `needs_human_consecutive_deferred` exit_reason + RunSummary +2 fields

**Files modified** (tests):
- 3 existing integration tests in `test_crafter_runtime.py` updated to inject stub producer
- 5 existing transcript tests updated v1.1→v1.2 string

**New test files** (23 tests total):
- `tests/l3_deliberation/tool_edge/test_response_selection_deferred_fields.py` (3)
- `tests/scenarios/crafter/test_compatibility_deferred_signal.py` (4)
- `tests/scenarios/crafter/test_execute_crafter_deferred.py` (3)
- `tests/kernel/test_lifecycle_dual_counters.py` (3)
- `tests/kernel/test_consecutive_deferred_exit.py` (2)
- `tests/l3_deliberation/test_llm_transcript_v12.py` (4)
- `tests/scenarios/crafter/test_role_contract_clock_source.py` (3)
- `tests/kernel/test_heartbeat_during_deferred.py` (1)

### §6 红线全 ✅

| # | 红线 | 状态 |
|---:|---|---|
| 1 | Linux clock_source="wall_clock" 行为不变 | ✅ Linux 16 tests pass |
| 2 | Linux 回归全绿 explicit 测试 | ✅ `pytest tests/ -k "linux"` → 16 passed |
| 3 | clock_source 字段不改定义 | ✅ ExistenceSemantics 字段未动 |
| 4 | clock_source="step" deferred 不调 env.step | ✅ test_deferred_selection_does_not_call_step_external_action |
| 5 | ⭐ heartbeat 不冻结 | ✅ test_heartbeat_continues_during_deferred_streak_clean_exit |
| 6 | env.step 绑 mediated release 不绑 LLM | ✅ env_step_invoked from bridge payload |
| 7 | 失败 attempt 要可见 | ✅ attempt_index bumps regardless |
| 8 | consecutive_deferred ≥10 → NEEDS_HUMAN | ✅ `needs_human_consecutive_deferred` exit |
| 9 | 不动 eva-theory | ✅ |
| 10 | 不动 blueprint | ✅ |
| 11 | dlPFC role contract 注入 clock_source 语义 | ✅ |
| 12 | transcript v1.1→v1.2 | ✅ |

### 验证

- focused: 23 PR-S1 tests passed
- full pytest: **715 passed** (baseline 693 + 23 new − 1 overlap)
- Linux regression: **16 passed**
- git diff --check: clean

## Gate Fix Round — CHANGES_REQUESTED (A gate 2026-05-29, commit 9049106)

A 复核 commit 9049106：行为层全部正确并保留（R4/R5/R6/R7/R8 + 715/16 Linux 全绿逐条确认）。
**唯一必改（gate 卡点）**：kernel **没真正消费** clock_source——`clock_source` 只在注释 +
`main.py` run_meta 记录，无任何 `clock_source=="step"` 行为分支。真正驱动行为的是 Crafter
bridge 无条件 set `is_deferred` + kernel 读 `env_step_invoked`。字段是**装饰性、非 load-bearing**，
违背 blueprint §2.7（kernel reads this to choose cadence；per-scenario cadence fork forbidden）。
反例：未来 scenario 声明 `wall_clock` 但 bridge 误设 `is_deferred`，当前 kernel 照样按 bridge 走。

### Change Intake（CHANGES_REQUESTED 回流，同分支 `scenario-time-model-pr-s1`）

1. 层：`kernel`（counter 逻辑 + exit gate）
2. canonical owner：`LifecycleRuntime` counter 更新逻辑 + `main.py` consecutive_deferred exit gate
3. owner 类型：stable（kernel）
4. slice 性质：当前 round 的 CHANGES_REQUESTED 修正 slice（非新 feature）
5. 冻结 tests：`test_lifecycle_dual_counters` / `test_consecutive_deferred_exit` / `test_heartbeat_during_deferred`
6. 同步文档：本 `current-intake.md`（gate notes 已在 board）

### 修法（A 给，窄 4-6 行 + 测试加固）

| # | 改动 | 文件 |
|---:|---|---|
| G1 | `__init__` guarded 读 `self._clock_source = get_active_existence_semantics().clock_source`（RuntimeError→`wall_clock`，复用 main.py:367 bare-kernel 同款 fallback） | lifecycle.py |
| G2 | 抽出 load-bearing `_update_scenario_counters(response_summary)`：`step`→honor `env_step_invoked`；`wall_clock`→强制 `attempt==scenario_step` 恒等（忽略任何 bridge `is_deferred`） | lifecycle.py |
| G3 | call site 901-907 改调 `self._update_scenario_counters(...)` | lifecycle.py |
| G4 | exit gate 显式 gate on `step`：`_clock_source=="step" and _consecutive_deferred>=MAX` | main.py |
| G5 | 重写 `test_deferred_..._bumps_consecutive` 调真实 `_update_scenario_counters`（消除 manual-replication drift） | test_lifecycle_dual_counters.py |
| G6 | 新 `test_clock_source_load_bearing.py`：wiring(step/wall_clock) + wall_clock 反例不变式 + step 分叉（**A 反例 1:1 编码**） | new test |

> 注：`tool_registry.py:64` 注释 + `lifecycle.py:183-188` 注释当时已写好目标语义（"kernel reads
> is_deferred together with the active scenario's clock_source"），本 fix 让代码追上注释，注释不动。
> 其余 7 production 文件全部保留不动。补此一项后重置 G2_REQUESTED。

### Gate Fix 验证（commit 待填）

- RED：`test_clock_source_load_bearing.py` 4 tests 因 `_clock_source` / `_update_scenario_counters` 缺失 AttributeError 失败（feature missing）
- GREEN focused：load-bearing 4 + dual_counters 3 + consecutive_deferred 2 + heartbeat 1 = **10 passed**
- full pytest: **719 passed**（715 + 4 新 load-bearing；dual_counters 重写不增减数）
- Linux regression `-k linux`: **17 passed**（16→17，新增 `test_linux_runtime_reads_wall_clock_source` 命中 linux 关键字）
- git diff --check: clean
- production 改动仅 `lifecycle.py`（`_clock_source` 读 + `_update_scenario_counters` 抽取 + call site）+ `main.py`（exit gate gate-on-step），其余 7 文件全保留

### clock_source 现已 load-bearing（A 反例闭环）

| 模式 | bridge `env_step_invoked` | kernel counter 结果 |
|---|---|---|
| `step` | True | scenario_step+1, consecutive=0 |
| `step` | False (defer) | scenario_step **不变**, consecutive+1 → ≥10 needs_human |
| `wall_clock` | True | scenario_step+1, consecutive=0 |
| `wall_clock` | **False（bridge 误设）** | **kernel 忽略，强制 scenario_step+1, consecutive=0** ← A 反例已堵 |

field 驱动行为，blueprint §2.7 承诺名副其实。
