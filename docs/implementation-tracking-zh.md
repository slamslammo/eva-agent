# Implementation Tracking

> 理论承诺 → 落地状态跟踪表：v0.5 和 v0.6 的每个理论承诺，现在在代码的哪里、完成了多少。

本文档追踪 EVA v0.5 和 v0.6 理论承诺在 `eva-agent` 代码中的当前落点及完成度。

它回答的问题是：**对于某个理论承诺，它现在在代码哪里、完成度如何？**

理论本身请阅读 [eva-theory](https://github.com/slamslammo/eva-theory)。架构鸟瞰请阅读 [`architecture-overview-zh.md`](architecture-overview-zh.md)（中文版）。当前框架落地情况请阅读 [`eva-framework-implementation.md`](eva-framework-implementation.md)。

---

## 完成度定义

每项承诺归于以下四级之一。不允许"进行中"或"即将完成"等模糊措辞——这些 tier 是稳定状态声明：

- **production**：已在代码落地，通过当前 runtime surface 验证，稳定到可以作为规范架构的一部分
- **partial**：已落地但有明确的、命名的限制，该限制实质影响这项能力的使用范围
- **skeleton**：框架所有的接口或 placeholder 存在，但实际能力表面有限
- **deferred**：理论承诺了，或文档标记为未来事项，但 runtime 当前未实现

---

## 1. 架构层追踪

### 1.1 Kernel 和运行时权威

| 组件 | 代码位置 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| 有界 heartbeat / tick / turn 运行时循环 | `eva/kernel/main.py`、`eva/kernel/lifecycle.py` | production | — | — |
| Instance legitimacy（lock / generation / lease） | `eva/kernel/instance.py` | production | — | — |
| 通过 RuntimeScenarioBundle 的显式场景激活 | `eva/scenario_bundle.py` | production | — | — |
| Shipped 场景的 runner-owned 启动装配 | `runners/run_linux.py`、`runners/run_crafter.py` | production | — | — |
| 显式 persistence hierarchy contract | `eva/persistence_targets/__init__.py` | production | — | — |
| 场景所有者在 shipped 场景中激活 lower persistence levels | `scenarios/linux_runtime/persistence/`、`scenarios/crafter/persistence/` | production | — | — |
| Persistence target Levels 5–7 | — | deferred | 理论 placeholder；机制预留至未来版本 | 后期 |
| 基于 trace 文件的架构无关稳定性 profile 计算 | `stability_metrics/` | production | — | — |
| Comparative Stability Hypothesis 评估程序 | — | deferred | 测量 surface 已落地；比较实验程序未实现 | 后期 |

### 1.2 L1  homeostatic sensing

| 组件 | 代码位置 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| 归一化 sensor registry 和 sensing contract | `eva/l1_sensing/sensor_registry.py`、`eva/scenario_bundle.py` | production | — | — |
| 带 rate-sensing tier 元数据的场景声明 dimension specs | `eva/l1_sensing/dimension_specs.py`、场景 `dimensions/` 声明 | production | — | — |
| 带显式 unknown fallback 的 rate-aware sensing | `eva/l1_sensing/rate_sensors.py`、`eva/l1_sensing/dimension_specs.py` | production | — | — |
| 带显式 status / threat 分类的 signal publication | `eva/l1_sensing/signal_bus.py` | production | — | — |

### 1.3 L2  drive 和 pressure 处理

| 组件 | 代码位置 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| Drive preset 和 drive-update 接口 | `eva/l2_drive/drive_registry.py`、`eva/l2_drive/pressure_to_drive.py` | production | — | — |
| 带 urgency 调制和有界 anticipatory pressure 的 pressure projection | `eva/l2_drive/pressure_projection.py` | production | — | — |
| 与较慢 deliberation 并行的保护性 reflex fast path | `eva/l2_drive/reflex.py` | production | — | — |

### 1.4 L3  deliberation、peer circuit 和 learning

| 组件 | 代码位置 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| 规范 deliberation 输入 contract | `eva/l3_deliberation/contracts.py` | production | — | — |
| Mediator 作为独立 peer circuit（default inhibition + 选择性 release） | `eva/l3_deliberation/peer_circuit/mediator.py` | production | — | — |
| 运行时独属 release token 边界 | `eva/l3_deliberation/contracts.py` | production | — | — |
| 带有界 learned overlay 的 drive 加权 candidate 评估 | `eva/l3_deliberation/reasoning/value_judgment.py`、`eva/l3_deliberation/peer_circuit/rpe.py` | production | — | — |
| 带规范 `OutcomeVector` 支持的 append-only learning outcome 记录 | `eva/l3_deliberation/contracts.py`、`eva/l3_deliberation/peer_circuit/rpe.py`、场景 outcome observers | production | — | — |
| RPE -like learning 作为内部更新信号 | `eva/l3_deliberation/peer_circuit/rpe.py` | production | — | — |
| 通过 habit track 的 habit shaping 和 skill crystallization | `eva/l3_deliberation/peer_circuit/habit_track.py`、`eva/l3_deliberation/memory/skill_library.py` | production | — | — |
| Advisory-only working-memory 装配 | `eva/l3_deliberation/reasoning/working_memory.py` | production | — | — |
| 带有界 fallback 的 model-backed working-memory advisory 路径 | `eva/kernel/main.py`、`eva/l3_deliberation/reasoning/working_memory.py` | production | — | — |
| 基于 append-only artifact 的 episodic retrieval | `eva/l3_deliberation/memory/episodic.py`、`eva/l3_deliberation/memory/retrieval.py` | production | — | — |
| Semantic memory — 一等存储 + 精确查询 + 有界 L3 参与 | `eva/l3_deliberation/memory/semantic.py`、`eva/skills/__init__.py` | partial | Store-side windowing / indexing 未实现；semantic → L2 drive-weight semantics 未实现 | Stage I follow-up #1、#2 |
| Semantic memory → L2 drive-weight semantics | — | deferred | 保留以维护 drive read-only boundary；最小安全路径评估 deferred | Stage I follow-up #2 |
| 通过现有 habit-track substrate 的 procedural memory | `eva/l3_deliberation/peer_circuit/habit_track.py`、`eva/skills/__init__.py` | partial | Surface 是显式的，但 backing track 仍是 `habit_bias.jsonl` 而非独立 procedural store | 后续评估 |
| Working-memory 接口签名 | `eva/l3_deliberation/reasoning/working_memory.py` | partial | 多参数装配在累积；接口复审阈值接近 | Watch（Stage I follow-up #3） |

### 1.5 Anchor 和 mediated release

| 组件 | 代码位置 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| 框架所有的 action domain 和生成前限制 surface | `eva/anchor/domain_restriction.py` | production | — | — |
| 通过 active bundle seam 的场景所有 anchor admission policy | `eva/scenario_bundle.py`、场景 `anchors/` | production | — | — |
| Mediated candidate 过滤、选择和 execution 路径 | `eva/l3_deliberation/tool_edge/tool_registry.py`、`eva/l3_deliberation/tool_edge/executors.py` | production | — | — |
| Anchor 三层区分（机制 / 宪法策略 / 涌现 overlay） | `eva/anchor/domain_restriction.py`、场景 anchor policies | partial | 机制 / 宪法策略分离清晰；emergent overlay 故事比理论的长期框架更窄 | 后续深化 |

### 1.6 Inherited priors 和 capability provenance

| 组件 | 代码位置 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| 同场 inherited-prior 蒸馏 pipeline | `inheritance_distillation/` | production | — | — |
| 同场 inherited-prior 加载和有界 deliberation 参与 | `eva/skills/__init__.py`、`eva/l3_deliberation/reasoning/working_memory.py`、`eva/l3_deliberation/peer_circuit/habit_track.py`、场景 `prior_skills/inherited.py` | production | — | — |
| 带 provenance 的 capability-tracking skill registry | `eva/skills/__init__.py`、场景 prior-skill bundles | partial | Provenance 在当前记录上是显式的；更广泛的 theory-side source taxonomy 尚未作为独立 runtime 源激活 | 后续评估 |
| 跨场 inherited-prior 传输 | — | deferred | 同场已落地；跨场需要额外约束工作 | 后期 |

### 1.7 Deferred 和预留项

| 组件 | 理论章节 | 完成度 | 已知限制 | 计划演进 |
|---|---|---|---|---|
| Exploration as growth driver | v0.6 §1.4 | deferred | 理论已指定；runtime 机制未实现 | 中期 |
| L4 self-model runtime | v0.5 §9、v0.6 §7.2 | deferred | 预留接口；实现 deferred | 后期 |
| L5 social-layer runtime | v0.5 §10、v0.6 §7.2 | deferred | 预留接口；实现 deferred | 后期 |
| 通用场景 loader / validator | — | deferred | 仓库使用显式 runner 装配 | 后续评估 |
| 单进程内多场景 runtime 切换 | — | deferred | 不在当前范围 | 后续评估 |

---

## 2. 场景契约追踪

追踪跨场景集成契约。完整契约规范见 [`scenarios-SPEC.md`](scenarios-SPEC.md)。

| 契约组件 | 代码位置 | 完成度 | 已知限制 |
|---|---|---|---|
| `RuntimeScenarioBundle` 接口 | `eva/scenario_bundle.py` | production | — |
| `SensorPolicyBundle` 集成 | `eva/l1_sensing/sensor_registry.py` | production | — |
| `ActionPolicyBundle` 集成 | `eva/l3_deliberation/tool_edge/tool_registry.py` | production | — |
| `AnchorPolicyBundle` 集成 | `eva/anchor/domain_restriction.py` | production | — |
| `OutcomeObserverBundle` 集成 | `eva/l3_deliberation/contracts.py` | production | — |
| `PriorSkillBundle` 集成 | `eva/skills/__init__.py` | partial | Provenance boundary 深化是未来事项 |
| 场景所有者 persistence hierarchy 注册 | `scenarios/linux_runtime/persistence/`、`scenarios/crafter/persistence/` | production | — |
| 规范多维 `OutcomeVector` | `eva/l3_deliberation/contracts.py` | production | — |
| 带场景所有 provenance 输入的框架所有 skill registry | `eva/skills/__init__.py` | production | — |

---

## 3. 单场景追踪

### Linux runtime

| 项目 | 状态 | 参考 |
|---|---|---|
| 主参考 runtime 部署 | production | [`scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md) |
| Linux 特定 drive 族、sensors、有界 action 词汇表、anchors、outcome observers | production | [`scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md) |
| Linux 限定 bundle 的同场 inherited-prior 重用 | production | [`scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md) |

### Crafter

| 项目 | 状态 | 参考 |
|---|---|---|
| 通过共享框架循环的有界端到端 Crafter runtime | partial | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) — 是真实的已落地 second scenario，但文档化为有意识地限制在 bounded scope 内 |
| Crafter 特定 drives、sensors、有界 action bridge、anchors、outcome observers、persistence hierarchy、prior-skill policy | production（bounded scope 内） | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) |
| 对 required-tier dimensions 的 trajectory-aware sensing 和有界 anticipatory pressure | production | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) |

---

## 4. 待处理 follow-up

以下项目确认为待延续 follow-up，不是意外 gap：

| 项目 | 来源 | 状态 |
|---|---|---|
| Semantic memory store-side windowing / indexing | Stage I follow-up #1 | open |
| Semantic memory → L2 drive-weight semantics 最小安全路径评估 | Stage I follow-up #2 | open |
| Working-memory 接口签名复审阈值 | Stage I follow-up #3 | watch |

---

## 5. 与其他文档的关系

- **`architecture-overview-zh.md`** — 本文档的条目是架构鸟瞰图映射的具体承诺
- **`eva-framework-implementation.md`** — 框架当前所有的权威来源；本跟踪文档将这些能力映射回其理论承诺
- **`scenarios-SPEC.md`** — 场景如何接入框架的契约规范；单场景追踪部分链接到具体场景 SPEC

本文档在每个 stage 关闭时更新。Stage 之间，它反映最后一次确认的状态。