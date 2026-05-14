# Stage G 进展

本文档记录 **Stage G：v0.6 capability landing** 的进展结论。

## 1. 当前状态

- 日期：2026-05-13
- 阶段状态：**Stage G 全部 G-0 ~ G-5 slices 已完成实现与本地回归；已按当前 maintainer 判断视为 exit review 通过并完成签收**
- 判断：Stage G 已完成 residual clearance、OutcomeVector 追加字段、三类 skill-source owner、explicit persistence hierarchy、独立 stability metrics 模块，以及 Linux scenario v0.6 alignment audit。Linux scenario SPEC 已收口为 G-5 对齐事实，trace smoke 与 full regression 已通过，当前 full regression 为 `251 tests, OK`。按当前用户确认，Stage G exit review 现作为已通过处理；后续 Crafter 相关工作转入 Stage H。

## 2. 当前已建立的前置条件

- 已决定保留历史 `Phase A / Phase B / Phase C` 编号与完成叙事，不回写重命名
- 已决定不归档旧 `phase-b-progress.md`，以保留既有 L3 历史基线证据链
- 新的 v0.6 capability landing 规划已独立命名为 `Stage G`
- `phase-a-residuals.md` 已建立，用于承接 Phase A closeout review 中识别出的 residuals
- `stage-g-v0.6-capability-landing-startup-instruction.md` 已成为当前 Stage G 的 maintainer 启动入口

## 3. 当前阶段目标

Stage G 计划顺序为：
- `G-0` residual clearance
- `G-1` multi-dimensional outcome schema
- `G-2` three-category skill separation
- `G-3` persistence target hierarchy
- `G-4` architecture-neutral stability metrics
- `G-5` Linux scenario v0.6 alignment audit

其中当前唯一已授权进入的直接下一步是：
- **G-0：清理 Phase A residuals**

## 4. G-0 完成情况

### 已完成内容
- `eva/scenario_bundle.py` 不再 fallback import `scenarios.linux_runtime`
- 未显式 activate scenario 时，scenario-dependent framework seam 现在会抛出明确 `RuntimeError`
- `eva/anchor/domain_restriction.py` 已移除 import-time scenario-shaped constant binding 与 framework-level re-export
- `eva/l3_deliberation/reasoning/candidate_generation.py`、`conflict_detection.py`、`value_judgment.py` 已切到 point-of-use anchor vocabulary lookup
- `eva/l3_deliberation/tool_edge/tool_registry.py` 已移除 import-time action constant binding，改为 lazy `get_action_constants()`
- `tool_edge` 相关 public/test import 已调整到显式 activation + scenario-owned constants / lazy lookup 语义
- CLI integration tests 已从 `python -m eva.kernel.main` 切到显式 activation 的 `python -m runners.run_linux`

### 验证结果
- targeted G-0 subset：通过
- framework grep `from scenarios|import scenarios`：无命中
- full regression：`243 tests, OK`

## 5. G-1 完成情况

### 已完成内容
- `eva/l3_deliberation/contracts.py` 已新增 canonical `OutcomeVector`
- `eva/l3_deliberation/peer_circuit/rpe.py` 的 `LearningOutcomeRecord` 已追加 `outcome_vector`
- `evaluate_response_outcome(...)` 已扩为返回 scalar compatibility fields + canonical vector
- `scenarios/linux_runtime/outcome_observers/compatibility.py` 已为 Linux runtime 落地最小 vector 语义：
  - 通过 `viability_delta.level_1` 保持既有 scalar learning path
  - 同时追加 `uncertainty` / `risk_delta` 等当前可合理表达的最小字段
  - 不伪造 task / capability 维度
- 相关 tests 已更新，验证 append-only record 追加字段而不破坏旧断言语义

### 验证结果
- targeted G-1 subset：通过
- broader G-1 subset：通过
- full regression：`243 tests, OK`

## 6. G-2 完成情况

### 已完成内容
- `eva/skills/__init__.py` 已从 skeleton 升级为三类 registry surface：
  - `PriorSkillRegistry`
  - `HabitSkillRegistry`
  - `InheritedPriorRegistry`（placeholder）
- `SkillProvenance`、`PriorSkillRecord`、`HabitSkillRecord` 已落地
- `eva/l3_deliberation/memory/skill_library.py` 已接到 registry surface，同时保留现有 read-side compatibility facade：
  - working-memory 仍读取 `HabitSkillSummary` / `HabitBiasSummary`
  - 但 habit skill 已能携带 provenance
  - prior registry 已能暴露 scenario-owned candidate-profile policy
- Linux skill path 当前保持行为兼容，不扩 capability，不改变 release authority
- 新增 tests 验证 prior / habit / inherited 三类 owner surface 与 placeholder 语义

### 验证结果
- targeted G-2 subset：通过
- broader G-2 subset：通过
- full regression：`246 tests, OK`

## 7. G-3 完成情况

### 已完成内容
- `eva/persistence_targets/__init__.py` 已从 skeleton 升级为 explicit hierarchy contract：
  - `PersistenceTarget`
  - `PersistenceHierarchy`
  - registration / lookup surface
- Linux runtime activation 时已注册最小 hierarchy：
  - Level 1: `substrate_instance`
  - Level 4: `runtime_artifact_substrate`
- `tests/persistence_targets/test_hierarchy.py` 已新增，验证：
  - Level 1 / 4 activation
  - failed / at-risk projection
  - local unrecoverable failure authorization rule
- `eva/l1_sensing/judgment.py` 的 runtime integrity evidence 已追加最小 `persistence_hierarchy` 投影，用于表达 `instance_invalid` / `runtime_files_missing` / `runtime_not_writable` 对应的 failed level baseline
- `eva/kernel/lifecycle.py` 已引入 hierarchy helper 与 registration-safe lookup，但保持既有 B0 `runtime_gate_context` 最小输入面不变，不把新 hierarchy 直接塞入旧 minimal contract

### 验证结果
- targeted G-3 subset：通过
- full regression：`246 tests, OK`

## 8. G-4 完成情况

### 已完成内容
- `stability_metrics/` 已从预留顶层位置收口为独立、architecture-neutral 的 trace metrics module
- `stability_metrics/trace_io.py` 已自持 trace 读取与时间解析能力，不再依赖 `eva/` 或 `scenarios/` 内部实现
- `stability_metrics/metrics.py` 已落地七类核心指标计算：
  - constraint violation rate
  - continuity preservation score
  - useful progress under constraint
  - recovery success rate
  - mean time to recovery
  - recovery path entropy
  - cost ratio
- CLI smoke 路径已验证可从 runtime trace 产出 `stability_profile.json`
- Linux runtime trace 当前可被 `stability_metrics` 直接消费，不要求导入 framework runtime state

### 验证结果
- targeted G-4 subset：通过
- CLI smoke：通过
- framework/scenario import grep：`stability_metrics/` 无 `import eva` / `from eva` / `import scenarios` / `from scenarios`
- full regression：`251 tests, OK`

## 9. G-5 完成情况

### 已完成内容
- `scenarios/linux_runtime/SPEC.md` 已补齐 Stage G 对齐信息，明确：
  - Outcome observer vector-compatible semantics
  - prior / habit provenance metadata
  - persistence hierarchy Level 1 / Level 4 alignment
  - stability_metrics trace compatibility
- 新增 G-5 alignment test，验证 Linux runtime bundle 与 Stage G 框架事实保持一致
- Linux runtime trace smoke 可正常产出并被 `stability_metrics` 消费
- 现有 Linux runtime 行为未扩 scope、未新增 task handling、未改变 release authority

### 验证结果
- targeted G-5 subset：通过
- full regression：`251 tests, OK`

## 10. 阶段出口状态

Stage G 当前已全部完成实现、本地回归与 maintainer exit review closeout，可视为已签收完成；后续工作转入 Stage H planning / implementation track。

## 11. 当前文档入口

- Stage G 启动指令：`maintainer/development/stage-g-v0.6-capability-landing-startup-instruction.md`
- Phase A residual handoff：`maintainer/development/phase-a-residuals.md`
- 当前总路线入口：`maintainer/development/roadmap.md`
- 当前执行 intake：`maintainer/development/current-intake.md`
