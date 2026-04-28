# Phase C 进展

本文档记录当前 **Phase C：学习能力** 的进展。

## 1. 当前状态

- 日期：2026-04-29
- 阶段状态：**Phase C 首轮最小实现已落地**
- 判断：当前已在 Phase B 评审收口后的最小 L3 骨架上接入独立 learning track、replaceable working-memory interface 与 bounded bias 回流；但当前仍应被视为 Phase C 首轮 learning slice，而不是完整 adaptive deliberation

## 2. 当前已完成内容

- 独立 `eva/l3_deliberation/` 包继续作为 L3 边界
- `DeliberationInput` 在保留 `signal_batch + drive_broadcast + runtime_gate_context` 为唯一强制 B0 输入的前提下，已可选接入 `working_memory_context`
- patrol 后仍先经 deliberation，再在 mediator 允许且 `bridge_target == pressure_led_compatibility` 时进入 compatibility response
- `deliberation_audit.jsonl`、`cognitive_memory_stub.jsonl`、`response_history.jsonl` 继续分轨存在
- `response.py` 当前仍只承担 pressure-led compatibility path
- runtime artifact 已新增独立 learning 轨：
  - `learning_outcomes.jsonl`
  - `habit_bias.jsonl`
- `StateStore` 已新增对应 append/read 能力，不把 learning 状态混入 `runtime_state.json`
- Phase C 最小合同已加入：
  - `LearningOutcomeRecord`
  - `WorkingMemoryContext`
  - `HabitBiasSummary`
- 本地 rule-based working-memory adapter 已建立，并可从本地轨道压缩出 bias summary
- compatibility response 之后已接入 post-hoc outcome evaluation，可生成：
  - `expected_outcome`
  - `observed_outcome`
  - `outcome_delta`
  - `rpe_like_score`
  - `evaluation_label`
- learning 已以 bounded bias 形式回流到 L3 value judgment，并保持 hard boundary 不变
- mediator 选择层已收紧为：优先保持结构分排序，learning bias 只在 allowed 候选并列时作为有界 tie-break，不成为新的 release authority

## 3. 当前边界仍保持不变

- 当前未扩展新的外部动作谱系
- 当前未让 LLM 成为 release authority
- learned bias 不能绕过 runtime gate / anchors / default inhibition
- learned bias 不能绕过 `bridge_target == pressure_led_compatibility`
- `response.py` 仍不是 owner，只是当前 compatibility bridge 的执行端

## 4. 当前验证状态

当前已补齐并通过与 Phase C 首轮实现直接相关的测试，包括：
- `tests/test_state.py`
- `tests/test_candidates.py`
- `tests/test_learning.py`
- `tests/test_value_judgment.py`
- `tests/test_lifecycle.py`
- `tests/test_mediator.py`

其中重点覆盖：
- learning artifact append/read
- working memory 空态与 bias summary
- outcome evaluation 与 learning outcome record 生成
- bounded bias 不能跨越 turn / critical 等硬边界
- compatibility response 后写入 learning outcome 与 habit bias
- mediator tie-break 只在 allowed 候选内生效

## 5. 下一步

下一步继续聚焦：
1. 观察是否需要把 bounded bias 进一步限制在更窄的近分区间
2. 持续收口 `phase-c-plan.md` / `phase-c-progress.md` 与公开文档的一致性
3. 仅在当前 learning slice 稳定后，再考虑更完整的 working-memory retrieval 或 habit crystallization 细化
