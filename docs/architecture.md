# EVA v0.5 对齐后的 `eva-agent` 总方案

本文档定义 `eva-agent` 当前公开的总方案。

它回答的是：**如果以 EVA v0.5 作为先验理论起点，`eva-agent` 应该按什么架构分层来设计，以及当前代码已经落到哪一层。**

这份文档是架构文档，不是 runbook，也不是内部治理备忘录。

## 1. 项目定位

`eva-agent` 是一个 **EVA v0.5 对齐**的 existence-centered agent 架构实验工程。

它关注的不是如何把一个 agent 做成更强的 task orchestrator，而是如何先建立一条符合 EVA 的结构主干，使后续能力在正确的位置上生长。当前公开主线聚焦以下几点：

- continuous existence as a first-order constraint
- drive as contextual broadcast
- anchors as pre-generative structural constraints
- action release structurally distinct from reasoning
- immutable audit trail 与 cognitive memory 分层

## 2. 架构总览

`eva-agent` 的目标工程结构采用：**五层 + 横跨层约束 + 基础设施**。

### 2.1 kernel / infrastructure

负责最底层运行前提：
- lifecycle arbitration
- instance identity / validity
- state persistence
- append-only event recording
- supervisor-facing runtime boundary

这一层是工程底盘，不负责高层认知语义。

### 2.2 L1：Homeostatic Sensing

负责：
- sensor registry
- state sensing
- rate sensing
- urgency pre-classification
- Signal Bus 输入发布

L1 输出的不是动作，而是可供后续层处理的信号与状态变化。

### 2.3 L2：Drive Layer

负责：
- drive registry
- continuous intensity update
- drive decay / accumulation
- drive broadcast
- reflex path 的快速响应承载

在 EVA 中，drive 不是 command，也不是 task，而是持续变化的内部上下文。

### 2.4 L3：Adaptive Deliberation

负责：
- candidate generation
- value judgment
- mediated release
- outcome evaluation
- episodic memory 的使用与写入

L3 可以 reasoning，但 reasoning 不直接等于动作释放。

### 2.5 L4：Self Model

L4 不是当前阶段重点。它只在 L1/L2/L3 已经积累出足够稳定的行为史、release 史与 memory 史之后，才有实现意义。

### 2.6 L5：Social / External Coordination

L5 同样不在当前实现重点内。它依赖更成熟的主体边界与更稳定的内部架构，不应提前进入。

### 2.7 Anchor System（横跨层）

anchor 不是末端 safety filter，而是 **pre-generative structural constraint**。

它横跨 L1/L2/L3，负责：
- 限制 capability 是否可进入当前候选域
- 限制 capability 的 parameter domain
- 在高风险状态下进一步收缩候选空间
- 防止系统滑向 unconstrained self-preservation

## 3. 结构约束

目标依赖方向是：

```text
L5 → L4 → L3 → L2 → L1 → kernel
```

同时保持以下硬约束：
- anchor 可被高层使用，但 anchor 自身不应反向依赖高层推理逻辑
- drive 只能由 L1 信号与 L2 更新规则改变，L3 只能读，不能写
- 所有外部 side effect 都必须经过 mediator
- audit trail 与 cognitive memory 不能混为一个存储层

## 4. 关键跨层合同

### 4.1 Signal Bus

Signal Bus 是 L1 与后续层之间的统一信号合同。

最小语义包括：
- `source`
- `class`：`threat | status | background`
- `payload`
- `captured_at`
- `rate_context`

它必须支持：
- fast path：直接触达 reflex / urgent handling
- slow path：进入 drive update 与 deliberation

### 4.2 Drive Broadcast

Drive Broadcast 是 L2 向后续层提供的只读上下文接口。

核心约束：
- drive state 是连续值，不是伪装成层级表的离散 severity
- broadcast 对 L3 是只读的
- L3 不得通过 reasoning 直接改写 drive

### 4.3 Anchor Domain Restriction

anchor 的职责不是“先生成动作，再过滤掉不安全动作”，而是：

```text
G(s) -> A'(s) ⊆ A(s)
```

也就是说，候选生成本身就只能发生在 restricted domain 内。

### 4.4 Action Mediator

mediator 是 default inhibition 的结构性保证。

它负责：
- 接收 candidate
- 维持显式 release gate
- 记录 release log
- 将 tool edge 与 reasoning 解耦

关键约束：
- reasoning 不能直接调用 tool executor
- 没有 mediator release，就没有外部 side effect

### 4.5 Audit Trail 与 Episodic Memory

两条轨道必须分离：

#### Immutable audit trail
用于：
- debugging
- replay
- traceability
- reconstructability

#### Cognitive / episodic memory
用于：
- salience-weighted encoding
- contextual retrieval
- threat recognition
- behavior shaping
- skill crystallization

memory 不能替代 audit，audit 也不等于 memory。

## 5. 当前实现映射

当前仓库还不是完整 EVA 系统，而是一个 **early reference implementation / partial instantiation**。

### 5.1 已成立的资产

| 当前模块 | 目标角色 | 当前判断 |
| --- | --- | --- |
| `eva/kernel/instance.py` | kernel identity / validity | 已成立，应保留 |
| `eva/lifecycle.py` | kernel lifecycle arbitration | 已成立，应保留 heartbeat-first 边界 |
| `eva/kernel/state.py` | kernel persistence / event recording | 已成立 |
| `eva/kernel/config.py` | kernel/runtime configuration | 已成立 |
| `eva/l1_sensing/sensing.py` | L1 sensing baseline | 已形成 state + rate sensing baseline |
| `eva/l1_sensing/judgment.py` | L1 judgment baseline | 已有规则基线 |
| `eva/l1_sensing/patrol.py` | L1 cadence organization | 已接入 signal / drive 编排 |
| `eva/l2_drive/pressure.py` | L2 过渡视图 | 作为 compatibility projection 保留 |
| `eva/response.py` | L3 过渡动作通路 | 仍是 temporary minimal action path |
| `eva/l1_sensing/history.py` | audit / baseline history | 仍是 projection / audit 层，不是 cognitive memory |

### 5.2 当前仍未建立的关键结构

当前尚未真正建立：
- anchor-bounded candidate generation
- default inhibition + mediator
- salience-weighted cognitive memory
- outcome delta / habit track / working-memory abstraction

### 5.3 当前过渡结构的定位

以下结构仍然只是过渡资产：
- `active_pressures.json`：当前 pressure / viability-gap view
- `response.py`：当前最小 action path
- `survival_log.jsonl` 与 `response_history.jsonl`：当前 baseline 历史，不是 cognitive memory

它们可以作为迁移期兼容面保留，但不应继续长成未来主架构。

## 6. 当前开发状态

当前仓库已经建立 Phase A 主干：

```text
sensing -> signal classification -> drive update -> drive broadcast
```

但这应被理解为：L1 / L2 baseline 已落地，当前进入 A5 strict closeout / audit，而不是直接把 Phase A 视为已正式关闭。

在当前口径下，需要继续明确并收紧：
- Signal Bus 当前已成立的是 normalized signal publication contract，而不是完整 routing layer
- urgency semantics 仍未作为正式 Phase A contract 落地
- `response.py` 仍是 pressure-led compatibility path，只兼容读取 `drive_broadcast`
- mediator、anchor 与 cognitive memory 仍属于后续 phase

## 7. 当前非目标

当前阶段明确不做：
- 把当前最小 action path 扩成更复杂的 repair orchestrator
- 把当前 pressure / viability-gap 视图当作长期核心控制模型
- 提前把 LLM 接成架构 prerequisite
- 提前进入完整 L4 / L5
- 过早扩张为多工具系统、开放式任务编排框架或通用对话产品

## 8. 相关文档

- `README.md`：公开入口与当前状态摘要
- `docs/development/roadmap.md`：分阶段路线
- `docs/development/phase-a-plan.md`：当前 Phase A 计划
- `docs/development/phase-a-progress.md`：当前 Phase A 进展
