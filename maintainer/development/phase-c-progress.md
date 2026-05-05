# Phase C 进展

本文档记录当前 **Phase C：学习能力** 的进展。

## 1. 当前状态

- 日期：2026-05-06
- 阶段状态：**Phase C 已完成并通过架构师核验；Stage D 已启动；external ChatGPT review 继续作为阶段外部 gate**
- 判断：当前代码路径上已经形成 bounded learning、habit crystallization、working-memory advisory seam、secondary admission gate、transitional closeout 与四轨 append-only schema freeze；Phase C 仓库内 closeout 已完成并获准进入后续阶段，外部 ChatGPT review 不再阻塞 Stage D 启动，而是作为阶段外部 review gate 继续保留

## 2. 当前落地进展表

| 条目 | 目标 | 当前状态 | 备注 |
| --- | --- | --- | --- |
| C-1 最小 learning slice | 建立 outcome-based learning 最小闭环 | 已完成 | `outcome delta`、`RPE-like evaluation`、append-only learning artifact 已成立 |
| C-2 learning reinforcement | 强化 evidence / recency / stability / confidence gating | 已完成 | 低证据、stale、recent negative 等约束已进入读侧 |
| C-3 habit crystallization | 从 recurring bias 派生 bounded habit skill | 已完成 | 单一强 skill 可触发 bounded candidate narrowing |
| C-4 working-memory adapter baseline | 建立 advisory-only adapter seam / protocol | baseline 已形成 | 当前不继续扩写真实 llm-assisted adapter |
| Alignment / consolidation | 完成 theory → engineering → plan → progress 的口径统一 | 已完成 | module organization、public status 与 tests owner tree 已完成落账 |

## 3. 当前已完成内容

- 独立 `eva/l3_deliberation/` 包继续作为 L3 边界
- 本轮 module organization consolidation 已完成：kernel runtime、L2 reflex、anchor、reasoning / peer_circuit / memory / tool_edge owner 已全部收口到目标 namespace
- `tests/` 已按 owner tree + `integration/` bucket 完成重排，并通过全量回归 `147 tests`
- `DeliberationInput` 在保留 `signal_batch + drive_broadcast + runtime_gate_context` 为唯一强制 B0 输入的前提下，已可选接入 `working_memory_context`
- patrol 后仍先经 deliberation，再在 mediator 允许且 `bridge_target == pressure_led_compatibility` 时进入 compatibility response
- `deliberation_audit.jsonl`、`cognitive_memory_stub.jsonl`、`response_history.jsonl` 继续分轨存在
- pressure-led compatibility execution bridge 已收口到 `eva/l3_deliberation/tool_edge/`，`eva/response.py` 已删除
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
- C-3 预铺已加入独立 `memory/skill_library.py`，可从 `habit_bias`/`learning_outcomes` 派生 `HabitSkillSummary`，并以只读 advisory 形式暴露到 `working_memory_context`
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

## 4. 当前收口点

当前收口点非常明确：
- 当前不直接推进真实 llm-assisted adapter
- 当前不扩写新的 release authority 或新的 habitual execution path
- 本轮 alignment / consolidation gate 已完成

这意味着当前工作的重心已切换为：
- 基于 stable owner tree 重新评估下一开发 slice
- 保持目标架构、当前状态与 maintainer progress 文档一致
- 不再恢复 root-level transitional owner 或 compatibility shim

## 5. 当前边界仍保持不变

- 当前未扩展新的外部动作谱系
- 当前未让 LLM 成为 release authority
- learned bias 不能绕过 runtime gate / anchors / default inhibition
- learned bias 不能绕过 `bridge_target == pressure_led_compatibility`
- `eva/l3_deliberation/tool_edge/` 是当前唯一合法的 bounded execution bridge owner

## 6. 当前验证状态

当前已补齐并通过与 Phase C 首轮实现及本轮结构收口直接相关的验证，包括：
- `python -m unittest tests.l3_deliberation.tool_edge.test_compatibility`
- `python -m unittest tests.l3_deliberation.memory.test_stub`
- `python -m unittest tests.l3_deliberation.reasoning.test_working_memory`
- `python -m unittest tests.integration.test_patrol_turn_flow`
- `python -m unittest tests.integration.test_main_runtime`
- `python -m unittest discover -s tests -t . -p 'test_*.py'`

其中全量回归结果为：`147 tests` 全部通过。

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
- alignment / consolidation gate：module organization、tests owner tree、public/current status 文档落账已成立

因此，当前下一步不是继续补“主功能缺口”或恢复过渡 owner，而是基于当前 stable owner tree 再决定后续功能 slice。

## 7.5 A-1 ~ A-4 阶段性里程碑

在 Phase C baseline 与 alignment gate 之后，仓库又完成了一轮面向 EVA v0.5 主线语义的 semantic realignment：
- **A-1**：drive-weighted value judgment
- **A-2**：anchor pre-generative restriction
- **A-3**：salience-weighted episodic encoding
- **A-4**：structural default inhibition

本轮里程碑的完成事实包括：
- candidate scoring 已以 `drive_levels × drive_impact_schema` 为主评分轴，不再由 signal label 主导
- anchor 已引入 `ActionDomain / CandidateSchema / AgentState`，候选生成先受 admitted schema 约束，再进入评估
- episodic encoding owner 已转入 `l3_deliberation/memory/encoding.py`，并加入连续 `salience` 与 `drive_state_at_encoding`
- mediator 已发放运行态 `ReleaseToken`，tool-edge execution 需经 token + selected candidate 校验，且 token 不写入持久化 artifact

当前 milestone 的边界仍保持：
- tool-edge 仍是 bounded compatibility bridge，不扩写为更大执行面
- mediator 仍是 release authority，kernel 只做 authority handoff
- audit / memory / learning 继续分轨
- A-2 的 pre-generative anchor 已成立，但仍保留少量 compatibility mirror，用于当前窄候选面下的参数注入

当前 milestone 已完成验证：
- A-4 定向测试：`61 tests`
- 全量回归：`193 tests`
- 当前可对外提供给其他 AI 进行 review 的阶段性结果为 commit `563f235`

外部 review 时建议优先检查：
- `eva/anchor/domain_restriction.py`
- `eva/l3_deliberation/reasoning/value_judgment.py`
- `eva/l3_deliberation/memory/encoding.py`
- `eva/l3_deliberation/peer_circuit/mediator.py`
- `eva/l3_deliberation/tool_edge/compatibility.py`
- `eva/l3_deliberation/tool_edge/executors.py`


## 7.6 B-1 anchor pre-generative residue closeout

在 A-1 ~ A-4 milestone 之后，仓库继续完成了一轮面向 anchor 收口的 B-1 slice：
- `ActionDomain` 继续作为候选生成主入口，生成后的候选已内建最小 runtime-gate projection
- `apply_structural_anchors(...)` 已收窄为 residual compatibility projection seam，不再承担主要 candidate legality 语义
- `eva/anchor/cross_layer.py` 保留为极小兼容投影层，用于 legacy/manual candidate 路径

本轮边界仍保持：
- 不恢复 post-hoc anchor 为主要合法化路径
- 不扩写 compatibility bridge
- 不改动 mediator / tool-edge authority 链
- 不引入新的 root-level owner

本轮验证已完成：
- `python -m unittest tests.anchor.test_domain_restriction`
- `python -m unittest tests.anchor.test_structural`
- `python -m unittest tests.l3_deliberation.reasoning.test_candidates`
- `python -m unittest tests.l3_deliberation.reasoning.test_value`
- `python -m unittest tests.l3_deliberation.peer_circuit.test_mediator`
- `python -m unittest tests.integration.test_patrol_turn_flow tests.integration.test_main_runtime tests.integration.test_lifecycle_patrol_learning tests.l3_deliberation.memory.test_stub`
- 全量回归：`193 tests`

Transitional / residual 评估：
- `eva/anchor/cross_layer.py` 仍保留，但已降为 residual compatibility projection seam
- 该文件保留的理由是兼容手工构造候选与少量 legacy 路径；若后续 slice 不再需要，可继续退场

## 7.7 B-2 richer episodic retrieval

在 B-1 之后，仓库继续完成了一轮面向 retrieval / working-memory 读侧的 B-2 slice：
- `memory/retrieval.py` 现在按 `situation_key`、`pressure_reason`、`top_drive`、`life_state` 与连续 `salience` 组合排序 episodic / learning traces
- `memory/encoding.py` 已把 `drive_state_at_encoding`、`pressure_reason` 与 `situation_key` 写入 append-only episodic payload
- `reasoning/working_memory.py` 已按 `learning_outcomes -> response_history -> episodic traces` 的顺序组装 advisory context

本轮边界仍保持：
- working memory 仍是 advisory-only context，不成为 release authority
- retrieval 只深化读侧语义，不回写 drive state
- audit / memory / learning 继续分轨

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.memory.test_stub`
- `python -m unittest tests.l3_deliberation.memory.test_encoding`
- `python -m unittest tests.l3_deliberation.reasoning.test_working_memory`
- `python -m unittest tests.l3_deliberation.memory.test_episodic`
- `python -m unittest tests.integration.test_lifecycle_patrol_learning`
- 全量回归：`193 tests`

## 7.8 B-3 compatibility bridge demotion

在 B-2 之后，仓库继续完成了一轮面向 tool-edge owner demotion 的 B-3 slice：
- `tool_registry.py` 现在拥有可复用的 response selection / bridge-policy 消费 helper
- `executors.py` 现在拥有 mediated execution closeout 与 release-context execution policy 消费
- `history.py` 现在拥有 response summary / history 组装
- `compatibility.py` 已压薄为 pressure-scoped wrapper，不再内联通用选择 / 执行 / summary 语义

本轮边界仍保持：
- 不扩大 action surface
- 不放松 mediator / release-token authority
- response history 继续 append-only
- compatibility bridge 继续保持 bounded

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.tool_edge.test_tool_registry`
- `python -m unittest tests.l3_deliberation.tool_edge.test_executors`
- `python -m unittest tests.l3_deliberation.tool_edge.test_compatibility`
- `python -m unittest tests.l3_deliberation.peer_circuit.test_goal_directed_track`
- `python -m unittest tests.integration.test_patrol_turn_flow tests.integration.test_main_runtime`
- 全量回归：`195 tests`

## 7.9 B-4 drive-native L3 shaping

在 B-3 之后，仓库继续完成了一轮面向 L3 reasoning / selection 语义收紧的 B-4 slice：
- `reasoning/value_judgment.py` 现在以 drive-weighted score 作为 allowed candidate 的主排序依据
- pressure / threat / compatibility-pressure 现在只保留为 compatibility projection reasons 与 bounded fallback score；仅在 drive score 无法分化候选时提供极小 fallback
- `peer_circuit/selection.py` 现在保持 drive-led score ordering，learning bias 只在同分 allowed candidate 内做 bounded tie-break
- `reasoning/conflict_detection.py` 的 reason vocabulary 已从 bias/pressure-led 表述收紧为 projection/fallback 表述

本轮边界仍保持：
- pressure 不恢复为 primary decision owner
- compatibility bridge 不扩大
- learning bias 继续保持 advisory and bounded
- mediator / default inhibition / release-token authority 不变

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.reasoning.test_value`
- `python -m unittest tests.l3_deliberation.reasoning.test_conflict_detection`
- `python -m unittest tests.l3_deliberation.peer_circuit.test_mediator`
- `python -m unittest tests.integration.test_patrol_turn_flow`
- `python -m unittest tests.l3_deliberation.tool_edge.test_tool_registry tests.l3_deliberation.tool_edge.test_executors tests.l3_deliberation.tool_edge.test_compatibility tests.l3_deliberation.peer_circuit.test_goal_directed_track tests.l3_deliberation.memory.test_encoding tests.l3_deliberation.peer_circuit.test_rpe`
- `python -m unittest tests.integration.test_main_runtime`
- 全量回归：`195 tests`

## 7.10 B-5 candidate and release vocabulary widening

在 B-4 之后，仓库继续完成了一轮面向 candidate / release 词汇受限扩展的 B-5 slice：
- `anchor/domain_restriction.py` 现在会在高风险 integrity reason（`runtime_files_missing`、`runtime_not_writable`、`recent_distress_detected`）下额外 admitted 一个受限 `escalate_first` candidate profile
- `reasoning/conflict_detection.py`、`reasoning/value_judgment.py` 与 `peer_circuit/goal_directed_track.py` 现在可在不放松 drive-led judgment 与 mediator-owned release 的前提下处理 `escalate_first` profile / policy / expected outcome
- `tool_edge/tool_registry.py` 与 bounded compatibility response path 继续复用既有 `escalate_integrity_risk` action，不新增 side-effect authority，也不新增并行 execution owner
- `peer_circuit/rpe.py` 与 `habit_track.py` 已对更宽 internal profile vocabulary 保持兼容，learning artifact 仍沿 append-only 轨道记录

本轮边界仍保持：
- 不新增新的 release authority
- 不绕过 mediator / release token
- 不扩大 compatibility bridge 为通用 execution layer
- 不新增 side-effect action；仅复用 bounded `escalate_integrity_risk`
- 当前 `escalate_first` admission 仍由高风险 `reason` 集合单字段控制；若后续 slice 要扩该集合，需先补 secondary admission gate（如 drive intensity / severity guard），避免 admission 无差别扩张

本轮验证已完成：
- `python -m unittest tests.anchor.test_domain_restriction tests.l3_deliberation.reasoning.test_candidates tests.l3_deliberation.reasoning.test_conflict_detection tests.l3_deliberation.reasoning.test_value`
- `python -m unittest tests.l3_deliberation.peer_circuit.test_goal_directed_track tests.l3_deliberation.peer_circuit.test_mediator tests.l3_deliberation.peer_circuit.test_rpe`
- `python -m unittest tests.l3_deliberation.tool_edge.test_tool_registry tests.l3_deliberation.tool_edge.test_compatibility tests.integration.test_patrol_turn_flow`
- 全量回归：`203 tests`

## 7.11 C-1 cross_layer residual seam closeout

在 B-5 之后，仓库开始进入新一轮 Phase C 深化 / transitional 清理序列；其中首个 C-1 slice 已完成：
- `eva/anchor/cross_layer.py` 已删除，不再保留独立 transitional anchor seam 文件
- residual `apply_structural_anchors(...)` compatibility projection helper 已并回 canonical owner `eva/anchor/domain_restriction.py`
- `eva/anchor/__init__.py` 继续对外暴露同名 helper，因此现有 anchor / L3 import surface 未被放大，也未恢复新的 root-level transitional path

本轮边界仍保持：
- 不恢复 post-hoc anchor 为主要 candidate legality 路径
- 不扩大 compatibility bridge
- 不放松 mediator / tool-edge authority 链
- 不新增新的 transitional owner；仅把 residual helper 收回 canonical anchor owner

本轮验证已完成：
- `python -m unittest tests.anchor.test_domain_restriction`
- `python -m unittest tests.anchor.test_structural`
- `python -m unittest tests.l3_deliberation.reasoning.test_candidates`
- `python -m unittest tests.integration.test_patrol_turn_flow`
- 全量回归：`205 tests`

## 7.12 C-2 retrieval similarity ranking

在 C-1 之后，仓库继续完成了一轮面向 retrieval / working-memory 读侧排序语义收紧的 C-2 slice：
- `memory/retrieval.py` 现在对 learning outcomes、response history fallback 与 episodic memory traces 统一引入连续 `drive_similarity`
- `top_drive` 已从主要硬过滤条件降为排序贡献；working-memory retrieval 现在以 `situation relevance + pressure relevance + drive similarity + salience` 的组合排序为主
- `reasoning/working_memory.py` 继续保持 `learning_outcomes -> response_history -> episodic traces` 的 fallback 次序不变，因此本轮只深化读侧排序，不改 advisory context 合同
- 为避免低相关 similar-drive 痕迹误召回，当前 similar-drive path 采用最小 similarity threshold

本轮边界仍保持：
- working memory 仍是 advisory-only context，不成为 release authority
- retrieval 只深化读侧语义，不回写 drive state
- 不恢复 pressure-led primary path
- append-only artifact schema 不变

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.reasoning.test_working_memory`
- `python -m unittest tests.l3_deliberation.memory.test_episodic`
- `python -m unittest tests.integration.test_lifecycle_patrol_learning`
- 全量回归：`207 tests`

## 7.13 C-3 impact schema RPE learning

在 C-2 之后，仓库继续完成了一轮面向 value expectation / impact estimation 的 C-3 slice：
- `peer_circuit/rpe.py` 现在可从 `bias_summaries` 与 `recent_relevant_outcomes` 读出 gated learned impact overlay，并按 `candidate_profile` + `top_drive` 生成 bounded learned signal 与 blend factor
- `reasoning/value_judgment.py` 现在会在 evidence / confidence / stability 达阈值后，把该 learned overlay 以有界 blend 的方式并入 candidate `drive_impact_schema`；若证据不足，则继续保留 static cold-start baseline
- learned impact 仍只影响 drive-led score shaping，不新增 release authority，也不绕过 mediator / anchor / runtime gate；既有 habit bias 与 recent negative bias 仍保持 advisory-only

本轮边界仍保持：
- learned outcome 只回流到 value expectation，不成为独立决策 owner
- evidence 未达阈值时继续使用 static impact schema，不放大学习噪声
- learned overlay 必须 bounded，且只允许局部接管 `top_drive` 对应 impact 估计
- 不恢复 pressure-led primary ranking，也不新增 compatibility shim

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.peer_circuit.test_rpe`
- `python -m unittest tests.l3_deliberation.reasoning.test_value`
- `python -m unittest tests.integration.test_lifecycle_patrol_learning`
- 全量回归：`213 tests`

## 7.14 C-4 working-memory adapter baseline observability closeout

在 C-3 之后，仓库继续完成了一轮面向 working-memory adapter seam 观测收口的 C-4 slice：
- `reasoning/working_memory.py` 现在在 `WorkingMemoryContext` 与 store 组装路径里显式携带 `advisory_source`，用于区分 `local_rule_based`、`auto_preferred_local`、`auto_no_adapter`、`explicit_adapter`、`builtin_heuristic_adapter`、`client_backed_model_shell`、`null_adapter` 等 advisory 路径
- `kernel/main.py` 与 `kernel/lifecycle.py` 现在会把 runtime 解析出的 advisory 源一路传到 deliberation 输入，但仍只作为只读 observability metadata，不改变 working-memory authority
- `tests/` 现在覆盖 local / auto / explicit / heuristic / null 路径的 advisory-source 断言，确保 adapter seam 仍保持 advisory-only，不会被误用为 release authority

本轮边界仍保持：
- working memory 仍是 advisory-only context，不成为 release authority
- 不扩写真实 llm-assisted adapter 行为
- 不新增 release-side authority contract
- append-only artifact schema 不变

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.reasoning.test_working_memory`
- `python -m unittest tests.kernel.test_lifecycle`
- `python -m unittest tests.integration.test_main_runtime`
- `python -m unittest discover -s tests -t . -p 'test_*.py'`
- 全量回归：`213 tests`

## 7.15 C-5 secondary admission gate for `escalate_first`

在 C-4 之后，仓库继续完成了一轮面向 anchor admission hardening 的 C-5 slice：
- `anchor/domain_restriction.py` 现在把 `primary_pressure_severity` 显式投影进 `ActionDomain.agent_state`，使 `escalate_first` admission 不再只由高风险 `reason` 单字段决定
- `escalate_first` 现在要求同时满足：高风险 integrity `reason` 命中，且 primary integrity pressure severity 通过二级守卫；当前守卫收紧为 `critical` severity 才可 admitted
- heartbeat-window narrowing 仍保持更强外层约束；即使是高风险 reason，也不会绕过 heartbeat-first schema narrowing

本轮边界仍保持：
- 不新增新的 release authority
- 不把 severity guard 下沉到 mediator / tool-edge release 层
- 不扩大 compatibility bridge 或 side-effect surface
- drive / pressure 仍保持只读上游投影，anchor 只收紧 pre-generative admission

本轮验证已完成：
- `python -m unittest tests.anchor.test_domain_restriction tests.l3_deliberation.reasoning.test_candidates tests.l3_deliberation.reasoning.test_value tests.l3_deliberation.peer_circuit.test_mediator tests.integration.test_patrol_turn_flow`
- 定向回归：`62 tests`

## 7.16 C-6 transitional file closeout

在 C-5 之后，仓库继续完成了一轮面向 transitional surface 收口的 C-6 slice：
- `eva/l3_deliberation/memory/stub.py`、`eva/l3_deliberation/tool_edge/actions.py`、`eva/l3_deliberation/peer_circuit/learning.py`、`eva/l2_drive/drive.py`、`eva/l2_drive/pressure.py` 已退场
- 需要继续保留的 surface 已收回 canonical package owner：
  - `eva/l2_drive/__init__.py`
  - `eva/l3_deliberation/memory/__init__.py`
  - `eva/l3_deliberation/peer_circuit/__init__.py`
  - `eva/l3_deliberation/tool_edge/__init__.py`
- `peer_circuit/__init__.py` 已改为直接从 canonical `rpe.py` 暴露 learning outcome helpers，不再依赖单独 transitional `learning.py`

本轮边界仍保持：
- canonical package exports 仍然可用
- 不保留独立 transitional shim module
- 不引入新的 compatibility surface
- 不改变运行时语义或 release authority

本轮验证已完成：
- `python -m unittest tests.l3_deliberation.peer_circuit.test_learning tests.l3_deliberation.memory.test_stub tests.l2_drive.test_drive tests.l2_drive.test_pressure`
- targeted grep 验证无 stale shim import
- 定向回归：`12 tests`

## 7.17 C-7 append-only schema freeze

在 C-6 之后，仓库继续完成了一轮面向 append-only contract surface 冻结的 C-7 slice：
- 四条上游轨道已显式冻结为 canonical append-only contract surface：
  - audit: `deliberation_audit.jsonl`
  - episodic: `cognitive_memory_stub.jsonl`
  - learning: `learning_outcomes.jsonl`
  - habit: `habit_bias.jsonl`
- 冻结后的 writer / reader / typed owner 已在维护规范中落账，并保持 additive-only 演进规则
- `response_history.jsonl` 明确排除在四轨 freeze 之外，仍作为 bounded compatibility / projection track 存在

本轮边界仍保持：
- 四条轨道继续分离，不能并入 `runtime_state.json`
- 已落地字段语义冻结，后续只允许 additive change
- 不新增 parallel compatibility shim
- 不把 response history 误升格为正式记忆轨

本轮验证已完成：
- `python -m unittest tests.kernel.test_state`
- `python -m unittest tests.l3_deliberation.memory.test_episodic`
- `python -m unittest tests.l3_deliberation.memory.test_stub`
- `python -m unittest tests.l3_deliberation.peer_circuit.test_rpe`
- `python -m unittest tests.integration.test_lifecycle_patrol_learning`
- `python -m unittest tests.kernel.test_lifecycle`
- `python -m unittest tests.l3_deliberation.reasoning.test_working_memory`
- `python -m unittest discover -s tests -t . -p 'test_*.py'`

## 7.18 C-8 full regression and docs sync

在 C-7 之后，仓库继续完成了 Phase C 的仓库内 final verification：
- C-5 / C-6 / C-7 的 closeout 状态已同步到 maintainer progress、development standards 与 public status
- 已明确区分 **Phase C implementation complete in-repo** 与 **external ChatGPT review pending**，避免把外部出口误记为仓库内已完成
- 当前 `current-intake.md` 已切换到 final verification closeout 口径

本轮验证已完成：
- `python -m unittest discover -s tests -t . -p 'test_*.py'`
- 全量回归：`217 tests`

## 8. 下一步

下一步主线已切换为：
1. D-1：落地 threat-triggered reflex fast path，并保持 mediated token gate
2. D-2：把 L1 sensing 收口到 plugin-style sensor registry composition
3. D-3：把 drive update mechanics 收口为显式命名语义与参数面
4. external ChatGPT review 继续作为 Stage D 阶段外部 review gate 保留
