# Current Intake

## Active Item

`ofc-robust-scoring` **PR-O3**（出口 PR）— 用 scenario-time-model-run 干净数据复核标定（区间/权重/经验组上限）+ 极端 regime 验证 + Linux A/B 对照；全链 canonical demo 等 warmup 落地后跑。

Coordination owner: `B-claude-2`
Branch: `ofc-robust-scoring`（worktree `/Users/mojiawen/Documents/claude_projects/eva-agent-ofc`，tip 87929ed）
Plan source:
- `eva-coordination/plans/ofc-robust-scoring-plan.md` §7(PR-O3) / §9(验证) / §10+§12.3(已敲定)
- `eva-coordination/plans/ofc-robust-scoring-g1-review.md` §3(caveat) / §5(PR-O2 G2_APPROVED → PR-O3)

## Change intake（6 点）

1. **层**：`l3_deliberation`（reasoning/value_judgment.py 评分聚合 + 测试）。如需再标定→只动 scale/weight 常数。
2. **canonical owner**：`value_judgment.py`（robust 聚合）+ tests/l3_deliberation/reasoning/。
3. **owner 类别**：stable（PR-O1/O2 已建 robust 主干，PR-O3 验证+精化，不扩职责）。
4. **slice 归属**：ofc-robust-scoring task 的出口 PR（PR-O3），承 PR-O1（聚合）+ PR-O2（dlpfc rank）。
5. **freeze tests**：现有 Linux 17 + full 749 = 基线；PR-O3 新增极端 regime 测试**不得弱化** Linux A/B 排序断言。
6. **同步文档**：`maintainer/development/ofc-robust-scoring-g1-design.md`（标定复核结果 + 极端 regime caveat）；本文件。

## Slice plan (TDD)

| # | Slice | Touches | Notes |
|---:|---|---|---|
| 1 | 极端 regime 验证测试：①类别层 drive 兜底（water-critical 朝水类别胜出）②同类内 dlpfc 方向透传 ③OFC 兜底反常 rank ④尺度可比（raw-action vs heuristic）| `tests/.../test_robust_scoring_extreme_regime.py`（新）| 纯 offline 构造极端输入；plan §9 行171/174 |
| 2 | 单因子作妖 + 经验组合谋测试：habit 尖峰 / habit+learning 同向尖峰，验组上限挡住、drive 主导 | 同上或新测试文件 | plan §9 行172/173 + §1.3 |
| 3 | T3 干净数据标定复核：复核 drive[-0.25,0.55]/权重/组上限初值是否合理；极端态判别力评估 | 探针脚本 + g1-design.md | review §3 caveat：温和标定未覆盖极端高端 |
| 4 | 标定结论 + caveat 文档化（若需小幅再标，**别过调** review §2）| g1-design.md | 出口文档 |
| (canonical) | 全链 post-warmup demo（一次跑双验 OFC 行为 + viewer）| 脚本 | **A 前置：warmup(crafter-life-panel-warmup) 落地 + DeepSeek env；现在不跑** |

## 红线 / 已敲定约束（plan §10 / §12.3，别重踩）

- **不加新因子**：CandidateEffectProjection / risk_cost / uncertainty_penalty 全已否决（§12.2）。
- **OFC 不重做 dlPFC 空间推理、不 LLM 化**（§12.4 核心判断）。drive 在类别层兜底，方向是 dlPFC 空间推理（OFC 只透传序）。
- **Q2 权重别过调**（review §2）：w_drive≈0.5 / w_dlpfc≈0.3 / 经验组≤0.2 是合理起点，关键不变量 w_dlpfc(0.3) > 经验 cap(0.2)。
- 归一化用**标定区间**不用候选集内 min-max（§10.2）；dlpfc v1 只 rank（§10.1）；projection_fallback v1 不清（§10.5）；权重 v1 全局（§10.4）。
- **Linux A/B 字节等价**：非 LLM 候选无 dlpfc_proposal_ref → 评分不变（PR-O2 已立，PR-O3 不得破）。

## Acceptance（plan §9）

| 指标 | 期望 |
|---|---|
| Linux 全回归 | 绿（共用评分，最关键）|
| Linux 评分前后对照 | 排序结论不变，或变化可解释 |
| Crafter 正常态 | dlPFC rank 被尊重（不再字母序兜底）— PR-O2 已立 |
| Crafter 极端态 | water-critical 朝水类别胜出 + 同类内 dlPFC 方向透传 + OFC 兜底反常 rank |
| 单因子作妖 | habit 尖峰不淹没合理选择 |
| 经验组合谋 | 组上限挡住、drive 主导 |
| 尺度不可比 | 标定区间归一后 raw-action vs heuristic 可比 |
| 全链 demo | post-warmup canonical（等前置）|

## Status: PR-O3 offline 部分完成（slice 1-4）

- slice 1 极端 regime 验证：`test_robust_scoring_extreme_regime.py` 8 测试 ✓（commit 1f76d11）
- slice 2 A/B 对照 + 尺度可比：`test_robust_scoring_ab_comparison.py` 5 测试 ✓（commit 98b2aff）
- slice 3-4 标定复核 + caveat 文档：`g1-design.md` §8 ✓
- 验证：full **762 passed** / Linux A/B **17 passed** / git diff --check clean
- 标定**不变**（极端 caveat 标注待 water-critical run 精化，review §2 别过调）
- **待 warmup**：全链 canonical demo（crafter-life-panel-warmup 落地 + DeepSeek，A 硬前置，不用 blind baseline）→ PR-O3 出口完成后请 A G2
