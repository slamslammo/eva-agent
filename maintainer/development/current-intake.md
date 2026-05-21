# Current Intake

> **当前执行项 = Round 1.H — Viz P1 全链路埋点（P1a+P1b）**。G1 intake + slice 计划全文见 `round-1h-viz-instrumentation-progress.md`（状态：G1_REQUESTED、待 A 批；0-token、opt-in `EVA_TRACE`、发射纯 additive、flag-off 字节等价）。
> 上一项 Round 1.G（L3 reasoning-core rebuild / dlPFC action_hint）已 **G2_APPROVED → DONE**（因果路径 live 证实 7/7、冻结 owner 净、model-off 等价）。见 `round-1g-progress.md`。
> 再上一项 Round 1.F（proposer eval）已 G2（结论：proposer 因果惰性 + live LLM 经 ≤0.12 推 passivity）。见 `round-1f-progress.md`。

## Round 1.G — L3 Reasoning-Core Rebuild（候选产出搬回 LLM/dlPFC）— G1 设计 Intake（B 提交，待 A 核设计 + 卡 token）

### 现状锚定（设计据此）
`anchor.admit_crafter_candidates` 枚举 3 profile → 每个 `_build_candidate` 产 Candidate（`candidate_profile` + `drive_impact_schema=COMPATIBILITY_RELEASE_IMPACT[profile]` + `action="compatibility_release"`）。下游：OFC `assess_candidates` 按 `drive_impact_schema` drive 加权评分 → mediator 选+放 → Crafter bridge 把 profile 解析成具体动作（Fix-B obs-directed）。**OFC 评分依赖 candidate 携带的 `drive_impact_schema`** —— 这是"冻结 OFC + 让 LLM 产候选"的关键约束。

### §5 六问回答

**Q2（anchor 只框域）+ Q1（LLM 怎么产候选）**——绑定回答，推荐**保留 3-profile 作结构化候选词汇**（最外科、OFC 零改）：
- anchor 拆成：①`bound_candidate_domain(agent_state)` = 返回**可允许 profile 集**（L0/结构门禁：escalate iff pressure；stabilize/observe 恒允许）+ 每 profile 的 `drive_impact_schema` 描述符（`COMPATIBILITY_RELEASE_IMPACT` 留作**域描述符**，不再当"最终候选枚举器"）。anchor 仍持框域 + L0 门禁（红线保留）。
- LLM（dlPFC）：在 bound 域内 + drive broadcast + memory 下，产 **schema-bound JSON ranked 候选集** = `[{candidate_profile∈域, action_hint∈该profile eligible动作(可选), rationale}]` + confidence。framework normalize → Candidate（attach 该 profile 的 `drive_impact_schema`；域外/非法 reject+log）。
- **与 round-1e 惰性 proposer 的本质差别**：proposer 只**重排**固定 3 候选（被 OFC max-by-score 抹平 → 惰性）；本轮 LLM **决定候选集成员**（可纳/排 profile + 选 action_hint）→ 真实影响 mediator 的可选集，**非顺序**。option(b) 的具体形态。
- 备选（更大、暂不推荐）：LLM 直接产 17 动作候选——需给每动作定 `drive_impact_schema`（现仅 3 profile 有），破"OFC 冻结"。**请 A 裁 Q1/Q2：保留 profile 词汇（推荐）vs 直产动作。**

**Q3（防 passivity 塌缩）**——三重约束（直接应对 round-1f 的 90% sleep）：
1. **drive 强制底线**：framework 按 top_drive 强制注入 drive 对齐候选（如 acquisition 高 → escalate 必在集内），LLM 可**加/排序但不得移除** drive 命令的活跃候选 → 杜绝"LLM 把活跃选项饿死"。
2. **OFC 冻结评分**：LLM 候选仍由 drive 加权 OFC 打分；偏被动候选在 drive 需行动时分低。
3. **RPE/learning bias 冻结**：继续按历史 outcome 修正。
→ "LLM 为 drive 服务地推理"：drive 定所欲、anchor 框可行、OFC 评估、mediator 守放行；LLM 不得反客为主。

**Q4（model-off fallback）**：新 `CandidateProducer` 协议 + `HeuristicCandidateProducer`（= 现 `admit_crafter_candidates` 逻辑搬入）。`local_rule_based`/model-off ⇒ 用确定性 producer ⇒ 候选与今日**字节等价**（behavior-preserving）。

**Q5（token 估算）**：live-LLM 产候选 = 每 deliberation 1 次 LLM 调用 × N。候选产出 prompt 比 round-1f advisory 略大（带域+drive+memory）→ 估 **~2–3K token/次** → **N=60 ≈ ~150–180K tokens ≈ ~¥0.15–0.20/run**（按 ¥0.95/M）。仅 bounded 短跑。**≲¥2 自动放行**。

**Q6（分阶段省 credit）**：
- **阶段 1（无 LLM，0 credit）**：建 `CandidateProducer` 协议 + HeuristicCandidateProducer（搬现逻辑）+ anchor 拆成框域 + 删 `_llm_advisory_bonus`(≤0.12) + 退役 round-1e proposer/ModelBackedProposer 接线。**验 model-off 字节等价 + 冻结 owner git-diff 干净 + 全量回归绿**。
- **阶段 2（live LLM，bounded）**：`LLMCandidateProducer`（schema-bound JSON、bounded、错误/超时 fallback heuristic）+ drive 底线约束 → bounded 短跑验行为 + 是否防住 passivity。

### Slice 计划（每 slice 一 commit；G1 后执行）
- G-1 failing tests：producer 协议 / model-off 等价 / ≤0.12 已删 / LLM 无释放权 / drive 底线存在。
- G-2 `CandidateProducer` 协议 + HeuristicCandidateProducer（搬 `admit_crafter_candidates`）+ 接入 `build_action_domain`/`run_deliberation`（model-off）。behavior-preserving。
- G-3 删 `value_judgment._llm_advisory_bonus`(≤0.12) + 退役 round-1e `proposer.py`/lifecycle 接线（superseded）。回归（test_value/test_reasoning_proposal 断言数据更新或移除）。
- G-4 drive 底线约束（强制注入 drive 对齐候选）。
- G-5 `LLMCandidateProducer`（schema-bound JSON + bounded + fallback）。
- G-6 lifecycle 在 `llm_assisted` 接 LLM producer；bounded 短跑 + passivity 检查。
- G-7 docs-sync + closeout。

### 冻结 tests
`tests/l3_deliberation/peer_circuit`、`tool_edge`、`l1_sensing`、`l2_drive`、`anchor`（结构性）、`kernel`、`test_existence_semantics`、`test_individual_identity`、`scenarios/linux_runtime`、`stability_metrics`、`inheritance_distillation`。
**允许断言数据更新/移除**：`test_value.py`（删 ≤0.12）、`tests/l3_deliberation/reasoning/test_reasoning_proposal.py`（proposer 退役 → 重写为新 producer 测试或移除）、`test_working_memory.py`。

### docs-sync（本轮，§7）
`implementation-tracking(.md/-zh)` L3 行标 `≤0.12 advisory + reorder-proposer = superseded(drift)` + `dlPFC 候选产出 = 本轮重建`；`blueprint §7.4` 注一句"早期 ≤0.12 占位已被 dlPFC 候选产出取代"。**eva-theory 不改**。

### 红线自检
不动 peer-circuit/mediator/release-authority/默认抑制/L1/L2/drive 计算/existence-semantics/L0 门禁；anchor 保留框域+L0；LLM 无释放权；model-off behavior-preserving。**请 A 核设计（尤其 Q1/Q2 profile vs 动作）+ 批 token**。
