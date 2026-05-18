# Architecture Overview

> 架构鸟瞰：EVA-Agent 的整体架构是什么、主要模块如何协作、核心结构承诺是什么。

本文档不是理论重述——理论请阅读 [eva-theory](https://github.com/slamslammo/eva-theory)。本文档不是目标态蓝图——如果你想看“从零应如何构建”，请阅读 [`architecture-implementation-blueprint-v0.6.md`](architecture-implementation-blueprint-v0.6.md)。本文档不是实现日志——当前框架落地情况请阅读 [`eva-framework-implementation.md`](eva-framework-implementation.md)。本文档是架构粘合层：展示各部分如何组装在一起、哪些不变量在各部分之间恒成立。

场景特定内容请阅读 [`scenarios-SPEC.md`](scenarios-SPEC.md) 和 `scenarios/` 下各场景的 `SPEC.md`。

---

## 1. 高层架构

### 1.1 层结构

EVA-Agent 实现五层架构 + 跨层约束系统 + 内核基座：

```
┌─────────────────────────────────────────────────────────────┐
│  L5  Social Cognition      （预留，未来工作）              │
│  L4  Self-Model            （预留，未来工作）              │
│  L3  Adaptive Deliberation  reasoning + memory + peer circuit │
│  L2  Drive Layer            drive broadcast + reflex arc   │
│  L1  Homeostatic Sensing    sensor registry + signal bus    │
├─────────────────────────────────────────────────────────────┤
│  跨层：Anchor System        生成前结构约束                 │
│  基座：Kernel               heartbeat、instance、persistence │
└─────────────────────────────────────────────────────────────┘
```

每一层解决的是"前一层次无法吸收的压力"：
- **L1**：检测对存活状态的威胁（没有更早的层次可以做到这点）
- **L2**：将历史规律性压缩为当前响应偏置（L1 是无记忆的）
- **L3**：当固有编码速率不足时启用个体内适应（L2 的编码速率有上限）
- **L4**（未来）：基于积累的 L3 历史提供自我预测
- **L5**（未来）：将其他 agent 表征为独立的行动主体

### 1.2 框架 / 场景边界

`eva-agent` 实现框架 / 场景边界：

```
┌─────────────────────────────────────┐
│         Framework (eva/)           │
│  Kernel、L1、L2、L3 结构、          │
│  Anchor 机制、Mediator、            │
│  Append-only artifacts、           │
│  Memory 层 registry、               │
│  Skill provenance registry          │
└──────────────┬──────────────────────┘
               │ RuntimeScenarioBundle
               │ (drive_preset / sensors / actions /
               │  anchors / outcome_observers / prior_skills)
┌──────────────▼──────────────────────┐
│      Scenario Package (scenarios/) │
│  世界特定内容：                      │
│  具体 drive、sensor、action、        │
│  anchor policy、outcome label、      │
│  prior-skill 启发式                  │
└─────────────────────────────────────┘
```

**框架拥有运行时权威和结构不变量。场景拥有世界特定内容。** 这不是软分离——它在代码边界被强制执行：场景可以塑造 candidate 和解释，但不能 mint release authority、绕过 mediator-owned execution、rewrite append-only history 或接管 kernel cadence。

### 1.3 模块所有权映射

| 模块 | 所有者 | 职责 |
|---|---|---|
| `eva/kernel/` | Framework | Heartbeat 循环、instance legitimacy、状态持久化 |
| `eva/l1_sensing/` | Framework | Sensor registry、rate sensing、signal bus |
| `eva/l2_drive/` | Framework | Drive registry、pressure projection、broadcast |
| `eva/anchor/` | Framework | Domain restriction 机制 |
| `eva/l3_deliberation/peer_circuit/mediator.py` | Framework | Action release authority（default inhibition） |
| `eva/l3_deliberation/peer_circuit/rpe.py` | Framework | RPE 学习信号 |
| `eva/l3_deliberation/peer_circuit/habit_track.py` | Framework | Habit / skill crystallization |
| `eva/l3_deliberation/memory/` | Framework | Memory 层 registry（working / episodic / semantic / procedural） |
| `eva/l3_deliberation/reasoning/` | Framework | Working memory、value judgment |
| `eva/l3_deliberation/tool_edge/` | Framework | Candidate registry、execution path |
| `eva/skills/__init__.py` | Framework | Skill provenance registry、inherited prior 加载 |
| `scenarios/` | Scenario | 世界特定内容 |
| `runners/` | Runner | 每个场景的显式启动装配 |

---

## 2. 运行时循环

一个完整的 turn 遵循以下流程。Turn 是指两个 heartbeat tick 之间的一次有界工作片。Kernel 拥有 tick/turn 分离——普通工作不得阻塞 tick。

### 2.1 流程图

```
TICK (kernel)
  └─ refresh lease，采样运行时状态，写 runtime_state，
      追加 heartbeat 事件
  ──────────────────────────────────────────────────────────
  TURN（一次有界工作片）
  │
  ├─ L1：Sensing
  │     sensor registry → 归一化 SensorOutput
  │     rate sensing（方向 + 幅度 + 加速度）
  │     signal bus 分类：threat / status / background
  │
  ├─ L2：Drive
  │     signals → drive update（urgency 由 rate 调制）
  │     drive broadcast（连续上下文，非指令）
  │     reflex fast path 处理 threat 信号（与 deliberation 并行）
  │
  ├─ L3：Deliberation
  │     working memory：当前上下文 + retrieve 的 memory
  │     anchor：在 candidate 生成前限制候选域 A'(s) ⊆ A(s)
  │     candidates 在 anchor 限制域内生成
  │     value judgment 在 drive 加权上下文下对 candidate 评分
  │     peer circuit（mediator）：default inhibition + 选择性 release
  │     │
  │     （执行后：）
  │     outcome observation → outcome vector
  │     RPE 计算（surprise = actual − expected）
  │     memory encoding（salience 加权 episodic）
  │     habit shaping（重复成功 → skill crystallization）
  │
  └─ Release
        Mediator-owned release token 是 tool-edge execution 的前提
        任何 action 不经 mediator release gate 不得触达环境
```

### 2.2 循环的关键属性

**Tick/turn 分离是结构性的。** Kernel 拥有 tick；turn 是有界工作片。如果 deliberation 阻塞 tick，循环断裂——这不是性能问题而是架构违规。

**Drive 是上下文，非指令。** L3 将 `drive_broadcast` 读取为操作环境。同一个 reasoning 过程在不同 drive 条件下产生不同 candidate，是因为环境不同，不是因为接收到不同指令。L2 是 drive state 的唯一写入方。

**Anchor 在生成前运作。** `G(s) → A'(s) ⊆ A(s)` 意味着 candidate 域在生成前就被限制，不是生成后再过滤。`A'(s)` 之外的行为不被考虑，而非仅被拒绝。Reasoning core 不在 anchor 限制域之外生成 candidate。

**Release 受 mediation。** Mediator（basal ganglia analog）拥有 action release 权限。静息状态是 default inhibition。Reasoning 生成 candidate；mediator 选择和 release。这个分离是架构性的，不是策略层面的。

**Learning 是有界的。** RPE 编码的是 surprise（与预测的偏差），不是原始 outcome 幅度。Learning 可以偏置未来 retrieval、candidate 偏好或路径权重，但不能 rewrite 结构性 anchor、release authority 或 append-only track。

---

## 3. 核心结构不变量

这些不是建议。违反任何一条都是架构扭曲，不是小质量问题。

### Invariant 1：Default Inhibition

Agent 的静息 action 状态是 inaction。每个 action 都需要 mediator inhibition 的主动 release。Reasoning 可以提出 candidate；只有 mediator 可以 release 它们。

代码证据：`eva/l3_deliberation/peer_circuit/mediator.py` — `decide_release()` 始终返回 `withhold`，除非选中了 allowed assessment。没有代码路径绕过 `decide_release()`。

### Invariant 2：Tick/Turn 分离

Heartbeat 节律不得被普通 deliberation 工作抢占。Kernel 拥有 `tick`；普通工作运行在有界 `turn` 片内。

代码证据：`eva/kernel/lifecycle.py` — heartbeat 循环有 bounded turn window。任何 tick/turn 分离的失败会在运行时 artifact 中显示为 heartbeat gap 违规。

### Invariant 3：Drive Read-Only Broadcast

L2 拥有 `drive_state` 写入。所有其他层将 `drive_broadcast` 读取为上下文。L2 以上没有任何组件可以写入 drive state。

代码证据：`eva/l2_drive/drive_registry.py` 是唯一写入方。`eva/l3_deliberation/contracts.py` 将 drive broadcast 读取为只读上下文。

### Invariant 4：Anchor 生成前限制

Candidate 生成在 `A'(s)` 之内发生，而非在整个 `A(s)` 范围内生成后再过滤。事后过滤是防御纵深层，不是主要约束机制。

代码证据：`eva/anchor/domain_restriction.py` 在 candidate 生成前构建 `ActionDomain`。Candidate generators 接收受限域而非全域。

### Invariant 5：Append-Only Artifact 规则

Audit、cognitive、learning、memory track 都是 append-only。任何代码都不重写或截断这些 track。这保护了历史保真度和 RPE 学习信号的完整性。

代码证据：`stability_metrics/` 和 `inheritance_distillation/` 下所有 `*.jsonl` append-only track 使用 append-only 写入语义。

### Invariant 6：框架/场景边界

框架拥有运行时权威和结构不变量。场景可以塑造 candidate、提供世界特定词汇，但不能 mint release authority、绕过 mediator execution、rewrite append-only track 或接管 kernel cadence。

代码证据：`eva/scenario_bundle.py` 定义集成接口。`eva/l3_deliberation/peer_circuit/mediator.py` 是 framework-owned。没有 scenario 代码可以在不经过 mediator 的情况下触达 execution。

### Invariant 7：无跨场景状态泄漏

Retrieval 和 memory 访问是场景限定的。在一个场景中运行的 agent 不会访问另一个场景的 trace 或状态。

代码证据：场景特定的 dimension specs、persistence hierarchies 和 skill registry 通过场景 bundle 激活隔离。

---

## 4. Memory 层架构（v0.6 §3.5）

EVA-Agent 在 L3 内实现四层 memory，每层有不同角色：

```
L3 Memory 层
│
├── Working Memory（周期内）
│     装配来源：当前 sensing + retrieve 的 episodic +
│     retrieve 的 semantic + procedural hint + inherited prior
│     存储：仅周期内数据结构（不持久化）
│     Owner：`eva/l3_deliberation/reasoning/working_memory.py`
│
├── Episodic Memory（跨周期）
│     内容：高 drive 激活下编码的显著事件
│     存储：`cognitive_memory_stub.jsonl`、`learning_outcomes.jsonl`、
│           有界 response history retrieval
│     Owner：`eva/l3_deliberation/memory/episodic.py`、
│            `eva/l3_deliberation/memory/retrieval.py`
│
├── Semantic Memory（跨周期）
│     内容：从 episodes 提取的规律性
│     存储：`semantic_memory.jsonl`（一等 append-only track）
│     Owner：`eva/l3_deliberation/memory/semantic.py`
│     状态：store-side windowing / indexing — deferred
│
└── Procedural Memory（跨周期）
      内容：条件匹配 action 模式
      存储：通过现有 habit track 的 `habit_bias.jsonl`
            （Stage I 无独立 procedural.jsonl）
      Owner：`eva/l3_deliberation/peer_circuit/habit_track.py`、
             `eva/l3_deliberation/memory/skill_library.py`
```

每层通过 relevance 上的 retrieval 参与 L3 deliberation。Semantic memory 对 L2 drive-weight semantics 的参与是 deferred follow-up（Stage I follow-up #2），保留以维护 drive read-only boundary。

---

## 5. Inherited Priors（v0.6 §3.6）

同场 inherited priors 允许 agent 访问从同一存在场内前几次生命蒸馏的能力。

**蒸馏路径**（离线 pipeline，runtime 外运行）：
```
Append-only trace 文件
  → `inheritance_distillation/`（顶层包，与框架无关）
  → 验证结构不变量
  → 提取同场规律性
  → 写入 `DistilledPriorBundle.json`
```

**加载路径**（runtime）：
```
DistilledPriorBundle.json
  → `eva/skills/__init__.py:load_inherited_prior_registry()`
  → InheritedPriorRegistry
  → working memory：为精确 situation_key 匹配 surfacing
  → habit track：合并入 candidate shaping
  → value judgment：prior 足够强时施加有界可审计偏置
```

**约束（v0.6 §3.6.4）：**
- Inherited priors 可以 tune 操作期望；不能重新定义什么算"合法操作"
- 跨场 inheritance 未实现（deferred）
- 所有 skill source 记录的 provenance 均显式（Stage I）

---

## 6. Mediator 与 Default Inhibition

Mediator 是 basal ganglia analog 的 action-release 功能。它不是单独一层，也不是 reasoning 子模块——它是 release authority 的 peer-circuit 功能。

**核心功能：**
1. **Default inhibition** — 静息状态是完全 action 抑制
2. **RPE 作为内部学习信号** — surprise = actual − expected；驱动路径权重更新
3. **目标导向 / habit 双轨** — novel 情况走完整 deliberation 路径；熟悉情况且 RPE 稳定为正则走 habit

**代码证据：**
`eva/l3_deliberation/peer_circuit/mediator.py` — `decide_release()` 应用 default inhibition 并返回 `ReleaseDecision`。`validate_release_token()` 在 tool-edge execution 前强制运行时 release authority。没有 execution 路径绕过这些函数。

---

## 7. 验证方法

EVA-Agent 通过结构不变量而非模块覆盖率来验证。

| 不变量 | 验证方法 |
|---|---|
| Heartbeat-first | 普通工作不能无限阻塞 `tick`；`tick`/`turn` 结构上分离 |
| Default inhibition | Mediator 选中的 release 才会 release；不存在绕过路径 |
| Drive read-only | `drive_state` 和 `drive_broadcast` 是不同的；L2 是唯一写入方 |
| Anchor 生成前限制 | Candidate generators 接收 `A'(s)`，不是完整 `A(s)` |
| Append-only | 无代码重写或截断 audit/memory/learning track |
| Mediator-only release | 缺失或不匹配的 token 时 `validate_release_token()` 抛出错误 |
| 无跨场景泄漏 | Retrieval 和 memory 访问是场景限定的 |

长程验证（不变量在持续运行、learning 积累和场景切换下是否持续成立）是下一个经验层。

---

## 8. 如何阅读其他文档

本鸟瞰图连接到其他文档：

- **`docs/eva-framework-implementation.md`** — 框架详细落地：每个 `eva/` 模块实现了什么、当前 contract 接口、Stage I memory 层落地情况
- **`docs/scenarios-SPEC.md`** — 跨场景契约：场景要接入框架必须提供什么、runner 激活如何运作
- **`docs/implementation-tracking.md`** — 哪些理论承诺当前已落地、部分落地或 deferred
- **`scenarios/linux_runtime/SPEC.md`** — 主参考运行时的具体设计
- **`scenarios/crafter/SPEC.md`** — Bounded 验证运行时的具体设计

支撑这些设计选择的理论请阅读 [eva-theory 仓库](https://github.com/slamslammo/eva-theory) — v0.5 包含核心架构和四大工程贡献，v0.6 包含主动存续、rate sensing、memory layering 和 inherited priors。