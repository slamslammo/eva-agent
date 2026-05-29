# scenario-time-model-completion — G1 设计（B-claude-2）

**任务**：`scenario-time-model-completion` ｜ 分支 `scenario-time-model-completion`
**方案**：`eva-coordination/plans/scenario-time-model-completion-substrate-scoping.md`（rev3）
**性质**：G1 **设计文档**——审计 + 覆盖方案 + 分流点 + Linux 安全策略。**不含任何 kernel 代码改动**，等 A G1 gate 通过再进 PR-T1。
**北极星对齐**：衬底无聊化；`heartbeat=liveness / lease=身份 / withhold=认知抑制` 这些 EVA 概念**不拿来解决进程问题**；Crafter 的脉搏就是 step。

---

## 0. 审计：当前 wall_clock 衬底各机制保护什么

逐项追到代码（`eva/kernel/main.py` 主循环 + `lifecycle.py::run_tick/run_turn` + `instance.py::InstanceGuard`）：

| 机制 | 代码位置 | 它**真正**保护什么 | 是否墙钟耦合 |
|---|---|---|---|
| **heartbeat tick** | `main.py:231-234` 触发；`lifecycle.py::run_tick:568` | ① liveness 自报（写 `last_heartbeat_at`/`heartbeat_age`/`heartbeat_ok`）② 触发 lease 续期 ③ 算 life-state（STABLE/DEGRADED/CRITICAL by missed beats，`compute_life_state:542`）④ instance_valid 快照检查 ⑤ 持久化 runtime_state | **是**（按 `heartbeat_interval_sec` 墙钟周期跳） |
| **lease** | `instance.py::refresh_lease`（run_tick:579 调）；`snapshot.lease_not_expired` | **liveness 裁定**：心跳停（进程僵死/挂起）→ lease 过期 → `instance_valid=false` → 判死。防"进程还在但卡死仍被当活"。 | **是**（`lease_expires_at = now + lease_duration_sec`，墙钟续期） |
| **yield** (heartbeat_deadline_near) | `lifecycle.py::run_turn:679-692` | tick/turn 同线程下，防一个长 deliberation（LLM ~40-120s）把下一次墙钟心跳拖晚。`remaining ≤ turn_guard_window` 就让位。 | **是**（依赖"距下次墙钟心跳还有多久"） |
| **lock** (fcntl.flock) | `instance.py::acquire:56-61` | 单实例互斥：同一 runtime_dir 不能两进程同跑。run 开始 acquire、结束 release，**不依赖墙钟**。 | **否** |
| **generation** | `instance.py::start_instance:76`；`snapshot.generation_matches` | 检测"我被新实例顶替了"（陈旧实例）。start 时 +1、快照时比对。**不依赖墙钟**。 | **否** |

**关键结论**：
- **lock + generation 不是墙钟耦合的** → step 模式**原样保留**，不动。
- **heartbeat + lease + yield 才是墙钟脚手架** → step 模式用步节律 + per-call 超时替代。
- run2/3 的"进程活但判死"死锁根因正是 **heartbeat ↔ turn 同线程耦合 + lease 用墙钟裁 liveness**：LLM 久了错过心跳 → lease 过期 → instance_valid=false → 恢复代码又跑不到。step 模式把 liveness 改成"step 在不在推进"后，这条死锁路径**结构上消失**。

---

## 1. step 模式逐项覆盖

| wall_clock 机制 | step 模式怎么覆盖 |
|---|---|
| heartbeat tick（脉搏） | **step 本身就是脉搏**：每成功 `env.step` 即一拍。无独立墙钟 tick。 |
| heartbeat → liveness 自报 | liveness = **scenario_step 是否在推进**。每 step 写进度（last_step_index / step 时间戳供外部观测）。 |
| heartbeat → life-state | step 模式 life-state 由 **step 推进 / infra-failure streak** 决定，不由 missed-beats。STABLE=正常推进；CRITICAL/NEEDS_HUMAN=连续 infra 失败 K 次。（细节 T1 定；保持 life-state 概念但换驱动量） |
| lease（墙钟续期裁 liveness） | **取消墙钟 lease**。有界同步单实例 run，**lock 已保证单实例**，不需要墙钟 lease 续期。崩溃恢复（如未来需要）用 **step marker / checkpoint**（记最后 step），不用墙钟租约。 |
| yield（防心跳被拖晚） | **取消 yield**。step 模式无墙钟心跳要保护，长 deliberation 不会"拖晚"任何东西。防卡死改用 **per-call LLM 超时**（producer 的 chat 调用 bounded timeout）——这是衬底进程手段，不是 EVA 概念。 |
| 存档（按 heartbeat 写 runtime_state） | **每 N step checkpoint**（写 runtime_state + 计数 + outcome 分解）。自维护（self_check/persist_marker）走步节律。 |
| 退出预算（max_turns/max_runtime 墙钟） | **max_steps（env.step 数）**为主预算；max_runtime 可留作衬底级硬上限兜底（防真死循环），但不再是语义预算。 |
| lock / generation | **原样保留**。 |
| instance_valid（=lock∧generation∧lease） | step 模式 lease 维度去掉 → instance_valid = **lock_held ∧ generation_matches**（单实例 + 未被顶替）。liveness 不再走 lease 维度，改由 step 推进判。（T1 需明确 `InstanceSnapshot` 在 step 模式怎么算，见开放问题 Q2） |

**LLM 掉线（rev3 §3 Q1 落地）**：transport_error/超时 → **衬底层 bounded 重试 + 结构化日志**（记 step / 第几次重试 / 原因）→ 重试耗尽则该拍不产 step、`consecutive_infra_failure += 1` → 连续 K 次 → NEEDS_HUMAN。**绝不调 OFC/mediator，绝不记成 withhold**。`withhold` 自此只剩真认知抑制（想了但无好/安全动作、anchor/OFC 砍空）。

---

## 2. clock_source 分流点（手术刀式，Linux 零改动优先）

**推荐：在 `main.py::run_runtime` 顶层按 clock_source 二分，wall_clock 走现有循环代码原样不动，step 走新循环函数。**

```
run_runtime(config, ...):
    ... 装配 runtime（共用：scenario 激活 / InstanceGuard.acquire / 个体身份解析 / sink）...
    clock_source = get_active_existence_semantics().clock_source
    if clock_source == "step":
        return _run_step_loop(runtime, config, ...)     # 新增：干净步循环
    return _run_wall_clock_loop(runtime, config, ...)    # 现有 228-274 循环，原样抽出，零行为改动
```

- **`_run_wall_clock_loop`** = 把现在 `main.py:228-274` 的 while 循环**原样**抽成函数，一行逻辑不改 → Linux 行为字节级不变（最低风险）。
- **`_run_step_loop`** = 新写（rev3 §4 主循环）：`while scenario_step < max_steps and agent_alive:` → L1→L2→anchor→dlPFC(per-call 超时)→OFC→mediator→(release→env.step→step+=1 / withhold→不 step) / (LLM 掉线→衬底重试→连续 K→NEEDS_HUMAN) → 每 N step checkpoint。**复用现有认知机件**（`run_deliberation` / drive / anchor / mediator / 记忆 / 学习 —— 结构原样在场，红线 §5.1），只换驱动节律（步代替墙钟心跳/巡逻）。

**为什么不在共享循环里加 `if clock_source` 分支**：那会 diff Linux 走的同一段代码，Linux 回归风险高、且难证等价。顶层二分让 wall_clock 路径**完全不被触碰**。

**装配阶段共用**（两模式都要）：scenario 激活、`InstanceGuard.acquire`（lock）、`_resolve_individual_id`、trace/transcript sink、RunSummary。差异只在 while 循环本体。

---

## 3. Linux 安全策略（最高风险 gate，rev3 §5.2）

1. **wall_clock 路径零 diff**：`_run_wall_clock_loop` 是现有循环原样搬迁。提供"搬迁前后等价"证据——diff 应只是缩进 + 函数签名，无逻辑行变更。
2. **Linux full 回归全绿**（不只 `-k linux`，跑 full suite）。
3. **existence_semantics 默认 wall_clock**（`scenario_bundle.py:119`），任何未声明/bare-kernel 场景落 wall_clock 路径 → 现有行为。
4. **instance_valid / lease / heartbeat scope 不删**（红线 §5.3）：这些在 wall_clock 路径完整保留，只是 step 路径不走它们。是"按场景 scope 心跳"，不是判心跳没用。
5. step 路径的新代码**不 import/复用**任何会改变 wall_clock 行为的共享可变状态；若必须共享 helper，加测试锁其 wall_clock 行为。

---

## 4. PR 拆分建议（细化 rev3 §7）

| PR | 内容 | 关键测试 |
|---|---|---|
| **PR-T1** | ① `run_runtime` 顶层 clock_source 二分 ② `_run_wall_clock_loop` 原样抽出（Linux 零改动）③ `_run_step_loop` 新建：步驱动主循环 + per-call LLM 超时 + 每 N step checkpoint + 取消 yield/墙钟 lease ④ 计数持久化（scenario_step/attempt/schema_version 落 artifact） | Linux full 回归绿（R2）；step 循环单测：yield 事件=0、无墙钟 tick、scenario_step==env.step、失败 0 推进；checkpoint 落盘 |
| **PR-T2** | ① LLM 掉线归衬底：bounded 重试 + 结构化日志（不进认知路径）② `consecutive_infra_failure` → 连续 K → NEEDS_HUMAN ③ withhold 只留真认知抑制 ④ 干净 run-summary（带标签）⑤ 事件重命名（区分 infra-failure / withhold / deferred） | infra-failure 不记 withhold 单测；连续 K→NEEDS_HUMAN 单测；deliberation 计数=真思考验证 |
| **PR-T3** | 100-step Crafter 验证跑（写**持久路径** validation-runs/，跑完即归档）+ Linux 回归 + A 数据验证 | rev3 §6 验收 9 项；需 DeepSeek env（用户注入，进程内） |

T1/T2 是否合并 A 定。**T1 是 Linux 最高风险 PR，建议单独 gate**。

---

## 5. 开放问题（请 A G1 裁定）

- **Q1 life-state 在 step 模式怎么定义**：保留 STABLE/DEGRADED/CRITICAL 概念但由 step 推进/infra-failure 驱动？还是 step 模式 life-state 简化为 {alive, needs_human}？倾向前者（保概念一致性），但驱动量换成 step。
- **Q2 `InstanceSnapshot` step 模式形态**：lease 维度去掉后，`instance_valid = lock ∧ generation`。是给 `InstanceGuard` 加 step 模式分支，还是 step 循环根本不调 snapshot（只在 start 时 acquire lock + 校 generation 一次）？倾向后者（更干净，单实例有界 run 不需中途反复校）。
- **Q3 checkpoint 间隔 N + infra-failure 阈值 K**：建议 N=每 10 step、K=10（与现 MAX_CONSECUTIVE_DEFERRED 对齐）？由 config 暴露还是 scenario 声明？
- **Q4 patrol 在 step 模式的去留**：现 shallow/deep/full 墙钟巡逻。step 模式自维护走"每 N step"，那 patrol 三级 cadence 是折叠成单一 step-checkpoint，还是按 step 数保留三级？倾向折叠（衬底简化），但需确认不丢 L1 sensing 的语义（感知本身每 step 都做，巡逻只是 cadence 包装）。
- **Q5 max_runtime 兜底**：step 模式主预算 = max_steps。是否仍保留一个墙钟 max_runtime 作"防真死循环"硬上限（纯衬底兜底，不参与语义）？倾向保留但调大、明确标注非语义。

---

## 6. 守住的红线（自检）

- ✅ 不退化成无状态策略：step 循环复用全套 L1-L3/drive/anchor/OFC/mediator/记忆/学习，只换节律（§5.1）。
- ✅ Linux wall_clock 零改动（顶层二分 + 原样抽出，§5.2）。
- ✅ heartbeat/lease scope 不删（wall_clock 路径完整保留，§5.3）。
- ✅ 核心不变式保留：scenario_step==env.step、失败不推进（rev2 已证，T1 不回退，§5.4）。
- ✅ 本文档不含 kernel 代码改动——等 A G1 gate。

---

## 7. T1 准备：R-a/R-b/R-c 审计结果（A G1 通过后补，进 T1 编码前）

A G1 review（`eva-coordination/plans/scenario-time-model-completion-g1-review.md`）裁定 Q1-Q5 + 加 3 项必补。审计结果：

### R-a（🔴 env-done = 个体死亡链路）
- 现 wall_clock loop 已接：`main.py:247` `if action_runtime.terminated: exit_reason="individual_terminated"`。
- 个体生命周期（死亡→蒸馏→新个体）在 run 级：本 run 终态 archive + 下次 run `_resolve_individual_id` 按 `reset_semantics=new_individual` 铸新 id + `--inherited-priors-path` 载蒸馏 prior。
- **T1 动作**：`_run_step_loop` 的 `agent_alive` 条件须在每次 `env.step` 后检 `action_runtime.terminated` → `individual_terminated` 退出（复制 wall_clock 语义）。**加测**：step loop 遇 env done=True → 正确 individual_terminated 退出（rev2 max_turns 结束没死过，必须新测）。

### R-b（🟡 defer 路径去向）—— 决断：**保留为衬底错误日志 + 不 step（非 infra 重试、非 withhold）**
- 触发：`compatibility.py::select_response_action:133-165`——`bridge_policy.action_hint` 不在 `_ALL_ACTIONS_SET` 时 `is_deferred=True, deferred_reason="no_valid_raw_action"`。
- raw-action 架构（producer 只产 admitted 合法 raw action + anchor 预过滤）下 live 0 样本，但它是 mediator 放行后 bridge 映射不到合法 action 的**防御 fallback**——非结构上不可能（如未来非-raw-action profile 被放行、或 action_hint 空）。
- **决断**：不删（删防御 guard 有风险）、不归 infra（非 LLM 掉线）、不算 withhold（非认知抑制）。step 模式视为**"released-but-unexecutable" 衬底异常**：结构化日志（记 step + deferred_reason）+ 该拍不 step。**不计 infra-failure streak**（它不是连不上，是映射 bug 信号，应显式日志让人查，而非静默重试）。T1 在 step loop 显式处理此分支。

### R-c（🟡 共享机件墙钟假设）—— 结论：**无墙钟假设，step-safe，无需 step-delta 改造**
- drive：`drive_state.py` `base_decay`(固定值/per-update) + `_trend_from_delta`(看 delta 非墙钟秒) + `_apply_base_decay`(每次 update 减固定量)。**per-update 语义**，step 模式每 step 一次 update 即正确。
- memory：`retrieval.py`/`semantic.py`/`encoding.py` 按 situation_key/candidate_profile/life_state/drive 语义键检索，**无 recency-by-wall-clock / now() / total_seconds 衰减**。
- learning/habit：grep 无墙钟时间用法。
- **结论**：shared 认知机件不依赖墙钟 delta，step 节律下"结构保留"即正确，T1 无需改这些。（T1 编码时若发现新点再补。）

### T1 slice 计划（TDD，每 slice commit，Linux full 回归是 R2 硬 gate）
1. **抽出 `_run_wall_clock_loop`**（纯搬迁，diff 仅缩进+签名）+ full/Linux 回归绿（等价证据）。
2. **`run_runtime` 顶层 clock_source 二分**（wall_clock→现有循环；step→新循环）。
3. **`_run_step_loop` 骨架**：step→感知→drive→anchor→dlPFC(per-call 超时)→OFC→mediator→release→env.step→step+1；无 heartbeat/lease/yield；snapshot 仅 start（Q2）。
4. **R-a env-done→individual_terminated** + 测。
5. **每 N step checkpoint**（N=10 config，Q3）+ 计数持久化（scenario_step/attempt 落 artifact，修 rev2 审计缺口）。
6. **R-b defer 分支**（结构化日志+不 step）。
7. **max_steps 预算 + max_runtime watchdog**（Q5，显式标注非语义）。
8. **patrol 折叠**（Q4：列 shallow/deep/full 各功能，证 step 节律下仍发生）。
9. life-state step={STABLE,NEEDS_HUMAN}（Q1，保 enum 字段）。
（LLM 掉线→infra 重试 + run-summary 归 PR-T2；R-a 死亡归 T1。）
