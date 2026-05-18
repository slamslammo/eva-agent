# EVA 框架实现

**状态**：Stage I I-4 同场 inherited-prior 重用已在 Stage G 框架边界落地  
**范围**：`eva/` 下的框架代码  
**配套文档**：`docs/scenarios-SPEC.md`、`scenarios/linux_runtime/SPEC.md`  
**历史参考**：`docs/archive/eva-agent-full-implementation-v0.5.md`

---

## 目的

本文档描述 `eva-agent` 仓库中当前已实现的框架机制。涵盖跨场景保持不变的结构运行时，以及场景所有者内容被激活的接口。

它不指定 Linux 专用 drive、sensor、action、anchor 规则、outcome label 或 prior-skill 启发式——那些属于场景文档。

## 当前框架边界

框架当前拥有以下运行时 surface。

### 1. Kernel 运行时权威

Kernel 拥有 bounded 运行时循环、cadence、instance legitimacy 和 persistence 边界。

规范框架入口：
- `eva/kernel/main.py` — 通用 `run_runtime()` 循环和兼容性 CLI 入口
- `eva/kernel/lifecycle.py` — heartbeat / tick / turn 权威
- `eva/kernel/instance.py` — instance legitimacy
- `eva/kernel/state.py` — 当前状态和 append-only artifact 写入
- `eva/kernel/config.py` — 运行时配置契约

### 2. 活动场景接口

框架在 `eva/scenario_bundle.py` 中暴露一个活动场景激活接口。

定义：
- `RuntimeScenarioBundle`
- `SensorPolicyBundle`
- `ActionPolicyBundle`
- `AnchorPolicyBundle`
- `OutcomeObserverBundle`
- `PriorSkillBundle`

运行中的 agent 同时使用一个活动 bundle。框架通过此接口读取场景策略，而不是在代码库中跨场景导入场景特定模块。

### 3. L1 框架机制

框架保留 sensing 的 registry 和 collection 契约：
- `SensorSpec`
- `SensorOutput`
- `SensingContext`
- `SensorRegistry`

位于 `eva/l1_sensing/sensor_registry.py`。

框架拥有归一化 sensing 契约和 collection 排序。具体 sensor provider 来自活动场景 bundle。

### 4. L2 Drive 机制

框架在 `eva/l2_drive/drive_registry.py` 保留通用 drive 接口：
- `DrivePreset`
- `DriveUpdatePolicy`
- default preset 注册 / 解析

框架仍拥有 drive update 语义、只读下游消费，以及"L3 以上层不得直接写入 drive state"的不变量。具体 drive 族和 dimension mapping 来自活动场景。

### 5. L3 结构机制

框架拥有以下结构：
- anchor 时 `ActionDomain` 构建：`eva/anchor/domain_restriction.py`
- response candidate / filter / selection 数据类：`eva/l3_deliberation/tool_edge/tool_registry.py`
- mediated execution 路径：`eva/l3_deliberation/tool_edge/executors.py`
- learning outcome 记录和 learned-impact overlay：`eva/l3_deliberation/peer_circuit/rpe.py`
- 规范多维 `OutcomeVector` 契约：`eva/l3_deliberation/contracts.py`
- skill provenance 和 registry 类型：`eva/skills/__init__.py`
- persistence-target hierarchy 契约：`eva/persistence_targets/__init__.py`
- working-memory 装配和有界 advisory attachment：`eva/l3_deliberation/reasoning/working_memory.py`
- episodic / semantic / procedural memory owners：`eva/l3_deliberation/memory/`
- habit-bias 和 habit-skill summary 数据类：`eva/l3_deliberation/memory/skill_library.py`
- inherited-prior 加载、shaping 和有界 value bias：通过 `InheritedPriorRegistry`、`eva/l3_deliberation/peer_circuit/habit_track.py` 和 `eva/l3_deliberation/reasoning/value_judgment.py`

框架因此拥有 deliberation 结构、mediated release、append-only learning 记录、读侧 learning overlay、显式 persistence-target lookup、Stage I 四层 memory surface 和 skill provenance。具体策略内容来自活动场景。

### 6. Append-only 和权威边界

框架仍然是以下内容的 owner：
- 当前运行时 state 写入
- append-only 事件和 audit 写入
- append-only cognitive / learning / habit / semantic memory track
- mediated release 权威
- 运行时仅限 release-token 验证
- "场景内容可以塑造 candidate 和解释，但不得绕过 release 或 rewrite 历史"规则

## Stage I 四层记忆模型

Stage I I-3 使 memory 层显式化，而不扩大权威边界。

### 层 surface

- `WorkingMemory` / `WorkingMemoryContext`：`eva/l3_deliberation/reasoning/working_memory.py`
  - 仅周期内；不持久化
  - 从 append-only artifact 有界 retrieval 装配
- `EpisodicMemoryRegistry`：`eva/skills/__init__.py`
  - 面向 relevance 的跨周期 trace 记录 surface
  - 当前实用 backing：`cognitive_memory_stub.jsonl`、`learning_outcomes.jsonl` 和有界 response-history reuse
- `SemanticMemoryRegistry`：`eva/skills/__init__.py`
  - 从 episodes 提取的规律性记录 surface
  - 当前实用 backing：`semantic_memory.jsonl`
- `ProceduralMemoryRegistry`：`eva/skills/__init__.py`
  - 条件匹配 action 模式记录 surface
  - 当前实用 backing：通过现有 habit 路径的 `habit_bias.jsonl`

### Stage I 存储映射

| 层 | 当前存储 / owner | Stage I 状态 |
|---|---|---|
| Working memory | 周期内 `WorkingMemory` 装配 | 显式接口已落地 |
| Episodic memory | `cognitive_memory_stub.jsonl`、`learning_outcomes.jsonl`、response history retrieval | 显式 registry surface 已落地 |
| Semantic memory | `semantic_memory.jsonl` | 一等 append-only 存储 + 查询接口已落地 |
| Procedural memory | `habit_bias.jsonl` | 通过 Stage I 路径 (b) 落地显式 registry surface |

### Stage I Semantic memory

- 存储路径在 `eva/kernel/config.py` 中配置，通过 `eva/kernel/state.py` 持久化
- owner helpers 在 `eva/l3_deliberation/memory/semantic.py` 支持 append、read、按 topic 精确查询、按 scope 精确查询
- Stage I **不**实现自动 episodic-to-semantic 提取；semantic storage 仅作为一等 owner 和读侧参与接口落地
- runtime 参与有界：匹配的 semantic 条目 retrieve 入 working memory，并在 value judgment 期间施加微小的可审计 candidate prior modifier

### Stage I Procedural memory

- Stage I 采用启动指令 review 中的路径 **(b)**：形式化并轻度扩展现有 habit 路径，而非添加独立 `procedural_memory.jsonl`
- `habit_bias.jsonl` 保持为 backing track
- `derive_habit_skills()` 和 `habit_skill_registry()` 现形成显式 procedural-memory 读 surface
- `shape_candidates_with_habit_track()` 保持为 candidate-generation shortcut 接口
- procedural shaping 可以缩小或重排 candidate，但不得拥有 release 权威，也不得绕过 mediator gate

### 各层集成状态

- **Working memory → L3 deliberation**：直接输入；已落地
- **Episodic memory → L3 deliberation**：相关性 retrieval；已落地
- **Semantic memory → L3 deliberation**：有界 candidate prior modifier；已落地
- **Semantic memory → L2 drive weights**：在 I-3 deferred，以保留现有 drive-boundary invariant
- **Procedural memory → L3 deliberation**：通过 habit 路径的 candidate shaping / shortcut；已落地

这些 Stage I memory surface 保持有界、append-only 兼容，并在 retrieval 可能跨场景泄漏的地方做场景限定。

## Stage I Inherited-Prior 重用

Stage I I-4 在不创建第二条决策线的前提下，添加同场跨生命重用。

### 框架 / runtime 边界

- `InheritedPriorRecord` / `InheritedPriorRegistry` 在 `eva/skills/__init__.py` 是加载 inherited prior 的框架所有记录 surface
- runtime config 在 `eva/kernel/config.py` 和 CLI 解析在 `eva/kernel/main.py` 现携带可选 `inherited_priors_path`
- 场景激活仍是 bundle 加载发生的唯一位置；框架通过现有活动场景接口读取 inherited priors

### Runtime 参与

- `eva/l3_deliberation/reasoning/working_memory.py` 中的 working-memory 装配现为精确当前 `situation_key` surfacing `inherited_priors`
- `shape_candidates_with_habit_track()` 将 inherited-prior hint 合并入现有 habit-path shaping 流程
- `assess_candidates()` 仅在匹配的 prior 足够强时施加微小的可审计 `inherited_prior_bias`
- inherited priors 保持 advisory：anchors 仍约束 admission，mediator 仍拥有 release，append-only artifact 仍为框架所有

### 蒸馏边界

- `inheritance_distillation/` 现为独立于 `eva/` 和 `scenarios/` 的落地顶层包
- 它读取 append-only trace 文件，提取同场规律性，验证结构不变量，并写入 `DistilledPriorBundle.json`
- 它不导入框架或场景模块

## 框架不拥有什么

框架不拥有：
- 具体 drive 名称或 dimension mapping
- 具体 sensor dimension 或 payload 策略
- 具体 action 名称、posture 或 handler
- 场景特定 candidate profile 或 anchor reason 词汇表
- 场景特定 expected-outcome label
- 场景特定 prior-skill 或 habit 派生策略
- 每场景启动装配

这些属于 `scenarios/<name>/` 和 `runners/run_<name>.py`。

## 当前兼容性 surface

Stage G 故意保留一小套框架所有兼容性 wrapper，通过活动 bundle 代理场景策略：
- `eva/l1_sensing/state_sensors.py`
- `eva/l2_drive/drive_registry.py`
- `eva/anchor/domain_restriction.py`
- `eva/l3_deliberation/tool_edge/tool_registry.py`
- `eva/l3_deliberation/tool_edge/executors.py`
- `eva/l3_deliberation/peer_circuit/rpe.py`
- `eva/l3_deliberation/memory/skill_library.py`

这些文件是框架边界的一部分。其职责是在避免散落导入特定场景的同时，保留结构性所有权。

## Runner 和激活模型

Runner 在调用通用框架循环之前激活场景 bundle。

当前 shipped 示例：
- `runners/run_linux.py` 激活 `scenarios/linux_runtime`，注册 Linux persistence hierarchy，然后调用 `eva.kernel.main.run_runtime()`

运行中的 runtime 必须在使用场景依赖的框架特性之前显式激活场景 bundle，且场景所有者的启动装配也负责注册匹配的 persistence hierarchy。`eva/kernel/main.py` 保持为兼容性入口，但当没有场景被激活时没有静默 fallback。

## 尚未落地为框架特性

以下概念未作为已实现的框架特性记录：
- 通用场景 loader / validator
- 具体 L4 self-model 或 L5 social-layer runtime 实现

顶层 `stability_metrics/` 包是一个落地的配套模块，`eva/l3_deliberation/contracts.py`、`eva/persistence_targets/` 和 `eva/skills/` 已包含实现的框架接口。本文将这些 surface 保留在上面的当前边界章节中，而非列为未来工作。

## 边界规则

如果一个机制必须保持 cadence、instance legitimacy、mediated release、append-only history 或跨场景结构，它属于框架。

如果一个能力随 agent 嵌入的世界变化而变化，它属于场景。
