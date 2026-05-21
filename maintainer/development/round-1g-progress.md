# Round 1.G — L3 Reasoning-Core Rebuild — Progress（B / 代码开发）

**当前状态**：`G1_REQUESTED`（设计 intake 见 `current-intake.md`，等 A 核设计 + 批 token）。
**分支**：`claude/recursing-hertz-7c4029`。本轮 = round-1e/1f 的正解收口（proposer + ≤0.12 退役）。

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
