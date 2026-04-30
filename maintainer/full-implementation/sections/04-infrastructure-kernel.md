# 4. 基础设施层：Infrastructure / Kernel

## 4.1 为什么它不在 EVA 五层编号里

EVA 五层架构（L1–L5）讨论的是**一个生命体的认知与行为结构**。但在它能讨论"感知 / 驱动 / 决策"之前，必须先有一具能持续运行的**身体**——一具不会因为代码崩溃、机器重启、或者多实例打架就消失的身体。

基础设施层就是这具身体。它不属于 L1，因为 L1 已经是认知活动（"我感觉到了什么"）；基础设施回答的是更前一步的问题：**"我能不能持续作为同一个我活下去"**。

它由四根独立但相互配合的支柱组成，对应理论里 L0/L1 锚点的工程基底：

![Infrastructure position](../../../docs/assets/architecture/infrastructure_position_in_eva.svg)

## 4.2 Lifecycle Kernel — heartbeat-first 的节律源

`Lifecycle Kernel` 是整具身体的**节律源**。它的全部职责只有一句话：**保证心跳不被任何"工作"挤掉**。

它把每一轮主循环明确拆成两种动作：

- **`tick`（生命体征采样）**：固定间隔（默认 15 秒）必须发生一次。它做的事很少——刷新 lease、采样运行状态、写一次 `runtime_state.json`、追加一条 `tick_completed` 事件。它不做"业务"。
- **`turn`（工作时隙）**：在两个 tick 之间的空闲时间里跑。它一次只跑**一个 work slice**（比如一次 patrol、一次 response），跑完就让位回主循环。

之所以要把 tick 和 turn 在代码上彻底分开，是因为 EVA 理论里有一条不可让步的论断：**心跳是反射弧，不是策略**。如果心跳变成了"在 turn 里如果有时间就做"，那就退化成 task agent ——LLM 永远会有"再多想一会儿"的理由。

下面这张图展示的就是 kernel 应承接的节律结构：

![Lifecycle kernel](../../../docs/assets/architecture/lifecycle_kernel_heartbeat_first.svg)

## 4.3 Instance Identity — “我是不是还合法的我”

长期运行的服务有一类很特殊的失败：**进程没死，但已经不是合法的执行者了**。常见场景包括 systemd 重启过程中老进程没退干净、机器假死后恢复出现两个实例、或者运行时目录被外部接管。

EVA 不允许这种情况下"两个我"或"过期的我"继续以 EVA 的名义对外行动。工程上这里不让本体自己直接判断"世界上是否存在另一个我"，而是用三个独立的机制投影出一个布尔值 `instance_valid`。本体只需要看这一个值。

三个机制各自管一种失败模式，缺一不可：

- **`lock` （文件锁）**：操作系统层保证同一时刻只有一个进程持锁
- **`generation` （代际编号）**：单调递增，新实例接管时加一；老实例发现编号对不上就知道自己已经被替代
- **`lease` （租约过期）**：每次心跳刷新过期时间；如果心跳本身停了，租约也会到期

这三个值用 AND 组合成 `instance_valid`。一旦它变成 false，所有 turn 立刻停止，只允许走最小的 yield 收尾路径：

![Instance identity](../../../docs/assets/architecture/instance_identity_three_mechanisms.svg)

## 4.4 Persistence — 两种截然不同的写入模式

很多 agent 系统的状态管理是个大泥潭：**当前状态、历史事件、决策记录全揉在一个数据库里**。EVA 在目标结构中严格地把持久化分成两种**互不混合**的模式，分别用于"当前是什么"和"发生过什么"：

- **现态（atomic state）**：原地覆盖写。文件名固定，每次写入是一次完整的原子替换（先写临时文件 → fsync → rename）。读者永远只看到一个完整的最新版本。这类文件回答的是 "**right now，我是什么样**"。
- **流水（append-only history）**：只能追加，永不修改、永不删除。每条记录是自包含的 JSON 行。这类文件回答的是 "**从我出生到现在，发生过什么**"。

为什么必须分开？因为这两种数据**生命周期不一样、消费者不一样、安全要求也不一样**：

- 现态文件**重启后用来恢复**——必须小、必须读得快、必须保证不会读到半截。
- 流水文件**用来事后回看、用来给 L3 当记忆素材**——必须保留全部历史的真实性，绝不能为了"清爽"被覆盖。

混在一起的后果是：要么牺牲恢复速度（每次启动都要 replay 整段日志），要么牺牲历史完整性（为了恢复方便定期 truncate）。

EVA 选择两者都不牺牲，代价就是接受两种文件并存：

![Persistence split](../../../docs/assets/architecture/persistence_two_patterns.svg)

## 4.5 Event Bus — 两种语义截然不同的内部通讯

这一根在工程架构里必须先把位置占住——因为后面 L2 的"drive 是连续广播而非命令"和 L3 的"事件驱动的 mediator"，全都依赖一个**职责清晰**的 event bus。

它必须同时承载两种**完全不同**的通讯语义，而把它们混在一起写代码就是当前最容易踩的坑：

- **事件通道（event channel）**：传播**离散的、过去时的发生**——"tick 完成了"、"turn 选了 recheck"、"pressure opened"。每个事件是一个时间点上的具体瞬间，会被订阅者在那个时刻收到，会被追加到 `events.jsonl`。push 模式。
- **Drive 广播（drive broadcast）**：传播**连续的、现在时的状态**——"当前 survival 强度是 0.72"。它不是一系列事件的累加，它是一个**任何时候都可以读到的实时状态**。pull 模式。L3 在每次决策前读它一次，得到当前的"情绪环境"。

为什么这两种**绝对不能合并成一个机制**？因为 EVA 理论里"drive as context, not instruction"这条论断的工程含义就是：**drive 不能用事件投递的方式给 L3**。如果 L3 通过订阅 `drive_changed` 事件来反应，那 drive 就退化成命令了——L3 在反应于一个被推送的指令。正确的方式是 drive **始终在那里作为环境**，L3 主动读取，就像化学反应里的温度一样。

下面这张图就是这两条通道的结构关系：

![Event bus](../../../docs/assets/architecture/event_bus_two_channels.svg)

## 4.6 这一层真正决定了什么

基础设施层不直接产生感知、推理或学习，但它决定后续层能否成立：
- 没有 kernel，heartbeat-first 只是口号；
- 没有 instance identity，同一性就是假的；
- 没有 persistence 分层，memory 会长在沙地上；
- 没有 event / drive 的语义分离，L2 的 drive 就会重新退化成命令。

因此，Infrastructure / Kernel 的角色不是“底层工程细节”，而是 **EVA-agent 得以作为同一个主体持续存在的前提**。

下一章进入 L1：Homeostatic Sensing。
