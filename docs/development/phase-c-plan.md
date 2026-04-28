# Phase C 计划

本文档定义当前 **Phase C：学习能力** 的首轮公开计划。

## 1. 目标

Phase C 的目标不是宣告 L3 已完整完成，而是在既有 **Phase B 最小骨架** 之上，引入 learning layer 的第一段：

```text
release intent -> compatibility execution outcome -> outcome delta -> bounded learning bias
```

首轮 Phase C 聚焦：
- `outcome delta`
- `RPE-like evaluation`
- `habit bias / skill crystallization` 的最小版本
- 可替换的 `working-memory interface`

## 2. 本阶段起点

进入 Phase C 前，仓库已经具备：
- 独立 `eva/l3_deliberation/` 包
- `DeliberationInput / CandidateAssessment / ReleaseDecision / DeliberationAuditRecord / MemoryWriteStub` 等最小合同
- `deliberation_audit.jsonl`、`cognitive_memory_stub.jsonl`、`response_history.jsonl` 的分轨持久化
- patrol 后先经 deliberation，再在 `compatibility_release + bridge_target == pressure_led_compatibility` 时进入 compatibility response

因此，Phase C 不应重写当前 lifecycle 主链，也不应把 `response.py` 重新提升为 future owner。

## 3. 工作重点

### C1. 建立独立 learning artifact

新增独立 learning 轨道，至少承载：
- `learning_outcomes.jsonl`
- 首轮可选的 `habit_bias.jsonl` 或等价 bias summary 轨道

它们不能混入：
- `runtime_state.json`
- `deliberation_audit.jsonl`
- `response_history.jsonl`
- `cognitive_memory_stub.jsonl`

### C2. 冻结 Phase C 最小合同

最小合同至少包括：
- `LearningOutcomeRecord`
- `WorkingMemoryContext`
- `HabitBiasSummary`

并以增量方式接入现有合同：
- `DeliberationInput` 可选携带 `working_memory_context`
- `CandidateAssessment` 可选携带 learning bias 信息
- `ReleaseDecision` 可选携带最小 `expected_outcome` 或等价 learning context

### C3. 建立 post-hoc outcome evaluation

首轮 learning 必须建立在 compatibility execution 之后，而不是改写 release authority。

因此，首轮至少需要：
- 从 release intent 与 response outcome 构造 `outcome delta`
- 给出最小 `RPE-like evaluation`
- 将 learning outcome 作为 append-only artifact 保存

首轮实际 outcome 至少复用：
- `execution_status`
- `pressure_outcome`
- `followup_needed`
- `selected_action`
- `release_context`

### C4. 建立 replaceable working-memory interface

working memory 当前的角色是：
- 读取局部历史
- 返回压缩后的 bias / recency / uncertainty context
- 供后续 deliberation 读取

首轮 working-memory interface：
- 必须是 replaceable abstraction
- 首个实现允许是本地 rule-based adapter
- 不能把 LLM 提升为 prerequisite

### C5. 将 learning 以 bounded bias 回流到 L3

首轮 learning 对 L3 的影响只允许体现为：
- candidate preference 的小幅偏置
- value judgment 的 bounded score adjustment
- mediator 在近似候选间的 tie-break bias

当前不允许：
- 让 learned bias 越过 hard boundary
- 让 learned bias 绕过 default inhibition
- 让 learned bias 直接触发 side effect

## 4. 本阶段硬约束

Phase C 期间必须保持：
- `signal_batch + drive_broadcast + runtime_gate_context` 仍是唯一强制 B0 输入
- working memory 只能是可选增强输入，不得变成新的架构 prerequisite
- `response.py` 仍是 pressure-led compatibility path
- compatibility release 仍只通过当前 mediator / bridge 边界进入下游
- LLM 只能作为 working-memory / reasoning adapter，不是 release authority
- lifecycle turn details 与 `response_selected.details` 的最小 surface 不扩张

## 5. 本阶段不做

Phase C 当前不做：
- 完整 anchor system
- 完整 mediator policy engine
- 完整 cognitive memory retrieval
- 新的外部动作谱系
- habit track 的独立自动执行通路
- 将 `response.py` 退场
- 提前进入完整 L4 / L5

## 6. 完成标准

Phase C 首轮完成后，至少应成立：
- 释放前 intent 与释放后 actual outcome 之间已建立最小 learning record
- `outcome delta` 与 `RPE-like evaluation` 已能 append-only 持久化
- working-memory interface 已成立，且首个本地 adapter 可用
- learning 能以 bounded bias 影响后续 candidate release tendency
- compatibility boundary 未被突破
- 当前 L3 仍保持 minimal skeleton 定位，而不是被误表述为完整完成态

## 7. 验证重点

需要重点验证：
- learning outcome 只在 compatibility response 之后写入
- 无 compatibility release / 无 response summary 时，不会写 learning outcome
- working-memory interface 在无历史数据时能安全返回空上下文
- learned bias 只能影响倾向，不能跨越 runtime gate / anchor / mediator 硬边界
- `response.py` 仍只作为 compatibility path 存在
- `runtime_state.json` 仍保持 kernel-only 语义
- `turn_completed.details.*` 与 `response_selected.details` 未扩张为 richer learning payload
