# Current Intake

> 只保留**当前正在执行**的一项 intake。上一项（Phase 2 V1 observation_tools）已 closeout，内容见 `v1-progress.md`。

## Round 1.E — L3 Reasoning Proposal Path — G1 Intake（已 APPROVED → 实现 E-1..E-8 完成 → 置 `G2_REQUESTED` 等 A 复核；G2 gate 包见 `round-1e-progress.md §7`）

### 可行性结论：FEASIBILITY_OK
已逐一核对 seam 代码（`runtime.run_deliberation` / `reasoning/candidate_generation` / `contracts` / `reasoning/value_judgment` / `reasoning/working_memory` / `peer_circuit`）：
- 插入点干净：`run_deliberation` 中 `candidates = build_candidates(action_domain)` 与 `assess_candidates` 之间即 proposer 槽位。
- 域边界明确：`build_candidates` = `[schema.to_candidate() for schema in action_domain.admitted_candidate_schemas]`——**anchor admitted schemas 就是 proposer 的硬边界**，proposer 只能在其中 rank/筛选，normalization 丢弃域外。
- LLM 路径已存在：`WorkingMemoryAdapter.build_advisory_context` 在上游组装 `working_memory_context.advisory_context`（candidate_suggestions / confidence）。
- audit 可加 additive proposal/rejection 记录（`DeliberationAuditRecord.to_dict` 加可选字段，不破现有）。
- red-lines（§6）全部可守。详见 `round-1e-progress.md`。

### 改动层 / canonical owner
- `eva/l3_deliberation/reasoning/`：新增 `proposer.py`（Proposer 协议 + HeuristicProposer + ModelBackedProposer + normalization/rejection）。
- `eva/l3_deliberation/contracts.py`：新增 `ReasoningProposal`；`DeliberationAuditRecord` 加可选 `proposals` / `rejected_proposals` 字段（additive）。
- `eva/l3_deliberation/runtime.py`：`run_deliberation` 加可选 `proposer` 注入；在 admission 与 assess 之间插 proposer→normalize。
- 测试：新增 `tests/l3_deliberation/reasoning/test_reasoning_proposal.py` + `tests/integration/test_crafter_runtime.py` 集成。
- **不动**：`peer_circuit/`（selection + release authority）、`anchor/`、`l2_drive/`、persistence、existence semantics、`reasoning/conflict_detection.py` 的 3-profile whitelist。

### Profile / action 词汇
不变：3 profile（observe/stabilize/escalate）+ Round 1.A 的 17 动作。proposer 只在 admitted 域内动作。

### 两个设计决策点（请 A 一并裁示）
- **DP1 — ModelBackedProposer 接 model 的方式**
  - 倾向 **(a)**：proposer 依赖注入到 `run_deliberation`（加可选 `proposer` 参数，默认 HeuristicProposer ⇒ `local_rule_based` behavior-preserving）；ModelBackedProposer **复用上游已组装的 `advisory_context`** 正规化成 ranked `ReasoningProposal`——不新增独立 LLM 调用、不改 lifecycle。满足 exit（considered set 相对 local 改变 + 可审计），最小改动，且字面"复用现有 working-memory model-client path"。
  - 备选 **(b)**：把 model-client 注入 proposer，proposer 自产 schema-bound JSON（更强结构化推理）。改动更大（lifecycle 组装 + run_deliberation 签名）。
  - 若 A 要求"模型独立产 schema-bound JSON ranking"，走 (b)；否则按 (a)。
- **DP2 — 现有 ≤0.12 advisory（value_judgment）去留**
  - 倾向 **保留** `assess_candidates` 内 ≤0.12 不动（red-line：assess 下游不动）作次要排序信号；proposer 是新增的上游强杠杆（塑形 considered set），与 ≤0.12 共用 advisory 数据源但作用层不同。model 影响力从"仅 ≤0.12"升为"塑形候选集 + ≤0.12"。

### tests to freeze（§5）
`tests/kernel` / `l1_sensing` / `l2_drive` / `anchor` / `l3_deliberation/peer_circuit` / `l3_deliberation/tool_edge` / `scenarios/linux_runtime` / `test_existence_semantics` / `test_individual_identity` / `stability_metrics` / `inheritance_distillation`。
允许改断言数据（非逻辑）：`test_value.py` / `test_working_memory.py`。

### docs to sync（§2）
`implementation-tracking(.md/-zh)` L3 reasoning 行 skeleton→partial/production；`blueprint-to-tracking-map(.md/-zh)` 对应行；`scenarios/crafter/SPEC.md`（若 deliberation surface 可观测变化）；`round-1e-progress.md`；本 intake closeout。

### slice 计划（G1 后执行，G1 前不进 E-1）
E-1 failing tests → E-2 `ReasoningProposal` contract → E-3 Proposer 协议+两实现 → E-4 normalize+reject+audit → E-5 wire `run_deliberation` → E-6 reasoning-contribution audit → E-7 Crafter 集成测试 → E-8 docs+closeout。
