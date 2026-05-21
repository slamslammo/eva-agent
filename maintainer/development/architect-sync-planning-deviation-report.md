# 开发进展与规划偏差报告（供架构师讨论）

> **受众**：仅掌握两块上下文的架构师——
> 1. 早期定的 **W1~W8** 周计划；
> 2. 在做可视化视图时发现的 **「框架把场景只放进 turn 处理」** 这一结构问题。
>
> **本报告目的**：补全 W 计划之后实际发生的工作、以及由实测暴露出的规划偏差，
> 重点是三件需要你拍板的事——**持续生存理解的基础偏差、LLM 决策过弱、长跑不符预期**。
> 所有结论尽量挂 git 提交锚点，便于核验。

---

## 一、W1~W8 规划 vs 实际落地（桥接你已知的第 1 块）

git 提交里直接带了 W 标注，可锚定的映射如下；**注意 `W1 redefined` 是计划中途被调整过的硬证据**：

| W | 对应 Round | git 锚点 |
|---|---|---|
| **W1（redefined）** | Round 1.D 长跑验证基础设施 | `8dcac74` |
| W2 | 无仓库记录 | 待你校准 |
| **W3** | Round 1.B-2 Crafter exploration drive | `53df65d` |
| **W4** | Round 1.C-1 semantic memory 索引 | `35aa2c3` |
| **W5** | Round 1.B-3 semantic→drive overlay | `2677a02` |
| **W6** | Round 1.C-2 working-memory limits | `9cb9bbc` |
| W7 / W8 | 全仓零记录 | 待你校准 |

**结论**：W1~W8 原始清单没有完整落库（W2/W7/W8 找不到，W1 已被重定义）。实际执行轨迹是
按 **Round 1.x 系列** 推进，并在中途**插入了两块计划外工作**：

- **插入①：LLM client**（Phase 1.6 接 DeepSeek `86942b6`、Round 1.7 通用化到 OpenAI Chat Completions、弃 Anthropic 协议 `e8b916e`）。
- **插入②：可视化升级**（Phase 2 observation_tools 黑盒查看器 V0/V1 `54b0acb`/`851991f` + 独立 worktree 迭代入口 `6b5f76a`）——**正是在这块工作里，你发现了「场景只放进 turn 处理」的问题**。

Round 1 系列实现层（1.A / 1.B-1~1.B-4 / 1.C-1 / 1.C-2 / 1.D 基础设施）**均已落地**；各 Round 的
architect-review gate 多数仍 `pending`（见第四节）。

---

## 二、承接你的发现：「场景只放进 turn 处理」是一个根、三个侧面

你在可视化时发现的结构问题，和我这边由实测暴露的几个现象是**同一个根**。先对齐框架的两条节律：

- **tick = heartbeat**：通用生命节律，**场景无关**（只查 instance 合法性、持久化、心跳年龄）。
- **turn = work**：**场景内容全在这里**——patrol sensing 读 `agent_observation`、L3 deliberation、action release 都在 turn 内发生。

由此，「场景只放进 turn」直接导出三个问题：

1. **场景世界的推进受框架时钟支配**：Crafter 是**回合（step）驱动**的世界，但它的 `env.step` 只在 turn 的
   action release 时被调用，而 turn 的调度是**挂钟（wall-clock）cadence**（patrol interval 秒）。step 世界被
   套进 wall-clock 节律 → 错配。这正是 rev2 决策点 3 / D 项要解决的。
2. **turn 会被心跳 deadline 抢占 → 场景可能完全不推进**：实测踩到一个坑——当
   `heartbeat-interval < turn-guard-window` 时，**每个 turn 都因 `heartbeat_deadline_near` 被跳过，`turns=0`，
   Crafter 一步都没走**（`validation-runs/` 早期一局）。这说明场景的"存活/推进"被框架心跳节律单方面支配，
   是「场景只放 turn」的直接后果。
3. **场景的"生死信号"也只在 turn 被消费**：Crafter avatar 死亡（`done`）的信号经 turn 上报，
   而原实现里它被 wrapper 的 `reset()` 在 turn 内吞掉、kernel 根本不感知——这就接到了下一节的基础偏差。

> **可讨论点 A**：是否承认"场景时钟来源"应由场景注入（step / wall-clock），框架只保证
> 连续性/单调/可恢复（rev2 收敛点①）？这会重塑 tick/turn 与场景的关系。

---

## 三、三个规划偏差（本报告核心，请逐一拍板）

### 偏差①：持续生存理解的基础偏差（rev2，已修主干 B+A）

**问题**：原实现把"持续存在"误解为"进程/tick 不停"。Crafter avatar HP=0（`done`）后，wrapper 在同一进程
`reset()` 满血续命，kernel 不知情——等于"角色死了、系统假装无事，换个角色接着用同一条命的记录"。这违反 EVA
"failure not an acceptable reset"。

**已修（B+A，已提交）**：
- **B 存在语义声明契约** `bc7e3fb`：把"什么算活/死"的解释权交还场景（`ExistenceSemantics` 六项 + 身份延续 + 时钟来源），框架读取并一致执行。
- **A-1 终止范式** `67e5606`：去 `done→reset` 续命，HP=0 = individual 真死 → `exit_reason=individual_terminated` → 归档本 run、不续命。
- **A-2 individual 身份层** `da6140d`：`individual_id`（"自我"）区别于 substrate 的 `instance_id`（"躯壳"），带 provenance 链；场景 `reset_semantics` 决定复用还是新生。

**未做**：rev2 的 **D（step 时钟注入）/ E（继承管线）/ F（实验 harness）**——决策点 4 明确"后续单独循环"。G（reset 体征 null）已核查、无需改码。

> **可讨论点 B**：B+A 的范式纠正你是否认可？D/E/F 的优先级与时机（见下文与偏差②/③联动）。

### 偏差②：LLM 决策过弱——L3 reasoning 位是"虚位"

这是和你讨论规划偏差的重点。**理论 vs 实现差了一整层**：

- **理论（v0.6 蓝图 §7 L3 Adaptive Deliberation + §2.2）**：L3 由 working-memory assembly、**reasoning**、
  peer-circuit selection、mediated release、tool edge、outcome evaluation、memory、inherited priors 组成。
  其中 **reasoning（LLM 对应位）** 应在 **Anchor 生成前约束**的候选域内做**实质推理/提议**；而**选择（peer
  circuit）与释放（mediator）在理论上独立于 reasoning**（"release authority 独立于 reasoning"、"L3 不能绕过
  mediator"）。即：**LLM 主导"想什么"，但不主导"激活什么"**——两道结构约束，不是弱化推理。
- **实现现状**：reasoning 这一位**几乎是空的**。LLM 只在 `value_judgment` 给匹配 profile 加一个
  **≤0.12 的事后偏置**（`MAX_SEMANTIC_OVERLAY_BLEND=0.15` 类的有界 overlay），**没有承担"提议候选/计划"**。
  实际"决定考虑哪些动作"的是**规则启发式**（drive 广播 + anchor admit + 习惯/先验 + obs-directed 觅食）。
- **实测铁证**：idle-spin 修复后一局里，**所有释放动作的 selection reason 都是 `crafter_minimal_selection`**
  （candidates[0] tie-break），没有一个走 LLM/习惯评分——即 **LLM 对最终动作的影响约等于零**。

**含义**：当前 Crafter 的"动作智能"全是规则；规则只能应付**简单反应式**行为。Crafter 的多步合成、生存权衡、
长程目标这类**复杂任务**，规则堆不出来——**得有受约束的强推理才能完成**。所以"LLM 不主导 action release"是
对的（理论），但"LLM 弱到不参与推理"是实现偏差，**不是理论要它弱**。

> **可讨论点 C（最高优先）**：L3 reasoning 位该如何**填实**——让 LLM 在 anchor 约束的候选域内**实质提议
> 候选/计划**，再交独立的 peer-circuit/mediator 选择与释放。这是原 W 计划从未包含的项，却是决定"LLM 有没有
> 意义、复杂任务能不能做"的真正 blocker。

### 偏差③：长跑不符预期——带 LLM 长跑当前意义不大

**问题**：原 Round 1.D 长跑（30min 验证 / 计划中的 6h）默认"带 live LLM 跑能验证系统行为"。但结合偏差②：

- LLM 虚位 → 长跑里观察到的行为**基本是规则系统的行为**，LLM 贡献被淹没、分辨不出。
- live LLM 每次调用约 2900 token；那次 30min 跑触发了 **1029 次 DeepSeek advisory**，6h 量级是几百万 token /
  数十元——**换来的是被压到 ≤0.12 的影响**。性价比极低。
- 默认 backend 其实是 `local_rule_based`（不调 LLM）；带 LLM 是显式 `llm_assisted` 才触发。

**结论**：长跑要分两种目的——
- **验证持续性/结构主干**（heartbeat 不崩、状态持久、不空跑、长程 drive/记忆/学习轨道）：**有意义，但应
  用 `local_rule_based`、不带 LLM**（省 token、干净、可复现）。
- **验证 LLM 推理对复杂任务的贡献**：在 reasoning 位填实前**没意义**，应推迟。

> **可讨论点 D**：Round 1.D 的长跑执行（D-4/D-5/D-6）是否**重定位**——剥离 LLM 做 local 持续性验证，
> 把"带 LLM 长跑"排到 reasoning 位填实之后？

---

## 四、完成 / 未完成总表 + 评估

| 项 | 状态 | 评估（中途调整导致 / 仍正确） |
|---|---|---|
| Round 1.A / 1.B-1~4 / 1.C-1 / 1.C-2 实现 | ✅ 已落地 | 仍正确 |
| Round 1.D 长跑**基础设施**（D-1/2/3） | ✅ 已落地 | 仍正确 |
| 插入①：LLM client（DeepSeek / OpenAI 通用化） | ✅ 已落地 | 计划外但必要（接入前提） |
| 插入②：可视化 observation_tools | ✅ 已落地 | 计划外；正是它暴露了"场景只放 turn" |
| rev2 基础偏差 **B + A** | ✅ 已落地 | **认知升级带来的正确新增**（持续生存语义纠正） |
| idle-spin 空跑修复（escalate schema + Fix-A/B/C） | ✅ 已落地 | 仍正确；sleep 91%→14%、move 0→33/局 |
| Round 1.A/1.B-4/1.C-2 **review gate** | ⏳ pending | 仍正确，建议并入 rev2 后统一 review |
| **Round 1.D 长跑执行 D-4/5/6** | ⏳ pending | ⚠️ **规划已不再正确**——建立在"LLM 有效"假设上（见偏差③） |
| rev2 **D / E / F** | ⏳ 未做 | 方向正确；D 经数据证当前非瓶颈、E/F 依赖"有意义一生"→应后移 |
| idle-spin 真瓶颈"视野无目标空挥 do" | ⏳ 未修 | 仍正确的纯本地小修 |
| **L3 reasoning 位填实** | ⏳ 未规划 | **新识别、当前最高优先**；原 W 计划缺失项（见偏差②） |

---

## 五、待你决策的开放问题（汇总）

- **A. 时钟/turn 结构**：场景时钟来源是否由场景注入（step/wall-clock），框架只保证连续性？（接你"场景只放 turn"的发现）
- **B. rev2 范式**：B+A 是否认可？D/E/F 时机？
- **C. L3 reasoning 位（最高优先）**：如何填实"受锚点约束的推理核心"——LLM 提议、peer-circuit/mediator 独立释放？
- **D. 长跑重定位**：D-4/5/6 是否剥离 LLM 改 local 持续性验证，带 LLM 长跑后置到 reasoning 填实之后？
- **E. 优先级排序**：建议次序 = C（reasoning 位）→ A（时钟/turn）→ 重定位 D（长跑）→ rev2 E/F；你定。

---

## 附：关键 git 锚点

```
95fdd12 Fix-C drive 去饱和（框架 approach 模式）
81e80e3 Fix-B 动作解析接入 observation
97ce0d9 Fix-A 结果奖励去偏（破 sleep 锁定）
da6140d rev2-A2 individual 身份层
67e5606 rev2-A1 Crafter 终止范式纠正
bc7e3fb rev2-B 存在语义声明契约
111c667 idle-spin: escalate schema + admit 耦合修复
6b5f76a / 851991f / 54b0acb  Phase 2 observation_tools（可视化）
e8b916e Round 1.7 LLM client 通用化（OpenAI Chat Completions）
86942b6 Phase 1.6 DeepSeek client
8dcac74 Round 1.D 长跑基础设施（W1 redefined）
9cb9bbc Round 1.C-2（W6） / 35aa2c3 Round 1.C-1（W4）
2677a02 Round 1.B-3（W5） / 53df65d Round 1.B-2（W3）
8523c3d Round 1.B-4 / d059bc2 Round 1.B-1 / 536c1ff Round 1.A
```
