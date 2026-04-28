# Phase B 计划

本文档定义当前 **Phase B：L3 最小骨架** 的公开计划。

## 1. 目标

Phase B 的第一步不是追求复杂 reasoning，而是先把 L3 的结构主干搭正确：

```text
B0 inputs -> candidate generation -> value judgment -> mediator -> compatibility release
```

这里的 `B0 inputs` 固定指：
- `signal_batch`
- `drive_broadcast`
- `runtime_gate_context`

## 2. 本阶段起点

进入 Phase B 前，仓库已经具备：
- kernel baseline
- L1 的 state + rate sensing 与 normalized signal publication
- L2 的 continuous drive state 与 read-only drive broadcast
- B0 冻结的最小上游输入合同
- 仍作为 compatibility path 存在的 `response.py`

因此，Phase B 不应从 `active_pressures.json` 重新起步，也不应继续扩写 `response.py`。

## 3. 工作重点

### B1. 建立独立 L3 包

新增 `eva/l3_deliberation/`，至少承载：
- contracts
- anchors
- candidates
- value judgment
- mediator
- memory stub
- runtime assembly

### B2. 冻结 L3 最小合同

最小合同至少包括：
- `DeliberationInput`
- `Candidate`
- `CandidateAssessment`
- `ReleaseDecision`
- `DeliberationAuditRecord`
- `MemoryWriteStub`

### B3. 建立 default inhibition 的 mediator

初版 mediator 只允许三种结果：
- `withhold`
- `defer`
- `compatibility_release`

其中 `compatibility_release` 仍只通向当前 `response.py`，不新增外部动作谱系。

当前进一步收紧为：
- mediator 在允许 release 时同时输出最小 `release_context`
- `release_context` 当前至少声明：
  - `bridge_target`
  - `response_mode`
- lifecycle 只在 `bridge_target == pressure_led_compatibility` 时进入当前 compatibility bridge

### B4. 分离 audit 与 cognitive memory stub

本阶段先建立两条独立 append-only 轨道：
- `deliberation_audit.jsonl`
- `cognitive_memory_stub.jsonl`

它们不能混入：
- `runtime_state.json`
- `response_history.jsonl`
- `events.jsonl`

当前进一步收紧为：
- memory stub 不是每轮都写
- 只有 threat trace 或 release trace 才写入最小 memory stub
- memory stub 至少显式携带：
  - `memory_type`
  - `write_reason`
  - `linked_audit_recorded_at`

### B5. 接入 lifecycle patrol 后通路

L3 应接在 patrol 完成之后，但不能破坏：
- heartbeat deadline guard
- instance invalid turn block
- critical state turn block
- conservative mode 边界

### B6. 收紧下游事件与 turn details 暴露面

patrol 后对下游暴露的最小 surface 应明确收紧为：
- `turn_completed.details.deliberation = { outcome, selected_action }`
- `turn_completed.details.response = { pressure_id, pressure_type, selected_action }`
- `response_selected.details = { work_slice, work_kind, pressure_id, pressure_type, selected_action }`

完整 deliberation 细节不进入 lifecycle turn details，完整 compatibility execution 细节不进入 `response_selected` event，而是分别保留在：
- `deliberation_audit.jsonl`
- `response_history.jsonl`

## 4. 本阶段硬约束

Phase B 期间必须保持：
- L3 只读 `drive_broadcast + signal_batch + runtime_gate_context`
- drive 仍只能由 L1/L2 更新，L3 不能写
- reasoning 不直接调用 side effect
- response 仍是 pressure-led compatibility path
- `active_pressures.json` 仍只是 compatibility projection

## 5. 本阶段不做

Phase B 当前不做：
- 完整 mediator policy engine
- 完整 anchor solver
- 完整 cognitive memory retrieval
- 新的外部动作谱系
- 用 LLM 作为 release authority
- Phase C 的学习能力

## 6. 完成标准

Phase B 最小骨架完成后，至少应成立：
- L3 有独立目录与清晰合同
- mediator 以 default inhibition 形式成立
- patrol 后会生成 deliberation audit 与 memory stub
- compatibility response 只能在 mediator 允许时触发
- `response.py` 仍不是 L3 owner

## 7. 验证重点

需要重点验证：
- `DeliberationInput` 只消费 B0 输入面
- `turn_completed.details.deliberation` 只暴露 `{ outcome, selected_action }`
- `turn_completed.details.response` 与 `response_selected.details` 只暴露最小 compatibility surface
- mediator 在 `compatibility_release` 时输出最小 `release_context`
- 没有 mediator release 时，不会进入 compatibility response
- `deliberation_audit.jsonl` 与 `cognitive_memory_stub.jsonl` 分轨存在
- memory stub 只在 threat/release 条件下写入，并携带最小 write policy 字段
- `runtime_state.json` 仍保持 Step 0 / kernel-only 语义
- heartbeat-first 与现有 block 语义未被 L3 破坏
