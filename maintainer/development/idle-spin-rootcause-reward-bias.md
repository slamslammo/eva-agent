# 空跑根因（深挖）：奖励错配 + 习惯收窄锁定

**数据来源**：`validation-runs/rev2-a2-life/`（当前 B+A 代码，一局完整生命：ticks=50 / turns=226 / exit_reason=individual_terminated，local_rule_based，无 LLM）
**前序**：`shortrun-behavior-analysis-and-fix-plan.md`（30min 数据，把 sleep 主因归为 escalate `drive_impact_schema` 反转）+ 修复 `111c667`（escalate schema + admit 耦合）。
**本文件结论**：**前序修复未解决空跑** —— 修复后再跑仍 91% sleep、escalate 整局 0 释放。真正的锁定机制更深：**Crafter 结果观测器的奖励错配 → 习惯学习把 sleep 学成"好"、do 学成"坏" → 习惯收窄把 escalate profile 直接剪掉**。本文件只出方案，不实施。
**工作模式**：短跑 → 分析 → 深入 → 出方案 → 修复 → 循环。

---

## 0. 一句话结论

agent 仍 **91% sleep、原地睡到 HP=0 的被动死亡**。三条根因互锁，主因是 **奖励错配**：
1. **（主因）奖励错配**：`scenarios/crafter/outcome_observers/compatibility.py` 给 **idle 的 sleep 无条件 +0.4 正奖励**，给 **接敌的 `do` 固定 −0.5 负奖励** → 习惯学习固化 sleep、把 escalate(`do`) 学成 `habit_eligible=false` → 习惯收窄在打分前就把 escalate profile 剪掉。
2. **（放大器）drive 饱和**：severity 累加(+0.16/tick degraded) 远超 base_decay(−0.04) → 持续 degraded 的 Crafter avatar 让所有生存 drive 在 ~8 tick 内顶满 1.0 并钉住；持续 threat 把 exploration 压到 0 → drive 失去区分力。
3. **（共谋）动作解析无视 observation**：`scenarios/crafter/actions/compatibility.py:175` `del agent_observation` → `do`/`move` 不看食物/水/资源在哪 → 真的无效 → 喂给主因的负学习。

互锁闭环：#3 让 do 真无效 → #1 惩罚无效的 do、奖励发呆的 sleep → 习惯收窄锁定 sleep；#2 抹掉任何可能翻盘的情境信号。

---

## 1. 行为现状（当前 B+A 代码，证据）

| 维度 | 数据 |
|---|---|
| 释放动作 | `sleep` 204 (91%) / `do` 19 (8%) / 导航·采集·合成 **0** |
| 动作效果 | `pressure_outcome`：unchanged **220/223**、relieved 2、unknown 1 |
| 选中 profile | 整局只有 `stabilize_first`(→sleep) 和偶尔 `observe_first`；**`escalate_first` 0 释放** |
| 候选集 | 每个 deliberation 1~2 个候选，全是 `compatibility_release`（profile 烤进 id）；`habit_narrowed_from=2 → 1` |
| drive（中段） | metabolic/safety/recovery/acquisition/capability 全 **1.0**、exploration **0.0**，整局不变 |
| 实际体征（中段） | health=9 food=6 water=5 energy=9，仅 1 threat → 传感多为 degraded —— **avatar 其实没事，drive 却全顶满** |
| 终止 | HP=0 → individual_terminated（B+A 正确）；individual.json provenance 正确 |

---

## 2. 根因链（代码 + 数据证据）

### 根因 1（主因）：结果观测器奖励错配 → 习惯锁定

**位置**：`scenarios/crafter/outcome_observers/compatibility.py:51 / 55`
```
viability_score = sum(life_delta.values()) if life_delta else (0.2 if selected_action=="sleep" else 0.0)
risk_delta      = 0.5 if (threat_count>0 and action=="do") else (-0.2 if action=="sleep" else 0.0)
权重：viability=1.0, risk=-1.0
```
代入常见情形：
- **sleep 且体征无变化（中段常态）**：`1.0×0.2 + (-1.0)×(-0.2)` = **+0.4 → positive**（发呆得正奖励）。
- **do 且附近有 threat（中段常态）**：`(-1.0)×0.5` = **−0.5 → negative**（接敌被惩罚）。

**学习数据印证**（`learning_outcomes.jsonl`）：
- `sleep`：positive **182** / negative 22，mean_delta +0.232 —— 稳定被奖励。
- `do`：positive 1 / negative **13** / uncertain 5。唯一一次 +42.7 是出生第一步（采到东西/解锁），其后基本 −0.5。

**习惯固化 + 收窄**（audit `release_context.selection_context.habit_summaries`，situation `acquisition|STABLE|threat_nearby`）：
- `stabilize_first→sleep`：support 12 / fail 1 / **bias +0.846** / `habit_eligible=true`。
- `escalate_first→do`：support 0 / fail 10 / **bias −1.0** / `habit_eligible=false`（`recent_negative_streak`,`last_outcome_negative`）。
→ 习惯收窄（`habit_narrowed_from=2→1`）在 mediator 选择前就把 escalate 剪掉。**这解释了为什么 `111c667` 改了 escalate schema 仍无效：escalate 在打分前已被习惯剪除。**

### 根因 2（放大器）：drive 饱和

**位置**：`eva/l2_drive/drive_state.py`（累加 `new_level=clamp(level+delta)`，`delta=-base_decay+severity_accumulation+threat_bonus`）+ `scenarios/crafter/drive_preset.py`（`base_decay=0.04, severity_degraded=0.16, severity_critical=0.32`）。
- 持续 degraded：净 +0.12/tick → ~8 tick 顶满 1.0 并钉住（degraded 的 +0.16 > decay 0.04）。
- 持续 threat：exploration 走 curiosity 抑制 −0.12/tick → 钉到 0。
- 结果：Crafter avatar 长期 degraded（食水缓降、常有 threat、早期无工具）→ 全生存 drive 饱和、exploration 归零 → drive 无区分力。

### 根因 3（共谋）：动作解析无视 observation

**位置**：`scenarios/crafter/actions/compatibility.py:175` `del life_state, top_drive, agent_observation # reserved for future heuristics`
- 具体走哪个 Crafter 动作只看 `pressure_reason`+profile 默认，**不看 observation**（食物/水/资源/威胁方位）→ 即便选了 observe_first 的"移动"也无法朝资源走，`do` 也只能原地无效交互 → 真无效 → 反哺根因 1 的负学习。

---

## 3. 同类排查（扩大检查范围）

- **Linux 结果观测器**（`scenarios/linux_runtime/outcome_observers/compatibility.py`）：按 confidence/followup 设 risk_delta，**无 sleep 免费 +0.2** 这类按动作名硬编码的奖励 → 奖励错配是 **Crafter 专属**，修它不动 Linux。
- **drive 饱和是共享机制**：Linux 用框架默认（`severity_degraded=0.18, base_decay=0.05`，净 +0.13/tick，更陡），但 Linux 传感不长期 degraded（runtime 多数健康）→ drive 不顶满。**饱和修复必须验证不破坏 Linux**（优先改 Crafter preset，不动框架默认）。
- **按动作名硬编码奖励**：`capability_score=1.0 for make_/place_`（line 53，鼓励合成，合理保留）；`reversibility`（line 56，风险评估用，合理）。问题项只有 line 51、55。

---

## 4. 修复方案（分阶段，最小改动优先，逐步验证）

> 顺序：Fix-A（最小、最高杠杆、Crafter 专属）→ 跑一局 → Fix-B（obs 感知）→ 跑一局 → 视情况 Fix-C（饱和）。每步只改一处，再跑一局完整生命对比指标。

### Fix-A（主因，先做）：结果奖励去偏 ✅ 已实施并验证

`outcome_observers/compatibility.py`：
- 去掉 sleep 无条件 +0.2 viability 默认：viability 只按真实 `life_delta` 给分，idle sleep ≈ 0（不奖励发呆）。
- 重平衡 risk：有 threat 时 `sleep`=0.5(最危险) / `do`=0.2(接敌恰当) / 其它=0.3；无 threat 时全 0（不再给 sleep 免费 +0.2）。
- 目标：让"无效 sleep"不再正奖励、"方向正确的 do"不再被结构性惩罚。

**验证结果**（`validation-runs/rev2-a2-life-fixA/`，同配置一局完整生命；回归 490 绿、Linux 不变）：

| 指标 | baseline | Fix-A |
|---|---|---|
| sleep 占比 | 204 (91%) | 48 (**30%**) |
| do 占比 | 19 (8%) | 111 (**70%**) |
| `escalate_first` 释放 | **0** | **111** |
| pressure relieved | 2 | 10 |
| sleep 学习标签 | 182 positive | 39 **negative** |

**结论**：sleep 锁定**已打破**、escalate 不再被习惯剪除、动作多样性恢复。**主因（奖励错配）证实**。
**遗留**：生命更短（36 vs 50 tick）—— agent 现在主动 `do` 但 obs-blind 致其多数无效（80 uncertain），未转化为生存。这正是 **Fix-B（动作解析接入 observation）** 要解决的。

### Fix-B：动作解析接入 observation ✅ 已实施并验证

最终落地三块（朝向用方案 (a)：wrapper 按上一次移动方向维护，写进 observation 的 `facing`；Crafter 不在 `info` 暴露 facing，`env._player.facing` 仅作印证）：
1. **`scenarios/crafter/wrapper/{observation.py,env_wrapper.py}`**：wrapper 跟踪上一次移动方向 → observation 的 `facing` 给真实值（不再恒为 `unknown`）。
2. **`scenarios/crafter/actions/compatibility.py`**：`_resolve_actions_for_profile` 接 `agent_observation`，按当前压力找最近有用目标——面朝目标 → `do`，否则朝它走一步（`_obs_directed_actions` + 几何辅助，坐标/朝向均经实测）；并给 `escalate_first` 的可选动作加 `move_*`（让主导的 escalate 能"接近+交互"）。
3. **`eva/kernel/lifecycle.py`**：把本回合 `agent_observation` 注入 `release_context["candidate_context"]`（两处响应调用点），让 `select_integrity_response` 重建候选时看得见视野。原本 observation 只到感知层、不进 L3 候选生成——这正是"原地空 do"的根因。

**验证结果**（`validation-runs/rev2-fixB-life/`，同配置一局；回归 495 绿、Linux 不变）：

| 指标 | Fix-A | Fix-B |
|---|---|---|
| 移动动作 | **0** / 159 | **33** / 165（20%，move_down/left/right）|
| sleep | 48 | 23 |
| do | 111 | 109 |
| do 正向学习 | 8 positive | 12 positive |

**结论**：观测已接入候选生成，agent 开始**朝目标移动**、动作多样性恢复（move/do/sleep 三类都在用）。
**遗留**：单局存活步数尚未明显变长（37 vs 36 tick），`do` 仍偏多（84 uncertain）。瓶颈转移到 **drive 饱和（Fix-C）+ 习惯偏置过度偏向 do** —— profile/动作选择没有稳定挑中"该接近时就接近"。下一轮做 Fix-C。

### Fix-C：drive 去饱和（框架加 approach 模式）✅ 已实施并验证

**关键发现**：只调 `drive_preset.py` 改不动饱和——框架 `drive_state.py` 的 drive 更新是**线性累加+clamp**（`-decay+Σseverity_delta`），持续压力（Crafter 开局资源全无）必然把 drive 钉到 1.0；要不饱和就得把累加压到≤衰减，那 drive 又升不起来（admit 门槛过不了）。线性累加无法停在中间稳态。第一组纯 preset 调参实测无效（drive 仍 ~20 次更新内全 1.0），已回退。

**根治（架构师拍板，碰框架 L2，机制补全）**：drive 更新加 **approach 模式**——
- `DriveUpdatePolicy` 加 `update_mode`（默认 `"accumulate"`，Linux/既有行为不变）+ `approach_rate=0.3` / `target_critical=0.9` / `target_degraded=0.55`。
- `drive_state.py:_risk_drive_delta` 按 mode 分支：approach 下 `delta = approach_rate × (target − level)`，target 取该 drive 映射维度的**最坏 severity**（critical→0.9 / degraded→0.55 / healthy→0），threat present 抬到至少 target_degraded。
- Crafter preset opt-in approach；**Linux 保持 accumulate 不变**。curiosity 仍走 recovery/suppression，Crafter 调小 suppression(0.06)/调大 recovery(0.07) 救 exploration。

**验证结果**（回归 497 绿、Linux 不变、9 个 drive 测试含 2 新 approach）：
- drive 轨迹**按 severity 分层、不再全饱和**：`acquisition`(critical)→0.90、`capability`(degraded)→0.55、体征随状态在 0~0.55 波动、`exploration` 能升起来。
- 多局存活 ~31–47 tick（与 Fix-B 同量级，无 regression），`sleep` 进一步大降（多局仅 4–5 次）。

**遗留**：`do` 仍偏多（真瓶颈"视野无目标时原地空挥 do"未动——见下）。drive 分层目前主要改善评估阶段的 profile 区分度；最终动作仍走 candidates[0] tie-break。

### 仍待修（真行为瓶颈）：视野无目标时原地空挥 do
数据显示 `do` 多数 uncertain 的主因是：obs-directed 在"视野里没有有用目标"时返回空，退回 pressure-driven 的原地空 `do`。应改为：无目标时返回探索性移动（朝未探索方向走找资源），而非原地空挥。纯 Crafter 本地小修。

### 可选：习惯收窄反锁定护栏
习惯收窄不应把某个 profile 的候选**永久剪到 0**（退化学习下的死锁）。可加：当某 profile 长期 ineligible 时仍保留低概率探索名额，或引入强制多样性，避免单一动作锁死。（先做 Fix-A/B 看是否还需要。）

---

## 5. 验证计划

每个 Fix 后跑一局完整生命（同 `rev2-a2-life` 配置：heartbeat 0.8 > turn-guard 0.05），对比：
- sleep 占比（目标显著 <91%）、动作多样性（出现导航/采集/合成）、escalate 释放次数（>0）。
- outcome label 平衡（sleep 不再压倒性 positive、do 不再压倒性 negative）。
- 存活步数 / achievement / 资源采集量。
- drive 是否仍全程 1.0（Fix-C 后应有区分）。
- 回归：`python -m pytest tests/ -q` 全绿；Linux 行为不变。

---

## 6. 与 rev2 的关系

- B+A（终止 + individual 身份）已对，G 无需改，**D（step 时钟）不触及本空跑主因**。
- 本空跑根因是 L3 学习/结果层（奖励错配 + 习惯锁定）+ L2 drive 饱和 + Crafter 动作解析，属当初挂起的 idle-spin 主线，优先级高于 rev2 D。
- rev2 D/E/F 待空跑行为修复、能跑出有意义的一生后再回来。
