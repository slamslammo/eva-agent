# 1. 工程目标与不变量

## 1.1 existence-centered 的工程目标

EVA-agent 的工程目标，不是把一个 task agent 包装得更复杂，而是先建立一个**持续存在、受边界约束、能在长期运行中被自身经历塑形**的主体结构。

因此，它的目标可以压缩为三点：

1. 先建立 continuous existence 的运行底盘；
2. 再建立以 drive 为内部环境的主体结构；
3. 最后才让 reasoning、memory、release 与 learning 在这条结构主干上增长。

这意味着，EVA-agent 的第一约束不是任务完成率，而是 heartbeat、实例合法性、内部状态 owner、候选生成边界与 side effect 边界是否先成立。

## 1.2 工程不变量

下面八条不是推荐实践，而是 EVA-agent 的最低结构条件。它们一旦被破坏，系统就会重新滑回 task-agent 形态。

| 维度 | task agent 的默认 | EVA-agent 的工程不变量 |
| --- | --- | --- |
| 默认行为状态 | ready-to-execute | **default inhibition** |
| 动机机制 | 外部 task 直接驱动 | **drive as internal context** |
| 约束机制 | 先生成再过滤 | **anchor as pre-generative constraint** |
| 推理与释放关系 | reasoning 同时负责候选与执行 | **peer circuit distinct from reasoning** |
| 学习信号 | 外部 reward / 人工评分 | **RPE as endogenous learning signal** |
| 技能形成 | 主要靠显式编排 | **habit crystallization** |
| 生命周期边界 | 任务边界优先 | **heartbeat-first lifecycle boundary** |
| 记忆功能 | 服务召回 | **memory serves threat recognition and skill formation** |

### 1.2.1 Default inhibition

系统默认状态不是 ready-to-execute，而是 default inhibition。候选形成不等于动作释放；任何 side effect 都必须经过独立 release boundary。

### 1.2.2 Drive as internal context

drive 不是 task command，而是 L2 拥有的连续内部状态。下游层只能读取它的 broadcast 面，不能把它当命令直接执行或随意改写。

### 1.2.3 Anchor as pre-generative constraint

约束必须发生在候选生成之前。系统面对的应是已经被收缩的 `A'(s)`，而不是先生成完整 `A(s)` 再在末端删减。

### 1.2.4 Peer circuit distinct from reasoning

reasoning 可以形成候选、预测结果、比较价值，但不能直接释放动作。candidate formation、selection、release 必须正式分离。

### 1.2.5 RPE as endogenous learning signal

学习首先来自 expected 与 actual 的偏差，而不是外部临时注入的奖励。outcome evaluation 必须是正式结构，而不是附属日志。

### 1.2.6 Habit crystallization

skill 不只等于显式编排。重复成功的行为路径应能在边界内逐步沉淀为更轻量的 habitual path。

### 1.2.7 Heartbeat-first lifecycle boundary

生命循环边界优先于任务边界。`tick` 与 `turn` 必须分离，ordinary work 不能长期阻塞 heartbeat，实例失效时普通 release 必须收缩。

### 1.2.8 Memory serves threat recognition and skill formation

memory 不是单纯 recall system。它既要支持 threat recognition，也要支持 skill formation，因此必须与 append-only audit 分层，并受 salience 与当前 context 共同塑形。

## 1.3 为什么这些不变量必须由代码结构保证

如果这些不变量只存在于 prompt、文档或运行时口径里，系统仍会退化成 task agent。EVA-agent 的关键要求是：**结构先于策略**。

因此，这些不变量必须落实为模块 owner、调用边界、数据边界与持久化边界：heartbeat-first 落成 `tick` / `turn` 主权，drive 落成只读 broadcast，anchor 落成 pre-generative domain restriction，release 落成独立 mediator，memory 落成 audit / cognitive / learning 分轨。

后文所有层级与模块，都是围绕这八条不变量展开。