# Phase C 进展

本文档记录当前 **Phase C：学习能力** 的进展。

## 1. 当前状态

- 日期：2026-04-29
- 阶段状态：**Phase C 已完成 C-1，C-2 learning reinforcement 已基本收口，C-3 habit crystallization closeout 已完成，当前进入 C-4 LLM working-memory adapter 的 protocol / placeholder baseline**
- 判断：当前已不再只是 C-2 reinforcement 或 C-3 closeout。代码路径上已经形成 bounded habit crystallization，并在此基础上建立了 C-4 的正式 adapter request/response 协议、placeholder null adapter、可选 heuristic placeholder、backend policy、runtime switch，以及独立的 model-client shell / config shell；但 LLM 仍只停留在受限 advisory seam，不是 release authority，也还未接入真实模型执行端

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
  - `HabitSkillSummary`（作为 C-3 预铺合同）
- 本地 rule-based working-memory adapter 已建立，并可从本地轨道压缩出 bias summary
- working memory 现在会额外暴露 advisory `habit_skills` surface，用于读取 crystallized bias，并已开始以只读 hint 形式回流到 candidate priority / score shaping，但仍未绕过 `assess_candidates()` 或 `decide_release()`
- working memory 现在按 append-only 语义读取 `habit_bias.jsonl`，对同一 `candidate_profile` 取最新 bias 条目，而不是复用旧摘要
- C-2 已开始为 `habit_bias` 与 `working_memory_context` 引入 `evidence_count`、`stability_score`、`confidence` 与 stale 降权逻辑
- C-3 预铺已加入独立 `skill_library.py`，可从 `habit_bias`/`learning_outcomes` 派生 `HabitSkillSummary`，并以只读 advisory 形式暴露到 `working_memory_context`
- crystallized habit skill 现在可在候选生成阶段提供 priority hint，并在 value judgment 中加入极小 bounded bonus，用于表达 habitual preference，但仍不形成新的 release authority
- 在仅有单一高置信 crystallized habit skill 命中时，candidate generation 现在允许受限 narrowing 到单候选；若 skill 冲突、证据不足或置信不足，则继续保留双候选 deliberation path
- narrowing 命中现在会继续写入 `release_decision.learning_context.habit_narrowed` 与 `learning_outcomes.content.habit_narrowed`，使候选收窄是否发生可在 audit / learning 轨中直接观测
- patrol turn details 与 `response_selected` event 现在也会暴露 `selected_candidate_id` / `habit_narrowed`，便于运行态直接观察 habitual narrowing 是否命中
- narrowing 命中时，运行态观测现在还会暴露 `habit_narrowed_from`，用于区分本轮是从多大候选集被收窄到单候选
- learning outcome 与 habit bias summary 现在还会累计 `habit_skill_match` / `habit_narrowed` 命中计数，使 habitual path 的实际命中频率可在 append-only learning 轨与 working-memory 摘要中直接观测
- habit crystallization 现在除 evidence / stability / confidence 之外，还要求重复的 habit hit / narrowed hit 命中计数，避免仅凭单次强 bias 过早成熟为 skill
- 当 recent negative outcome 累积或最近一次 outcome 转负时，已形成的 habit skill 也会失去 crystallized 状态，避免过时习惯继续触发 narrowing
- working memory 暴露的 `habit_skills` 现在会直接携带 `crystallization_reasons`，可区分是证据不足、命中不足还是 recent negative 导致未成熟/已降级
- `bias_summaries` 现在也会同步暴露 `habit_eligible` / `habit_eligibility_reasons`，便于解释某个 profile 当前为何不会进入 habitual narrowing path
- `recent_relevant_outcomes` 现在会直接暴露 `habitual_trace` / `habitual_trace_reasons`，用于区分最近反馈是在支持还是抑制 habitual narrowing
- recent negative outcome 现在可在同情境、同 profile 下回流为有界负偏置，但仍只作为 advisory bias，不改变 hard boundary
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
- C-3 预铺的 habit skill derivation 与 working-memory advisory surface
- crystallized habit skill 只影响 candidate priority / 微小 score bonus，不绕过 mediator
- 单一强 habit skill 才允许 bounded candidate narrowing，多 skill 或弱 skill 不触发 narrowing
- narrowing 命中会写入 audit / learning 轨，确认 `habit_narrowed` trace 可端到端落盘
- patrol turn details / `response_selected` event 也会暴露 narrowing 命中元数据，便于运行态检视 candidate narrowing 是否发生
- narrowing 规模（`habit_narrowed_from`）现已进入运行态观测，可区分 2→1 之类的 bounded narrowing 命中
- `habit_skill_match` / `habit_narrowed` 现在也会在 learning outcome 与 habit bias summary 中形成累计计数，可直接验证 habitual path 是否真的在重复命中
- crystallized habit skill 现在还要求重复命中计数达标，避免单次高置信 bias 过早触发 habitual narrowing
- repeated negative outcome 会让既有 habit skill 退出 crystallized 状态，防止过期习惯持续缩窄候选集
- `habit_skills.crystallization_reasons` 已进入 working-memory 观测面，可直接解释某个 skill 当前为何未 crystallize
- `bias_summaries.habit_eligible` / `habit_eligibility_reasons` 也已进入 working-memory 观测面，可直接解释本轮为何不会沿 habitual path 收窄某个 profile
- `recent_relevant_outcomes.habitual_trace` / `habitual_trace_reasons` 也已进入 working-memory 观测面，可直接解释最近反馈是在强化还是抑制 habitual path
- outcome evaluation 与 learning outcome record 生成
- bounded bias 不能跨越 turn / critical 等硬边界
- C-2 门槛验证：低证据 / 低置信 / stale bias 不会生效，高置信 recent negative outcome 才会触发负偏置
- compatibility response 后写入 learning outcome 与 habit bias
- mediator tie-break 只在 allowed 候选内生效
- latest append-only habit bias 会覆盖同 profile 的旧 bias 读取
- recent negative outcome 只影响 matching profile，且负偏置保持 bounded

## 5. C-3 当前完成边界

当前可视为已经完成的 C-3 核心边界：
- habitual preference 已能从 recurring learning artifact 派生为 crystallized skill
- 单一强 skill 命中时可触发 bounded candidate narrowing，且不会绕过 mediator
- hit / narrowed 命中计数、recent negative streak、last outcome negative 都会影响 skill 成熟与降级
- working-memory 观测面已能解释：
  - skill 为什么 crystallize / 不 crystallize
  - profile 为什么 habit-eligible / not eligible
  - recent feedback 为什么 support / suppress habitual path
- audit 中已经能直接看到 candidate-level habitual explanation，能解释本轮为什么 narrow / 为什么没 narrow
- C-4 当前已完成最小 adapter seam：
  - working memory backend 已显式分为 `local_rule_based / auto / llm_assisted`
  - `llm_assisted` 当前只允许 candidate suggestion / prediction hint / reasoning trace / confidence 进入 advisory context
  - `auto` 当前会优先保留高置信 local habit path，只在本地弱上下文时切向 llm-assisted
  - 已新增正式 `WorkingMemoryAdapterRequest / WorkingMemoryAdapterResponse / WorkingMemoryAdapter` 协议，替代裸 `dict -> dict` callable 口径
  - 已新增 `NullWorkingMemoryAdapter` placeholder，用于保持 C-4 seam 显式存在但默认不产生 advisory payload
  - 已新增 `HeuristicWorkingMemoryAdapter` 作为本地 bounded placeholder，只从现有 request surface 产出 advisory strings，不进行任何外部模型调用
  - 已新增独立 `WorkingMemoryModelClientConfig / WorkingMemoryModelClient*` protocol / null client / heuristic client shell，以及 `ClientBackedWorkingMemoryAdapter`，使未来真实模型接入只需替换 client，而不改 runtime / mediator 边界
  - runtime 已支持受控 `working_memory_adapter` 注入；当 backend 为 `auto/llm_assisted` 且未显式提供 adapter 时，会自动回落到 inert placeholder，而不是隐式接入真实模型
  - runtime / CLI 已支持受控 `working_memory_model_client_mode / provider / model / timeout` 选择口径，用于验证 client-backed advisory path 但不触发任何真实外部请求

进入 C-4 前仍建议完成的最小入口条件：
- C-3 文档口径与 roadmap / plan 全部对齐
- C-3 closeout 回归保持稳定
- working-memory local path 的 explainability 不再有明显缺口
- 再决定是否引入 llm-assisted working-memory adapter

## 6. 下一步

下一步继续聚焦：
1. 将 C-4 protocol / placeholder baseline 同步到 roadmap / architecture 口径
2. 为真实 llm-assisted adapter 预留受控注入点，但继续保持 default inert / advisory-only 行为
3. 继续保持 model-client config shell 只作为受控替换点，不把 provider/model/timeout 配置误扩张为 release-path authority
