# ofc-robust-scoring — G1 设计（B-claude-2）

**任务**：`ofc-robust-scoring` ｜ 分支 `ofc-robust-scoring`
**方案**：`eva-coordination/plans/ofc-robust-scoring-plan.md`（DRAFTED，评审已纳入）
**性质**：framework `value_judgment.py::assess_candidates` 评分聚合改动，跨 scenario（Linux+Crafter 共用）。**最高风险=Linux 回归**。
**北极星对齐**：OFC 规则化稳健聚合，不 LLM 化；只改聚合方式，不碰 anchor/dlPFC/mediator/drive。
**性质声明**：G1 **设计文档**，不含 kernel/framework 代码改动，等 A G1 gate 再进 PR-O1。

---

## 0. 审计：当前 value_judgment.py 评分聚合（eva/l3_deliberation/reasoning/value_judgment.py:14 assess_candidates）

当前 = **无界直接相加**：
```
score = 0.0
score  = drive_score                 # _drive_weighted_score(impact_schema, drive_levels)
score += projection_score            # _projection_fallback_score(conflict.score_delta, ...)  若 !=0
score += learning_bias               # _learning_bias_for_candidate_profile(...)
score += habit_priority_bonus        # _habit_skill_priority_bonus(...)  若 !=0
```
ScoreDecomposition（PR-Γ）已记 drive_weighted / projection_fallback / learning_bias / habit_priority_bonus / final_score —— **标定与 A/B 对照的现成观测点**。

**问题（plan §1 + T3 数据实证）**：异尺度因子直接相加无界 → 单因子冲极端/算错即淹没合理选择；平分时丢 dlPFC 序。

---

## 1. T3 baseline 标定数据（~96 clean step，剔前 2 warmup + 2 infra）

跨 245 个 candidate assessment 的因子分布（deliberation_audit.score_decomposition）：

| 因子 | min | max | mean | 评估 |
|---|---|---|---|---|
| **drive_weighted** | -0.2301 | 0.5517 | 0.0396 | **唯一有实区间的活因子**（跨度 ~0.78） |
| projection_fallback | 0.0 | 0.0 | 0.0 | **全程 0** —— 本 run 从不激活（死因子） |
| learning_bias | -0.2500 | 0.2500 | -0.1556 | 经验因子，常 -0.25 拉低（§3.7 组上限对象） |
| habit_priority_bonus | 0.0 | 0.0 | 0.0 | **全程 0**（本 run 无 habit） |
| final_score | -0.4801 | 0.6474 | -0.1161 | — |

**核心病实证**：**64/103 deliberation（62%）所有候选 final_score 相同 → 丢 dlPFC 序**。
**活样本 turn-0**：3 候选（move_up/left/down，LLM 有序有理由）全 final=0.0（drive/proj/learn/habit 全 0）→ flat → **withhold**（mediator 无法区分）。根因：warmup blind 态 drive_levels 低 + move_* 统一 impact schema → drive_weighted≈0 → 全平。

→ **dlpfc_preference(rank) 因子是破这 62% 平分的直接解**：LLM 给了序，OFC 不该把它抹平。

---

## 2. 稳健聚合设计（plan §3）

```
score = Σ_i  w_i · saturate( calibrated_normalize( factor_i ) )
```

### 2.1 三变换
- **calibrated_normalize**：每因子用**标定的绝对区间** + clip/tanh（**不用候选集内 min-max**，避免"全 0 也被拉成有序"的假信号 / 跨 turn 不可比）。rank 用固定映射。
- **saturate**：单因子贡献封顶（tanh/clip），0.99 与 0.90 不暴差。
- **weight**：显式 w_i；经验因子组另设组上限（§2.4）。

### 2.2 因子清单 + 标定区间（T3 数据 grounded 初值，PR-O3 终标定）

| 因子 | 来源 | calibrated range（初值，从 §1 数据）| 说明 |
|---|---|---|---|
| drive_alignment | drive_weighted | **[-0.25, 0.55]** clip→[0,1] 或 tanh | 主活因子 |
| **dlpfc_preference**（新） | dlPFC 输出 rank | 固定映射 **rank0=1.0 / rank1=0.6 / rank2=0.3** | 破平分、保 LLM 序 |
| learning_bias | inherited prior/RPE | **[-0.25, 0.25]** | 经验组 |
| habit_bonus | habit track | 标称区间（本 run 0，保守小区间）| 经验组 |
| semantic_overlay | 语义记忆 | 标称（当前 0.0）| 经验组 |
| projection_fallback | conflict.score_delta | 本 run 全 0 → **低权重/标注休眠**；不删（防御）| — |

### 2.3 权重（初值，PR-O3 标定）
- **drive_alignment + dlpfc_preference 为主导**（活因子 + LLM 序），建议初值 w_drive≈0.5、w_dlpfc≈0.3。
- 经验组（learning+habit+semantic）合计**组上限 ≤ 0.2**（§2.4），防"经验合谋淹没生存"（§1.3：learning_bias 常 -0.25，三因子合谋能压过 drive）。

### 2.4 经验因子组上限（plan §3.7）
`learning_bias + habit_bonus + semantic_overlay` 三者**归一后加权和再封一个组上限**（如 ≤0.2），使经验永远不能单独翻转 drive+dlpfc 的主判。

### 2.5 dlpfc_preference rank 来源（实现要点，T 阶段验证）
rank = 候选在 dlPFC producer 输出列表中的**位置**（LLM 按偏好序返回）。G1 需在 PR-O2 确认**该序从 producer→assess_candidates 全程保序**（candidate list 顺序不被中途重排）。v1 **只用 rank 不用 plausibility**（plausibility 仅记录）。

---

## 3. clock 两 regime 行为（plan §3.5，Crafter 例）
- drive 有明显信号（饥渴/威胁）→ drive_alignment 主导，dlpfc 微调序。
- drive 平（warmup/探索期，如 turn-0）→ **dlpfc_preference 接管破平分**（不再 flat→withhold/字母序）。这正是 §1 活样本要修的。

---

## 4. PR 拆分（plan §7）
| PR | 内容 | gate |
|---|---|---|
| **PR-O1** | calibrated normalize + saturate + weight + 经验组上限（value_judgment.py 聚合重写），权重/区间保守初值 | A G2（framework 核心+跨 scenario） |
| **PR-O2** | dlpfc_preference(rank 固定映射)接入 + 替换字母序 tiebreak；plausibility 仅记录 | A G2 |
| **PR-O3** | 用 T3 干净数据标定区间+权重+组上限 + **Linux A/B 对照** + 全链 demo | A 出口 |

PR-O1 是 Linux 最高风险（共用评分重写），建议单独 gate + 等价考量。

## 5. Linux 安全策略（最高风险，plan §6）
1. `assess_candidates` 跨 scenario 共用 → Linux 也走新聚合。**必须 Linux full 回归绿**。
2. **A/B 等价考量**：保守初值下，新聚合对 Linux 现有候选的排序应与旧直接相加**一致或可解释**（PR-O3 给 A/B 对照证据）。
3. 标定区间默认值需保证 Linux 因子（drive 等）落在合理区间、不被 clip 误伤。
4. ScoreDecomposition 字段保留 + 扩展（加 normalized/weighted 分量），不破坏下游 OFC_classical transcript reader。

## 6. 红线自检
- ✅ 只改评分聚合，不碰 anchor/dlPFC/mediator/drive（聚合在 assess_candidates 内）。
- ✅ OFC 规则化不 LLM 化（normalize/saturate/weight 都是确定性数学）。
- ✅ Linux 回归 + 等价（PR-O1/O3 gate 硬条目）。
- ✅ dlpfc_preference v1 只用 rank（不用 plausibility 评分）。
- ✅ 本文档不含代码改动 —— 等 A G1 gate。

## 7. 开放问题（请 A G1 裁定）
- **Q1 normalize 用 clip 还是 tanh**？drive [-0.25,0.55] 不对称 → clip 到 [0,1] 会丢负向（drive 反向=该惩罚）。建议 tanh（保符号+饱和）或对称 clip [-0.55,0.55]→[-1,1]。A 定。
- **Q2 权重初值**：w_drive≈0.5 / w_dlpfc≈0.3 / 经验组 ≤0.2 是否合理起点？还是 dlpfc 该更高（破平分是主诉求）？
- **Q3 经验组上限值**：≤0.2 够不够压住 learning_bias 的 -0.25 单点？组上限是封"和"还是封"每个"？
- **Q4 projection_fallback 处置**：本 run 全 0（休眠）。给低权重保留，还是本 plan 顺手标 deprecated？（关联 mediator-projection 调查结论）
- **Q5 dlpfc rank 保序验证**：producer→assess_candidates 的 candidate 顺序是否已保证不重排？若中途按 id 排过（earlier 字母序 bug 根因），PR-O2 需先修保序再接 rank。
