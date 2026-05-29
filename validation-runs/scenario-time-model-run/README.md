# scenario-time-model-run — clock_source=step 验证跑

Date: 2026-05-29 ｜ Owner: B-claude-2 ｜ Branch: `scenario-time-model-run`
Plan: `eva-coordination/plans/scenario-time-model-and-step-driven-execution-plan.md` §7
前置：PR-S1 + PR-S2 已 G2_APPROVED + 合入 main（commit 6160492 / 4b76d8b），clock_source 消费 + 文档全落地。

## ⚠️ 数据丢失（B 失误，如实记录）

本跑 **clean 跑完**（`exit_reason=max_turns`），但**原始产物丢失**：run 输出写到 `/tmp/scenario-time-model-run`（临时盘），跑完后归档被延迟（B 先处理 PM 的机制问答），期间 macOS `/tmp` 被清理 → 98+98 transcript + response_history / deliberation_audit / events 原文**无法找回**。

**根因**：① run 输出写 `/tmp`（ephemeral）而非仓内持久路径；② 跑完未第一时间归档。
**改进**：后续 live 跑直接写 `validation-runs/<task>/`（持久），跑完即 force-add。

下表 §7 指标是 **B 在跑完、数据仍在时已计算并记录的真实值**；原始数据不可复现（LLM 非确定性）。

## Run metadata（跑完时捕获）

- run_id: `eva-20260529061527-0229a8`
- model: deepseek-v4-pro ｜ seed: 1 ｜ reasoning_effort: medium ｜ max_tokens: 8192
- config: heartbeat=60 / lease=300 / turn_guard=1.0 / idle_sleep=0.05（run4 稳定配置）
- exit_reason: **max_turns** ｜ turns(executed)=100 ｜ ticks=60 ｜ instance_valid=true 全程（0 次 false）
- wall clock: ~74 min

## §7 验收指标（跑完时计算）

| 指标 | 期望 | 实测 | 结果 |
|---|---|---|---|
| env_step_invoked_count == mediated_release_count | == | 74 == 74 | ✅ |
| scenario_step_index 终值 == env_step_invoked_count | == | 74 == 74 | ✅ |
| attempt_index == scenario_step_index + deferred | == | 74 == 74 + 0 | ✅ |
| heartbeat 在 deferred 期间持续 | 持续跳 | 0 deferred；60 ticks 全程 instance_valid=true，无卡死 | ✅（heartbeat 健康；deferred 路径 vacuous，见下） |
| Linux 回归 | 全绿 | `pytest -k linux` → 17 passed | ✅ |
| consecutive_deferred ≥10 → needs_human | — | 未触发（0 deferred）；仅单测保证 | N/A live |
| 分离 telemetry 四值各自可查 | 可查 | release=74 / withhold=24 / transport_error=23 / env_step=74，可从 audit+history 派生 | ✅ |

## 关键计数（跑完时捕获）

- deliberation 总数: 98（dlPFC 98 / OFC 98）
- LLM parse_status: 75 ok / 23 transport_error / 0 parse_error
- mediator outcome: 74 compatibility_release / 24 withhold
- scenario step (env.step): 74 ｜ deferred (is_deferred): **0**
- yield (heartbeat_deadline_near, executed=false): 17（真实跨度 0.89s，= 心跳前 1s guard 窗内 idle_sleep=0.05s × ~17 次迭代，非卡死）

## ⚠️ deferred 路径 0 live 样本（gate 必读，勿被 §7 全绿掩盖）

本跑 23 次 LLM 掉不通（transport_error）**全部走 withhold 路径**（producer 返空候选 → mediator 默认抑制），**不是 PR-S1 的 defer 路径**（`is_deferred`，由 bridge `no_valid_raw_action` 触发）。因此：

- defer 计数器（is_deferred / consecutive_deferred / needs_human 护栏）在本 live 跑里 **0 样本**，仅由单测保证（`test_clock_source_load_bearing` / `test_compatibility_deferred_signal` / `test_execute_crafter_deferred`）。
- "env.step==mediated release" 与 "attempt==scenario_step+deferred" 在 deferred=0 下成立，但**未在 live 中压到 deferred 分支**。
- LLM 持续掉不通 → 连续 withhold → scenario time 冻、但 consecutive_deferred 恒 0 不升 needs_human（已立项 `withhold-streak-observability-guardrail` 给 A 跟进）。

## 结论

clock_source=step 消费在 live 100-turn 下**行为正确**（§7 全过，heartbeat 不冻结红线守住），是首个 discrete-step-driven 语义下的 Crafter 验证跑。**但原始 baseline 数据丢失** —— 是否需重跑取回原始 transcript 供 A §8 行为分析，待 A gate 裁定。
