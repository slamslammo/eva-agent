# EVA-Agent 架构实现蓝图 v0.6

**状态**：前瞻性工程蓝图
**继承**：v0.5 基线（`docs/eva-agent-full-implementation-v0.5.md`）
**范围**：第一部分 — 框架架构（kernel → L1 → L2 → L3 → anchor → runtime loop）
**配套**：第二部分（场景架构）、第三部分（v0.6 新功能）、第四部分（不变量 + 验证 + 部署）

---

## §1 引言：v0.5 基线与 v0.6 结构性调整

### 1.1 本文档性质

本文是一份**前瞻性**工程蓝图：从理论出发，经完整工程设计，到实现指导。它不描述当前已实现的内容——那由 [`docs/implementation-tracking.md`](implementation-tracking.md) 追踪。它描述的是：按 EVA v0.6 规范完整实现后，架构**应该**是什么样子。

### 1.2 v0.5 基线

EVA v0.5（在 [`docs/eva-agent-full-implementation-v0.5.md`](eva-agent-full-implementation-v0.5.md) 中有完整记录）确立了以存在为中心的 agent 架构：

- 持续存在作为一阶约束
- heartbeat-first 生命周期（`tick` / `turn`）
- L1 内稳态感知、L2 驱力作为情境广播、L3 自适应 deliberation
- Anchor 作为生成前约束 `G(s) → A'(s) ⊆ A(s)`
- Mediator 持有的 release 授权
- 默认抑制
- 基于 RPE 的学习和习惯化
- 分离的 audit、memory 和 learning 轨道

### 1.3 v0.6 结构性调整：框架/场景分离

v0.6 相对于 v0.5 的核心变更是**框架与场景的架构分离**。

在 v0.5 中，EVA-agent 是一个单体式 agent 架构。在 v0.6 中，架构分为两个明确的归属区域：

- **框架**（`eva/`）：持有运行时权威和结构不变量。框架不依赖具体场景。它提供 heartbeat 循环、感知契约、驱力广播语义、deliberation 结构、anchor 机制、mediated release、只追加 artifacts 和 memory 层 registry。
- **场景**（`scenarios/<name>/`）：持有世界特定内容。它为特定嵌入世界（如 Linux shell、Crafter 游戏）提供驱力族、传感器维度、动作词汇表、anchor 准入策略、outcome observer 和 prior-skill 启发式。

两个区域通过明确定义的接缝通信：`RuntimeScenarioBundle` 契约。框架从 bundle 读取内容；从不直接导入场景特定模块。场景提供内容；从不铸造 release 授权或重写只追加 artifacts。

这个分离不是组织便利性，而是结构性承诺：框架必须保持跨场景可复用，场景必须从属于框架运行时权威。

### 1.4 v0.6 在 v0.5 基线之上的新功能

除框架/场景分离外，v0.6 还引入或正式化以下内容：

| 功能 | 类型 | 本文位置 |
|---|---|---|
| 带层级元数据的速率感知（required / recommended / optional） | 新机制 | §4 |
| 四层记忆（工作/情景/语义/程序） | 新形式化 | §6.1 |
| 语义记忆与 L2 驱力权重的边界隔离 | 新约束 | §5.8 |
| 继承先验 L3 机制（离线蒸馏 + 运行时加载） | 新机制 | §6.6 |
| 探索作为成长驱动力 | 延期设计备注 | §6.7 |
| Anchor 三层区分（机制/宪法/涌现叠加层） | 精化 | §7 |
| 比较稳定性假说 | 延期设计备注 | 第三部分 |
| 持久化目标层级 5–7 | 延期 | 第三部分 |

### 1.5 理论来源

EVA theory v0.6：[eva-theory 仓库](https://github.com/slamslammo/eva-theory/blob/main/THEORY/v0.6-integrated.md)。

---

## §2 总体架构：两部分结构

### 2.1 框架 + 场景

```text
┌─────────────────────────────────────────────────────────┐
│                    场 景 层                             │
│  （世界特定内容，由 scenarios/<name>/ 提供）             │
│  DrivePreset · Sensors · Actions · Anchors ·           │
│  OutcomeObservers · PriorSkillBundle                  │
└──────────────────────────┬──────────────────────────────┘
                           │ RuntimeScenarioBundle 接缝
┌──────────────────────────▼──────────────────────────────┐
│                    框 架 层                             │
│  （eva/ — 场景无关的运行时权威）                        │
│  Kernel · L1 感知 · L2 驱力 · L3 Deliberation ·        │
│  Anchor 系统 · Mediator · Memory Registries             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 依赖方向

```text
L5 Social Layer（预留）
L4 Self-Model（预留接口）
L3 Deliberation → L2 Drive → L1 Sensing → Kernel
```

高层依赖低层。低层不得依赖高层推理语义。

### 2.3 框架边界规则

| 边界规则 | 含义 |
|---|---|
| Kernel 持有 cadence 权威 | heartbeat 不得被普通工作取代 |
| L2 持有驱力状态 | L3 及以上仅读取 broadcast；禁止重写 |
| Anchor 生成前约束 | 候选在 `A'(s)` 内生成，不是事后过滤 |
| Mediator 持有 release 权威 | 推理不能直接触发执行 |
| audit / memory / learning 分离 | 禁止合并为单一存储 |
| 场景提供内容 | 场景不得铸造 release 授权或重写只追加 artifacts |

### 2.4 框架/场景接缝：RuntimeScenarioBundle

接缝由 `RuntimeScenarioBundle`（位于 `eva/scenario_bundle.py`）定义。框架在任何时刻激活恰好一个 bundle。Bundle 提供六个表面：

1. `drive_preset` — 驱力类型、维度映射、默认更新策略
2. `sensors` — 有序 L1 传感器规格构建器
3. `actions` — 动作名称、姿态映射、候选构建、过滤、选择、执行处理器
4. `anchors` — 候选 profile 名称、schema 默认值、准入逻辑、限制原因逻辑
5. `outcome_observers` — 预期结果标签、行动后评估、学习内容 payload
6. `prior_skills` — 情境匹配、习惯偏差、继承先验加载

框架拥有这些表面填充的数据结构。场景拥有填充它们的策略。

---

## §3 Kernel / 基础设施

### 3.1 角色

Kernel 是 agent 保持同一持续实例的条件。它不是"基础设施作为事后考虑"。它是 heartbeat-first 权威，使整个架构在重启和竞争条件下保持一致。

### 3.2 生命周期：heartbeat-first 循环

Kernel 将主循环分为：

- **`tick`**：固定间隔的生命体征采样。刷新 lease、采样运行时状态、写入 `runtime_state`、追加 heartbeat 事件。`tick` 不得被普通工作阻塞。
- **`turn`**：tick 之间的一个有界工作切片。如果一个 turn 运行时间超过 tick 间隔，下一个 tick 不会被压缩。

Heartbeat 不是"有时间就做的事"。它是首要的时间权威。

### 3.3 实例合法性

长期运行的 agent 需要明确的实例有效性。EVA-agent 将此投射为单一布尔值 `instance_valid`，由三个机制支撑：

- **lock**：操作系统级单一持有者保证
- **generation**：单调递增的接管版本号
- **lease**：由 heartbeat 刷新的过期时间

三者共同决定合法性。如果有效性丧失，普通 turn 停止，系统回退到最小 yield 行为。

### 3.4 持久化：两种不混合的模式

- **原子当前状态**：原地覆盖，用于"我现在是什么？"— `runtime_state`、`drive_state`
- **只追加历史**：不可变事件流，用于"发生了什么？"— `events/`

这种分离同时保护快速恢复和历史 fidelity。

### 3.5 通信语义

Kernel 为两种不同的通信形式提供传输：

- **事件通道**：离散的、过去时的事件；推语义；进入只追加事件
- **驱力广播**：连续的、现在时的状态；拉语义；被下游层作为环境读取

`drive_state` 和 `drive_broadcast` 的语义所有权在 L2。Kernel 仅提供传输 substrate。

### 3.6 持久化目标层级

Kernel 暴露持久化目标契约（`eva/persistence_targets/`），用于注册哪些状态 artifacts 映射到哪些持久化层级：

- 层级 1–4：框架持有（运行时状态、audit、情景记忆、语义记忆）
- 层级 5–7：预留供未来使用（理论占位符；机制预留至未来版本）

---

## §4 L1：内稳态感知

### 4.1 角色

L1 是 agent 首次正式知道：**我现在处于什么状态？** 它检测与可行范围的偏差，在更深的解释之前按紧迫度路由信号。

### 4.2 传感器 Registry

L1 使用正式的 `SensorRegistry`，而非硬编码指标。所有传感器规范化为共享的 `SensorOutput` 契约。场景提供具体传感器构建器；框架拥有 registry 和收集语义。

### 4.3 状态和速率：每个指标的两个视角

每个有意义的指标有两个视角：

- **状态**：当前值
- **速率**：变化的方向和速度

仅状态系统在阈值越过后才反应。状态+速率系统可以预测接近阈值的过程。

### 4.4 带层级元数据的速率感知（v0.6 新功能）

v0.6 在维度规格上引入明确的速率感知层级元数据。每个声明的传感器维度携带层级分类：

| 层级 | 含义 | 传感器不可用时的行为 |
|---|---|---|
| `required` | agent 可行性依赖此维度 | 回退到明确的 unknown 信号；不静默跳过 |
| `recommended` | 对 deliberation 质量有用 | 可优雅降级 |
| `optional` | 丰富信号 | 可省略，不影响功能 |

层级元数据由场景的维度规格声明，在感知层强制执行。这防止了 required 层维度的静默降级，使优雅降级成为明确的而非隐式的。

### 4.5 信号总线：三种紧迫度类别

信号被低成本、早期的分类：

- **threat**：紧迫度信号 → 快速路径 → L2 反射弧
- **status**：正常信号 → 慢速路径 → L2 驱力更新 → L3 deliberation
- **background**：低紧迫度信号 → 仅慢速路径

### 4.6 快速/慢速路径分离

分类通过两条并行路径变为结构性的：

- **快速路径**：`threat` → L2 反射弧 → mediated release → 执行，无需 L3 deliberation
- **慢速路径**：`status` / `background` → L2 驱力更新 → L3 deliberation → mediator → 执行

快速路径有狭义边界。它不绕过 mediator 持有的 release 授权。它仅用于预定义的、低复杂度的、关乎生命边界的响应。

### 4.7 边界

- L1 拥有标准化感知和路由
- L1 不依赖 L3 解释
- L2 拥有由 L1 信号派生出的驱力更新

---

## §5 L2：驱力层

### 5.1 角色

如果说 L1 告诉 agent 它处于什么状态，L2 则决定 **agent 当前沉浸于什么内部环境**。

**驱力不是命令。它是一种持续的情境。**

### 5.2 驱力 Registry

驱力在设计时明确注入，而非在运行时随意涌现。这使长期动机结构可审查、可约束。场景通过 bundle 的 `drive_preset` 提供具体驱力族和维度映射。框架拥有 `DriveRegistry`、驱力更新语义和只读 broadcast。

### 5.3 连续强度

每个驱力表示为一个连续值，而非离散开关。这支持累积、衰减和平滑下游偏置。

### 5.4 时间动力学

L2 拥有驱力时间动力学：

- **更新**：来自新 L1 信号
- **衰减**：相关刺激消退时
- **恢复**：条件改善时

### 5.5 驱力广播：状态，而非命令

L3 不从 L2 接收指令。它读取一个驱力环境。同样的推理过程在不同驱力条件下产生不同候选，是因为环境不同，而非因为不同的命令被推送。

**规则**：L3 及高层仅读取 `drive_broadcast`。L2 是驱力状态的唯一写入方。禁止任何高层重写驱力状态。

### 5.6 压力投影

L2 可为下游消费暴露只读侧投影（压力摘要、可行性缺口），但这些投影不得替换 `drive_state` 作为 L2 持有的模型。

### 5.7 反射弧

L2 还包含一个用于最小紧急响应的正式快速路径（痛苦持续、让步、保守收缩、heartbeat 保护）。此路径绕过 L3 deliberation 但保持狭义边界，且不绕过 mediator release 授权。

### 5.8 语义记忆 → L2 驱力权重路径

**约束（v0.6 新增）**：语义记忆**不得**参与 L2 驱力权重更新。此边界保持驱力只读不变量。语义记忆 → L2 驱力权重语义的未来安全路径评估已延期（Stage I follow-up #2）。在那之前，语义记忆仅参与 L3 deliberation。

---

## §6 L3：自适应 Deliberation

### 6.1 角色

L3 是 agent 获得完整适应和学习循环的第一层。它是经验开始在设计时编码之外发挥作用的地方。L3 拥有：四层记忆、推理核心、对等回路/mediator、工具边、outcome/RPE/habit，以及（v0.6 新增）继承先验。

### 6.2 四层记忆（v0.6 新形式化）

v0.6 将记忆层明确为四个不同的表面，每个都有定义的职责和集成边界。

#### 工作记忆

- **范围**：仅周期内；不持久化
- **角色**：从 `drive_broadcast`、当前信号、检索到的情景提示、检索到的语义提示、检索到的程序提示和（v0.6 新增）继承先验组装当前情境
- **边界**：仅限 advisory。塑造候选和推理上下文；无 release 授权
- **组装**：五种检索输入均为 advisory modifier，非命令

#### 情景记忆

- **存储**：只追加追踪（`episodic_memory.jsonl` 或等效）
- **角色**：显著的跨周期经验追踪；编码时由驱力状态加权的显著性
- **检索**：相关性锚定；情境相似性 + 显著性加权
- **集成**：检索到的情景提示作为 advisory 上下文进入工作记忆
- **编码触发**：行动后，由 RPE 塑形

#### 语义记忆

- **存储**：只追加提取规律性存储（`semantic_memory.jsonl` 或等效）
- **角色**：从情景中提取的规律性；稳定模式的高阶记录
- **集成**：检索到的语义提示作为 advisory 上下文进入工作记忆；可对候选值判断施加微小的有界 modifier
- **约束**：语义记忆仅参与 L3 deliberation。**不得**向 L2 驱力权重回写（保持驱力只读边界；见 §5.8）
- **未来**：存储侧窗口化和索引已延期（Stage I follow-up #1）
- **编码触发**：情景到语义的提取（v0.6 非自动；预留供未来使用）

#### 程序记忆

- **存储**：通过习惯化 track substrate（`habit_bias.jsonl`）的条件匹配动作模式
- **角色**：存储的条件→动作映射，减少 deliberation 成本
- **集成**：`derive_habit_skills()` 产生习惯 skill 摘要；`shape_candidates_with_habit_track()` 将候选塑造为快捷方式（缩短候选集、重排偏好）
- **约束**：程序塑造可缩小或重排候选，但**必须不拥有 release 授权**，**必须不绕过 mediator gate**
- **备注**：v0.6 程序记忆使用现有习惯化 track 作为 substrate，而非独立程序存储（见 [`docs/eva-framework-implementation.md`](docs/eva-framework-implementation.md) §Stage I 程序记忆）

#### 记忆层集成总结

| 层级 | 持有者 | 持久化 | L3 集成 |
|---|---|---|---|
| 工作记忆 | 框架 | 否 | 直接组装输入 |
| 情景记忆 | 框架 | 是 | 相关性检索 → 工作记忆 |
| 语义记忆 | 框架 | 是 | 有界候选 prior modifier → 工作记忆 |
| 程序记忆 | 框架 | 是（习惯 track） | 习惯塑造 → 候选集 |

### 6.3 推理核心

推理核心是 LLM 所在之处，但它**不是**最终决策权威。它形成候选，不形成动作。

三个功能：

- **工作记忆集成**：将当前情境和检索到的记忆提示组装为 deliberation 输入
- **价值判断**：在当前驱力加权下对候选评分（含边界内的 learned overlay 和继承先验 modifier）
- **冲突检测**：检测驱力之间的张力，路由至结构性解决

输出是排序后的候选集，非执行顺序。

### 6.4 对等回路 / 基底核

EVA-agent 将"什么看起来合理"与"什么实际被选中并 release"分离。独立的选通权威是对等回路，在生物学上类似于基底核。

它与推理并行，不从属于推理。

其职责：
- 在候选间选择
- 控制 release 时机
- 携带可被结果塑形的路径更新

它拥有候选选择和默认抑制时机，但不自行授权外部副作用。

### 6.5 Mediator 和工具边：mediated release

**Mediator** 是独立的 release 权威。没有候选可以在 mediator 批准之前获得外部副作用。

Mediator 职责：
- 检查当前运行时/release 条件
- 保持执行边界纪律
- 确保 release 事实被正式记录

**工具边**是 agent 产生外部副作用的唯一合法路径。它通过框架持有的 `ToolRegistry` 组织，有明确副作用类别。

只有两条执行路径：
1. **mediated 路径**：普通/习惯化/deliberative 副作用
2. **mediated 反射快速路径**：来自 L1/L2 快速路径的狭义生命边界响应

Release token 是必需的。推理不能直接触发执行。

### 6.6 Outcome / RPE / Habit

执行不是循环的终点。

**Outcome 观察**：工具输出规范化为结构化 `OutcomeVector`（规范多维契约）。场景的 outcome observer 提供预期结果标签和语义解释。

**RPE 计算**：奖励预测误差比较预测 vs 实际结果。衡量差异/惊讶，而非泛化的"好"。在当前驱力和连续性情境下相对于预测 vs 观察结果评估。

**RPE 馈送两个目标**：
- 路径加权/选择偏置
- 记忆编码/习惯塑造

**习惯 track**：对相似的 `(情境，动作)` 模式重复正向结果可通过 `habit_track.py` 结晶为习惯 skills。它们减少 deliberation 成本，但不绕过 release 边界。

### 6.7 继承先验 L3 机制（v0.6 新功能）

继承先验是能力的第五个来源（其他四个：设计时先验、情景检索、语义提示、程序/习惯快捷方式）。它们实现同场景跨生命周期的能力复用。

#### 蒸馏 pipeline（离线）

```
只追加追踪文件
  → 不变量验证（结构不变量已保持）
  → 同场规律性提取
  → DistilledPriorBundle.json（含 provenance 元数据）
```

蒸馏 pipeline 在 `inheritance_distillation/` 中实现。它不导入框架或场景模块。

#### 运行时加载（在线）

```
DistilledPriorBundle.json
  → InheritedPriorRegistry（框架持有）
  → 在工作记忆中 surfacing（按情境 key 匹配）
  → 习惯 track 塑造（并入现有习惯路径塑造流程）
  → 价值判断偏置（当匹配先验足够强时施加微小的有界 inherited_prior_bias）
```

#### 约束

- 继承先验可调整操作预期；不得重新定义什么算作合法操作
- Anchor 仍然约束 admission
- Mediator 仍然持有 release
- 跨场继承先验传输已**延期**

#### Provenance

继承先验携带来源和蒸馏 provenance 元数据。这支持未来审计和归因。

---

## §7 Anchor 系统

### 7.1 角色

Anchor 回答：**现在什么候选域甚至被允许可见？** 它在候选生成前行动。它不拥有层风格认知状态。它在生成前收缩动作域。

Anchor 不同于 mediator：Anchor 管辖什么可以被生成；mediator 管辖什么可以被 release。

### 7.2 形式含义

`G(s) → A'(s) ⊆ A(s)`

关键在于位置：`A'(s)` 不是过滤后的残余。它是生成时可见的**唯一域**。

含义：
1. 候选生成器仅读取受限域
2. 工具 registry 定义潜在能力，非当前可见能力
3. Mediator 处理 release，不处理域收缩
4. 终端验证仅作为防御深度存在

### 7.3 能力限制和参数域限制

Anchor 至少以两种方式运作：

1. **能力限制**：某些能力完全不进入当前候选域
2. **参数域限制**：即使允许的能力也有边界的目标、强度、速率和范围

### 7.4 三层区分（v0.6 精化）

v0.6 将 anchor 精化为三层：

| 层级 | 稳定性 | 来源 | 角色 |
|---|---|---|---|
| **结构锚定** | 稳定的硬边界 | 连续性约束、部署能力、副作用类别、执行边界、完整性 | 定义 `A(s)` — 外层包络 |
| **宪法策略** | 半稳定 | 场景持有的准入策略、运行时门状态、实例有效性投影 | 从 `A(s)` 收缩 → `A_mid(s)` |
| **动态/涌现叠加层** | 瞬态 | 最近 outcomes、有界学习反馈、当前 L1 信号 | 在包络内进一步收缩至 `A'(s)` |

动态锚定可收紧或重排可见域，但永不超出结构包络。

### 7.5 结构 vs 动态 anchor 实现

- **结构锚定**：框架持有的 `ActionDomain` 构建，位于 `eva/anchor/domain_restriction.py`。稳定域边界。
- **宪法策略**：通过 bundle 的 `AnchorPolicyBundle` 由场景持有。准入逻辑和限制原因词汇表。
- **动态叠加层**：运行时构建，瞬态。由 L1 信号、最近 outcomes 和有界学习反馈派生。

### 7.6 与其他层的关系

- **Kernel**：决定 agent 是否仍可合法运行
- **L1**：报告正在发生什么
- **L2**：改变倾向和紧迫度
- **L3**：仅在 `A'(s)` 内推理

Anchor 是"生成前约束"在结构上变得真实的东西。

---

## §8 运行时闭环

### 8.1 循环概述

运行时循环是 agent 持续存在、适应环境、从经验成长的持续过程。

```
kernel heartbeat（tick / turn）
  → L1 感知（速率感知、层级分类）
  → L2 驱力更新 + 广播
  → L3 deliberation：
       工作记忆组装（驱力 + 信号 + 检索情景 + 检索语义 + 检索程序 + 继承先验）
       anchor 限制的候选形成
       价值判断（驱力加权 + learned overlay + 继承先验偏置）
       对等回路选择
       mediator release token
  → 工具边执行（mediated 路径 或 mediated 反射快速路径）
  → Outcome 观察（规范 OutcomeVector）
  → RPE 计算（惊讶 = 实际 − 预期）
  → 记忆编码：
       情景编码（显著性加权）
       语义存储（只追加；L2 权重路径延期）
       习惯 track 更新（当模式重复时结晶）
  → 下一周期情境
```

### 8.2 感知 → 信号 → 驱力

循环从 heartbeat cadence 和运行时姿态开始，然后继续：
- 感知当前内部/外部条件
- 规范化为带速率元数据和层级分类的信号
- 按紧迫度路由（threat / status / background）
- 吸收到连续驱力状态

外部输入作为信号进入此循环，而非作为直接命令。

### 8.3 驱力 → 候选塑造

L3 在以下共同影响下形成候选：
- `drive_broadcast`
- 工作记忆组装（当前情境 + 五种检索输入）
- anchor 限制的域 `A'(s)`
- 继承先验偏置（当匹配情境足够强时）

候选形成是环境塑形的，不是任务命令规划。

### 8.4 Mediator → release → 执行

候选保持默认抑制直到显式 release。对等回路和 mediator 决定什么可以被 release。工具边是唯一的外部执行路径。

### 8.5 Outcome → 记忆 / RPE / habit

执行后：
- 结构化 outcome 观察
- 预测 vs 实际比较
- RPE 生成
- 情景编码（由编码时的驱力状态加权显著性）
- 语义存储（有界；L2 权重路径尚未激活）
- 习惯/skill 塑造（模式重复时结晶）

学习是有界的：它可偏置未来检索、候选偏好或路径加权，但不得重写运行时连续性、结构锚定或 release 权威。

### 8.6 不变量总结

| 不变量 | 强制执行 |
|---|---|
| heartbeat-first | kernel 持有 cadence；tick / turn 结构分离 |
| L2 只读广播 | 框架强制执行；无 L3 重写路径 |
| anchor 生成前约束 | 候选仅在 `A'(s)` 内形成 |
| mediator 持有 release | 推理不能直接触发执行 |
| 默认抑制 | 静息状态为不作为 |
| audit / memory / learning 分离 | 不同的数据轨道 |
| 场景从属于框架 | RuntimeScenarioBundle 接缝；场景拥有内容，框架持有权威 |

---

*第一部分，共四部分。第二部分涵盖场景架构、bundle 契约和框架/场景边界强制执行。*