# scenario-time-model-run-final — discrete-step-driven Crafter baseline (PR-T3)

Date: 2026-05-29 ｜ Owner: B-claude-2 ｜ Task: `scenario-time-model-completion` PR-T3
Plan: `eva-coordination/plans/scenario-time-model-completion-substrate-scoping.md` §6
前置：PR-T1 + PR-T2 已 G2_APPROVED + FF main（commit `5945340`）—— Crafter 衬底真按 `clock_source="step"` 塌缩。

**这是第一个 step-时钟语义正确的 Crafter baseline**：主循环无墙钟 heartbeat/lease/yield，step 即脉搏，LLM 掉线归衬底，计数持久化。可作后续行为分析的干净基线，并据此重做之前 wall_clock 假设下的结论。

## Run metadata

- run_id: `eva-20260529121831-4f8ddb` ｜ individual: `individual-crafter-66e2d2b2a8bc`
- model: deepseek-v4-pro ｜ seed: 1 ｜ reasoning_effort: medium ｜ max_tokens: 8192 ｜ thinking: enabled
- runtime-dir: `validation-runs/scenario-time-model-run-final/runtime`（持久路径，非 /tmp）
- exit_reason: **max_steps** ｜ state: STABLE ｜ instance_valid: true
- wall clock: 12:18:31 → 14:02:17 = **103.8 min** ｜ ~62.3 s/step（瓶颈=dlPFC thinking 生成，非 input/衬底）

## shutdown tally（带标签，§6 #6 一眼懂）

```
scenario_step=100  step_attempts=103  env_steps=100
infra_failures=2   withholds=1   deferred=0
exit_reason=max_steps  instance_valid=true  state=STABLE
```

**103 step_attempts = 100 env.step + 2 infra + 1 withhold**（内部自洽）。

## §6 验收（9 项）

| # | 项 | 期望 | 实测 | 结果 |
|---|---|---|---|---|
| 1 | Crafter 主循环干净 | yield=0、无墙钟 tick | `event=tick`=0、`heartbeat_deadline_near`=0 | ✅ |
| 2 | 存在按步 | 预算=max_steps、step 节律 checkpoint | exit=max_steps、step_checkpoint 每 10 步 | ✅ |
| 3 | 核心不变式 | scenario_step==env.step==mediated release，失败 0 推进 | 100==100==100；response_history env_step_invoked 全 True | ✅ |
| 4 | LLM 掉线归衬底 | transport→重试+日志、不记 withhold、连续 K→needs_human | 2 transport_error → 2 step_infra_failure（孤立未连击）；真认知 withhold=3−2=1；deferred=0 | ✅ |
| 5 | 计数持久化 | scenario_step 等落 artifact | step_checkpoint 事件×10 + shutdown 含 scenario_step_index/attempt_index | ✅ |
| 6 | run 可读 | 带标签 summary | shutdown tally（env_steps/infra/withholds/deferred） | ✅ |
| 7 | 结构在场 | drive/学习/L1-L3 全链非策略函数 | dlPFC transcript×103、learning_outcomes/habit_bias 在场 | ✅ |
| 8 | **Linux 回归** | full 绿、wall_clock 行为不变 | `pytest -k linux` → 17 passed；run_turn 字节未碰 | ✅ |
| 9 | 100-step 验证跑 | 干净跑到 100 env.step | exit=max_steps、scenario_step=100、infra 透明 | ✅ |

## dlPFC LLM 响应

- 103 次调用：**101 ok / 2 transport_error / 0 parse_error**
- 2 transport_error = 2 infra failure（衬底层重试耗尽→归 infra、孤立未连击→未升 needs_human）
- 101 ok 里：100 → mediated release → env.step；**1 → LLM 正常返回候选但 mediator 默认抑制（真认知 withhold）**

## 对比旧 wall_clock baseline（llm-ontology run4，半解耦）

| | run4（wall_clock 半解耦，已弃） | **本跑（step 完整塌缩）** |
|---|---|---|
| 主循环时钟 | 墙钟 heartbeat tick | **step（env.step 即一拍）** |
| yield 事件 | **17 次**（heartbeat_deadline_near，墙钟脚手架噪声） | **0** |
| tick 事件 | 有 | **0** |
| LLM transport 失败归类 | 走 withhold（污染认知账，23 次混入） | **归 infra（step_infra_failure，2 次干净分离）** |
| 退出预算 | max_turns（墙钟 turn） | **max_steps（env.step 语义）** |
| 计数可查 | RunSummary 内存态、artifact grep 不到 | **step_checkpoint + shutdown 落 artifact** |

**结论**：rev2 的"半解耦"在 rev3（T1+T2）做完整——Crafter 主循环回到本来的样子，只有 step、无墙钟脚手架噪声；LLM 掉线是衬底无聊处理的事、不污染认知账。这是 EVA 实验的干净跑道。

## 给 A 的后续设计项（PM 反馈）

- **Q1 thinking 阶段策略**：验证/分析阶段保留（A 本体消费分析靠 reasoning 内容）；将来高吞吐长跑切 OFF 或换非推理模型（~10x 提速，当前 62s/step 几乎全是 thinking 生成）。
- **Q2 dlPFC prompt 语言**：实测 system 84% 英 / 16% 中（role contract 中文框架 + 英文本体）。**PM 判定混合是问题、应统一全英文**（影响 LLM 一致性 + 违 CLAUDE.md 公开主线英文）；A 跟进 role contract 全英化（关联 single-source-scenario-drive-metadata），未在本跑中改以保数据一致性。
