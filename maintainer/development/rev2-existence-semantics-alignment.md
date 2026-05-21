# v0.6 rev2 存在语义 — 工程对齐分析

**状态**：分析完成，待与架构师对齐 4 个决策点后进入实施。
**触发**：理论 rev2 修订（生死解释权从框架交还场景）。空跑修复循环暂时挂起。
**理论依据**：工程蓝图 `docs/architecture-implementation-blueprint-v0.6.md`（吸收 v0.5/v0.6）+ 架构师提供的 rev2 修改要点。eva-theory 原文在外部仓库。

---

## 一、背景：理论为什么调整（一句话）

起点是工程观察：Crafter 跑 EVA 时，avatar 死了（HP=0）后同一个进程 `reset()` 续命。往根上挖后收敛到一个判断：

> **EVA 是"以持续存在为目标的架构方法"，不是一个本体。"持续存在"的判据由场景定义；框架提供维持持续存在的机制，但不替场景裁决生死。**

这是一次 boundary-failure revision（只改 v0.6 正文，v0.5 未动，因为本意一致）。

---

## 二、我对 rev2 的理解

### 核心判断
生死的解释权从框架**交还场景**。框架给"机制" + 七层"分类语言"，场景声明"什么算活、什么算死"。

### 三个派生结论
1. **持续存在 ≠ 持续运行**。可恢复中断（重启 / 迁移 / 充电）不是死；**不可恢复地丢失状态 / 结构不变量 / provenance 链**才是死。
2. **Crafter HP=0 是真死**（单局世界，无 in-life 复活）。`done→reset` 是强化学习训练范式的痕迹，违反 v0.5 §2 C1（"failure not an acceptable reset"）。
3. **继承是跨独立个体的种群信息延续**（手段），不是同一个体多次生命。"进程 tick 没停"不构成个体延续。

### EVA / 场景分工
| | 框架（场景无关、结构不变量） | 场景声明（field condition，框架消费） |
|---|---|---|
| 生死语义 | 提供机制 + 一致执行场景声明 | **存在语义六项**（见下） |
| 持续性层级 | 7 层分类 + 在激活层上运作 | 激活哪些层（Crafter：embodied + capability） |
| 实例身份 | legitimacy（lock/generation/lease）+ recovering 作为"可恢复→同一个体"判据 | 哪些中断算可恢复 / 算终止 |
| 感知 | sensing / rate 机制 | 信号→dimension/drive 映射；rate/cadence 配置 |
| 继承 | 接收 prior bundle 的 registry + 不变量校验 | 是否有继承通道、如何蒸馏 |

### 存在语义六项（每个场景必须声明）
continuity criterion（什么算"还活着"）/ recoverable interruption（哪些中断可恢复）/ terminal failure（什么算真死）/ individual boundary（一个个体的边界）/ reset semantics（reset 意味着什么）/ inheritance channel（有无继承通道）。

**Crafter 示例**：continuity = HP>0（及必要 vitals）；recoverable interruption = 无（单局）；terminal = HP=0；individual boundary = 单 episode；reset = 新个体；inheritance = 死亡个体 trace → 蒸馏 → 新个体 priors。

### 与蓝图的一致性（重要）
rev2 不是推翻蓝图重来。蓝图已有兼容概念：§828 "unrecoverability floor"（不可恢复地板）、§88 active persistence、§960 "Level 2 embodiment-specific continuity"、§1158 "host process continuity ≠ Kernel"。rev2 只是把"生死交给场景声明"这条线**说透并接好**。

---

## 三、工程实现的问题（代码证据）

| # | 问题 | 代码证据 | 偏离点 |
|---|---|---|---|
| **A** | done→reset 同进程续命 | `runners/run_crafter.py:55`：`next_observation = ... if not done else self.wrapper.reset()`；`scenarios/crafter/SPEC.md:176` **明确写了被推翻的旧观点**："avatar death or env done=True triggers a bounded wrapper reset... without treating one episode boundary as substrate-level death" | HP=0 应是个体终止 + 归档 + 本 run 结束，而非 episode 边界续命 |
| **B** | 无存在语义声明 | `RuntimeScenarioBundle` 只有 drive_preset/sensors/actions/anchors/outcome_observers/prior_skills，**无存在语义字段**；`docs/scenarios-SPEC.md` 必备 surface 不含六项 | 终止/恢复逻辑应由场景声明驱动，现在默认套进程级语义 |
| **C** | substrate continuity ≡ tick/进程 | kernel 循环（heartbeat/tick/legitimacy）是 substrate 级，**从不感知 avatar 死亡** —— 死亡在 wrapper 层被 reset() 吞掉，`done` 记进 CrafterActionStep 但 kernel 不消费 | "是否同一个体"应锚在 legitimacy 链 + 可恢复性 + provenance，而非 tick 连续 |
| **D** | rate/cadence 用 wall-clock，与 Crafter step 错配 | `eva/l1_sensing/sensing.py:80` 用 `elapsed_sec`（挂钟秒）算变化率；`patrol.py:21 PATROL_INTERVAL_SECONDS` 用秒。Crafter 是回合（step）驱动 | Crafter 应 rate per-step、cadence step-driven（场景配置） |
| **E** | inheritance 未真正接入 Crafter | `activate_crafter_scenario(inherited_priors_path=...)` 只能**手动加载** priors 文件；**无 死亡→蒸馏→新个体 流程** | A 未改则无"死亡个体 trace"可蒸馏（A/E 串联） |
| **F** | metrics 把多 episode 当一命 | 一个 run 内 reset 续命 → 多条"命"聚成一条轨迹（*需确认 stability_metrics 的跨 episode 处理*） | 1 run=1 个体一生；多 run=种群统计 |
| **G** | reset 体征 null | 实测 30min 数据 turn 0 vitals 全 None；`env_wrapper.py:48 reset()` 依赖 gym reset 的 info，常为空 | reset 时应标 available=False 或主动取一次 info |

### 额外关联
- 偏离集中在 **Crafter 接入层 + 缺失声明契约**，不在框架核心机制（legitimacy/recovering/persistence 大多已就位）。
- **A/B/E 串联**：B（声明）是前提；A（终止）改完才有"死亡个体 trace"喂 E（继承）。
- **与空跑修复正交但互补**：空跑修复让个体"活着时努力采集存续"，rev2 让"死亡有意义"。rev2 范式下，1 run = 1 个体一生，个体活着时是否积极（空跑修复）直接决定它能活多久。空跑修复不是白做。

---

## 四、待对齐的 4 个决策点（通俗版）

> 这 4 点都是"该怎么改"的设计选择。下面用通俗语言 + 类比 + 选项给出，方便讨论。

### 决策点 1：场景的"生死规则"登记在哪？

**现状（通俗）**：现在没有任何地方让场景写下自己的生死规则。框架只能默认套一套"进程级"的通用规则，于是 Crafter 的"HP=0=真死"无从表达。

**要决定**：让场景声明的"存在语义六项"放在哪？

| 选项 | 通俗含义 | 权衡 |
|---|---|---|
| **A. 做成代码契约字段** | 每个场景的"登记表"里多一栏"生死规则六项"，框架启动时读取并照做 | 正式、框架能强制消费、不易漏；改动稍大（动 RuntimeScenarioBundle 契约） |
| B. 先写文档 + 轻量读取 | 六项先写在 SPEC 文档里，框架用一个简单接口读 | 改动小；但容易停留在"纸面声明"，没真正驱动运行逻辑 |

**我的倾向：A**。理由：rev2 的核心就是"框架读取并一致遵守场景声明"。只有契约化，框架才能真正"消费"声明去裁决终止。纸面声明无法驱动运行时。

---

### 决策点 2：个体"死了"之后，这次运行怎么收尾？

**背景（通俗）**：EVA 有两个层次的"生命"，容易混：
- **substrate（底层载体）**：进程 / 运行本身 —— 像"主机 / 身体的底层硬件"。可以重启、迁移、充电（可恢复中断），不算死。
- **embodied（具身）**：avatar 在 Crafter 世界里的角色 —— 像"游戏里的人物"。HP=0 就是这个角色真死了。

**现状**：现在 avatar（游戏角色）死了，会被 wrapper 偷偷 `reset()` 满血复活，而 kernel（管底层载体的那层）**根本不知道角色死过**。等于"游戏角色死了，但系统假装无事发生，换了个新角色接着用同一条命的记录"。

**要决定**：avatar 死后，谁来宣告、这次 run 怎么结束？

| 选项 | 通俗含义 | 权衡 |
|---|---|---|
| **A. kernel 引入"个体终止"概念** | 让 kernel 明确区分两种结束："个体死了"（avatar HP=0）vs"进程被叫停"（超时/手动）。场景检测到 avatar 死 → 告诉 kernel"这个个体终止了" → kernel 归档这一生的 trace + 正常结束本次 run（不 reset） | 正本清源——kernel 真正"理解"个体一生结束（这正是 rev2 想要的）；需要给 kernel 加一个概念 |
| B. 场景层发停止信号 | 不动 kernel 概念，场景在动作执行层检测到死亡后，发一个"停"的信号让 kernel 退出 | 改动小；但 kernel 仍不"理解"死亡，只是被动停，"个体一生"在 kernel 里没有一等地位 |

**"下一个体"怎么办（两选项都一样）**：一个个体死了，要研究"下一代"就**重新跑一次**（新 run / 新进程），可以带上"上一代的经验"（inherited priors）。**不是同进程接着续命**。

**我的倾向：A**。理由：让 kernel 把"个体一生结束"当成一等事件，是 rev2 范式的核心；否则 kernel 仍只懂"进程在不在跑"，生死语义还是悬空的。

---

### 决策点 3：Crafter 的"时间"对不上框架的"时间"

**现状（通俗）**：框架按"真实挂钟秒"过日子 —— 心跳每 N 秒、巡逻每 N 秒、变化率按"每秒多少"算。但 **Crafter 是回合制**，它的时间单位是"步（step）"，不是"秒"。现在硬把"秒"套到"回合"上，导致"变化速率 / 巡逻节奏"和 Crafter 的真实节律对不上（比如之前长跑用"心跳 1 秒"加速，其实和 Crafter 的回合根本不是一回事）。

**要决定**：rev2 说"这应该场景配置解决，不改框架"。但框架现在把"按秒"写死了。要让 Crafter 改用"按步"，框架得开一个"时间从哪来"的小口子（让场景说"我的时间是步，不是秒"）。这个口子算"框架机制的小扩展"还是"纯场景配置"？

| 选项 | 通俗含义 | 权衡 |
|---|---|---|
| **A. 框架开一个最小"时钟来源"注入点** | 框架允许场景注入自己的时钟（Crafter 注入"步时钟"），sensing/patrol 用注入的时钟而非写死的挂钟 | 最干净；严格说动了框架（但很小、且是通用能力，别的回合制场景也受益） |
| B. 完全在场景接入层绕过 | 不动框架，场景接入层自己把"步"折算成"假秒"喂给框架 | 不动框架；但是"糊弄"——本质还是秒，折算容易出语义偏差，治标不治本 |

**我的倾向：A**（最小注入点）。理由：B 的"折算假秒"正是现在错配的根源延续。开一个干净的时钟注入点，是通用的、可解释的，且符合"回合制场景"这一类的真实需求。这虽然碰框架，但属于"机制补全"而非"为单场景特判"。

---

### 决策点 4：这一轮先做多少？

**背景**：调整清单有 A–G 七项，建议顺序 B→A→D/G→E→F。

**要决定**：这一轮先做哪些。

| 选项 | 通俗含义 |
|---|---|
| **先做 B + A（范式纠正）** | 先把"场景声明生死"（B）+ "Crafter 不再 reset 续命、HP=0 终止"（A）做掉。这是必须先做的根本纠正。D/G（时钟/体征精化）、E（继承接入）、F（实验设计）留后续单独循环 |
| 一次做更多 | B+A 之后顺带 D/G 或 E | 

**我的倾向：先 B + A**。理由：B+A 是范式纠正（生死语义正本清源），是后面一切的前提；D/G/E/F 是接入精化，依赖 A 先到位（尤其 E 要等 A 产出"死亡 trace"）。一轮专注一件事，改完短验证再下一轮。

---

## 五、护栏（rev2 六不要，实施时遵守）
1. 不引入 P1/P2 运行模式（存在语义是场景声明，不是 runtime 开关）。
2. 不把 avatar vitals 提升为 substrate viability（保 Level 1/2 分离 + 跨场景能力）。
3. 不为 Crafter 时钟去改框架核心逻辑（错配在接入层，用"时钟注入"通用机制解决）。
4. 不把"进程没停 / 继承到了"读成个体延续。

---

## 六、建议实施顺序（对齐 4 决策点后）
B（场景存在语义声明 + 框架读取）→ A（Crafter 终止语义，去 reset 续命）→ D/G（per-step rate / step cadence + null 修复）→ E（接 inheritance pipeline）→ F（比较实验：单体到终止 + 种群统计）。

---

## 七、关联文档与代码
- 理论蓝图：`docs/architecture-implementation-blueprint-v0.6.md`
- 场景契约：`docs/scenarios-SPEC.md`、`scenarios/crafter/SPEC.md`（§176 旧表述待改）
- 终止续命点：`runners/run_crafter.py:55`、`scenarios/crafter/wrapper/env_wrapper.py`
- 场景 bundle 契约：`eva/scenario_bundle.py`（待加存在语义字段）
- 继承管线：`inheritance_distillation/`（Stage I，待 Crafter 接入）
- 空跑修复（挂起中，正交）：`maintainer/development/shortrun-behavior-analysis-and-fix-plan.md`

---

## 八、对齐结论与实施方案（已与架构师对齐）

### 决策结论
- 决策点 1（声明放哪）：**A —— 代码契约字段**（`RuntimeScenarioBundle.existence_semantics`）。
- 决策点 2（死后收尾）：**A —— kernel 引入"个体终止"概念**（新 `exit_reason="individual_terminated"`），下一个体 = 新 run。
- 决策点 3（时钟）：**A —— 框架开最小"时钟来源"注入点**，场景注入 step-clock；连续性仍由框架保证。
- 决策点 4（这轮做多少）：**先 B + A**（范式纠正），D/G/E/F 后续单独循环。

### 三个收敛点
1. **tick 心跳节律通用，不动**。"检查什么健康指标"已场景化（sensor registry / patrol）。时钟**来源**由场景注入，**连续性/单调/可恢复**由框架保证。
2. **框架引入 individual 身份层**（`individual_id` + provenance），区别于 substrate 的 `instance_id`/`generation`。类比：重启换躯壳，躯壳 id 新，但"灵魂"`individual_id` 延续。provenance 链**带场景标识**（防跨场景误继承）。
3. **B 声明契约** = 存在语义六项 + identity 延续判据 + 时钟来源。

### 并发隔离结论（已核实代码）
隔离边界 = `runtime_dir`（文件层）+ 进程（内存全局单例）。正常用法（不同 runtime_dir + 不同进程）**物理完全隔离**，instance_id/individual_id 不混；无任何固定共享路径（`~/.eva`、`/tmp`、`/var` 均无）。**共用代码、隔离数据**。会混的非正常情况：同一 runtime_dir（lock 争用，框架阻止）或同进程跑两场景（进程内全局单例污染，违反 one-scenario-per-runtime）。

### B + A 实施拆解

**B（存在语义声明契约）**：
- 新 `ExistenceSemantics` dataclass（`eva/scenario_bundle.py`）：`continuity_criterion` / `recoverable_interruption` / `terminal_failure` / `individual_boundary` / `reset_semantics` / `inheritance_channel` / `identity_continuity`（重启后怎么算同一个体）/ `clock_source`（step / wall_clock）。先用结构化字符串/枚举描述，框架据此一致执行。
- `RuntimeScenarioBundle` 加 `existence_semantics` 字段（2 个构造点：crafter + linux）。
- Crafter 声明：continuity=HP>0；recoverable=无（单局）；terminal=HP=0；individual_boundary=单 episode；reset=新个体；inheritance=死亡 trace→蒸馏→新个体；identity=加载同一 save→同一 individual；clock=step。
- Linux 声明（优先级低，先显式化当前语义）：进程连续性重；restart=高风险但可恢复；clock=wall_clock。
- 框架读取接口（`get_active_existence_semantics()` 或挂在 bundle 上）。
- 测试。

**A（Crafter 终止 + individual 身份）**：
- 框架 individual 身份层：`individual_id` + provenance（存 runtime_dir，带场景标识）；区别 substrate `instance_id`/`generation`。
- `runners/run_crafter.py:55` 去 reset 续命；HP=0（done）→ 报告"individual terminated"。
- kernel loop（`main.py`）消费 action_runtime 的终止信号 → `exit_reason="individual_terminated"` → 归档 + 正常结束本 run。
- `scenarios/crafter/SPEC.md:176` 旧表述改为 rev2 语义。
- 测试 + 短验证（一个 individual 跑到 HP=0 自然终止，不续命）。
