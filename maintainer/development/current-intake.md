# Current Intake

> 只保留**当前正在执行**的一项 intake。上一项（Round 1.E L3 reasoning proposal path）已 DONE（G2_APPROVED），见 `round-1e-progress.md`。

## Round 1.F — Proposer Eval（local/heuristic/llm 短跑对比）— G1 Intake（B 提交，待 A 批 token 预算）

### 目标
量化 round-1e proposer（reorder-only）是否真改变行为，落到 §4 三结论之一。**只测量、不改** proposer / mediator / anchor / selection / value_judgment。

### 三档配置 + heuristic≈local 结论
- **local**（基线）：`--working-memory-backend local_rule_based` → proposer None（inert，无塑形，audit 无 `proposals`）。
- **heuristic**：HeuristicProposer。**结论：heuristic ≈ local（行为等价）**——round-1e 已证 `HeuristicProposer→normalize_proposals == build_candidates`（同候选、同序 ⇒ 同 tie-break ⇒ 同选择）；唯一差异是 audit 多 heuristic-provenance `proposals`。且 lifecycle **无**"传 HeuristicProposer"的生产 backend（只有 `llm_assisted` 传 ModelBackedProposer，其余 None），要单独全程跑 heuristic 需改 lifecycle 接线 = 违反"不改行为"红线。→ **heuristic 不单独全程跑，作分析性 behavior-neutral 机制对照**；实跑 = local vs llm。
- **llm**：`--working-memory-backend llm_assisted --working-memory-model-client-mode live`（DeepSeek，`EVA_LLM_*` env）→ ModelBackedProposer。**唯一花 credit 档。**

### `--seed` 验证（✅ 已验证 + 提交 `6ccd90e`）
A 的 WIP 验证通过：同 seed ⇒ 同世界 + 同轨迹（给定同动作）、异 seed ⇒ 异世界（seed1 spawn cow+4 树 / seed7 无 cow+2 树）。三档用同一 `--seed` + 同 `--max-turns` 保证可比。behavior-neutral（default None=随机，旧行为不变）。

### 选定 N
**N = 60 turns**（`--max-turns 60` + `--max-runtime-sec` 安全帽）。bounded、够快速定性（看 proposal 是否改选 + 存活/achievements/no-op 趋势），不追求长跑统计严谨（§7）。三档同 N 同 seed。

### llm 档 token 估算（A 在此卡 credit）
- 每 deliberation turn 1 次 LLM advisory 调用，~2900 token/次（按 30min 实测 2.96M tokens / 1029 calls ≈ 2877）。
- N=60 → ≤60 次调用（heartbeat-skip / reflex turn 不 deliberate，实际 <N）→ **≤ ~175K tokens / 次完整 llm 档跑**。
- DeepSeek 成本（按 30min 实测 ¥2.82 / 2.96M ≈ ¥0.95/M）→ **≤ ~¥0.17 / 次 llm 档跑**。bounded、极低。
- 执行顺序：先 N=20 短验证确认归因频率非零 → 再 N=60 正式。local 不花钱可先跑。

### 复用 infra + eval 脚本
- `runners/run_crafter`（`--seed` / backend / model-client-mode / `--max-turns`）。
- round-1e audit：`deliberation_audit.jsonl` 的 `proposals` / `reasoning_contribution`；`response_history.jsonl`（动作分布 / no-op）；observation achievements；ticks/turns 存活。
- **新增 eval 跑分脚本**（工具侧，`runners/` 或 `validation-runs/`，**不碰 `eva/`**）：对齐 local vs llm 同 seed 同 turn 的 `selected_action` → 算"proposal 改变选择"的 turn 占比（核心归因指标）+ 存活 + achievements + no-op 率 + llm token。

### 指标 → 结论
归因频率（llm vs local 同 turn 选择差异占比 + `reasoning_contribution` provenance 佐证）/ 存活 / achievements / no-op / llm token/progress → 落 §4 之一（①几乎无效→加 lever 或上 (b) ②弱效仅 tie-break ③决策效果明显→保留深化）。

### 红线自检
不改 proposer/mediator/anchor/selection/value_judgment；唯一代码改动 = `--seed`（已提交、behavior-neutral）+ eval 脚本（工具侧）。llm 档 token bounded，**待 A 批准后才跑 llm 档**。
