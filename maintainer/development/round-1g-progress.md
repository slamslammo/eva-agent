# Round 1.G — L3 Reasoning-Core Rebuild — Progress（B / 代码开发）

**当前状态**：**phase-1 DONE**；**phase-2 scope=(a) 进行中**——**G-5（action_hint 因果路径，结构层）+ G-6（`LLMCandidateProducer` 模块 + 8 单测）+ G-6b（lifecycle/runner 接线 + 端到端集成测试）全 DONE**（全量回归 **516 绿**，纯 additive、冻结 owner 干净、model-off 字节等价）；**仅剩 G-7（live bounded 短跑：审计 hint→executed 真样本 + 真 LLM 行为验，~¥0.18）待做**。
**分支**：`claude/recursing-hertz-7c4029`。本轮 = round-1e/1f 的正解收口（proposer + ≤0.12 退役）。

## phase-2 (a) 完成记录（2026-05-21）

A 裁示（用户已选 (a)）：drive 定 posture（OFC 冻结 max + drive 底线）不变；**LLM 因果杠杆 = 选中 posture 候选的 `action_hint`**——须 (i) 随候选流到 bridge、(ii) bridge 消费（优先于 `PROFILE_DEFAULT_ACTION`/prior）、(iii) 审计 hint→executed；OFC 不二次评分；model-off 字节等价；drive 底线锁 posture 防 passivity。

| slice | 状态 | 内容 |
|---|---|---|
| **G-5 action_hint 因果路径（结构层）** | **DONE** | ①`Candidate.action_hint: str\|None`（`to_dict` 仅非空输出 → None 字节等价）。②`run_deliberation._thread_selected_action_hint`：mediator 选定 posture 后，按 `selected_candidate_id` 取胜者 candidate 的 hint，折进 `release_context["action_hint"]`（不动 outcome/selected_candidate_id/release_token/默认抑制；无 hint → 决策不变 = 字节等价；与 lifecycle `_release_context_with_observation` 同理增强）。③Crafter bridge 消费：`_candidate_context_from_release_context` 提升 `action_hint`；`build_integrity_response_candidates` 把合法（profile-eligible）hint 前置进候选；`select_response_action` 中合法 hint **权威**（优先于 default/prior/habit，reason=`crafter_llm_action_hint_selection`）；非法/无 hint → 启发式不变。 |
| **G-6 live LLMCandidateProducer（模块 + 单测）** | **DONE** | 新 `eva/l3_deliberation/reasoning/llm_candidate_producer.py`：`LLMCandidateProducer(base_producer, *, chat_fn, profile_action_vocab)`。base 候选 → 1 次 bounded schema-bound JSON 调用（`chat_fn` 注入的 vendor-neutral transport seam）→ 解析 `{"action_hints":{profile:action}}` → 仅当 action ∈ 该 profile 的注入 vocab 时 `dataclasses.replace` 标 `action_hint`。**结构性防 passivity**：只标注既有候选、**不增删候选 / 不改 profile**（drive 锁 posture 不变）。任何 transport/timeout/parse 失败 或 无 vocab/无 chat_fn → 返回 base（degrade to heuristic、字节等价）。vocab/transport 依赖注入（框架 generic、scenario 注 vocab、lifecycle 注 transport）。**8 单测**（stub chat_fn、token-free）：合法 in-vocab hint 标注 / 非法 hint 丢弃 / 成员+profile 不变 / transport 失败 degrade / 不可解析 degrade / 无 vocab 跳过调用 / 无 chat_fn 纯启发式 / protocol。全量回归 **515 绿**（纯新增、未接线 → 0 行为变更）。 |
| **G-6b lifecycle/runner 接线** | **DONE** | ① `build_live_chat_fn`（working_memory_model_client 新增**公共** helper，复用 env-config + OpenAI-compatible transport，env 未配 live → 返 None；additive、不动 advisory 路径）。② `LifecycleRuntime.__init__` 加 `candidate_producer` 可选参 + 存；`run_deliberation(producer=self.candidate_producer)`。③ `run_runtime` 加 `candidate_producer` 可选参 → 透传 LifecycleRuntime。④ runner `_build_candidate_producer(config)`：仅当 backend=`llm_assisted` **且** client_mode=live **且** env 已配 → 构 `LLMCandidateProducer(chat_fn=build_live_chat_fn, profile_action_vocab=PROFILE_ELIGIBLE_ACTIONS)`，否则 None（→ heuristic 默认、字节等价）。**scenario vocab 由 runner 注入**（框架 producer scenario-agnostic，无需改 scenario_bundle）。⑤ **端到端集成测试**（stub chat_fn、无 token）：注入 producer → 跑 bounded run → `response_history` 至少 1 条 `selected_action_reason==crafter_llm_action_hint_selection` 且 `selected_action==hints[selected_posture]`——**证 producer→threading→release_context→bridge→执行 全链路因果**。全量回归 **516 绿**；diff 纯 additive plumbing（lifecycle/main 透传、runner 接线、model_client 公共 helper、1 集成测试），未触 mediator/peer_circuit/anchor policy/OFC/L1/L2/existence-semantics/默认抑制；model-off（producer=None）字节等价。 |
| G-7 审计 + bounded 短跑 | TODO | 审计样本证 LLM hint=X → 执行=X（candidates[].action_hint + release_context.action_hint + response_history selected_action/reason 三处对齐）；model-off → 默认动作字节等价回归；bounded 短跑（~¥0.18）验 action_hint 因果 + drive 锁 posture 无 90% sleep 回潮。 |

**G-5 验证**：全量回归 **507 passed**（499 + 8 新：threading×4 + serialization×2 + bridge consumption×3 −1 重叠计数）；冻结 owner git-diff 干净（仅 `eva/l3_deliberation/contracts.py` 加字段 + `runtime.py` 加 threading + `scenarios/crafter/actions/compatibility.py` bridge 消费 + tests；**未触** mediator/peer_circuit/goal_directed_track/anchor policy/value_judgment(OFC)/l2_drive/l1_sensing/existence-semantics）；model-off / 无 hint byte-preserving。

**设计点（G2 请 A 确认）**：合法 action_hint 设为 bridge 选择**权威**（不止优先于 default/prior，亦优先于 habit）——理由：phase-2(a) 本意是 live reasoning 在 drive 锁定 posture 内选具体动作，habit 是 model-off 时的回退学习偏置；A 契约 ③「posture 内动作交 LLM + RPE 反馈」支持此读法。habit 仍在 model-off / 无 hint 时主导。

## phase-1 完成记录（2026-05-21）

| slice | commit | 内容 |
|---|---|---|
| 退役 ≤0.12 advisory | `1cb46c8` | 删 `_llm_advisory_bonus` + 其 assess 调用 + 2 测试。OFC 仅 drive 加权。model-off 不变（advisory 从不影响 local）。 |
| 退役 round-1e reorder-proposer | `783bf66` | `run_deliberation` 回 `build_candidates→assess→decide_release`；删 `proposer.py`、契约 proposal 字段、lifecycle proposer 接线、相关测试。 |
| dlPFC CandidateProducer seam | `b26d850` | 新 `candidate_producer.py`：`CandidateProducer` 协议 + `HeuristicCandidateProducer`（= `build_candidates`、behavior-preserving 默认）；`run_deliberation(producer=…)` 注入点（phase-2 live-LLM 产出器插这里）。 |
| docs-sync | `aec76e1` | tracking×2 + blueprint-map×2 标 proposer/≤0.12 superseded、producer seam landed；blueprint §7.4 注 drift→producer 更正。 |

**验证**：全量回归 **499 passed**；**冻结 owner git-diff 干净**（`5cd000e..HEAD` 未触 peer_circuit/mediator、anchor、l2_drive、l1_sensing、existence-semantics）；model-off byte-preserving（`run_deliberation` 默认 producer = `build_candidates`）。

**phase-2 待办（A+用户敲定因果设计后）**：`LLMCandidateProducer`（schema-bound JSON、bounded、fallback heuristic）+ **drive 底线防 passivity 塌缩**（G-4，其设计取决于 phase-2 因果设计）+ lifecycle 在 `llm_assisted` 接线 + bounded 短跑验行为。token 估算 ~¥0.15–0.20/run（见 `current-intake.md`）。

## 1. Feasibility = OK（外科式重建可行）

---

## 1. Feasibility = OK（外科式重建可行）
- 现状已锚定：`anchor.admit_crafter_candidates` 枚举 3 profile → Candidate(`drive_impact_schema`) → OFC 评分 → mediator → bridge 解析动作。**OFC 评分依赖 candidate 携带的 `drive_impact_schema`**。
- 重建可保 OFC/peer-circuit/mediator/bridge 冻结：**保留 3-profile 作结构化候选词汇**，anchor 退回"框可允许 profile 域 + L0 门禁 + impact 描述符"，LLM 在域内**产候选集成员（纳/排/排序 + action_hint）**（option(b)，真实影响而非 round-1e 的惰性重排）。
- model-off：`CandidateProducer` 协议 + `HeuristicCandidateProducer`（搬现 admit 逻辑）⇒ 字节等价。

## 2. 待 A 裁（G1 设计 + token 卡点）
- **Q1/Q2 关键裁示**：候选词汇保留 3-profile（推荐、最外科、OFC 零改）vs LLM 直产 17 动作（需给每动作定 impact、破 OFC 冻结）。
- **防 passivity（Q3）**：drive 强制底线（drive 对齐候选必在集内，LLM 不得移除）+ OFC 冻结评分 + RPE bias。
- **token**：live producer ≈ ~2–3K/次 × N=60 ≈ **~¥0.15–0.20/run**，仅 bounded 短跑。
- 六问完整答案 + slice 计划（G-1..G-7，分阶段：先无-LLM 结构验等价、后 live-LLM 短跑）+ 冻结 tests + docs-sync 见 `current-intake.md`。

## 3. 下一步（B 已停在 G1）
等 A 在 board 写 `APPROVED`（含 Q1/Q2 裁示 + token 批准）→ 被重新激活 → 阶段 1（无 LLM 结构 + 退役 ≤0.12/proposer + 验等价）→ 阶段 2（live LLM 短跑）→ G2。
