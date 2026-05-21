# Phase 3 — Crafter 长跑计划

> EVA-Crafter 第一次正式长跑的执行计划与评估。涵盖：执行动作、token / 成本、
> 执行过程影响、执行后分析（D-6）、前置检查、两阶段执行方案。
>
> 基础设施：Round 1.D（`runners/longrun_validation.py` + CLI longrun flags）。
> 数据基线：`validation-runs/phase1.7-live-smoke/`（5min / 211 turns 实测）。

---

## 0. 重要提醒：旧命令已失效

主索引 `federated-snacking-engelbart.md` 里的 Phase 3 命令用了
`--working-memory-model-client-mode deepseek`，**该 mode 在 Round 1.7-c 已删除**。
现在必须用 `--working-memory-model-client-mode live` + `source .local-archive/llm.env`
（EVA_LLM_* 环境变量）。本文件的命令是更新后的正确版本。

---

## 1. 核心变量：turn 速率取向

phase1.7-live-smoke 实测 **43 turns/min**（heartbeat 1.0s 等极限加速配置）。
6h 外推随节律差异巨大，这是**首先要拍板**的：

| 取向 | 配置 | 6h turn 数 | LLM calls | 性质 |
|---|---|---|---|---|
| **A. 吞吐 / 压力** | 沿用加速（heartbeat 1s、idle-sleep 0.01s、patrol 0.5/2/5s） | ~15,000 | ~15,000 | 大量行为样本；成本 / 磁盘高；偏"压力测试"而非"自然生命" |
| **B. 自然节律** | heartbeat 5-15s | ~2,000-4,000 | ~2,000-4,000 | 接近 EVA "持续运行体" 真实生命节律；成本低；样本少 |

> 取向 A 适合"快速攒大量样本看行为分布"；取向 B 适合"观察长时间真实节律下的演化"。
> 第一次长跑建议先 A（拿样本），后续若要研究节律再单独 B。

---

## 2. 执行命令（更新版）

### 30min 验证跑（取向 A）

```bash
source .local-archive/llm.env
python -m runners.run_crafter \
  --runtime-dir validation-runs/crafter-30min-validate/runtime \
  --max-runtime-sec 1800 \
  --heartbeat-interval 1.0 \
  --recovering-window 0.05 \
  --idle-sleep-sec 0.01 \
  --turn-guard-window 0.01 \
  --shallow-patrol-interval 0.5 \
  --deep-patrol-interval 2.0 \
  --full-report-interval 5.0 \
  --working-memory-backend llm_assisted \
  --working-memory-model-client-mode live \
  --working-memory-model-client-timeout-sec 15.0 \
  --longrun-snapshot-dir validation-runs/crafter-30min-validate/snapshots \
  --longrun-hook-interval-sec 300
```

### 正式 6h 跑（取向 A）

```bash
source .local-archive/llm.env
caffeinate -i \                              # ← 6h 无人值守必须：防 Mac 休眠挂起进程
python -m runners.run_crafter \
  --runtime-dir validation-runs/crafter-6h/runtime \
  --max-runtime-sec 21600 \
  --heartbeat-interval 1.0 \
  --recovering-window 0.05 \
  --idle-sleep-sec 0.01 \
  --turn-guard-window 0.01 \
  --shallow-patrol-interval 0.5 \
  --deep-patrol-interval 2.0 \
  --full-report-interval 5.0 \
  --working-memory-backend llm_assisted \
  --working-memory-model-client-mode live \
  --working-memory-model-client-timeout-sec 15.0 \
  --longrun-snapshot-dir validation-runs/crafter-6h/snapshots \
  --longrun-hook-interval-sec 1800            # 每 30min 一个 stability snapshot
```

取向 B 在此基础上把 `--heartbeat-interval` 调到 5-15s（并相应放宽 patrol intervals）。

### tripwire（默认开启）

- `--longrun-tripwire-max-constraint-violation-rate 0.0`：任何 constraint violation 即停
- `--longrun-tripwire-min-continuity-score 0.5`：continuity 跌破 0.5 即停
- 关闭：两者传负值

---

## 3. Token / 成本消耗

### Token 记录现状（调查结论）

- **DeepSeek API 每次返回完整 usage**（OpenAI Chat Completions 协议标准）。实测一次：
  ```json
  {"prompt_tokens": 203, "completion_tokens": 66, "total_tokens": 269,
   "prompt_cache_hit_tokens": 128, "prompt_cache_miss_tokens": 75}
  ```
  含 **context caching**：system prompt 被缓存（128 tokens 命中），大幅降低重复 input 成本。
- **但当前没落盘**：model client 的 `_openai_compatible_text_response` 只取
  `choices[0].message.content`，丢弃了 `usage`；`llm_advisory_audit.jsonl` 不含 token。
- **后续补**（本次长跑不改）：在 transport / response 层提取 `usage` 记进 audit，
  约 5-10 行小改动。这关系到后续"关注上下文规模 + LLM token 量"的需求 —— 是个
  独立的小 follow-up（属主线 model client）。

### 成本估算（基于实测 269 tokens/call + cache）

单次 ~$0.0001（cache 命中拉低 input 成本，远低于不含 cache 的粗估）：

| 取向 | calls | 估算成本 |
|---|---|---|
| A（15k） | ~15,000 | **~$1.5** |
| B（3k） | ~3,000 | **~$0.3** |
| 30min 验证（~1,290） | ~1,290 | **~$0.13** |

**不确定性**：`deepseek-v4-flash` + `thinking.disabled` 的精确单价需以 DeepSeek 平台
dashboard 实际账单为准（v4-flash base 单价是否高于 deepseek-chat 我不能 100% 确定）。
30min 验证跑后看 dashboard 即可校准。

### 模型选择

- **deepseek-v4-flash + thinking.disabled**（phase1.7 已验证，211/211 成功）—— 当前 env 默认
- **deepseek-chat**（legacy alias，定价更便宜确定，~$0.0001/call）—— 若成本敏感的备选

---

## 4. 执行过程影响

| 维度 | 评估 |
|---|---|
| **磁盘** | 实测 9.4M / 5min（加速）。取向 A 6h ≈ **~677M**（`deliberation_audit` 占 ~330M）；取向 B ≈ ~130M。`validation-runs/` 已 gitignored |
| **内存** | runtime 进程稳定（heartbeat 循环 + 每 tick 持久化）；semantic memory 进程内 cache（Round 1.C-1）随 turn 增长，15k turns 估几十 MB，可接受 |
| **网络 / API** | 串行单 agent，QPS<1，远低于 DeepSeek 任何并发限制；6h 持续调用 |
| **进程稳定性** | retry/fallback（1.7-b：5xx/timeout 指数退避 3 次 → heuristic 兜底，不崩）；崩溃可从持久化状态恢复；tripwire 早停 |
| **Mac 休眠** | **6h 无人值守最大实操风险** —— 系统休眠挂起进程。正式 6h 必须 `caffeinate -i` 包裹（30min 验证可省） |
| **网络抖动** | 单次失败走 retry → 耗尽走 heuristic fallback，长跑不中断；advisory 质量临时降级，会记入 `reasoning_trace`（`live_client_fallback:...`） |

---

## 5. 执行后分析（D-6）

跑完后的分析维度：

1. **stability metrics 7 指标轨迹**（从 `snapshots/profile-*.json`）：
   constraint_violation_rate / continuity_preservation_score /
   useful_progress_under_constraint / recovery_success_rate /
   mean_time_to_recovery_sec / recovery_path_entropy / cost_ratio
2. **L3 profile 分布**：observe/stabilize/escalate 占比 —— **finding #2 复检**
   （短跑里 75-90% stabilize 主导，长跑是否仍然）
3. **action 多样性**：是否仍只出 `move_left` —— **finding #3 复检**
   （habit 累积后是否出现方向分化 + 工具动作）
4. **drive 轨迹**：exploration drive 长期是否健康（不恒 0、不过饱和）
5. **memory 累积**：semantic_memory 是否还是 0 —— **finding #1 复检**；
   habit_bias 累积曲线
6. **副产物**：给视觉线提供真实长跑数据。viewer 实时 `--runtime-dir` 指向
   `validation-runs/crafter-6h/runtime` 即可边跑边观察

工具：viewer（实时观察） + `stability_metrics`（已有） + D-6 报告（待写）。

---

## 6. 前置检查清单

- [ ] **命令更新**：`live` mode + `source .local-archive/llm.env`（旧 deepseek mode 失效）
- [ ] **caffeinate 包裹**：正式 6h 必须，防 Mac 休眠
- [ ] **turn 速率取向**：A（吞吐）还是 B（自然节律）
- [ ] **模型选择**：v4-flash+disabled（已验证）vs deepseek-chat（更便宜确定）
- [ ] **成本验证**：30min 验证后看 DeepSeek dashboard 实际单价
- [ ] **tripwire 确认**：默认开（任何 violation 即停）还是放宽
- [ ] **磁盘空间**：确认 ~1GB 可用（取向 A 6h）

---

## 7. 两阶段执行方案（已确认）

### 阶段一：30min 验证跑（取向 A 加速）

验证：
1. **实际成本单价** —— 跑完看 DeepSeek 平台 dashboard
2. **进程稳定性** —— 无崩溃 / 无内存泄漏 / retry-fallback 行为正常
3. **tripwire 不误触发** —— constraint/continuity 在正常范围
4. **数据 schema 完整** —— 各 trace 文件结构与 viewer 兼容（已知 schema 稳定）

预期：~1,290 turns，~$0.13。

### 阶段二：正式 6h 跑

基于验证结果定：
- 取向 A / B
- 是否调 tripwire 阈值
- 是否先补 token usage 记录（独立小 follow-up）

---

## 8. 关联

- 基础设施：`runners/longrun_validation.py`（Round 1.D）、`maintainer/development/round-1d-progress.md`
- 数据基线：`validation-runs/phase1.7-live-smoke/`
- 视觉观察：`observation_tools/`（viewer，实时 `--runtime-dir` 指向长跑输出）
- 后续分析：D-6 报告（待写）
- 主索引：`.claude/plans/federated-snacking-engelbart.md`
