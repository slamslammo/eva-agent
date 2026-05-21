# Round 1.E — L3 Reasoning Proposal Path — Progress（B / 代码开发）

**当前状态**：`DONE`（A 于 2026-05-21 G2_APPROVED；git diff + 实跑复核通过，红线 owner 0 改动、proposer reorder-only 限 admitted 域、model-off 字节等价、DP1/DP2 落实、86 reasoning/peer tests + 全量 503 绿）。前瞻（非阻塞，留后续 eval round）：proposer 为 reorder-only，影响集中 tie-break；后续 local/heuristic/llm eval 量化 reasoning-contribution 频率，过弱再加 lever 或上 (b)。
**分支**：`claude/recursing-hertz-7c4029`。

---

## 1. Feasibility 评估（基于真实 seam 代码，非自报）

逐一读取并核对了指令 §1/§12 列的 seam，结论：**可行，插入点干净，red-lines 可守**。

| seam | 核对结果 |
|---|---|
| `runtime.run_deliberation` | 流程与指令 §3 一致：`build_action_domain → build_candidates → assess_candidates → decide_release → audit`。proposer 槽位 = `build_candidates(action_domain)` 与 `assess_candidates` 之间。run_deliberation 是纯函数（输入 `DeliberationInput`），**不持有 model-client**——advisory 在上游 `build_deliberation_input_from_store` 组装进 `working_memory_context`。 |
| `reasoning/candidate_generation.build_candidates` | = `[schema.to_candidate() for schema in action_domain.admitted_candidate_schemas]`。**anchor admitted schemas 即 proposer 的硬域边界**；proposer 只能在其中 rank/筛选。 |
| `contracts` | `Candidate` / `DeliberationInput` / `DeliberationAuditRecord` 均 frozen dataclass；audit `to_dict` 可加可选 `proposals`/`rejected_proposals`（additive，不破现有 reader）。 |
| `reasoning/value_judgment` | `assess_candidates` 内 `_llm_advisory_bonus_for_candidate_profile` 读 `working_memory_context.advisory_context.candidate_suggestions` + `confidence`，给匹配 profile 加 ≤0.12（`MAX_SEMANTIC_OVERLAY_BLEND=0.15`）。这是现有唯一 model lever。 |
| `reasoning/working_memory` | `build_working_memory_context_from_store(backend, llm_adapter, …)`；`llm_assisted` → `build_llm_working_memory_context` → `llm_adapter.build_advisory_context(...)` 产 `advisory_context`（candidate_suggestions / prediction_hints / confidence）。**model 调用路径已存在、可复用**。 |
| `peer_circuit/{mediator,selection}` | selection（`decide_release`）+ release authority；本轮**不动**。 |

## 2. Red-lines / invariants 可守性（§6 逐条）

1. **anchor pre-generative** ✅ proposer 只在 `admitted_candidate_schemas` 内；`conflict_detection.py` 3-profile whitelist 不动。
2. **mediator 唯一释放权 / peer-circuit 唯一选择权** ✅ proposer 只供候选；`decide_release` / mediator 不动。
3. **default inhibition** ✅ proposal 路径不触发任何 side effect。
4. **model 仅产 operational content** ✅ proposer 只产候选/排序；不写 drive/anchor/mediator/audit 语义/persistence/existence。
5. **`local_rule_based` behavior-preserving** ✅ model off ⇒ HeuristicProposer（确定性）/inert，候选与现状等价。
6. **append-only additive** ✅ audit 加可选 proposal/rejection 字段，无 schema 破坏、现有记录无新必填字段。
7. **Linux bit-exact** ✅ Linux 走同一 L3 路径，model off ⇒ 等价；以回归 + smoke 验证。
8. **bounded model use** ✅ schema-bound、timeout、失败 fallback heuristic；model 失败不得 crash deliberation 或释放未校验动作。

## 3. 待 A 裁示的设计决策点

见 `current-intake.md` 的 **DP1**（ModelBackedProposer 接 model 的方式：倾向 (a) 复用上游 advisory + proposer 注入；备选 (b) proposer 自产 schema-bound JSON）与 **DP2**（≤0.12 advisory 保留为次要信号）。

## 4. Slice 计划

E-1 failing tests → E-2 `ReasoningProposal` contract → E-3 Proposer 协议+两实现 → E-4 normalize+reject+audit → E-5 wire `run_deliberation` → E-6 reasoning-contribution audit → E-7 Crafter 集成测试 → E-8 docs+closeout。每 slice 一 commit（前缀 `[round-1e][E-x]`），逐 slice 全量回归自检，slice 间不停。

## 5. A 裁示固化（G1 APPROVED，2026-05-21）

- **DP1 → (a)**：复用上游 `advisory_context` + proposer 依赖注入 `run_deliberation`，不新增 LLM 调用。**Proposer 协议须让 (b)（自产 schema-bound JSON）日后 drop-in**（协议层预留扩展位）。
- **Scope**：本轮只交付 "seam + model 塑形 considered-set"；**不**把 (b)"模型从零多步结构化提议"塞进 E（留后续 round）。
- **DP2 → 保留** ≤0.12 advisory、`assess` 下游不动。**条件**：proposal-shaping 与 ≤0.12 两触点 audit **分别可见**（供 E-6 归因）；**model-off ⇒ behavior-preserving**。

## 6. Slice log（APPROVED 后一口气跑，slice 间不停）

- **E-1（failing tests）— ✅ done** `98b1da7`：`tests/l3_deliberation/reasoning/test_reasoning_proposal.py`，4 个 test 红（TDD）；全量回归 497 passed + 4 预期红、不 interrupt、Linux 不变。防御性 import 保持 suite 可 collect。
- **E-2（ReasoningProposal contract）— ✅ done** `af44170`：`contracts.py` 加 frozen `ReasoningProposal`（additive；optional action_hint/predicted_outcome 为 (b) 预留）。
- **E-3（Proposer 协议 + 两实现 + normalize）— ✅ done** `b94de3b`：`reasoning/proposer.py`。Heuristic（admitted 序、behavior-preserving）/ ModelBacked（DP1=a，复用上游 advisory 重排、不丢候选、无 advisory 退化 heuristic）/ `normalize_proposals`（域外 profile/action 拒绝+log）。E-1 (a)(b)(d) 转绿；(c) 待 E-5。回归 500 passed + 1 预期红。
- **E-4（audit additive）— ✅ done** `bf357ec`：`DeliberationAuditRecord` 加 optional `proposals`/`rejected_proposals`；to_dict 仅非空时输出 → inert 与 pre-1.E byte-identical。
- **E-5（wire run_deliberation seam）— ✅ done** `308816a`：`run_deliberation(proposer=…)`，admission 与 assess 间 propose→normalize→audit；空 shaping 回退全 admitted（不饿死 mediator）；`proposer=None`（含现有 lifecycle 调用）byte-identical。E-1 (c) 转绿，**4 个不变量全绿**，全量回归 **501 passed**。
- **E-6（reasoning-contribution audit）— ✅ done** `046d9b6`：`normalize_proposals` 返回 linkage（candidate_id→proposal_id）；`DeliberationAuditRecord.reasoning_contribution`{selected_candidate_id, source_proposal_id, source_provenance}；`run_deliberation` 关联 mediator 选中候选→其 proposal+provenance（heuristic / model_advisory）。新增 E-6 test，回归 **502 passed**。
- **E-7（Crafter 集成 + lifecycle 生产接线）— ✅ done** `96015a5`：lifecycle 在 `llm_assisted` 传 `ModelBackedProposer`（local/auto inert → byte-identical，**无需改任何 freeze/断言**）；`CrafterReasoningProposalIntegrationTests` 端到端证 llm_assisted 记 model_advisory proposals 塑形 considered-set、local 无 proposals、释放动作仍在 admitted 内且过 mediator。全量回归 **503 passed**。
- **E-8（docs+closeout）— ✅ done** `a56cc1a`：4 个 tracking 文档（EN+zh）加 L3 reasoning 提议路径行（implementation-tracking=partial / blueprint-map=landed mechanism）；G2 audit excerpt 生成 `validation-runs/round-1e-g2/audit-excerpt.json`；无 Crafter SPEC 改动（提议路径是框架 L3、非场景可观测面）；intake closeout。

---

## 7. G2 gate 包（B 提交，置 `G2_REQUESTED` 等 A 复核）

**实现状态**：E-1..E-8 全部落地（commits `98b1da7`→`a56cc1a`），分支 `claude/recursing-hertz-7c4029`，**全量回归 503 passed**。

按指令 §7 G2 五项证据：
- **(a) proposals 改变 considered set（vs local）**：`validation-runs/round-1e-g2/audit-excerpt.json` —— local 候选序 [stabilize_first, escalate_first]、无 proposals、选中 stabilize_first；llm 候选序经 model_advisory 重排为 [escalate_first, stabilize_first]、记 proposals(provenance=model_advisory)、`reasoning_contribution` 归因到 `prop-model-0`、选中 escalate_first。**模型塑形了 considered-set，进而改变了 tie-break 选择**。
- **(b) 非法 proposal 拒绝轨迹**：`test_reasoning_proposal.py::test_out_of_domain_proposal_is_rejected_and_logged`（域外 profile→rejections 带 reason）。
- **(c) authority-holds + default-inhibition**：`test_high_confidence_proposal_is_still_gated_by_mediator`（critical_blocked 下高置信 proposal 仍不释放）+ `test_proposal_path_has_default_inhibition`（proposer 无 select/release、normalize 纯函数）+ 集成 `CrafterReasoningProposalIntegrationTests`（释放动作仍在 admitted 内、过 mediator）。
- **(d) git diff 无释放权 / anchor / drive-ownership / schema 加宽**：`95fdd12..HEAD` 仅改 docs/lifecycle/contracts/proposer/runtime/2 测试；**mediator.py/selection.py/anchor//l2_drive//conflict_detection.py(3-profile whitelist) 全未触动**；contracts 改动皆 additive（to_dict 仅非空输出 → inert byte-identical）。
- **(e) Linux 等价**：Linux 默认 `local_rule_based` → proposer None → inert；frozen 套件（含 scenarios/linux_runtime、peer_circuit、tool_edge、anchor、l2_drive）全绿、未改任何断言。

**DP 落实**：DP1=(a) 复用上游 advisory、proposer 注入、无新增 LLM 调用，Proposer 协议预留 (b) drop-in；DP2 保留 ≤0.12（assess 下游未动），proposal-shaping 与 ≤0.12 两触点 audit 分别可见（`proposals`/`reasoning_contribution` vs assessment.reasons 的 advisory）。

**遗留（按指令 §8，非本轮）**：LLM-reasoning 长跑评估（local vs heuristic vs llm proposer：存活/achievements/no-op 率/归因占比/token-per-progress）为后续单独 validation round。

> 跑 slices 期间 board `Status` 保持 `APPROVED`；到 E-7 后置 `G2_REQUESTED`。
