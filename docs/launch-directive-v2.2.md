# 文档整理启动指令 v2.2（终版）
**覆盖 `architecture-implementation-blueprint-v0.6.md` Part I 完整开发**
**可直接转发给 Claude Code 执行**

---

## 0. 任务范围与自主推进规则

本指令覆盖 Part I 两个阶段：
- **阶段一**：大纲 + 每节整合承诺句 + 工程对齐标记
- **阶段二**：每节按三件套模板展开内文 + 中文版同步

**自主推进规则**：
- 阶段一所有节都标 `[✓ aligned]` 或 `[⏳ deferred]` → 直接进入阶段二，无需再问
- 出现任何 `[⚠ beyond impl]` 标记 → 在聊天中贴出大纲并停下，等架构师评审
- 阶段二展开中发现理论承诺与代码实现冲突 → 停下贴聊天，描述冲突，等指引
- 全部完成后 commit + push，只在聊天贴一条总结，不展示全文

**介入条件**：除非你（架构评审方）主动确认出现偏离预期的情况，否则本轮不介入审查。

---

## 1. Blueprint 性质重定位

`architecture-implementation-blueprint-v0.6.md`（及其 `-zh.md`）是**整合后的当前唯一落地基准**，不是"承接 v0.5 + 标记 v0.6 增量"。v0.5 archive（`docs/eva-agent-full-implementation-v0.5.md`）退为历史参考，蓝图正文不依赖它作为前置必读。

---

## 2. v0.6 的两件事

1. **框架/场景分离**：结构性重切分——`eva/` 持运行时权威，`scenarios/<name>/` 持世界特定内容，通过 `RuntimeScenarioBundle` 通信。这是 Part I 的组织脊柱。
2. **机制精化内嵌**：速率 tier → §4；四层记忆 → §6；语义→L2 约束 → §5.8；继承先验 → §6 末段；Anchor 分层 → §7。机制沿脊柱内嵌进各节，不在引言列清单，不集中堆到 Part III。

---

## 3. Part I 本轮结构性调整（5 项）

### 3.1 §1 引言收为 3 个子节

- §1.1 蓝图性质（自足落地基准；v0.5 退为历史参考，用一句话带过）
- §1.2 v0.6 两件事（只说"机制沿脊柱内嵌到各层"，不列具体清单）
- §1.3 理论与代码来源链接

**禁止**：不单设"机制内嵌概览"或"v0.5 退位说明"子节。

### 3.2 §4 L1

§4.4 改为"速率感知 + 速率 tier 元数据"：required / recommended / optional 三级，在 L1 sensor 契约层面内嵌，不是附录。

### 3.3 §5 L2

§5.8 新增"语义→L2 驱力权重路径约束"：为什么禁止、Stage I 显式延期、保持 drive 只读不变量。

### 3.4 §6 L3

- **§6.2 四层记忆形式化**：工作 / 情景 / 语义 / 程序，四表 + 集成总结。
  **必须显式说明**：程序记忆当前由 `habit_bias.jsonl` 承担 backing store（Stage I 选择路径 b：形式化并轻度扩展现有 habit 路径，不添加独立 procedural store）；蓝图承诺的是"程序记忆的条件-动作模式必须显式、有界、由 mediator 把守"，不承诺独立存储文件。

- **§6.7 继承先验 L3 机制**：蒸馏 pipeline + 运行时加载 + 约束 + provenance。
  **必须显式说明**：
  - 当前 **same-scenario only**（`load_inherited_prior_registry()` line 269 强制校验，跨场直接 reject）；cross-scenario 是 deferred
  - distillation pipeline 在 `inheritance_distillation/` 独立包（既不在 `eva/` 也不在 `scenarios/`）

### 3.5 §7 Anchor

§7.4 标题"三层区分"保留为理论承诺层级描述，但正文必须反映代码实现现实：

| 代码实现 | 对应理论层 | 稳定性 | 持有 |
|---|---|---|---|
| `apply_structural_anchor()`（`structural.py`） | 结构锚定 | 稳定硬边界 | 框架 |
| `AnchorPolicyBundle.admit_candidates()` | 宪法策略 | 半稳定 | 场景 |
| `apply_dynamic_anchor()`（`dynamic.py`） + habit track | 涌现叠加层 | 瞬态 | 框架 + habit |

---

## 4. 已核实的工程基线（直接使用，不再核实）

### 程序记忆
- backing store：`habit_bias.jsonl`（唯一存储）
- 读 surface：`derive_habit_skills()` / `habit_skill_registry()` / `shape_candidates_with_habit_track()`
- 无独立 `procedural_memory.jsonl`

### 六种 working memory 输入
1. `drive_broadcast`（通过 `DeliberationInput`，含 L1 sensing + L2 drive broadcast）
2. episodic（CognitiveMemoryStub retrieval via `recent_cognitive_memory_stub_traces()`）
3. semantic（SemanticMemory retrieval via `recent_semantic_memory()`）
4. procedural/habit（HabitSkill + HabitBias summary via `derive_habit_skills()`，backed by `habit_bias.jsonl`）
5. inherited prior（via `InheritedPriorRegistry.for_situation()`）
6. outcome trace（via `recent_learning_outcomes()` → `recent_response_history()` → `recent_cognitive_memory_stub_traces()` 三级 fallback）

### Anchor 分层
- 代码层一：`structural.py::apply_structural_anchor()`
- 代码 bundle 层：`AnchorPolicyBundle.admit_candidates()`（场景持有）
- 代码层二：`dynamic.py::apply_dynamic_anchor()` + habit track

### 继承先验
- `load_inherited_prior_registry()` 在加载时强制 same-scenario 校验（line 269）
- `inheritance_distillation/` 是独立顶层包，不在 `eva/` 也不在 `scenarios/`

---

## 5. 三件套模板（阶段二每节按此组织）

**【整合承诺】**：本节完整覆盖什么——第一句话说出承诺，不先说 v0.5。
**【框架 vs 场景】**：本层哪些归框架、哪些归场景，明确边界。
**【相对 v0.5 位移】**：与 v0.5 的实质性差异，行内轻量标注 `v0.5 §X / v0.6 §Y`；节末不附"v0.5 已说明..."段。

---

## 6. 对齐标记机制（阶段一每节必填）

每个 §N.N 节的整合承诺句末尾追加三选一标记：

| 标记 | 含义 | 处理方式 |
|---|---|---|
| `[✓ aligned]` | 承诺与当前代码实现一致 | 阶段二照常展开 |
| `[⏳ deferred: <说明>]` | 蓝图承诺接口/边界，具体实现显式延期 | 阶段二展开时必须说明延期理由 + 当前替代路径 |
| `[⚠ beyond impl]` | 承诺超出当前代码，需要架构师评审 | 阶段二不要展开此节，先停下 |

---

## 7. SVG 处理规则

蓝图不复刻 SVG。每节末附一行"延伸阅读 → `docs/eva-agent-full-implementation-v0.5.md` 对应节"。Part II 涉及具体场景装配若需新图，由架构师生成，不要自行绘制。

---

## 8. 阶段一输出格式（本轮第一次交付）

```markdown
## §1 引言：整合的落地基准
- §1.1 <标题> — <整合承诺句> [对齐标记]
- §1.2 <标题> — <整合承诺句> [对齐标记]
- §1.3 <标题> — <整合承诺句> [对齐标记]

## §2 总体架构
- §2.1 <标题> — <整合承诺句> [对齐标记]
...
```

每节一行，标题 + 整合承诺句 + 对齐标记。不展开任何节正文。

**关键约束**：
- §8.1 整合承诺句必须明确列出六种 working memory 输入来源的具体名称
- §6.7 整合承诺句必须包含 same-scenario only + distillation 独立包位置
- §7.4 整合承诺句必须反映代码的两套实体 + 场景 bundle（不是四套独立实现）

---

## 9. 阶段二执行规则

- 英文版先行，逐节展开，一节写完再下一节，不批量并行
- §6.2 程序记忆段必须忠实反映 Stage I 实现（backing = `habit_bias.jsonl`）
- §6.7 继承先验段必须忠实反映 same-scenario only + distillation 位置
- §8.1 选法 A："working memory 接收 1 路实时 channel（DeliberationInput，含 L1 sensing + L2 drive broadcast）+ 5 路 memory retrieval = 6 路输入"，并在节内用一句话说明"为什么算 6 路而不是 7 路"
- Part I 英文版全部完成后同步中文版（`-zh.md`），逐节翻译，保持标注和结构对齐
- 完成后 commit + push，只在聊天贴一条总结

---

## 10. 执行约束

- 不要修改 `architecture-overview.md`、`implementation-tracking.md`、`eva-framework-implementation.md`、`scenarios-SPEC.md`（已有明确职责）
- 不要引入新的公开文档文件名
- Part II / Part III / Part IV 本轮不动，只处理 Part I