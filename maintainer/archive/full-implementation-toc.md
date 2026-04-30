# EVA-agent v0.5 完整实现方案

本文档作为 **EVA-agent v0.5 完整实现方案** 的主目录与章节入口。

当前阶段先不把它写成一篇连续长文，而是采用：
- 一份总目录文档
- 一组 `sections/*.md` 分章文稿

这样做的目的，是先把整套结构和章节职责稳定下来，再逐章确认与扩写正文。

## 0. 摘要

- 0.1 从 EVA theory v0.5 到 EVA-agent
- 0.2 EVA-agent 是什么
- 0.3 本文回答什么问题

见：[sections/00-abstract.md](sections/00-abstract.md)

## 1. 工程目标与不变量

- 1.1 existence-centered 的工程目标
- 1.2 八条工程不变量
- 1.3 为什么这些不变量必须由代码结构保证

见：[sections/01-engineering-goals-and-invariants.md](sections/01-engineering-goals-and-invariants.md)

## 2. 总体架构总览

- 2.1 五层 + 横跨层约束 + 基础设施层
- 2.2 各部分在整体中的位置
- 2.3 依赖方向与系统边界
- 2.4 从理论到工程的总映射

见：[sections/02-overall-architecture.md](sections/02-overall-architecture.md)

## 3. 横跨层约束：Anchor System

- 3.1 Anchor 的位置
- 3.2 structural anchors 与 dynamic anchors
- 3.3 capability restriction 与 parameter-domain restriction
- 3.4 `G(s) -> A'(s) ⊆ A(s)` 的工程含义
- 3.5 Anchor 与 kernel / L1 / L2 / L3 的关系

见：[sections/03-anchor-system.md](sections/03-anchor-system.md)

## 4. 基础设施层：Infrastructure / Kernel

- 4.1 为什么它不在 EVA 五层编号里
- 4.2 lifecycle kernel
- 4.3 instance identity
- 4.4 persistence
- 4.5 event bus
- 4.6 这一层真正决定了什么

见：[sections/04-infrastructure-kernel.md](sections/04-infrastructure-kernel.md)

## 5. L1：Homeostatic Sensing

- 5.1 L1 的职责边界
- 5.2 sensor registry
- 5.3 state + rate sensing
- 5.4 signal publication contract
- 5.5 signal bus / signal routing
- 5.6 fast / slow path split
- 5.7 L1 与 kernel / L2 的关系
- 5.8 这一层真正决定了什么

见：[sections/05-l1-homeostatic-sensing.md](sections/05-l1-homeostatic-sensing.md)

## 6. L2：Drive Layer

- 6.1 L2 的职责边界
- 6.2 drive registry
- 6.3 continuous intensity
- 6.4 drive update / decay / recovery
- 6.5 drive broadcast
- 6.6 reflex arc
- 6.7 pressure 作为 projection，而不是主模型
- 6.8 L2 与 L1 / L3 / Anchor 的关系
- 6.9 这一层真正决定了什么

见：[sections/06-l2-drive-layer.md](sections/06-l2-drive-layer.md)

## 7. L3：Adaptive Deliberation

### 7.1 L3 的职责边界
- L3 是第一个能积累并使用初始化时不存在信息的层
- Outcome / RPE / Habit 作为执行后的学习回流

### 7.2 Memory
- 7.2.1 episodic memory / salience-weighted encoding
- 7.2.2 retrieval
- 7.2.3 skill library / crystallization

### 7.3 Reasoning Core
- 7.3.1 working memory
- 7.3.2 value judgment
- 7.3.3 conflict detection

### 7.4 Basal Ganglia
- peer circuit
- default inhibition
- selection distinct from reasoning

### 7.5 Tool Edge / Execution Boundary
- 7.5.1 mediated release
- 7.5.2 tool edge position
- 7.5.3 mediator
- 7.5.4 tool registry
- 7.5.5 reflex-exempt path 与 mediated path 的边界

### 7.6 Outcome Evaluation / RPE / Habit
- 7.6.1 outcome observation
- 7.6.2 RPE computation
- 7.6.3 two update targets
- 7.6.4 complete learning loop

### 7.7 这一层真正决定了什么
- L3 四个子系统与执行后学习回流的完整闭环

见：[sections/07-l3-adaptive-deliberation.md](sections/07-l3-adaptive-deliberation.md)

## 8. L4：Self-Model 的接口位置与下层依赖

- 8.1 L4 的职责边界
- 8.2 它依赖 L3 的哪些产物
- 8.3 它不应越界侵入哪些层
- 8.4 为后续实现预留的接口与边界
- 8.5 当前不展开内部实现细节的原因

见：[sections/08-l4-self-model-interfaces.md](sections/08-l4-self-model-interfaces.md)

## 9. L5：Social Layer 的接口位置与系统边界

- 9.1 L5 的职责边界
- 9.2 与 L4 / L3 / 外部系统的关系
- 9.3 conspecific / human / other agents 的边界问题
- 9.4 为后续实现预留的接口与边界
- 9.5 当前不展开内部实现细节的原因

见：[sections/09-l5-social-layer-boundaries.md](sections/09-l5-social-layer-boundaries.md)

## 10. 持久化工件与核心运行时对象

- 10.1 runtime_state
- 10.2 drive_state
- 10.3 external_life_snapshot
- 10.4 events
- 10.5 candidate / release / learning artifacts
- 10.6 哪些是主状态，哪些是 projection，哪些是审计流

见：[sections/10-runtime-artifacts-and-state-objects.md](sections/10-runtime-artifacts-and-state-objects.md)

## 11. 运行闭环

- 11.1 sensing -> signal -> drive
- 11.2 drive -> candidate shaping
- 11.3 mediator -> release -> execution
- 11.4 outcome -> memory / RPE / habit
- 11.5 整个系统如何形成持续运行闭环

见：[sections/11-runtime-closed-loop.md](sections/11-runtime-closed-loop.md)

## 12. 工程验证与不变量测试

- 12.1 heartbeat-first
- 12.2 instance validity
- 12.3 read-only drive
- 12.4 anchor pre-generative restriction
- 12.5 mediator-only side effects
- 12.6 audit / memory 分层
- 12.7 长跑验证与结构验证

见：[sections/12-validation-and-invariant-tests.md](sections/12-validation-and-invariant-tests.md)

## 13. 部署与实现形态

- 13.1 单机长期在线基线
- 13.2 supervisor / systemd
- 13.3 运行目录与工件约定
- 13.4 从 reference implementation 到更完整系统的部署路径

见：[sections/13-deployment-and-implementation-shape.md](sections/13-deployment-and-implementation-shape.md)

## 14. 结语

- 14.1 EVA-agent 作为 EVA v0.5 工程实例的意义
- 14.2 它解决了什么
- 14.3 后续演化方向

见：[sections/14-conclusion.md](sections/14-conclusion.md)
