# 文档整合规划 v2.2（终版）
**基于架构师评审 + 工程实现全面核实**

---

## 一、两轮整理问题回顾与原因分析

### 第一轮（Codex）

**操作**：将散乱文档归并为四条平行线，另起蓝图文件。

**缺陷**：蓝图写成 v0.5 摘要 + v0.6 增量补丁；v0.6 机制隔离在 §1.4 表格；v0.5 archive 仍为前置必读；三层文档职责边界部分重叠。

### 第二轮（上一轮 Claude Code）

**操作**：在第一轮基础上补充中文版和部分新小节。

**缺陷（架构师评审指出的根本性失败）**：

1. **当成增量补丁**：每节以"v0.5 已说明... v0.6 新增..."连接句打断流畅性
2. **误解 v0.6 性质**：v0.6 最大的动作是**框架/场景分离**（结构性重切分），四层记忆等是沿脊柱内嵌的机制精化
3. **v0.6 机制隔离**：速率 tier → §4、四层记忆 → §6、继承先验 → §6 末段、语义→L2 → §5.8、Anchor 三层 → §7

**根本认知偏差**：把蓝图定位为"承接 v0.5 + 标记 v0.6 增量"，而非"整合后的当前唯一落地基准"。

### 评审机制引入

架构师（Claude 评审）引入**对齐标记机制**：每节整合承诺句末尾追加 `[✓ aligned]` / `[⏳ deferred]` / `[⚠ beyond impl]`，在阶段一（最便宜节点）完成工程对齐审计。

---

## 二、工程实现全面核实

### Procedural memory 实际状态

**代码核实路径**：`eva/l3_deliberation/memory/skill_library.py` + `eva/l3_deliberation/memory/episodic.py`

- backing store：`habit_bias.jsonl`（唯一存储）
- procedural 读 surface：`derive_habit_skills()`、`habit_skill_registry()`、`shape_candidates_with_habit_track()`
- `ProceduralMemoryRecord` / `ProceduralMemoryRegistry` 在 `eva/skills/__init__.py` 定义为框架数据类型，但无独立 backing store
- **没有**独立的 `procedural_memory.jsonl`

**Stage I 选择路径 (b)**：形式化并轻度扩展现有 habit 路径，而非添加独立 procedural store。

### Working memory 六种输入的代码对应

**代码核实路径**：`eva/l3_deliberation/reasoning/working_memory.py` 的 `WorkingMemoryContext` 字段

| 代码实际字段 | Blueprint 对应来源 | 备注 |
|---|---|---|
| `DeliberationInput.drive_broadcast` + L1 signals | sensing + drive broadcast | 来自 runtime loop，非 memory retrieval |
| `cognitive_memory_stub` retrieval | episodic hint | `recent_cognitive_memory_stub_traces()` |
| `semantic_patterns` | semantic hint | `recent_semantic_memory()` |
| `habit_skills` + `bias_summaries` | procedural/habit shortcut | `derive_habit_skills()`，backed by `habit_bias.jsonl` |
| `inherited_priors` | inherited prior hint | `inherited_prior_registry().for_situation()` |
| `recent_relevant_outcomes` | outcome trace | 三级 fallback：`recent_learning_outcomes()` → `recent_response_history()` → `recent_cognitive_memory_stub_traces()` |

"六种输入"是 `DeliberationInput` + 五路 memory retrieval 的自然计数，不是发明概念。

### §7.4 Anchor 分层核实

**代码核实路径**：`eva/anchor/structural.py` + `eva/anchor/dynamic.py` + `eva/anchor/domain_restriction.py` + `eva/scenario_bundle.py`

代码有两套可识别实体：

| 代码实体 | 对应理论层 | 稳定性 | 来源 |
|---|---|---|---|
| `apply_structural_anchor()` (`structural.py`) | **结构锚定** | 稳定硬边界 | `eva/anchor/` 框架持有 |
| `AnchorPolicyBundle.admit_candidates()` | **宪法策略** | 半稳定 | 场景持有（bundle） |
| `apply_dynamic_anchor()` (`dynamic.py`) + `shape_candidates_with_habit_track()` | **涌现叠加层** | 瞬态 | 框架 + habit track |

**结论**：代码有两套明确可分的 anchor 实现（structural + dynamic），加上场景持有的 constitutional admission policy。v0.6 的"三层区分"是理论承诺层级的三描述，映射到代码的两层实现 + 场景 bundle 层。蓝图 §7.4 标题可用"三层区分"，但正文必须反映代码实现现实。

### §6.7 继承先验核实

**代码核实路径**：`eva/skills/__init__.py` 的 `load_inherited_prior_registry()` + `inheritance_distillation/` 目录

两件关键事：

1. **`load_inherited_prior_registry()`** line 269：`if str(payload.get("scenario") or "") != expected_scenario: raise ValueError(...)` — **same-scenario 在 bundle 加载时被强制校验**，跨场直接 reject

2. **`inheritance_distillation/`** 确认是独立顶层包（`eva/` 和 `scenarios/` 之外），包含 `pipeline.py`/`bundle_writer.py`/`validators/`/`extractors/`，不导入框架或场景模块

**结论**：same-scenario only 有代码强制；cross-scenario 未实现（deferred）；distillation pipeline 位置与架构承诺一致。

---

## 三、文档整理思路调整

| 维度 | 旧思路 | 新思路 |
|---|---|---|
| 蓝图定位 | "承接 v0.5 + 标记 v0.6 增量" | **整合后的当前唯一落地基准** |
| v0.5 archive 角色 | 事实上的前置必读 | 退为历史参考；正文用一句话带过 |
| v0.6 机制处理 | "在 §1.4 表格里列出，正文引用" | **沿脊柱内嵌到各节** |
| §1 结构 | §1.1-§1.5 五子节 | **§1.1/§1.2/§1.3 三子节** |
| 每节写法 | "v0.5 已说明... v0.6 新增..." | **三件套模板** |
| Part III | 收集 v0.6 新机制 | **只保留真正理论占位项** |
| 对齐审计 | 无 | **阶段一每节三选一标记** |

---

## 四、三件套模板

**【整合承诺】**：本节完整覆盖什么——第一句话说出承诺，不先说 v0.5。
**【框架 vs 场景】**：本层哪些归框架、哪些归场景，明确边界。
**【相对 v0.5 位移】**：与 v0.5 的实质性差异，行内轻量标注 `v0.5 §X / v0.6 §Y`，节末不附"v0.5 已说明..."段。

---

## 五、对齐标记机制

每节整合承诺句末尾追加三选一标记：

| 标记 | 含义 | 处理方式 |
|---|---|---|
| `[✓ aligned]` | 承诺与当前代码实现一致 | 阶段二照常展开 |
| `[⏳ deferred: <说明>]` | 蓝图承诺接口/边界，具体实现显式延期 | 阶段二展开时必须说明延期理由 + 当前替代路径 |
| `[⚠ beyond impl]` | 承诺超出当前代码，需要架构师评审 | 阶段二不要展开此节，先停下 |

---

## 六、完整 4-Part 结构规划

### Part I：框架架构（本轮重建目标）

#### §1 引言：整合的落地基准
- §1.1 蓝图性质（自足落地基准；v0.5 退为历史参考，用一句话带过）
- §1.2 v0.6 两件事（框架/场景分离脊柱 + 机制精化沿脊柱内嵌，不列清单）
- §1.3 理论与代码来源链接

#### §2 总体架构
- §2.1 框架 + 场景二层图
- §2.2 依赖方向
- §2.3 框架边界规则（含场景从属规则）
- §2.4 RuntimeScenarioBundle 接缝（六 surface，双栏框架 vs 场景）

#### §3 Kernel
- §3.1 角色
- §3.2 heartbeat-first 循环（tick/turn）
- §3.3 实例合法性
- §3.4 持久化两种模式
- §3.5 通信语义
- §3.6 持久化目标层级

#### §4 L1 感知
- §4.1 角色
- §4.2 SensorRegistry
- §4.3 状态 + 速率两个视角
- §4.4 **速率感知 + tier 元数据**（required/recommended/optional，在 L1 sensor 契约层面内嵌）
- §4.5 三种紧迫度（threat/status/background）
- §4.6 快慢路径分离
- §4.7 边界

#### §5 L2 驱力
- §5.1 角色
- §5.2 DriveRegistry
- §5.3 连续强度
- §5.4 时间动力学
- §5.5 驱力广播（状态非命令）
- §5.6 压力投影
- §5.7 反射弧
- §5.8 **语义→L2 驱力权重路径约束**（禁止，Stage I 延期）

#### §6 L3 Deliberation
- §6.1 角色
- §6.2 **四层记忆**：
  - 工作 / 情景 / 语义（各有权责表）
  - 程序记忆：形式化承诺 + **Stage I 实现说明**（backing = `habit_bias.jsonl`；不承诺独立存储文件）
  - 集成总结表
  - 引用 §5.8 语义→L2 约束
- §6.3 推理核心
- §6.4 对等回路/基底核
- §6.5 Mediator + 工具边
- §6.6 Outcome/RPE/Habit
- §6.7 **继承先验 L3 机制**：
  - 蒸馏 pipeline（独立包）
  - 运行时加载
  - **same-scenario only**（代码强制）—— cross-scenario deferred
  - provenance
- §6.8 探索作为成长驱动力（理论占位符 → Part III）

#### §7 Anchor
- §7.1 角色
- §7.2 形式含义 `G(s) → A'(s) ⊆ A(s)`
- §7.3 能力限制 vs 参数域限制
- §7.4 **三层区分**：
  - 结构锚定（`structural.py`，稳定）→ 代码层一
  - 宪法策略（场景持有的 `admit_candidates`，半稳定）→ 代码 bundle 层
  - 涌现叠加层（`dynamic.py` + habit track，瞬态）→ 代码层二
  - 正文必须反映代码的两套实体 + 场景 bundle，标题"三层"保留为理论承诺层级描述
- §7.5 结构 vs 动态实现
- §7.6 与其他层关系

#### §8 运行时闭环
- §8.1 循环概述：六种 working memory 输入来源（明确列出：drive_broadcast + episodic + semantic + procedural-habit + inherited prior + outcome trace）；采用选法 A（1 路 channel 含 sensing+drive + 5 路 retrieval = 6 路），说明为何不算 7 路
- §8.2 感知→信号→驱力
- §8.3 驱力→候选塑造
- §8.4 Mediator→release→执行
- §8.5 Outcome→记忆/RPE/habit
- §8.6 不变量总结表

### Part II：场景架构
- RuntimeScenarioBundle 详细规范
- 场景装配要求
- 激活模型
- 场景边界强制
- 落地契约 surface
- 契约限制

### Part III：理论占位符（精简版）
- Exploration as growth driver（设计尚未完成）
- Comparative Stability Hypothesis（理论占位符）
- Persistence target levels 5–7（理论占位符）

### Part IV：不变量 + 验证 + 部署

---

## 七、两阶段执行策略

**阶段一（本轮，只做这步）**：产出具录大纲 + 每节开头第一句话（整合承诺） + 对齐标记

- 输出：完整三级标题树 + 每节一行（标题 + 整合承诺句 + 标记）
- §7.4 整合承诺句必须反映代码核实结果（两套实体 + 场景 bundle）
- §6.7 整合承诺句必须包含 same-scenario only + distillation 独立包的位置
- §8.1 整合承诺句必须列出六种来源名称
- 完成后贴出，等确认

**阶段二（确认后）**：按三件套模板逐节展开，英文先行，一节一节写，不要批量并行

---

## 八、已核实的工程基线（直接使用，不再核实）

### 程序记忆
- backing store：`habit_bias.jsonl`（唯一存储）
- 读 surface：`derive_habit_skills()` / `habit_skill_registry()` / `shape_candidates_with_habit_track()`
- 无独立 `procedural_memory.jsonl`
- `ProceduralMemoryRecord` / `ProceduralMemoryRegistry` 是框架数据类型，但无独立 backing

### 六种 working memory 输入
1. `drive_broadcast`（通过 `DeliberationInput`）
2. episodic（CognitiveMemoryStub retrieval via `recent_cognitive_memory_stub_traces()`）
3. semantic（SemanticMemory retrieval via `recent_semantic_memory()`）
4. procedural/habit（HabitSkill + HabitBias summary via `derive_habit_skills()`，backed by `habit_bias.jsonl`）
5. inherited prior（via `InheritedPriorRegistry.for_situation()`）
6. outcome trace（via `recent_learning_outcomes()` → `recent_response_history()` → `recent_cognitive_memory_stub_traces()` 三级 fallback）

### Anchor 分层
- 代码层一：`structural.py::apply_structural_anchor()`（稳定硬边界）
- 代码 bundle 层：`AnchorPolicyBundle.admit_candidates()`（宪法，场景持有）
- 代码层二：`dynamic.py::apply_dynamic_anchor()` + `shape_candidates_with_habit_track()`（涌现叠加层）

### 继承先验
- `load_inherited_prior_registry()` 在加载时强制 same-scenario 校验（line 269 强制 reject cross-scenario bundle）
- `inheritance_distillation/` 是独立顶层包，不在 `eva/` 也不在 `scenarios/`
