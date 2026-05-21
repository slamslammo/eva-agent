# 短跑行为分析 + 修复方案（30min Crafter 验证）

**数据来源**：`validation-runs/crafter-30min-validate/`（1029 ticks / 1031 turns，live + DeepSeek v4-flash，已退役但数据保留）
**分析目的**：长跑前用短跑诊断行为，定位"空跑"等非预期问题，出修复方案（**本文件只出方案，不实施**）。
**工作模式**：短跑 → 分析 → 深入 → 发现 bug 出方案 → 修复 → 循环，再逐步延长跑时间。

---

## 0. 一句话结论

agent **91.8% 在 sleep（空跑）**，根因是 **Crafter 的 `escalate_first` profile 的 `drive_impact_schema` 语义反转** —— 本该追求 acquisition/capability 的 escalate profile，对这两个 drive 反而是负权重。Crafter 资源稀缺让 acquisition/capability 长期顶满 1.0，于是 escalate 永远被 stabilize（→sleep）压制。这是 Crafter 专属的 schema 适配错误，Linux 不受影响。

---

## 1. 行为现状（空跑确认）

| 维度 | 数据 | 判断 |
|---|---|---|
| 动作分布 | sleep **91.8%**(944) / move_left 4.6%(47) / noop 3.6%(37) | 几乎全程消极 |
| 最长连续同一动作 | **346 turn 连续 sleep** | 严重重复 |
| 选中 profile | stabilize_first **91.7%**(944) / observe_first 8.3%(85) / **escalate_first 0%** | 固化保守 |
| 资源采集 | wood/stone/tool 全程 **0** | 无任何采集 / 制作 |
| achievement | 累计 6（疑似生存类 / 偶发移动，非采集链） | 几无实质进展 |
| vitals | HP/Food/Water 波动但未崩（sleep 苟活） | 消极存活 |
| drive | acquisition 长期顶满；turn 500 时 metabolic/safety/acquisition/capability 全 1.0 | drive 在工作，但未转化为动作 |

---

## 2. 根因分析（按影响排序）

### 根因 1（主因）：escalate_first `drive_impact_schema` 语义反转

**位置**：`scenarios/crafter/anchors/policy.py:50-60`（`COMPATIBILITY_RELEASE_IMPACT`）

当前三 profile 的 schema：

| profile（语义） | metabolic | safety | recovery | acquisition | capability | exploration |
|---|---|---|---|---|---|---|
| observe_first（看 / noop） | 0.1 | 0.1 | 0.0 | **0.4** | **0.3** | 0.5 |
| stabilize_first（睡 / 防御） | 0.7 | 0.8 | 0.6 | 0.1 | 0.0 | -0.05 |
| escalate_first（砍 / 挖 / 造 / 战） | 0.2 | **0.9** | 0.1 | **-0.1** | **-0.1** | 0.3 |

**问题**：scoring 是 `score = Σ(impact[drive] × level[drive])`，选最大值。schema 语义（policy.py:33 注释明确）= "正值让高 drive 把 selection 推向该 profile"。所以"去采集 / 建造"的 escalate 对 acquisition/capability 应是**高正值**。但实际是 **-0.1 / -0.1（负）**，且把最高权重错放在 safety:0.9。

**实测证据**（escalate 作为候选的 turn）：

```
turn 13: top=acquisition(1.0) capability(1.0) chosen=stabilize_first
  stabilize_first  score=0.947  (metabolic0.7×0.16 + safety0.8×0.8 + ... = 0.947)
  escalate_first   score=0.574  (含 acquisition(-0.1)×1.0 + capability(-0.1)×1.0 = -0.2 惩罚)
turn 14/15/16: 同样 stabilize(1.23/1.54/1.62) 完胜 escalate(0.76/0.77/0.78)
```

**因果链**：Crafter 资源稀缺 → acquisition/capability drive 长期顶满 1.0 → escalate 因对这两个顶满 drive 是负权重，被扣 -0.2 → 永远输给 stabilize → stabilize→sleep → 不采集 → 资源继续稀缺 → acquisition 继续顶满 →（自我强化的 sleep 死循环）。

**性质**：从 Linux 模板**误适配**。Linux 的 escalate→`integrity:0.8`（最高）是正确的（Linux escalate = "修复 integrity"，确实满足 integrity drive）。适配到 Crafter 时，高权重被错放到 `safety:0.9`（对应 Linux 的 integrity 位置），而 Crafter escalate 真正满足的 acquisition/capability 反被设负。policy.py:56-59 注释只解释了 exploration，没解释 acquisition/capability 为何为负 —— 说明这俩值未经推敲。

### 根因 2：`admit_crafter_candidates` 错误耦合

**位置**：`scenarios/crafter/anchors/policy.py:64-85`

```python
if safety >= 0.7:
    profiles = [ESCALATE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE]
elif metabolic >= 0.65 or recovery >= 0.65:
    profiles = [STABILIZE_FIRST_PROFILE]          # ← 只 admit stabilize
else:
    profiles = [OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE]
```

**问题**：
- escalate 只在 `safety >= 0.7` 才被 admit —— 把"去采集 / 建造"的 profile 耦合到 **safety 压力**，而非 acquisition/capability 压力（应当：需要资源时才更应该 escalate 去采集）。
- `metabolic/recovery >= 0.65 → 只 admit stabilize` —— 代谢 / 恢复压力高时强制只能 sleep。但 Crafter 里饿了（metabolic 高）正应该去**采集食物**（escalate），而非 sleep。这把"饿了 → 去找吃的"锁死成"饿了 → 睡觉"。
- 这是 472 个"单候选(只 stabilize→sleep)" turn 的来源。

### 根因 3（次要 / 复合）：scenario `select_response_action` drive-blind

**位置**：`scenarios/crafter/actions/compatibility.py:487 _score_candidate_for_selection`

**问题**：concrete action 选择只用 habit bias + inherited-prior bias 打分；无 habit / prior 命中时（早期 / semantic=0），所有候选 score 0.0 → 退化为 `candidates[0]`（生成顺序第一个）。完全不读 drive levels 或候选的 drive_impact_schema。

**定位为次要**：因为根因 1+2 已在框架层把 profile 定死为 stabilize_first，scenario 多数 turn 只拿到单一 stabilize→sleep 候选，这层 selection 是从属问题。但根因 1/2 修好后，这层也应让 drive 参与 tie-break，否则多候选时仍可能退化。

### 根因 4（独立）：semantic_memory 写入路径未接线

**位置**：`eva/l3_deliberation/memory/semantic.py` —— `append_semantic_memory` 有 API + 在线缓存镜像，但**全仓库无任何 runtime 调用者**（peer_circuit / encoding / runtime loop / scenarios 都不调用）。

**这是 finding #1（semantic_memory=0）的真因**：不是"写入阈值太严"，而是**根本没有写入触发点**。Stage I 落地了 semantic 的存储 + 查询 + 索引，但写入触发从未接入运行闭环。

### 复合因素：drive 饱和

turn 500 时 metabolic/safety/acquisition/capability 全部顶到 1.0。drive 全饱和后失去区分度，scoring 退化为"哪个 schema 权重和更大"→ stabilize（其 schema 和最高）。这放大根因 1 的影响。属于 drive update/decay 调参问题，次于 schema 修复。

---

## 3. 三个 findings 归一

| Finding | 根因 |
|---|---|
| #2 L3 stabilize 主导 | ← 根因 1+2（escalate schema 反转 + admit 耦合，escalate 永远输） |
| #3 action 单一（实为 sleep 主导） | ← 同上（固化 stabilize→sleep） |
| #1 semantic_memory=0 | ← 根因 4（写入路径未接线，**独立**） |

前两者同源，第三个独立。

---

## 4. 扩大检查结果（同类 bug 排查）

- **Linux scenario**：`scenarios/linux_runtime/anchors/compatibility.py` 的 schema 内部自洽 —— escalate→`integrity:0.8`（最高，正确），未受影响。**这是 Crafter 专属适配 bug**。
- **admit 逻辑**：Linux 的 `admit_linux_runtime_candidates` 按 heartbeat 窗口收窄，未见同类"drive 错耦合"。
- **drive_impact_schema 语义一致性**：建议修复时统一审一遍 Crafter 三 profile 全部 6 个 drive 的权重符号是否符合动作语义（不只 escalate）。

---

## 5. 修复方案（待 review，不马上实施）

> 每条修复后用短跑（~5-10min）复验行为，循环验证，达预期再延长跑时间。

### 修复 A（最高优先）：重标 Crafter `escalate_first` schema
- `acquisition` / `capability` 改为**高正值**（如 0.6 / 0.5），反映 escalate 满足这两个 drive。
- `safety` 降到合理（如 0.2）—— safety（防威胁）应是 stabilize 的强项，不是 escalate。
- 对照 Crafter 动作语义重审 observe_first（其 acquisition 0.4 / capability 0.3 偏高，被动观察不该满足采集 drive，疑似与 escalate 权重错位/对调）。
- **冻结测试**：scenario 的 drive-weighted 选择测试；Linux 行为 bit-equivalent。

### 修复 B：重写 `admit_crafter_candidates` 耦合
- escalate admission 改为按 acquisition/capability 压力（需要资源 → 允许 escalate 去采集）。
- 去掉"metabolic/recovery 高 → 只 stabilize"的硬锁；饿了应允许 escalate 采集食物。
- 保留 heartbeat 窗口收窄到 stabilize 的安全机制（参考 Linux）。

### 修复 C（B/A 之后）：`select_response_action` 增加 drive-aware tie-break
- 无 habit / prior 命中时，按候选的 drive_impact_schema 与当前 drive_levels 对齐度做 tie-break，而非退化 candidates[0]。
- 保持 habit > prior > drive 的优先级（habit 最强）。

### 修复 D（独立）：接线 semantic_memory 写入
- 在 outcome 观察 / encoding 之后，按条件 `append_semantic_memory`（如：某 situation_key 重复经历 + 稳定 outcome 模式时凝练一条 semantic pattern）。
- 需先定义写入触发条件（避免每 turn 写）。这是 Stage I 的收尾缺口。

### 修复 E（评估后定）：drive 饱和
- 检查 drive update/decay，让 drive 不要长期全顶 1.0 而失去区分度（可能需要更强的 decay 或满足后回落）。
- 次于 A/B；A/B 修好后重看饱和是否仍是问题（agent 开始采集后 acquisition 应回落）。

---

## 6. 建议的下一轮循环

1. 先实施 **修复 A + B**（schema 重标 + admit 重写）—— 这是空跑主因，改动集中在 `scenarios/crafter/anchors/policy.py`。
2. 短跑复验（~10min）：看 escalate 是否开始被选、是否有采集动作、sleep 占比是否下降。
3. 若行为改善，再评估 C（selection tie-break）、E（drive 饱和）是否仍需要。
4. D（semantic 接线）可并行或单独一轮（独立于空跑）。
5. 行为达预期后，再考虑延长跑时间 / 长跑。

---

## 7. 关联

- 数据：`validation-runs/crafter-30min-validate/`
- 主因代码：`scenarios/crafter/anchors/policy.py`
- 次因代码：`scenarios/crafter/actions/compatibility.py`、`eva/l3_deliberation/memory/semantic.py`
- 框架 scoring（无需改，工作正常）：`eva/l3_deliberation/reasoning/value_judgment.py`、`conflict_detection.py`
- 长跑计划：`maintainer/development/phase3-longrun-plan.md`（行为修好前不启动 6h）
- 观察工具：`observation_tools/`（可视化复验行为）
