# EVA v0.5 目标架构

本文档定义 `eva-agent` 的 **EVA v0.5 目标架构**。

它只回答一件事：**如果以 EVA v0.5 作为先验理论起点，`eva-agent` 应该按什么结构来设计。**

因此，本文档只保留：
- 理论对齐后的目标分层
- 各层关键能力与边界
- 横跨层约束
- 关键结构合同

本文档**不记录当前实现进展**、不记录 phase 完成度，也不承担路线图职责。当前状态见：
- `docs/engineering-architecture.md`
- `docs/development/roadmap.md`
- `docs/development/phase-c-progress.md`

## 1. 项目定位

`eva-agent` 是一个 **EVA v0.5 对齐**的 existence-centered agent 架构实验工程。

它关注的不是如何把 agent 做成更强的 task orchestrator，而是如何先建立一条符合 EVA 的结构主干，使后续能力在正确的位置上生长。公开主线聚焦以下几点：

- continuous existence as a first-order constraint
- drive as contextual broadcast
- anchors as pre-generative structural constraints
- action release structurally distinct from reasoning
- audit trail 与 cognitive memory 分层

## 2. 工程不变量

EVA theory 给出的不是“更好的 task agent 架构”，而是一组必须被工程结构显式承接的反转。它们不能只体现在 prompt、运行时约定或末端策略里。

| 维度 | task agent 的默认 | EVA agent 的工程不变量 |
| --- | --- | --- |
| 默认行为状态 | ready to execute | **default inhibition**，动作必须被显式释放 |
| 动机机制 | 外部 task = drive | drive 是**连续强度的内部状态广播**，不是命令 |
| 约束机制 | 输出后过滤 | **生成域约束**（anchor），`G(s) -> A'(s) ⊆ A(s)` |
| 选择与论证 | reasoning 同时负责 | **peer circuit 与 reasoning 分离**，候选生成 ≠ 选择释放 |
| 学习信号 | 外部 reward / RLHF | **RPE 内生信号**，`actual - expected` |
| skill 形成 | 显式编程 | RPE 驱动的**涌现**（habit crystallization） |
| 生命边界 | 任务边界 | 生命循环边界，**heartbeat-first** 不可被 ordinary work 抢占 |
| 记忆功能 | 服务召回 | 服务**威胁识别 + 技能形成**，按 salience 加权 |

这八条不变量决定了后续所有层的边界。

## 3. 总体结构

`eva-agent` 的目标结构采用：**五层 + 横跨层约束 + 基础设施层**。

```text
L5  Social / External Coordination
L4  Self Model
L3  Adaptive Deliberation
L2  Drive Layer
L1  Homeostatic Sensing
----------------------------------
横跨层：Anchor System
基础设施层：Lifecycle Kernel / Instance Identity / Persistence / Event Bus
```

其中：
- **基础设施层**回答“我能否持续作为同一个我运行”
- **L1-L5**回答“我如何感知、维持、思辨、形成主体与外部协同”
- **Anchor System**回答“候选域在生成前如何被结构性收缩”

在当前材料中，L4 / L5 只保留理论位置与依赖前提；本文不擅自扩写超出材料支持的新定义。

## 4. 基础设施层

基础设施层是 EVA 五层结构之下的工程底盘。它不承担高层认知语义，而是先保证主体连续性、实例合法性、持久化边界与内部通讯语义成立。

![Infrastructure position](./assets/architecture/infrastructure_position_in_eva.svg)

### 4.1 Lifecycle Kernel

`Lifecycle Kernel` 是整套系统的节律源。

它的基本约束是：**heartbeat-first**。生命节律不是一个“如果有空就执行”的 ordinary task，而是主循环的优先边界。

因此主循环必须显式分成两种动作：
- **`tick`**：生命体征采样与最低限度状态刷新
- **`turn`**：两个 tick 之间的工作时隙，一次只承载有限的 work slice

![Lifecycle kernel](./assets/architecture/lifecycle_kernel_heartbeat_first.svg)

### 4.2 Instance Identity

EVA 要求系统能够判断“我是不是还合法的我”。

工程上，这个判断不由高层 reasoning 负责，而由实例合法性机制负责。目标结构采用三个互补机制共同投影出 `instance_valid`：
- `lock`
- `generation`
- `lease`

只有 `instance_valid == true`，后续 ordinary turn 才有继续运行的前提。

![Instance identity](./assets/architecture/instance_identity_three_mechanisms.svg)

### 4.3 Persistence

持久化必须明确分成两种**不可混淆**的模式：
- **atomic current state**：回答“right now，我是什么状态”
- **append-only history**：回答“从我启动到现在，发生过什么”

两者的职责、消费者、恢复语义与安全要求都不同，不能混成同一个存储层。

![Persistence split](./assets/architecture/persistence_two_patterns.svg)

### 4.4 Event Bus

基础设施层还必须承载两种语义完全不同的内部通讯：
- **事件通道**：离散、过去时、push 的发生
- **drive 广播通道**：连续、现在时、pull 的状态

这两种通道不能合并，否则 `drive as context, not instruction` 无法在工程上成立。

![Event bus](./assets/architecture/event_bus_two_channels.svg)

## 5. L1：Homeostatic Sensing

L1 是主体第一次“知道自己处在什么状态”的层。

它不负责生成动作，而负责：
- 检测偏离
- 统一信号形状
- 在深度解释前先做紧急程度分流
- 为后续 drive 更新与 deliberation 提供输入

![L1 position](./assets/architecture/l1_position_in_eva.svg)

### 5.1 Sensor Registry

L1 的第一原则不是“固定几项指标”，而是“先有一个可扩展的感知注册系统”。

部署环境不同，传感器会不同；L1 固化的是注册接口与统一输出形状，而不是钉死某个部署场景下的具体指标。

![L1 sensor registry](./assets/architecture/l1_sensor_registry.svg)

### 5.2 State + Rate

EVA 的感知不是只看当前态，还必须同时看变化率：
- **State**：此刻是什么值
- **Rate**：它正以什么方向、什么速度变化

只有同时拥有 state 与 rate，系统才不仅是阈值触发式反应，而具备最小的代谢式预判能力。

![L1 state vs rate](./assets/architecture/l1_state_vs_rate.svg)

### 5.3 Signal Bus

L1 需要把传感器输出统一进入 `Signal Bus`，并在深度解读前先做粗分类。目标分类至少包括：
- `threat`
- `status`
- `background`

分类的意义不是给出最终解释，而是先决定后续进入哪一类路径。

![L1 signal bus](./assets/architecture/l1_signal_bus_classification.svg)

### 5.4 Fast / Slow Path Split

在 L1 中，信号分类之后应形成明确的快慢分流：
- **快路**：`threat -> reflex arc -> execution`
- **慢路**：`status/background -> drive update -> deliberation -> mediated release`

快路不等待慢路；慢路也不争夺快路的执行权。

![L1 fast/slow split](./assets/architecture/l1_fast_slow_path_split.svg)

## 6. L2：Drive Layer

L2 负责让系统持续地处在某种内在动机环境里。

在 EVA 中，drive 不是外部任务的改写，也不是中央控制器下发的命令；它更像化学反应里的温度，会持续改变整个系统的反应倾向。

![L2 position](./assets/architecture/l2_position_in_eva.svg)

### 6.1 Drive Registry

L2 的第一步是显式定义长期方向性的 drive registry，而不是让这些方向性在运行后隐式涌现。

当前材料里保留四类基础 drive：
- `survival`
- `integrity`
- `continuity`
- `curiosity`

![L2 drive registry](./assets/architecture/l2_drive_registry.svg)

### 6.2 Continuous Intensity

每个 drive 在目标结构里都应是**连续值**，而不是离散 severity 开关。

连续 drive 允许：
- 多个小信号累积
- 一段时间后自然衰减
- 对下游产生平滑的上下文影响

![L2 continuous intensity](./assets/architecture/l2_continuous_vs_discrete.svg)

### 6.3 Drive Broadcast

Drive 影响下游的方式不是下达命令，而是提供一个**只读环境面**。

L3 不接收“去做 X”的命令；L3 在当前 drive broadcast 所定义的环境里完成候选生成、评分与释放判断。

![L2 drive broadcast](./assets/architecture/l2_drive_broadcast_state_not_command.svg)

### 6.4 Reflex Arc

L2 内部与 drive broadcast 并行存在的是 `reflex arc`。

它负责承接 threat 类快速反应：
- 不经过 L3
- 不依赖复杂 reasoning
- 只触发预设的最小响应模式

这使系统同时拥有：
- 长时段的连续动机环境
- 当前时刻的快速威胁反应

![L2 reflex arc](./assets/architecture/l2_reflex_arc_parallel_to_broadcast.svg)

## 7. L3：Adaptive Deliberation

L3 是目标结构中第一个能积累并使用“初始化时不存在的信息”的层。

它不是单个 reasoning 模块，而是至少由四个相互制衡的子系统组成：
- Memory
- Reasoning Core
- Basal Ganglia Peer Circuit
- Tool Edge / Mediated Action Edge

![L3 position](./assets/architecture/l3_position_in_eva.svg)

### 7.1 Memory

L3 的 memory 子系统不是通用日志堆，而是第一层“个人经历”存储。

它由两个职责不同的部分构成：
- **Episodic Memory**：按 salience 编码的事件经历
- **Skill Library**：从重复成功经验中结晶出的可复用模式

![L3 memory overview](./assets/architecture/l3_memory_overview.svg)

#### Episodic Memory

Episodic memory 的关键不是“记下来”，而是**按当时的 salience 加权编码**。

Salience 来源于事件发生时的 drive 环境，它决定：
- 记忆保留强度
- 相似情境下的检索优先级

![L3 episodic salience](./assets/architecture/l3_episodic_salience_encoding.svg)

#### Skill Library

Skill library 不负责理解情境，而负责在高度稳定、反复验证的情境下直接复用“情境 -> 动作”模式。

它的来源不是显式硬编码，而是由重复成功的 outcome 与 RPE 信号逐渐结晶而成。

![L3 skill library](./assets/architecture/l3_skill_library_crystallization.svg)

#### 两类存储的边界

Audit、episodic memory、skill library 不能混成单一数据层。

![L3 memory boundary](./assets/architecture/l3_memory_two_stores_boundary.svg)

### 7.2 Reasoning Core

Reasoning Core 是 L3 中唯一“想”的地方，但它不拥有释放权，也不拥有直接执行权。

它至少由三个区域构成：
- **Working Memory**：整合上下文，产出候选与预测
- **Value Judgment**：按 drive 权重对候选评分
- **Conflict Detection**：当 drive 拉扯时显式路由冲突

![L3 reasoning core](./assets/architecture/l3_reasoning_core_overview.svg)

#### Working Memory

Working memory 负责把 `signal`、`drive`、`memory`、`runtime gate` 等输入整合成当前推理上下文。LLM 如被使用，也只能坐在这个位置。

![L3 working memory](./assets/architecture/l3_working_memory_llm_position.svg)

#### Value Judgment

候选动作的评估不是抽象“任务效用”最大化，而是由当前 drive 环境加权决定。

![L3 value judgment](./assets/architecture/l3_value_judgment_drive_weighted.svg)

#### Conflict Detection

当多个 drive 对候选给出互相矛盾的偏好时，冲突不应由 LLM 自我合理化消解，而应被显式路由到 anchor 约束与结构性边界上解决。

![L3 conflict detection](./assets/architecture/l3_conflict_detection_routing.svg)

### 7.3 Basal Ganglia Peer Circuit

Basal Ganglia 与 Reasoning Core 是**平级**关系，不是 reasoning 的下游执行器。

它承担的结构性职责是：
- 维持 default inhibition
- 在候选之间做选择
- 控制何时释放
- 读取 outcome / RPE 并推动 habit crystallization

![L3 basal ganglia](./assets/architecture/l3_basal_ganglia_overview.svg)

### 7.4 Tool Edge / Mediated Action Edge

Tool Edge 是系统影响外部世界的唯一合法出口。

任何对外 side effect 都必须经过：
- candidate generation
- value judgment
- peer-circuit 选择
- mediator release
- tool edge execution

![L3 tool edge](./assets/architecture/l3_tool_edge_position.svg)

#### Mediator

Mediator 的职责不是“业务编排”，而是 default inhibition 的结构性保证：
- 接收 candidate
- 维持显式 release gate
- 记录 release log
- 确保 reasoning 与 side effect 解耦

![L3 mediator](./assets/architecture/l3_mediator_three_functions.svg)

#### Tool Registry

Tool Edge 通过工具注册表定义哪些执行器是可用的，以及它们属于什么 side effect class。Anchor 与 release 约束会作用在这里。

![L3 tool registry](./assets/architecture/l3_tool_registry_side_effects.svg)

### 7.5 L3 协作闭环

L3 不是单个模块，而是 memory、reasoning、peer circuit、tool edge 四者的协作闭环。

![L3 full loop](./assets/architecture/l3_full_collaboration_loop.svg)

## 8. L4：Self Model

L4 对应更高阶的自我模型能力。

在当前材料中，L4 的理论位置已明确，但工程细节尚未展开。它的前提是：
- L1 / L2 / L3 已积累足够稳定的状态史、release 史与 memory 史
- 下层结构边界已足够清晰
- L3 的 learning / habit / memory 语义已经稳定

因此，本文只保留其理论位置，不额外扩写未被材料支持的工程定义。

## 9. L5：Social / External Coordination

L5 对应主体与外部系统、其他主体或更复杂部署环境之间的协同结构。

在当前材料中，L5 同样只保留理论位置与依赖前提：
- 需要更成熟的主体边界
- 需要更稳定的内部架构
- 需要比当前阶段更清晰的 deployment 语义

本文不提前补写超出材料支持的实现模型。

## 10. Anchor System（横跨层）

Anchor 不是末端 safety filter，而是 **pre-generative structural constraint**。

它的含义不是“先生成，再删掉不安全候选”，而是：

```text
G(s) -> A'(s) ⊆ A(s)
```

也就是说，候选生成本身就发生在被约束后的域中。

在当前材料中，Anchor System 横跨 L1 / L2 / L3，并以多层约束形式出现：
- `L0 Constitutional`：注入式根约束
- `L1 Integrity`：与主体连续性、完整性相关的边界
- `L2+ Emergent`：随着更高层结构形成而出现的上层收缩约束

## 11. 关键结构约束

目标结构至少保持以下硬约束：

- drive 只能由 L1 信号与 L2 更新规则改变；高层只能读，不能直接写
- reasoning 不等于 release；候选生成、评分、选择、释放必须分层
- 所有外部 side effect 都必须经过 mediator 与 tool edge
- audit trail 与 cognitive memory 必须分离
- reflex arc 可以绕过 L3，但不能绕过基础连续性边界
- anchor 作用于生成域，而不是仅作用于末端过滤

## 12. 依赖方向

目标依赖方向保持：

```text
L5 -> L4 -> L3 -> L2 -> L1 -> Infrastructure
```

同时满足：
- 高层可以读取低层暴露面，但不应反向改写低层内部主状态
- Anchor 可以被高层使用，但 Anchor 自身不依赖高层推理成立
- 任何兼容层、过渡层、执行桥接层，都不能反向重写目标结构的 owner 关系
