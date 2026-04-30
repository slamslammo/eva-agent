# EVA v0.5 工程架构映射

本文档定义 `eva-agent` 的 **v0.5 工程架构映射**。

它回答的是：**目标架构如何在工程上被拆成模块边界、数据边界、运行边界与持久化合同。**

文档职责划分如下：
- `docs/architecture.md`：目标架构是什么
- `docs/engineering-architecture.md`：目标架构如何落成工程结构
- `docs/development/roadmap.md`：按什么顺序推进
- `docs/development/*-progress.md`：当前已经落到哪里

因此，本文档不做 phase 进展汇报，但会保留实现落地所必需的**工程接缝**与**兼容约束**。

## 1. 工程映射原则

理论到工程的映射至少遵守以下原则：

1. **结构优先于 prompt**
   - default inhibition、drive broadcast、anchor、mediator 等边界必须由代码结构承接

2. **owner 关系清晰**
   - 哪一层拥有主状态、哪一层只读、哪一层只能投影，必须可明确指出

3. **目标结构与兼容投影分离**
   - 兼容层可以存在，但不能重新变成未来主结构的 owner

4. **audit 与 memory 分离**
   - 运行回放、调试追溯与 cognitive / episodic memory 不是同一条数据轨

5. **遇到理论空白时显式提出**
   - 不在正文里隐式扩写未经材料支持的新定义

## 2. 工程结构总览

工程上，目标结构可视为四类边界共同作用：

- **运行边界**：kernel、instance validity、runtime gate
- **状态边界**：signal、drive、memory、audit、tool release
- **持久化边界**：atomic state、append-only history、cognitive memory、compatibility projections
- **执行边界**：reasoning、peer circuit、mediator、tool edge

其中最重要的工程链条是：

```text
signal_batch -> drive_broadcast -> deliberation -> mediator -> tool edge
```

这条链之外，仍允许存在：
- reflex arc 快路
- compatibility projection / compatibility execution

但它们不能反向改写主结构 owner。

## 3. 基础设施层的工程边界

![Infrastructure position](./assets/architecture/infrastructure_position_in_eva.svg)

### 3.1 Lifecycle Kernel

Kernel 的工程职责是：
- 维护 heartbeat-first 主循环
- 明确 `tick` / `turn` 的优先级边界
- 暴露下游可读但不可越权的 runtime gate context

工程含义：
- 心跳刷新、实例合法性检查、最小运行态写入属于 kernel owner
- downstream 读取的是运行边界，不是反向改写 kernel 决策

### 3.2 Instance Identity

实例合法性由一组低层机制投影成 `instance_valid`。目标工程边界是：
- `lock` 负责同一时刻的单实例持有
- `generation` 负责实例替换检测
- `lease` 负责心跳中断后的自然过期

工程上，downstream 不直接参与“我是不是合法的我”的判定，只读取投影结果。

### 3.3 Persistence

工程落地必须至少形成四类持久化语义：

1. **kernel current state**
   - 原子覆盖写
   - 服务重启恢复
   - 不混入 drive / memory 主模型

2. **append-only audit / event history**
   - 生命周期事件、release 轨、运行回放
   - 只追加，不回写

3. **cognitive / learning artifacts**
   - episodic memory、learning outcome、habit bias、skill summary 等认知相关数据轨
   - 不与 audit 轨混写

4. **compatibility projections**
   - 迁移期允许保留，但只作为投影或兼容输出面

![Persistence split](./assets/architecture/persistence_two_patterns.svg)

### 3.4 Event Bus

工程上必须把两类内部通讯拆开：

- **event channel**
  - 传播离散发生
  - 支持 append-only event stream
  - 适合作为订阅与回放的基础

- **drive broadcast channel**
  - 传播连续状态
  - 以只读快照方式暴露给下游
  - 不通过“命令推送”驱动 deliberation

![Event bus](./assets/architecture/event_bus_two_channels.svg)

## 4. L1 的工程映射

![L1 position](./assets/architecture/l1_position_in_eva.svg)

L1 的工程 owner 是：
- 感知输入归一化
- state + rate 形成
- urgency pre-classification
- 对下游暴露标准化 signal surface

### 4.1 Sensor Registry

工程上，L1 应优先固化的是 sensor 接口与注册方式，而不是部署期的具体指标集合。

这意味着：
- sensor 可替换、可扩展
- 不同底层采样来源输出统一形状
- 上层只面对标准化信号，不面对每个部署源的细节

![L1 sensor registry](./assets/architecture/l1_sensor_registry.svg)

### 4.2 标准化信号合同

目标最小语义至少包括：
- `source`
- `class`：`threat | status | background`
- `payload`
- `captured_at`
- `rate_context`

这组字段的工程意义不是定义所有语义，而是：
- 为 L2 drive update 提供统一读侧
- 为 L3 deliberation 保留统一输入面
- 为未来 fast / slow routing seam 预留结构接缝

### 4.3 Signal Batch

L1 对下游暴露的工程输入面应是标准化的 `signal_batch`，而不是一组松散的 patrol 局部变量。

最小结构可保持为：
- `signal_batch.signals`
- `signal_batch.summary`

这使 L3 面向的是“信号批次合同”，而不是 patrol 的内部实现细节。

### 4.4 Fast / Slow Routing Seam

工程上，L1 应在分类后保留快慢分流接缝：
- `threat` 保留进入 reflex arc 的快路能力
- `status/background` 保留进入 drive update 与 deliberation 的慢路能力

即使某些快路在当前实现中仍是特例，这个接缝也应先作为 owner 边界存在。

![L1 signal bus](./assets/architecture/l1_signal_bus_classification.svg)

## 5. L2 的工程映射

![L2 position](./assets/architecture/l2_position_in_eva.svg)

L2 的工程 owner 是：
- drive registry
- continuous intensity update
- accumulation / decay rules
- drive broadcast
- reflex arc

### 5.1 Drive Registry

目标工程结构将 drive 显式保持为独立主状态，而不是 pressure 表的别名。

当前材料支持的基础 drive 为：
- `survival`
- `integrity`
- `continuity`
- `curiosity`

它们应成为可审计、可解释、可更新的状态槽位。

### 5.2 Continuous Drive State

工程上，drive 更新规则至少应支持：
- 从 L1 信号增量累积
- 随时间衰减
- 在每个评估周期形成当前快照

其结果是一个连续 drive state，而不是只在阈值越界时翻档的离散压力表。

![L2 continuous intensity](./assets/architecture/l2_continuous_vs_discrete.svg)

### 5.3 Drive Broadcast

L2 向后续层暴露的 canonical read surface 应为 `drive_broadcast`。

其工程最小语义可稳定为：
- `captured_at`
- `top_drive`
- `drive_levels`
- `drive_trends`

关键约束：
- 这是只读接口
- L3 不能直接改写 drive
- compatibility action path 如需读取 drive，也只能经兼容接口读取该广播面

![L2 drive broadcast](./assets/architecture/l2_drive_broadcast_state_not_command.svg)

### 5.4 Reflex Arc

L2 还拥有与 broadcast 并行的 fast path owner：`reflex arc`。

它的工程含义是：
- threat 输入可触发最小响应模式
- 不经过 L3 候选生成与评分
- 仍受 kernel 连续性边界与 anchor 约束

![L2 reflex arc](./assets/architecture/l2_reflex_arc_parallel_to_broadcast.svg)

### 5.5 Pressure 兼容视图的定位

在 theory-to-engineering 的落地过程中，pressure / viability-gap 视图可以作为兼容投影保留，但工程 owner 必须清楚：
- pressure 不是 drive 的 owner
- pressure 是 projection，不是内部主模型
- compatibility response path 也不等于未来 L3 owner

## 6. L3 的工程映射

![L3 position](./assets/architecture/l3_position_in_eva.svg)

L3 的工程 owner 不再是单个“response selector”，而是四个子系统的协作闭环：
- memory
- reasoning core
- basal ganglia peer circuit
- tool edge / mediator

### 6.1 Deliberation Input

L3 的稳定强制输入面应来自上游三条合同：
- `signal_batch`
- `drive_broadcast`
- `runtime_gate_context`

此外，`working_memory_context` 可以作为可选增强输入，而不成为新的架构 prerequisite。

### 6.2 Runtime Gate Context

Kernel 对 downstream 的 canonical runtime surface 是 `runtime_gate_context`。

最小语义包括：
- `instance_valid`
- `turn_allowed`
- `critical_blocked`
- `conservative_mode`
- `life_state`

它的工程含义是：L3 读取 signal / drive 时，同时读取当前运行边界，而不是在脱离 kernel 约束的真空里推理。

### 6.3 Memory Subsystem

L3 memory 的工程落地必须至少形成三条语义分离的数据轨：

1. **deliberation / release audit**
   - 供回放、调试、追责

2. **episodic / cognitive memory**
   - 供 salience-weighted 编码与 contextual retrieval

3. **learning / habit artifacts**
   - 供 outcome evaluation、bounded bias、habit crystallization、skill summary 使用

这三条轨不能因为都“长得像 jsonl”就被合并为同一 owner。

![L3 memory overview](./assets/architecture/l3_memory_overview.svg)

### 6.4 Reasoning Core

Reasoning Core 的工程职责是：
- 整合当前上下文
- 生成候选
- 按 drive 权重评分
- 在发生拉扯时显式暴露冲突

但它不拥有 release authority。

![L3 reasoning core](./assets/architecture/l3_reasoning_core_overview.svg)

Working memory / LLM adapter 的工程位置只允许在这里：
- 输入：signal / drive / memory / runtime gate
- 输出：candidate suggestion、prediction hint、reasoning trace、confidence
- 不直接输出 side effect

![L3 working memory](./assets/architecture/l3_working_memory_llm_position.svg)

### 6.5 Basal Ganglia Peer Circuit

Peer circuit 的工程 owner 是：
- 维持 default inhibition
- 在候选之间进行选择
- 决定何时释放
- 消化 outcome / RPE，并推动 habit crystallization

它与 reasoning core 平级，不能退化成“reasoning 之后顺手执行一下”的下游函数。

![L3 basal ganglia](./assets/architecture/l3_basal_ganglia_overview.svg)

### 6.6 Mediator 与 Tool Edge

工程上，所有对外 side effect 都必须经过 `mediator -> tool edge`。

因此，mediator 的 owner 边界是：
- 接收 candidate
- 维持显式 release gate
- 记录 release log
- 将 reasoning 与 tool execution 解耦

Tool edge 的 owner 边界是：
- 维护工具注册表
- 按 side effect class 管理可执行器
- 成为唯一触碰外部世界的合法路径

![L3 mediator](./assets/architecture/l3_mediator_three_functions.svg)
![L3 tool edge](./assets/architecture/l3_tool_edge_position.svg)

### 6.7 Learning Loop 的工程位置

在工程上，learning 不是额外旁路，而是 L3 中受限回流的结构：

```text
release intent
-> compatibility execution outcome
-> outcome delta
-> bounded learning bias
-> habit crystallization
-> working-memory advisory context
```

关键约束：
- learning 只能回流为 bounded bias / bounded narrowing / advisory context
- learning 不能扩成新的 release authority
- habit 不能绕过 runtime gate、anchor、mediator

![L3 full loop](./assets/architecture/l3_full_collaboration_loop.svg)

## 7. 工程工件与暴露面

下表给出目标工程结构中的关键工件 / 暴露面与 owner 关系：

| 工件 / 暴露面 | Owner | 主要消费者 | 角色 |
| --- | --- | --- | --- |
| `runtime_gate_context` | kernel | L3 / downstream | 最小运行边界输入 |
| `signal_batch` | L1 | L2 / L3 / downstream | 标准化感知输入 |
| `drive_broadcast` | L2 | L3 / downstream | 只读动机环境面 |
| audit event stream | kernel / mediator / execution edges | replay / debugging | append-only audit |
| cognitive / episodic memory | L3 memory | reasoning core | 情境回忆与 threat recognition |
| learning / habit artifacts | L3 learning path | working memory / habit derivation | bounded adaptation |
| compatibility projections | projection / compatibility layer | legacy read surfaces | 迁移期投影，不是主 owner |

## 8. 兼容层与迁移约束

为了让目标结构能在现有 repo 上逐步落地，需要保留一组明确降级的兼容层：

- `active_pressures.json`
- `survival_log.jsonl`
- `response_history.jsonl`
- `response.py` 所代表的 compatibility execution path

这些接缝可以保留，但工程定位必须稳定：
- 它们属于 compatibility / projection layer
- 它们可以承载迁移期输出
- 它们不再定义未来主结构 owner

## 9. Open alignment questions

以下问题在当前材料里仍应保持显式 defer，而不是擅自补写：

1. **L4 / L5 的工程落地形状**
   - 当前材料只支持理论位置与依赖前提，不支持完整工程细化

2. **完整 habit execution layer 的后续扩展边界**
   - 当前材料明确支持 bounded bias、bounded narrowing 与 advisory seam；更完整的 habit execution 不应在本轮文档里被提前补写

3. **更完整的 social / deployment coordination 结构**
   - 当前材料不足以定义完整 L5 owner、部署协议与外部主体协同模型

在这些问题明确之前，本文档只保留当前材料所支持的工程边界。