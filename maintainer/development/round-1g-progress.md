# Round 1.G — L3 Reasoning-Core Rebuild — Progress（B / 代码开发）

**当前状态**：**phase-1 结构重建 DONE**（drift 退役 + dlPFC producer seam，behavior-preserving，全量回归 **499 绿**，冻结 owner git-diff 干净）；**phase-2（live-LLM 产出器 + drive 底线防 passivity）待 A+用户敲定因果设计**（A 在 G1 已标注）。
**分支**：`claude/recursing-hertz-7c4029`。本轮 = round-1e/1f 的正解收口（proposer + ≤0.12 退役）。

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
