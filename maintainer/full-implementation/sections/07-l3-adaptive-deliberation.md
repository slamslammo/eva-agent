# 7. L3：Adaptive Deliberation

## 7.1 L3 的职责边界

如果说 L1 让主体知道“现在发生了什么”，L2 让主体持续浸润在某种 drive environment 中，那么 L3 就是主体第一次拥有**适应与学习闭环**的地方。

理论对"intelligence"有一个工程上的精确定义：**当且仅当一个系统能使用超出原始设计所包含的信息，它才在工程意义上变得智能**。

L1 和 L2 只能处理设计时编码的模式，L3 是第一个能做到的层。它第一次正式承接了初始化时不存在的信息：memory 可以保留经历，reasoning 可以使用经历，peer circuit 可以在候选之间做 release gate，outcome evaluation 可以把结果重新压回未来结构。

它由四个核心子系统组成；Outcome / RPE / Habit 则是这些子系统在执行之后形成的学习回流：

![L3 position](../../../docs/assets/architecture/l3_position_in_eva.svg)


## 7.2 Memory — 第一个有“个人经历”的存储层

L1 和 L2 处理的仍然主要是设计期已知的结构。到了 L3，系统第一次拥有“我经历过什么”的正式位置。

memory subsystem 至少分成两部分：episodic memory 保留有 salience 的具体经历，skill library 保留反复验证后结晶出的稳定模式。它们都属于 memory，但职责完全不同。

![L3 memory overview](../../../docs/assets/architecture/l3_memory_overview.svg)

### 7.2.1 深入：Episodic Memory — 按"当时有多紧张"来决定记多深

#### 核心概念：Salience Weight

普通的日志系统把每一条记录都平等对待——startup 事件和 distress 事件在文件里占同样的位置。EVA 要求的不是平等存储，而是**按重要性加权存储**。重要性的来源不是人工标注，而是**编码时的 drive state**——当某件事发生时，如果 survival intensity 是 0.85，这件事对这个 agent 的生存来说显然比 survival intensity 是 0.1 时发生的事更值得记住。这个权重叫 **salience**。

salience 决定两件事：**存多久**（高 salience 的记忆不容易被淘汰），以及**检索时排多前**（相似情境下高 salience 的记忆优先被取出来给 reasoning core）。

![L3 episodic salience](../../../docs/assets/architecture/l3_episodic_salience_encoding.svg)

### 7.2.2 Retrieval — 记住什么，还要决定何时把它取回来

Episodic memory 不是静态仓库。它只有在相似情境下能被重新取回，并进入当前 working memory，才真正参与后续 deliberation。

因此，retrieval 至少要同时受两类因素塑形：

- **情境相似性**：当前处境与哪段既往经历足够接近；
- **salience 权重**：即使都相关，高 salience 的经历也应更容易排到前面。

这就是为什么 EVA 的 memory 不是简单全文检索：它取回的不是"文本上最像的历史片段"，而是"在当前处境下最可能真正塑形候选判断的经历"。

### 7.2.3 深入：Skill Library — 不再思考，直接做

Episodic memory 帮助 agent **理解情境**（"这种情况上次发生了什么"）。Skill library 解决的是完全不同的问题：**对于已经反复验证过的情境，彻底绕过理解，直接执行**。

这是 L3 memory 子系统里最接近"本能"的部分。

---

#### 技能是怎么形成的：Crystallization

技能不是被编程进来的——它是从**反复成功的经历中涌现**的。这个过程叫 **skill crystallization**（技能结晶），机制如下：

每当 agent 在某类情境下采取了某个动作，都会产生一个 **RPE 信号**（reward prediction error，后面在 basal ganglia 子系统里详细讲）。当同一个 `(情境类型, 动作)` 组合积累了**足够多次一致的正向 RPE**，basal ganglia 就会把这个组合"固化"进 skill library。

固化之后，下次遇到相同情境类型，**不需要再经过高成本 reasoning 或调用 LLM 形成新候选**，而是可以直接进入更轻量的 habit track；但它仍需经过 basal ganglia 的选择与后续 release / execution boundary。

![L3 skill library](../../../docs/assets/architecture/l3_skill_library_crystallization.svg)

#### Skill Library 与 Episodic Memory 的分工

这两个存储之间有一个值得单独说的边界：

![L3 memory boundary](../../../docs/assets/architecture/l3_memory_two_stores_boundary.svg)

#### Memory 子系统小结

||Episodic Memory|Skill Library|
|---|---|---|
|**存什么**|事件 + 当时的 drive 强度|反复验证的 (情境, 动作) 对|
|**由谁写**|每次事件发生时自动写入|仅由 basal ganglia 在结晶时写入|
|**由谁读**|reasoning core（辅助推理）|basal ganglia（绕过推理）|
|**更新频率**|高频·连续|低频·门控|

Memory 子系统是 L3 里**最基础的前提**——没有它，reasoning core 在每次决策时都从零开始，basal ganglia 没有东西可以结晶。它是整个 L3 的**信息底座**。

## 7.3 Reasoning Core — LLM 落座的位置，但不是决策的终点

Reasoning Core 是 L3 里**最容易被误解**的子系统。误解通常是这样的："LLM 在这里，所以这里负责决策和执行。"

EVA 的立场完全相反：**Reasoning Core 只负责生成候选，不负责选择，更不负责执行**。它是整个 L3 里唯一"想"的地方，但"想完"之后产出的东西要交给 basal ganglia 去选、交给 mediator 去放行、才能到 tool edge 去执行。

Reasoning Core 在生物上对应**前额叶皮质（PFC）**，EVA 把它拆成三个功能区：

![L3 reasoning core](../../../docs/assets/architecture/l3_reasoning_core_overview.svg)

### 7.3.1 working memory：LLM 真正坐在哪里

Working Memory 是 Reasoning Core 的核心区域，对应 PFC 里的 **dlPFC（背外侧前额叶）**。它做一件事：**把所有输入整合成当前的推理上下文，然后产出候选动作和预测**。

LLM 就坐在这里。但"坐在这里"有非常明确的边界含义：

![L3 working memory](../../../docs/assets/architecture/l3_working_memory_llm_position.svg)

### 7.3.2  Value Judgment：同一候选，在不同 drive 环境下评分不同

这是 Reasoning Core 里**最体现 EVA 特色**的区域。

传统的 agent 对候选动作的评估通常依赖某种抽象效用（"这个动作完成任务的可能性有多高"）。EVA 的 Value Judgment 区域不用抽象效用——它用**当前 drive 强度作为权重**来评分每个候选。

同样一个候选"recheck + shrink"，在两种 drive 环境下的得分完全不同：

![L3 value judgment](../../../docs/assets/architecture/l3_value_judgment_drive_weighted.svg)

### 7.3.3 Conflict Detection：当 drive 互相拉扯时

有时两个 drive 会对同一个候选给出**互相矛盾的评分**。比如：

- **survival drive 高** → 倾向于"立刻缩减消耗，停止所有探索"
- **integrity drive 高** → 倾向于"先把当前状态如实记录，再做其他事"

"立刻缩减消耗"和"如实记录"可能在资源极度紧张时发生冲突——记录本身就要消耗资源。

这时 Conflict Detection 区域（ACC）介入，把冲突**显式路由到 anchor 系统解决**，而不是让 LLM 自己"想"出一个说法来合理化某个违规动作：

![L3 conflict detection](../../../docs/assets/architecture/l3_conflict_detection_routing.svg)

### Reasoning Core 小结

|区域|生物类比|职责|
|---|---|---|
|Working Memory|dlPFC|整合上下文·产出候选|
|Value Judgment|OFC|drive 加权评分|
|Conflict Detection|ACC|识别 drive 冲突·路由到 anchor|

**最重要的一句话**：Reasoning Core 的产出是**评分后的候选列表**，不是执行指令。它把这个列表交给 basal ganglia——一个**与它平级的独立子系统**——由 basal ganglia 决定选哪个、什么时候放行。

这就是为什么下一个子系统 basal ganglia 要单独拿出来讲，而且必须被理解为"peer circuit"而不是"reasoning 的下游模块"。

## 7.4 Basal Ganglia — 最反直觉的设计

这是 EVA 整个架构里**最难理解、也最重要**的结构性决定。

大多数 agent 框架里，推理产出动作，动作直接执行——这是一条直线。EVA 在这条直线中间插入了一个**独立的、与 Reasoning Core 平级的**子系统，专门负责"选哪个"和"什么时候放行"。这个子系统不听从 Reasoning Core 的命令，它有自己的判断机制。

**为什么一定要这样？** 因为"能说清楚这个动作为什么合理"和"现在应该执行这个动作"是**两件完全不同的事**。Reasoning Core 负责前者，Basal Ganglia 负责后者。把两件事混在一起，就失去了对"执行权"的结构性控制。

Basal Ganglia包含三个核心能力，一个统一原则:

![L3 basal ganglia](../../../docs/assets/architecture/l3_basal_ganglia_overview.svg)

## 7.5 Tool Edge — 与外部世界接触的唯一出口

Tool Edge 是 L3 里**最小的子系统**，但它承担着整个架构里一个不可替代的结构性角色：**它是 agent 影响外部世界的唯一合法路径**。

没有什么动作可以"绕过" Tool Edge 直接执行。这不是策略约束，而是**物理边界**——只有通过 Tool Edge 注册的执行器，才能真正触碰外部资源。

### 7.5.1 Mediated release —— candidate 变成行为之前还要跨一道边界

Tool Edge 前面必须先有 formal release boundary。也就是说，候选就算已经被 reasoning 评分、被 basal ganglia 选中，也还没有自动变成行为；它仍需要经过 mediator 的正式放行，才能进入 execution edge。

这条边界的意义在于：

- reasoning 不拥有执行权；
- skill / habit 也不拥有直接 side effect 权；
- ordinary path 里的任何外部行为，都必须留下 release 事实与 execution 事实。

### 7.5.2 为什么 Tool Edge 必须独立存在

在没有 Tool Edge 概念的框架里，工具调用通常散落在各处——reasoning 模块里、orchestrator 里、甚至 prompt 里。这带来一个根本性的问题：**执行发生在哪里是不确定的**。

EVA 的要求是相反的：执行发生在哪里**必须是确定的**，而且**必须在 Basal Ganglia 释放之后**。Tool Edge 就是那个确定的位置。

![L3 tool edge](../../../docs/assets/architecture/l3_tool_edge_position.svg)

### 7.5.3 Mediator：Tool Edge 前的最后关卡

Tool Edge 本身只是执行器的注册表和调用入口，但**在执行器被调用之前**，还有一个 Mediator（调度员）负责最终的放行决定。

Mediator 做三件事：

![L3 mediator](../../../docs/assets/architecture/l3_mediator_three_functions.svg)


### 7.5.4 Tool Registry：可扩展的执行器清单

Tool Edge 本身维护一个**工具注册表**——每种工具在使用前必须先注册。注册的不只是"这个工具存在"，还包括这个工具的**副作用等级**（side effect class）。副作用等级直接影响 Anchor System 对它的准入判断：

![L3 tool registry](../../../docs/assets/architecture/l3_tool_registry_side_effects.svg)

### 7.5.5 reflex-exempt path 与 mediated path 的边界

这里必须把两条路径分清：

- **mediated path**：ordinary candidate、deliberative candidate、habitual candidate 只要会越过外部 side effect 边界，都必须经过 `basal ganglia -> mediator -> tool edge`；
- **reflex-exempt path**：只保留给前面 L1 / L2 已经定义过的最小快路反应，例如 distress、yield、conservative shrink 这类生命边界优先动作。

所谓 exempt，指的是它不经过完整 deliberation，而不是指它获得了任意越权的执行自由。它仍然只应承接预先定义、边界极窄、以连续性保护为目的的最小响应。

## 7.6 Outcome / RPE / Habit — L3学习闭环：执行之后发生了什么

这是 L3 里**最容易被忽视、但没有它整个系统就不会进化**的部分。

前面介绍的四个子系统描述的都是"决策发生时"的结构。但 EVA 与 task agent 最深层的差别之一，是 EVA **在执行之后还有事情发生**——执行的结果会反过来改变 agent 未来的行为方式。这个"改变"不是人工调参，而是通过一个完整的反馈回路自动完成的。

### 第一步：Outcome 观测 — 结果不是自动清晰的

工具执行完毕之后，结果并不是自动就变成"学习信号"的。**Outcome 观测**是一个独立的步骤，它把工具的原始返回值转化为结构化的可评估信息。

为什么需要这一步？因为不同工具的输出形式完全不同——有的是返回码（0/1），有的是文件内容，有的是进程状态，有的什么都不返回。Basal Ganglia 的 RPE 计算需要的是统一格式的"结果"，而不是各种工具的原始输出。

![L3 outcome observation](../../../docs/assets/architecture/l3_outcome_observation.svg)

### 第二步：RPE 计算 — 量化"这次是否符合预期"

有了结构化的 outcome，现在可以进行 RPE 计算。

计算需要两个输入：**执行前 Basal Ganglia 记录的预测**，以及**刚刚观测到的实际结果**。差值就是 RPE。

但 RPE 有一个反直觉的关键性质：**它编码的是"惊讶程度"，不是"结果有多好"**。

![L3 RPE computation](../../../docs/assets/architecture/l3_rpe_computation.svg)

### 第三步：两个更新目标 — RPE 同时更新两个地方

RPE 信号产生之后，它**同时**流向两个目的地，更新两种不同的内部结构：

![L3 RPE two targets](../../../docs/assets/architecture/l3_rpe_two_update_targets.svg)

### 完整学习闭环：一次执行的完整生命周期

把三个步骤串在一起，一次完整执行的生命周期是这样的：

![L3 complete learning loop](../../../docs/assets/architecture/l3_complete_learning_loop.svg)

### 学习闭环小结

|步骤|机制|
|---|---|
|Outcome 观测|工具输出 → 结构化 outcome|
|RPE 计算|actual − predicted · 编码惊讶|
|BG 权重更新|强化或抑制被使用的通路|
|Episodic 写入|事件 + drive_state → salience 加权|

没有这个闭环，agent 每次执行都是从零开始，经历不积累，判断不进化。

## 7.7 这一层真正决定了什么

### L3 四个子系统完整闭环

介绍完四个子系统，最后用一张图把它们的**协作关系**放在一起看：

![L3 full loop](../../../docs/assets/architecture/l3_full_collaboration_loop.svg)

因此，L3 的关键不只是 planner 更复杂，而是它第一次把 **thought、memory、selection、release、execution、outcome、learning** 串成了正式闭环。下一章进入 L4：Self-Model 的接口位置。
