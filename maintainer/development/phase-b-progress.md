# Phase B 进展

本文档记录 **Phase B：L3 最小骨架** 的进展结论。

## 1. 当前状态

- 日期：2026-04-30
- 阶段状态：**Phase B 评审后收口已完成；当前作为已完成基线保留**
- 判断：当前已经建立最小 L3 包、最小 mediator、独立 deliberation audit / selective memory stub 轨道，并完成 lifecycle 接入、合同收紧、事件边界收紧、candidate profile -> bridge 的 structured bridge policy handoff，以及 anchors / value judgment 边界收紧与最终回归收口。本文档当前的角色，是保留 Phase B 的已完成事实；当前项目活跃主线已经进入 Phase C 之后的 alignment / consolidation gate

## 2. 已完成工作

### B0 -> B1 衔接
- L3 已明确从 `drive_broadcast + signal_batch + runtime_gate_context` 起步
- `active_pressures.json` 未被重新提升为 L3 主输入
- `response.py` 继续保持 pressure-led compatibility path

### L3 最小骨架
- 已新增 `eva/l3_deliberation/`
- 已建立：
  - `contracts.py`
  - `anchors.py`
  - `candidates.py`
  - `value.py`
  - `mediator.py`
  - `memory.py`
  - `runtime.py`
- 已形成最小合同：
  - `DeliberationInput`
  - `Candidate`
  - `CandidateAssessment`
  - `ReleaseDecision`
  - `DeliberationAuditRecord`
  - `MemoryWriteStub`

### default inhibition + compatibility release
- mediator 当前默认 `withhold`
- 仅当 integrity / threat 压力足够明确时，才允许 `compatibility_release`
- `compatibility_release` 当前会同时产出最小 `release_context`
- compatibility release 当前已从单一占位候选升级为多 internal compatibility candidates 的选择结果
- candidate generation 当前只读取 `drive_broadcast + signal_batch.summary + compatibility pressure count` 来产出内部候选，不再混入 runtime gate judgment
- anchors 当前只负责把 `instance_valid / turn_allowed / critical_blocked / conservative_mode / life_state` 压入 candidate parameter domain
- value judgment 当前只基于 drive / signal pressure 与 anchored runtime boundary 做 disposition / score 判断
- `candidate_profile` 当前已显式映射进 compatibility bridge，并通过 structured `bridge_policy` handoff 到 response bridge：
  - policy 已分成 `selection`、`applicability`、`execution` 三个子合同
  - `observe_first` 会下发 `observe_first_bias`
  - `stabilize_first` 会下发 `stabilize_first_bias`
- compatibility release 仍只流向 `response.py`

### 持久化分轨
- `EvaPaths` 已新增：
  - `deliberation_audit.jsonl`
  - `cognitive_memory_stub.jsonl`
- `StateStore` 已新增对应 append/read 接口
- `runtime_state.json` 仍未混入 L3 数据
- memory stub 已收紧为 selective write policy：仅在 threat trace / release trace 下写入

### lifecycle 接入
- patrol 完成后会构造 `DeliberationInput`
- `turn_completed.details.deliberation` 已收紧为 `{ outcome, selected_action }`
- `turn_completed.details.response` 已收紧为 `{ pressure_id, pressure_type, selected_action }`
- `response_selected.details` 已收紧为最小 compatibility event surface
- patrol 后先经过 L3 mediator，再依据 `release_context.bridge_target` 决定是否进入 compatibility response
- 当前 `release_context` 已显式携带 `candidate_profile`，使 bridge selection 原因可审计但不外泄到 turn details

## 3. 当前已确认边界

- heartbeat-first guard 仍先于 L3
- instance invalid / critical block 仍先于 L3
- L3 不写 `drive_state.json`
- `response.py` 不拥有 drive update 权限
- audit trail 与 cognitive memory stub 当前已开始分轨，但仍只是最小骨架，不等于完整 cognitive memory
- `deliberation_audit.jsonl` 保留完整 L3 内部细节，`response_history.jsonl` 保留 richer compatibility execution 细节

## 4. 当前验证结果

已通过：

```bash
PYTHONPATH="/Users/mojiawen/Documents/claude_projects/eva-agent" python -m unittest \
  tests.test_state \
  tests.test_candidates \
  tests.test_value_judgment \
  tests.test_mediator \
  tests.test_memory_stub \
  tests.test_patrol \
  tests.test_lifecycle \
  tests.test_response \
  tests.test_main_loop
```

最近一次结果：`78 tests, OK`

## 5. 当前在总主线中的位置

Phase B 当前应被理解为：
- 其最小骨架目标已经完成
- 它为 Phase C 的 learning layer 提供了结构前提
- 它明确了 release / audit / memory stub / compatibility bridge 的最小 owner 关系
- 它现在不再是当前活跃实施阶段，而是已完成基线的一部分

其后续关系也已经明确：
- 其“进入 Phase C”这一历史下一步已经完成
- Phase C 的 C-1 / C-2 / C-3 已完成
- C-4 baseline 已形成
- 当前主线已切到 alignment / consolidation gate，而不是回到 Phase B 继续扩张
