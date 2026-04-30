# Phase C 进展

本文档记录当前 **Phase C：学习能力** 的进展。

## 1. 当前状态

- 日期：2026-04-30
- 阶段状态：**Phase C 的 C-1 / C-2 / C-3 已完成，C-4 working-memory adapter baseline 已形成；进一步开发暂时挂起，当前进入 alignment / consolidation gate**
- 判断：当前代码路径上已经形成 bounded learning、habit crystallization 与 working-memory adapter protocol baseline；但当前优先事项不再是继续扩写 C-4，而是先完成 theory → engineering → plan → progress 的总对齐

## 2. 当前落地进展表

| 条目 | 目标 | 当前状态 | 备注 |
| --- | --- | --- | --- |
| C-1 最小 learning slice | 建立 outcome-based learning 最小闭环 | 已完成 | `outcome delta`、`RPE-like evaluation`、append-only learning artifact 已成立 |
| C-2 learning reinforcement | 强化 evidence / recency / stability / confidence gating | 已完成 | 低证据、stale、recent negative 等约束已进入读侧 |
| C-3 habit crystallization | 从 recurring bias 派生 bounded habit skill | 已完成 | 单一强 skill 可触发 bounded candidate narrowing |
| C-4 working-memory adapter baseline | 建立 advisory-only adapter seam / protocol | baseline 已形成 | 当前不继续扩写真实 llm-assisted adapter |
| Alignment / consolidation | 完成 theory → engineering → plan → progress 的口径统一 | 进行中 | 当前优先级高于继续推进 C-4 |

## 3. 当前已完成内容

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
  - `HabitSkillSummary`
- 本地 rule-based working-memory adapter 已建立，并可从本地轨道压缩出 bias summary
- working memory 现在会额外暴露 advisory `habit_skills` surface，用于读取 crystallized bias，并已开始以只读 hint 形式回流到 candidate priority / score shaping，但仍未绕过 `assess_candidates()` 或 `decide_release()`
- working memory 现在按 append-only 语义读取 `habit_bias.jsonl`，对同一 `candidate_profile` 取最新 bias 条目，而不是复用旧摘要
- C-2 已开始为 `habit_bias` 与 `working_memory_context` 引入 `evidence_count`、`stability_score`、`confidence` 与 stale 降权逻辑
- C-3 预铺已加入独立 `skill_library.py`，可从 `habit_bias`/`learning_outcomes` 派生 `HabitSkillSummary`，并以只读 advisory 形式暴露到 `working_memory_context`
- crystallized habit skill 现在可在候选生成阶段提供 priority hint，并在 value judgment 中加入极小 bounded bonus，用于表达 habitual preference，但仍不形成新的 release authority
- 在仅有单一高置信 crystallized habit skill 命中时，candidate generation 现在允许受限 narrowing 到单候选；若 skill 冲突、证据不足或置信不足，则继续保留双候选 deliberation path
- narrowing 命中现在会继续写入 `release_decision.learning_context.habit_narrowed` 与 `learning_outcomes.content.habit_narrowed`
- patrol turn details 与 `response_selected` event 现在也会暴露 `selected_candidate_id` / `habit_narrowed`
- narrowing 命中时，运行态观测现在还会暴露 `habit_narrowed_from`
- learning outcome 与 habit bias summary 现在还会累计 `habit_skill_match` / `habit_narrowed` 命中计数
- habit crystallization 现在除 evidence / stability / confidence 之外，还要求重复的 habit hit / narrowed hit 命中计数
- 当 recent negative outcome 累积或最近一次 outcome 转负时，已形成的 habit skill 也会失去 crystallized 状态
- working memory 暴露的 `habit_skills` 现在会直接携带 `crystallization_reasons`
- `bias_summaries` 现在也会同步暴露 `habit_eligible` / `habit_eligibility_reasons`
- `recent_relevant_outcomes` 现在会直接暴露 `habitual_trace` / `habitual_trace_reasons`
- recent negative outcome 现在可在同情境、同 profile 下回流为有界负偏置
- compatibility response 之后已接入 post-hoc outcome evaluation，可生成：
  - `expected_outcome`
  - `observed_outcome`
  - `outcome_delta`
  - `rpe_like_score`
  - `evaluation_label`
- learning 已以 bounded bias 形式回流到 L3 value judgment，并保持 hard boundary 不变
- mediator 选择层已收紧为：优先保持结构分排序，learning bias 只在 allowed 候选并列时作为有界 tie-break
- C-4 已建立 `local_rule_based / auto / llm_assisted` backend seam、`inert / heuristic` built-in adapter mode，以及独立 model-client shell

## 4. 当前暂停点

当前暂停点非常明确：
- 当前不继续直接推进真实 llm-assisted adapter
- 当前不扩写新的 release authority 或新的 habitual execution path
- 当前先完成文档性 alignment / consolidation gate

这意味着当前工作的重心是：
- 把目标架构与当前进展正式拆开
- 把 theory → engineering 的过渡补齐
- 把 roadmap / phase-c / README 口径统一

## 5. 当前边界仍保持不变

- 当前未扩展新的外部动作谱系
- 当前未让 LLM 成为 release authority
- learned bias 不能绕过 runtime gate / anchors / default inhibition
- learned bias 不能绕过 `bridge_target == pressure_led_compatibility`
- `response.py` 仍不是 owner，只是当前 compatibility bridge 的执行端

## 6. 当前验证状态

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
- C-3 预铺的 habit skill derivation 与 working-memory advisory surface
- crystallized habit skill 只影响 candidate priority / 微小 score bonus，不绕过 mediator
- 单一强 habit skill 才允许 bounded candidate narrowing，多 skill 或弱 skill 不触发 narrowing
- narrowing 命中会写入 audit / learning 轨
- patrol turn details / `response_selected` event 会暴露 narrowing 命中元数据
- `habit_skill_match` / `habit_narrowed` 会在 learning outcome 与 habit bias summary 中形成累计计数
- repeated negative outcome 会让既有 habit skill 退出 crystallized 状态
- outcome evaluation 与 learning outcome record 生成
- bounded bias 不能跨越 turn / critical 等硬边界
- mediator tie-break 只在 allowed 候选内生效
- latest append-only habit bias 会覆盖同 profile 的旧 bias 读取
- recent negative outcome 只影响 matching profile，且负偏置保持 bounded
- adapter protocol / placeholder / client-backed shell 的 advisory-only 边界成立

## 7. 当前已完成边界

当前可视为已经完成的边界：
- C-1：最小 outcome-based learning loop 已成立
- C-2：强化学习读侧 gating 已成立
- C-3：habit crystallization closeout 已成立
- C-4 baseline：working-memory adapter seam / protocol / placeholder / client shell 已成立

因此，当前 Phase C 的下一步不是继续补“主功能缺口”，而是先完成 alignment gate，再决定是否继续推进真实 llm-assisted adapter。

## 8. 下一步

下一步继续聚焦：
1. 统一 `README.md`、`docs/eva-agent-full-implementation.md`、`docs/current-status.md`、`maintainer/development/roadmap.md`、`maintainer/development/phase-c-plan.md` 与本文件的口径
2. 明确当前处于“暂停开发、先做深度梳理与对齐”的阶段
3. 在 alignment gate 完成后，再重新评估 C-4 的后续推进方式
