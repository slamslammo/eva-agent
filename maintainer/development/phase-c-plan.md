# Phase C 计划

本文档定义当前 **Phase C：学习能力** 的本地计划记录。

当前应将其理解为一个分轮推进的阶段，而不是单次实现：
- **Phase C-1**：最小 learning slice（已完成）
- **Phase C-2**：learning reinforcement（已完成）
- **Phase C-3**：habit crystallization（已完成）
- **Phase C-4**：LLM working-memory adapter（baseline 已形成，后续扩展暂时挂起）

## 1. 总目标

Phase C 的总目标不是宣告 L3 已完整完成，而是在既有 **Phase B 最小骨架** 之上，沿着以下主线逐步建立更完整的学习能力：

```text
release intent -> compatibility execution outcome -> outcome delta -> bounded learning bias -> habit crystallization -> llm-assisted working memory
```

整个 Phase C 聚焦：
- `outcome delta`
- `RPE-like evaluation`
- `habit bias / skill crystallization`
- 可替换的 `working-memory interface`

## 2. 本阶段起点

进入 Phase C 前，仓库已经具备：
- 独立 `eva/l3_deliberation/` 包
- `DeliberationInput / CandidateAssessment / ReleaseDecision / DeliberationAuditRecord / MemoryWriteStub` 等最小合同
- `deliberation_audit.jsonl`、`cognitive_memory_stub.jsonl`、`response_history.jsonl` 的分轨持久化
- patrol 后先经 deliberation，再在 `compatibility_release + bridge_target == pressure_led_compatibility` 时进入 compatibility response

当前已经完成：
- `learning_outcomes.jsonl`
- `habit_bias.jsonl`
- `LearningOutcomeRecord / WorkingMemoryContext / HabitBiasSummary`
- compatibility response 之后的 post-hoc outcome evaluation
- bounded learning bias 回流到 value judgment / mediator tie-break
- recurring learning artifact 到 habit skill 的 bounded crystallization path
- working-memory adapter 的 protocol / placeholder baseline

因此，后续 Phase C 的工作不应重写 lifecycle 主链，也不应把 `response.py` 重新提升为 future owner。

## 3. 子迭代拆分

### C-1. 最小 learning slice（已完成）

已完成内容：
- 独立 learning artifact
- 最小 learning contract
- post-hoc outcome evaluation
- replaceable local rule-based working-memory adapter
- bounded bias 回流到 L3

### C-2. Learning reinforcement（已完成）

已完成方向：
- evidence / recency / stability / confidence gating
- 对低证据、旧证据、混杂证据降权
- recent negative outcome 的 bounded 生效条件
- 继续保持当前 release authority 结构不变

### C-3. Habit crystallization（已完成）

已完成方向：
- 从 recurring bias summary 派生 habit skill
- 在稳定情境下缩窄候选搜索面，降低 deliberative 成本
- 继续保持 runtime gate、anchors、mediator、compatibility bridge 不被绕过

### C-4. LLM working-memory adapter（baseline 已形成）

目标：
- 把 LLM 放在 `working_memory.py` 的 adapter 位置
- 让 LLM 在复杂、低置信度、规则覆盖不足的情境中提供 candidate suggestion / prediction / reasoning trace
- 已经 crystallize 的 habitual 情境继续优先本地 path，避免滥用 LLM

当前已完成的最小预铺：
- `working_memory.py` 已形成三种 backend 口径：
  - `local_rule_based`
  - `auto`
  - `llm_assisted`
- `llm_assisted` 当前只允许受限 advisory output：
  - `candidate_suggestions`
  - `prediction_hints`
  - `reasoning_trace`
  - `confidence`
- 当前已新增正式 protocol / placeholder baseline：
  - `WorkingMemoryAdapterRequest`
  - `WorkingMemoryAdapterResponse`
  - `WorkingMemoryAdapter`
  - `NullWorkingMemoryAdapter`
  - `HeuristicWorkingMemoryAdapter`
  - `WorkingMemoryModelClientConfig`
  - `WorkingMemoryModelClientRequest`
  - `WorkingMemoryModelClientResponse`
  - `WorkingMemoryModelClient`
  - `NullWorkingMemoryModelClient`
  - `HeuristicWorkingMemoryModelClient`
  - `ClientBackedWorkingMemoryAdapter`
- runtime / CLI 已支持受控 `working_memory_model_client_mode / provider / model / timeout` 选择口径，用于在不接真实外部模型的前提下验证 client-backed advisory path

### 当前暂停点

当前不直接继续扩写 C-4，而是在进入后续 C-4 之前先完成一次 **alignment / consolidation gate**。

这个 gate 的目标是把以下链条对齐：
- 完整 v0.5 理论架构
- 完整 v0.5 工程架构
- 完整 v0.5 开发落地方案
- eva-agent 当前落地进展

## 4. C-3 当前完成判断

截至当前代码状态，C-3 已经完成首轮核心落地：
- crystallized habit skill 已形成独立 summary / derivation path
- habitual narrowing 已能在单一强 skill 命中时发生，并保持 bounded
- hit / narrowed counters、recent negative degradation、crystallization reasons、habit eligibility、habitual trace 都已进入 working-memory / audit observability
- candidate / assessment / audit 已可解释本轮为什么 narrow 或为什么未 narrow

因此，C-3 当前剩余工作不再是补主功能，而主要是 closeout、口径对齐与为 C-4 预留干净入口。

## 5. C-4 当前 baseline 判断

截至当前代码状态，C-4 已不再只是 seam 预设，而是已经形成首轮 protocol baseline：
- working-memory advisory path 已显式使用 `WorkingMemoryAdapterRequest / WorkingMemoryAdapterResponse`
- `NullWorkingMemoryAdapter` 已可作为默认 inert placeholder 保持 seam 显式存在
- `HeuristicWorkingMemoryAdapter` 已可作为本地 bounded placeholder 验证 advisory-only runtime path，而不接入真实模型
- `ClientBackedWorkingMemoryAdapter + WorkingMemoryModelClient` 已形成独立 shell，使未来真实模型接入只需替换 client
- runtime 已支持受控 `working_memory_adapter` 注入；未显式提供 adapter 时，`auto/llm_assisted` 仍保持 inert，不隐式接入真实模型执行端
- 当前 client-backed path 还支持 `inert / heuristic` 两种 built-in model-client mode

因此，C-4 下一步不再是“是否建立 adapter seam”，而是：**在 alignment gate 完成后，再决定是否继续推进真实 llm-assisted adapter。**

## 6. 当前进入条件

在继续推进 C-4 之前，应至少满足：
- 本地 rule-based working-memory path 的 observability / explainability 已基本收口
- C-3 相关回归稳定通过
- `README.md` / `docs/eva-agent-full-implementation.md` / `docs/current-status.md` / `maintainer/development/roadmap.md` / `maintainer/development/phase-c-progress.md` 口径已经对齐
- LLM adapter 的职责被限制在 working-memory seam，不侵入 mediator authority

## 7. 本阶段硬约束

Phase C 期间必须保持：
- `signal_batch + drive_broadcast + runtime_gate_context` 仍是唯一强制 B0 输入
- working memory 只能是可选增强输入，不得变成新的架构 prerequisite
- `response.py` 仍是 pressure-led compatibility path
- compatibility release 仍只通过当前 mediator / bridge 边界进入下游
- habit path 只能缩窄或优先候选，不能绕过 runtime gate / anchors / mediator
- LLM 只能作为 working-memory / reasoning adapter，不是 release authority
- lifecycle turn details 与 `response_selected.details` 的最小 surface 不扩张

## 8. 本阶段不做

Phase C 当前不做：
- 完整 anchor system
- 完整 mediator policy engine
- 完整 cognitive memory retrieval
- 新的外部动作谱系
- habit track 的独立自动执行通路
- 将 `response.py` 退场
- 提前进入完整 L4 / L5
- 在 alignment gate 完成前继续扩写真实 llm-assisted adapter

## 9. 当前完成标准与后续完成标准

### C-1 已完成标准
- 释放前 intent 与释放后 actual outcome 之间已建立最小 learning record
- `outcome delta` 与 `RPE-like evaluation` 已能 append-only 持久化
- working-memory interface 已成立，且首个本地 adapter 可用
- learning 能以 bounded bias 影响后续 candidate release tendency
- compatibility boundary 未被突破

### C-2 已完成标准
- 同一 `situation_key` / `candidate_profile` 的稳定正负证据可有界影响倾向
- 低证据 / 旧证据 / 混杂证据不会产生过强偏置
- learning effect 在测试和 append-only artifact 中可解释、可观测

### C-3 已完成标准
- 部分常见高频情境能形成可复用的 habit skill / crystallized preference
- habitual path 可以减少 deliberative 负担，但不越权

### C-4 后续完成标准
- LLM 可在复杂情境中提供合理 suggestion / prediction / trace
- 高置信度 habitual 情境优先本地 path，不滥用 LLM
- LLM 始终受 runtime / anchor / mediator / bridge 约束

## 10. 验证重点

需要重点验证：
- learning outcome 只在 compatibility response 之后写入
- 无 compatibility release / 无 response summary 时，不会写 learning outcome
- working-memory interface 在无历史数据时能安全返回空上下文
- learned bias 只能影响倾向，不能跨越 runtime gate / anchor / mediator 硬边界
- habit crystallization 只缩窄或优先候选，不直接执行
- LLM 只提供 advisory context，不成为 release authority
- `response.py` 仍只作为 compatibility path 存在
- `runtime_state.json` 仍保持 kernel-only 语义
- `turn_completed.details.*` 与 `response_selected.details` 未扩张为 richer learning payload
- alignment gate 完成后，Phase C 文档与总路线、目标架构、工程架构口径一致
