# 2. 总体架构总览

## 2.1 五层 + 横跨层约束 + 基础设施层

EVA-agent 的整体架构，不是一个“在 LLM 外面包几层工具和规则”的系统，而是一个由 **五层主体结构、一个横跨层约束系统、以及一个位于最底部的基础设施层** 共同构成的工程体。这个结构的核心目的，不是最大化任务吞吐，也不是把全部复杂性都堆进一个中央 planner，而是让“持续存在”“约束先于生成”“动作释放与推理分离”“记忆与学习有正式位置”这些理论要求，在工程上拥有明确落点。

如果把 EVA-agent 压缩成一张最简结构图，可以写成：

```text
L5  Social Layer
L4  Self-Model
L3  Adaptive Deliberation
L2  Drive Layer
L1  Homeostatic Sensing
----------------------------------
横跨层：Anchor System
基础设施层：Infrastructure / Kernel
```

这里最容易被误解的地方有两个。

第一，**基础设施层不是 L1 之前的实现细节**，而是整个系统得以成为“同一个持续主体”的前提。没有 lifecycle kernel、instance identity、persistence 与 event bus，就谈不上任何上层认知结构；因为在那之前，系统甚至无法保证“此刻运行的仍然是合法的、连续的、可恢复的同一实例”。这也是为什么基础设施层虽然不编号为 L1–L5，却必须在总体架构中被单独标出来。

第二，**Anchor System 不是第六层，也不是某个安全插件**。它不是和 L1、L2、L3 平级的“又一层”，而是一个横跨层的结构性约束系统。它限制的不是最终输出，而是候选空间本身；它不等系统先生成动作再去末端过滤，而是在 candidate generation 发生之前就收缩当前允许的动作域。因此，Anchor 必须在总体架构总览阶段就出现，而不能等讲到某个局部模块时再顺带补充。

因此，EVA-agent 的总体结构不是“分层系统 + 附带约束”，而是：

- **基础设施层** 提供持续存在的身体与运行主权；
- **L1–L5** 提供主体的感知、驱动、思辨、自我建模与社会协调结构；
- **Anchor System** 作为横跨层约束，决定上层在任何时刻究竟能进入怎样的候选空间。

三者缺一不可。缺基础设施层，系统会退回一次性进程或不稳定服务；缺横跨层约束，系统会退回先生成再过滤的 task agent；缺层级主体结构，则只剩一具会运行的壳，而没有真正的内部组织。

## 2.2 各部分在整体中的位置

从工程位置上看，EVA-agent 的每一部分都在解决不同层次的问题。

### Anchor System：回答“即使上层想做，哪些事从结构上也不能做”

Anchor 的位置之所以特殊，正是因为它不回答“此刻应该生成什么候选”，而回答“此刻**允许生成**什么候选”。它既要约束 capability 的进入，也要约束 parameter-domain 的范围；既要有 designer-injected 的 structural anchors，也要允许随历史与结果逐渐形成的 dynamic anchors。它不是高层 reasoning 的附属条件，而是 reasoning 所在候选空间的边界。

### 基础设施层：回答“我能不能持续作为同一个我运行”

基础设施层负责：
- lifecycle arbitration
- instance identity / validity
- state persistence
- append-only event recording
- runtime boundary

它不负责“理解世界”，也不负责“决定做什么”，而是负责更前置的问题：**这个主体是否还在、是否合法、是否可恢复、是否有连续的运行边界。** 在 EVA-agent 中，heartbeat-first、tick / turn 分离、lock / generation / lease、运行态写回，全部属于这一层。

### L1：回答“我现在处在什么状态”

L1 是系统的第一认知层。它把来自运行环境、内部状态与外部生命函数的原始输入组织成可以供后续层使用的标准化信号。这里的关键词不是“采集更多指标”，而是：
- state sensing
- rate sensing
- signal publication
- routing
- fast / slow path split

也就是说，L1 不直接做行动决策，而是把“当前发生了什么、正在朝哪个方向变化、这些变化属于 threat 还是 status / background”组织成后续层的统一输入面。没有 L1，就不会有后续的 drive update、candidate shaping 或 threat-triggered reflex。

### L2：回答“系统当前浸润在怎样的内部环境里”

L2 不是任务层，也不是 planner 的前置。它负责的是 **Drive Layer**：把来自 L1 的信号与 judged state 组织成连续变化的内部 drive state，并通过只读 broadcast 向后续层暴露一个上下文环境。

这里的关键不是“告诉 L3 现在该做什么”，而是让 L3 在一个被 drive 改变了倾向的环境里运行。L2 同时还承载 reflex arc：某些低复杂度、高优先级、必须快速发生的反应，不经由完整 deliberation，而由 L2 的快路直接承载。

### L3：回答“如何在受限候选域中形成、评估并释放行为”

L3 是 EVA-agent 中第一个真正意义上的适应性层。它不是单纯的 reasoning layer，而是一个内部还要继续分层的主结构，包括：
- reasoning core
- memory subsystem
- peer circuit / mediator
- tool edge
- outcome evaluation / RPE / habit

L3 之所以复杂，是因为它承担了传统 task agent 往往混在一起做的工作簇：**候选形成、价值判断、记忆检索、动作释放、结果比较与习惯沉淀。** 而 EVA-agent 的关键主张恰恰是：这些事情不能再堆进一个单一 planner 里，而必须被拆开成有边界的子系统。

### L4：回答“系统如何形成对自身能力、代价与风格的抽象”

L4 代表更高阶的 self-model。一个系统只有在已经积累了足够多的 release history、episodic memory、habit trace 之后，才有可能形成关于“我能做什么、我在哪些情境下成本更高、我有哪些稳定偏好”的模型。因此，L4 必然依赖 L3 的积累，而不是先于 L3。

### L5：回答“主体如何把其他主体与外部协作对象纳入自己的世界模型”

L5 关心的是 social / external coordination。它不是一般意义上的联网能力，也不是简单地“加上多 agent 协同”，而是要回答：谁是本体的 conspecific，谁是人类协作对象，谁是别的系统，哪些关系会反过来影响自身结构。它建立在更稳定的 L3 / L4 之上，因此不能前置。


## 2.3 依赖方向与系统边界

EVA-agent 的依赖方向不是任意的。总体上，它遵循以下原则：

```text
L5 → L4 → L3 → L2 → L1 → Infrastructure / Kernel
```

这个箭头表示的是：**高层依赖低层，但低层不能反向依赖高层的推理语义。** 这是一条关键工程边界。

### Kernel 不依赖高层认知

基础设施层必须保留自己的主权。heartbeat-first、instance validity、tick / turn 分离等边界，不能依赖 L3 是否“同意”，也不能被高层 reasoning 解释后绕过。否则整个系统会重新退化成一个由 planner 管所有事的结构中心。

### L1 不依赖 L3

L1 负责 sensing、classification 与 routing。它可以为后续层提供输入，但不能反过来把 L3 的高层推理结果当作感知结构的一部分。否则 L1 会被污染成一个自我解释系统，而不是可靠的输入层。

### L2 只接受来自 L1 的更新，不接受来自 L3 的改写

Drive 是内部环境，不是高层策略变量。也就是说，L3 可以读 `drive_broadcast`，但不能直接写 drive。drive 的变化只能来自 L1 信号与 L2 自身的更新规则。这个边界一旦被破坏，drive 就会退化成“planner 可任意重写的内部变量”，从而失去作为环境的意义。

### L3 必须被 Anchor 约束，且所有 side effect 必经 mediator

L3 可以形成候选、比较价值、调取记忆，但不能直接越过工具执行边界。任何外部 side effect 都必须经过 mediator。与此同时，candidate generation 不能在完整动作全集上展开，而必须受 Anchor 收缩后的 action domain 约束。

### audit trail 与 cognitive memory 必须分层

系统中的所有历史都不是同一种历史。用于重建、审计、调试的 append-only event stream，与用于 salience encoding、retrieval、skill formation 的 cognitive memory，不能混在同一条持久化轨里。否则既不能保证真实审计，也不能保证 memory 有自己的塑形语义。

这些依赖方向共同保证了 EVA-agent 不会重新出现一个中央大脑去统管全部层级。取而代之的是：不同层在自己的位置上处理不同问题，并通过明确接口与边界相互协作。

## 2.4 从理论到工程的总映射

把总体架构再向前压一步，可以得到 EVA v0.5 核心论断与工程结构之间的一一对应关系。

| 理论主张 | 工程对应 |
| --- | --- |
| continuous existence first | Infrastructure / Kernel 主权，heartbeat-first，instance validity |
| drive as contextual broadcast | L2 Drive Layer + read-only `drive_broadcast` |
| anchors as pre-generative structural constraints | Cross-layer Anchor System，`G(s) -> A'(s) ⊆ A(s)` |
| action release structurally distinct from reasoning | L3 内部的 peer circuit / mediator 与 reasoning core 分离 |
| immutable audit trail 与 cognitive memory 分层 | persistence / events 与 L3 memory subsystem 分层 |
| reflex 与 deliberation 并行 | L1 / L2 的 fast path 与 L3 的 slow path 并行存在 |
| learning from outcome discrepancy | L3 的 outcome evaluation、RPE 与 habit crystallization |
| higher self/social layers depend on lower history | L4 / L5 依赖 L3 的 memory、release 与行为历史 |

这张映射表的意义在于提醒：EVA-agent 不是先有一个通用 agent 再往上“加上”这些概念，而是从架构起点开始，就把这些理论主张翻译成不同模块的职责、调用边界与持久化对象。也正因为如此，后文不会把任何一章写成功能介绍，而会持续追问一个问题：

> 这一层、这一模块、这一边界，究竟在保证哪一条工程不变量？

下一章将单独展开 Anchor System。