# 10. 持久化工件与核心运行时对象

## 10.1 runtime_state

到这一章，完整实现方案已经从层级职责展开到了跨层数据面。前面各章讨论的是：系统有哪些结构、每层回答什么问题、边界如何成立；而本章讨论的是：**这些结构在运行中究竟落成哪些正式工件与核心状态对象。**

首先需要明确的是 `runtime_state`。它不是“所有状态的总包”，而是基础设施层面用来表达主体当前最低运行姿态的正式对象。它回答的是：在当前这个时刻，系统作为一个持续实例，处于怎样的运行边界之中。

从前文的 kernel 语义出发，`runtime_state` 至少应当承接以下内容：
- 当前 heartbeat / cadence 相关姿态；
- instance validity 相关投影；
- 当前 turn 是否允许；
- 当前 life-state / conservative posture；
- 其他作为最低运行边界输入面所需的当前态摘要。

它之所以重要，是因为 L1–L5 都不是在真空中运行。尤其 L3 的 reasoning、release 与 learning，必须始终读取当前 runtime posture，而不是假设“系统总是可以普通工作”。因此，`runtime_state` 应当被理解为基础设施层对全系统暴露出的**最低连续性主状态**。

同时，它还必须和其他数据轨严格分开：
- 它不是 append-only history；
- 它不是 drive 主模型；
- 它不是 cognitive memory；
- 它也不是面向兼容层的 projection summary。

所以，`runtime_state` 的本质不是“方便恢复的一份快照”，而是主体最低运行边界的正式当前态。

## 10.2 drive_state

如果 `runtime_state` 表达的是主体当前能否、以及以怎样的姿态继续存在，那么 `drive_state` 表达的就是：**主体当前正浸润在怎样的内部动机环境里。**

`drive_state` 是 L2 的主状态对象。它不等于某个摘要分数，也不等于 pressure 表，更不等于某次推理里的临时目标变量。它承接的是 L2 作为 Drive Layer 的正式 owner：
- 各个 drive slot 的当前强度；
- 它们的变化趋势；
- update / decay / recovery 的当前结果；
- 对后续层可稳定读取的当前内部环境面。

因此，`drive_state` 和 `drive_broadcast` 虽然紧密相关，但不完全等同。更准确地说：
- `drive_state` 是 L2 内部拥有的主状态；
- `drive_broadcast` 是由该主状态向下游暴露的 canonical read surface。

这一区分很关键。因为如果把广播面和主状态混成一个东西，系统就会很容易让高层直接改写 drive；而 L2 之所以能成立，恰恰在于 drive 作为环境必须保持 owner 边界清晰。

所以，`drive_state` 是主体内部环境的主模型，而不是面向外界的展示投影。

## 10.3 external_life_snapshot

除了内部运行态与内部 drive 环境，完整实现还需要一类正式对象，用来表达主体所面对的外部生命函数或外部生存面。这一类对象在这里统一写成 `external_life_snapshot`。

它的作用不是重复 L1 的原始 sensors，而是把那些与主体持续存在密切相关、并需要被跨层读取的外部生命状态，组织成一个较稳定的当前快照面。

它之所以不能简单等同于某条 raw signal，是因为：
- L1 的 signals 是标准化感知输入流；
- `external_life_snapshot` 更接近一个较稳定的跨层当前面；
- 它服务于后续对外部生命条件的持续读取，而不只是一次 signal routing。

在概念上，它可以被理解为：主体对“我所处的外部生命相关环境现在是什么样”的较稳定当前投影。它与 `runtime_state` 的区别在于：
- `runtime_state` 偏向主体内部运行边界；
- `external_life_snapshot` 偏向主体所面对的外部生命相关面。

这类对象之所以值得单列，是因为 EVA-agent 不是纯内省结构。主体既要维持自己的内部连续性，也要持续面对外部生命条件；两者都需要正式数据面，而不能全靠局部推理临时拼接。

## 10.4 events

如果说 `runtime_state`、`drive_state`、`external_life_snapshot` 都偏向当前态，那么 `events` 承接的就是另一条完全不同的语义：**发生过什么。**

`events` 不应被理解为“所有东西最后都写成一行日志”。在完整实现里，它更准确地对应 append-only 的事件流与审计轨。它记录的是：
- 生命周期事件；
- state transition 的关键事实；
- release 相关事实；
- execution 结果；
- 需要被回放、追踪、审计的离散发生。

之所以必须把 `events` 与主状态分开，是因为它们的语义完全不同：
- 主状态回答“现在是什么”；
- 事件流回答“发生过什么”。

如果两者混在一起，就会同时失去两边：当前态恢复不再稳定，历史事实也不再保真。因此，`events` 在完整实现里不是附带记录，而是独立的数据轨 owner。

同时，也要再次强调：`events` 不等于 cognitive memory。事件流可以成为 learning / memory 的事实来源，但“被记住什么、如何被记住”是 L3 memory subsystem 的另一层问题。

## 10.5 candidate / release / learning artifacts

在基础状态对象和事件流之外，完整实现还需要一组更接近 L3 行为闭环的工件。这里把它们收敛成三类：`candidate / release / learning artifacts`。

这组工件至少包括三类语义：

### candidate artifacts

它们承接的是候选形成与内部 deliberation 相关的中间产物，例如：
- candidate suggestion
- prediction hint
- conflict exposure
- reasoning trace 的局部产物

这些产物不一定都要长期持久化为主状态，但它们构成 L3 内部过程可解释性的正式痕迹。

### release artifacts

它们承接的是 candidate 真正越过结构边界时留下的正式记录，例如：
- release decision
- release log
- execution edge metadata
- side effect class / target 相关正式记录

这些 artifacts 对审计、回放、outcome evaluation 都很关键，因为只有 release 被正式记录，系统才知道哪些候选真正越过了内外边界。

### learning artifacts

它们承接的是 L3 memory / learning 路径上的正式产物，例如：
- episodic memory items
- salience-weighted encodings
- skill summaries
- learning bias / habit-related artifacts

这些工件既不同于主状态，也不同于原始事件流。它们构成的是“经验如何被重新沉淀进系统”的正式轨道。

因此，这一组 artifacts 的意义在于：让 L3 内部从候选到释放、从释放到结果、从结果到记忆的过程，不再只存在于一次性推理上下文里，而拥有可持续追踪的工件面。

## 10.6 哪些是主状态，哪些是 projection，哪些是审计流

把本章统一收束起来，可以得到三类不同的数据层级：

### 主状态

主状态是系统当前运行所正式拥有、会被后续层稳定读取、并具有明确 owner 的当前态对象，例如：
- `runtime_state`
- `drive_state`
- 某些稳定的外部生命当前面，如 `external_life_snapshot`

它们回答的是“现在系统是什么状态”。

### projection

projection 是从主状态或更复杂结构中导出的读侧表面，用于兼容、摘要或特定消费者读取，但它本身不是主 owner。例如：
- `drive_broadcast`
- pressure / viability-gap 一类兼容视图
- 某些对外或对下游的压缩摘要面

projection 的意义是读侧便利，不是主权归属。

### 审计流 / 事件流

这类数据轨回答的是“发生过什么”，例如：
- lifecycle events
- release events
- execution outcome events
- append-only audit stream

它们不是当前主状态，也不是认知记忆，而是系统历史事实的正式轨道。

在这三类之外，还存在一条与 L3 相关但不应混入审计流的认知 / 学习工件轨：episodic items、skill traces、learning artifacts。它们与 audit 的区别在于：audit 追求事实保真，memory / learning 追求结构塑形。

因此，本章真正想要立住的不是某几个文件名，而是一条更根本的数据层级关系：**完整 EVA-agent 必须同时拥有当前主状态、读侧投影、历史审计流、以及认知学习工件，而且这些轨道不能混写。**

下一章将把这些工件重新放回运行过程，说明 sensing、drive、deliberation、release、outcome、memory 与 habit 如何在时间上接续成持续运行闭环。
