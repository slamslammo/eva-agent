# 6. L2：Drive Layer

## 6.1 L2 的职责边界

如果说 L1 让主体知道“我处在什么状态”，那么 L2 让主体**持续处在某种内部状态里**。它的核心不是命令，而是环境。

EVA 在这里和 task agent 明确分道扬镳：task agent 把动机外化为任务命令；EVA 把动机内化为连续 drive environment。更准确的类比是：**像化学反应里的温度。** 温度不命令任何分子，却改变所有反应倾向。L2 的作用，就是让 drive 在工程上表现得像这种环境，而不是像一条待执行指令。

L2 由四个结构元素组成：

![L2 position](../../../docs/assets/architecture/l2_position_in_eva.svg)

## 6.2 Drive Registry — 被显式注入的长期方向性

L2 的第一件事是回答："这个 agent 内部到底有哪些**长期方向性**？"

EVA 在这里做了一个**非常关键的工程决策**：drive **不是从经验中涌现的，而是设计期就被显式注入的**。

为什么不让它们涌现？因为理论里有一个被严肃对待的假设——**instrumental convergence**：足够能干的系统，无论设计者是否希望，都会发展出某些收敛的子目标（资源获取、自我保存、目标稳定）。既然挡不住，就**主动把它们显式地写出来**，让它们成为可审计、可约束的对象。

EVA 默认注册四种 drive，按优先级（也对应 anchor 层级）排列：

![L2 drive registry](../../../docs/assets/architecture/l2_drive_registry.svg)

## 6.3 Continuous Intensity — 从离散压力到连续状态

离散压力开关代表的是一种常见设计：当某个 signal 跨越阈值时，状态翻档；阈值之内的小变化、积累与自然恢复都不会进入主模型。EVA 要求的是另一种东西：每个 drive 是一个**连续值**（默认 0.0 到 1.0），它会**累加**、会**衰减**、会**平滑地**改变下游行为。这是为了让 drive 行为得**像生物情绪一样**——不是触发器，是底色。

下面这张图把同一组事件序列在两种模型下呈现出来，差距就直观了：

![L2 continuous intensity](../../../docs/assets/architecture/l2_continuous_vs_discrete.svg)

## 6.4 Drive Update / Decay / Recovery — L2 自己拥有时间动力学

Continuous intensity 不是只把 severity 改成浮点数，而是要求 L2 正式拥有 drive 的时间动力学。至少包括三类更新：

- **update**：新的 signal 进入后，按类别、方向与强度把对应 drive 往上推或往下拉；
- **decay**：当没有新的相关信号时，drive 强度应随时间逐步回落，而不是永久停在高位；
- **recovery**：当外部或内部条件持续改善时，系统应允许 drive 回到更低、更稳定的背景水平。

这三类变化都应由 L2 owner 承接，而不是由 L3 在推理时临时"估一个当前情绪值"。只有这样，drive 才是主体内部环境，而不是一次 deliberation 的局部参数。

## 6.5 Drive Broadcast — drive 状态是"环境"，不是"命令"

这是 EVA 整个架构里**最反直觉**的一个工程决策，也是把 EVA 与几乎所有 task agent 框架区分开的核心机制。

绝大多数 agent 系统里，"动机"是命令——某个模块产生一个指令（"现在去做 X"），另一个模块接收并执行。这种模式有两个隐含的代价：**第一，必须有一个中央控制器**来决定何时下令；**第二，"接收指令的模块"事实上变成了执行器**，失去了在自己上下文里独立判断的能力。

EVA 不允许这种结构。drive 在 EVA 里**不能被发送**，只能**作为环境存在**。L3 不"接收 L2 的命令"——L3 在 L2 设定的环境里运行。同一个 L3 推理过程，在 survival = 0.8 的环境下产出的候选，与在 survival = 0.1 的环境下产出的候选会**自然不同**——不是因为它收到了不同的指令，而是因为它工作的环境本身改变了。

理论用了一个非常准确的物理类比：**像化学反应里的温度**。温度不命令分子；它通过改变所有分子的反应倾向来影响系统。drive broadcast 在 EVA 里就是这种"温度"。

工程上这意味着 drive 状态文件**只读不可写**给上层模块——任何 L3 模块都不能"覆盖"survival drive 的值；它只能读取并据此推理。

![L2 drive broadcast](../../../docs/assets/architecture/l2_drive_broadcast_state_not_command.svg)

## 6.6 Reflex Arc — 与 broadcast 并行存在的快路

L2 不只有慢变量环境，还必须同时拥有一条正式快路：`reflex arc`。

reflex arc 是预设的"刺激—反应"模式：threat 信号进来，**不经过 L3**，直接触发一个事先设定好的最小响应（distress 落盘、yield 让位、heartbeat 优先、收缩到 conservative mode）。这一路的延迟是亚秒级的，对应生物体里"被烫到立刻缩手"的脊髓反射弧。

为什么 L2 必须**同时**有这两套机制？因为它们解决的问题完全不同：

- **drive broadcast** 解决"长期处于什么环境"——慢慢累加，缓慢衰减，影响每一次推理的底色
- **reflex arc** 解决"现在这一秒必须立刻做什么"——零延迟，零思考，只走预设模式

两者**不是**同一通路的两个阶段——它们是**架构上并行**的两条路径，共享 L1 信号入口，但出口完全不同：drive broadcast 出口是给 L3 读的状态文件；reflex arc 出口是直接执行。

这里还有一个重要的**结构性不对称**：L3 可以适度抑制 drive broadcast 影响下的某些行为（比如在高 survival 状态下决定不去追求 curiosity），但 **L3 无法关闭 L0/L1 级别的 reflex arc**——心跳优先、instance_invalid 后的 yield 路径，无论 L3 怎么"想"都拦不住。

![L2 reflex arc](../../../docs/assets/architecture/l2_reflex_arc_parallel_to_broadcast.svg)

## 6.7 Pressure 是 projection，而不是主模型

Pressure、viability-gap 或类似兼容视图，可以作为对外暴露或对下游消费的摘要面存在；但它们不应取代 L2 的主状态。

原因很简单：projection 关注的是**读侧可见性**，而主模型关注的是**owner 语义**。如果把 pressure summary 直接当成 L2 的真实内部状态，系统就会把连续 drive environment 重新压扁成若干方便读取的标签，最后又退化回离散控制模型。

因此，正确关系应当是：

- `drive_state` 是 L2 的主模型；
- pressure / viability-gap 是从主模型导出的 projection；
- projection 可以服务兼容层或读侧摘要，但不反向拥有主状态主权。

## 6.8 L2 与 L1 / L3 / Anchor 的关系

L2 的边界只有放回相邻层里才真正清楚：

- **与 L1**：L1 发布标准化 signal，L2 读取这些 signal 并完成 drive update / decay / recovery；
- **与 L3**：L3 只能读取 drive broadcast，并在该环境中形成候选与评分，不能直接改写 drive 主状态；
- **与 Anchor**：drive 可以改变候选倾向、排序与紧迫度，但不能放宽 Anchor 已经收缩的结构域。

所以，L2 真正提供的不是命令入口，而是一层连续、只读、由 L2 owner 维护的内部环境。

## 6.9 这一层真正决定了什么

L2 是 EVA 与 task agent 真正分道扬镳的地方：
- 没有 continuous intensity，drive 只是压力开关；
- 没有 broadcast，drive 会重新退化成命令；
- 没有 reflex arc，除 heartbeat-first 外的快速反应都不存在。

因此，L2 的角色不是“给上层一点优先级信息”，而是让后续 reasoning、memory retrieval、value judgment 与 release 全都发生在某种**连续、只读、可衰减的内部环境**之中。

下一章进入 L3：Adaptive Deliberation。
