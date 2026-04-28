# Phase B 进展

本文档记录当前 **Phase B：L3 最小骨架** 的进展。

## 1. 当前状态

- 日期：2026-04-29
- 阶段状态：**Phase B 评审后收口完成，可进入 Phase C 规划**
- 判断：当前已经建立最小 L3 包、最小 mediator、独立 deliberation audit / selective memory stub 轨道，并完成 lifecycle 接入、合同收紧、事件边界收紧、candidate profile -> bridge 的 structured bridge policy handoff，以及 anchors / value judgment 边界收紧与最终回归收口；当前评审结论已确认可以在该最小骨架上规划 Phase C learning layer，但不应把当前 L3 误判为完整 adaptive deliberation

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
  - `observe_first` 会下发 `observe_first_bias`，通过 `selection.preferred_action / fallback_action / default_path`、`applicability.*` 与 `execution.allow_repair_side_effects=false` 来约束 bridge
  - `stabilize_first` 会下发 `stabilize_first_bias`，通过同一子合同结构把 bridge 保持在 bounded repair-first compatibility path 中
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

## 5. 评审结论与下一步

当前评审结论：
1. Phase B 最小骨架已完成到足以进入 Phase C 的结构前提
2. 当前可启动的是 Phase C 的 learning layer 第一段，而不是将当前 L3 视为完整完成态
3. 当前 compatibility boundary 保持不变：`response.py` 仍为 pressure-led compatibility path，LLM 仍不能成为 release authority

下一步进入：
1. 启动 `phase-c-plan.md` 与 `phase-c-progress.md`
2. 先建立 outcome delta / RPE-like evaluation / habit bias / working-memory interface 的最小合同与文档口径
3. 仅在上述 Phase C 首轮 scope 内推进实现，不提前扩张为完整 anchor system、完整 cognitive memory retrieval 或新的外部动作谱系
