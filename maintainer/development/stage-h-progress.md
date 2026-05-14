# Stage H 进展

本文档记录 **Stage H：Crafter scenario landing** 的进展结论。

## 1. 当前状态

- 日期：2026-05-13
- 阶段状态：**Stage H 已完成 H-0 ~ H-5 与 closeout**
- 判断：Crafter 现已通过与 Linux 相同的 generic framework seam 完成 bounded end-to-end runtime integration。H-0F 收口后的 scenario-owned dimension metadata seam 保持成立；H-5 进一步补齐了 runner-owned `agent_observation` 注入、wrapper-backed action execution、bounded episode reset、Crafter runtime integration test 与 stability-metrics compatibility。Linux 行为保持原有回归覆盖；Stage H 本地 closeout 已完成。

## 2. 当前前置条件

- 历史 `Phase A / Phase B / Phase C` 叙事保持保留，不回写重命名
- Stage G 已完成本地实现、full regression 与 exit review closeout
- `crafter_test/docs/phase-c-handoff.md` 作为 Crafter handoff 的历史 gate source 已被 Stage H 落地结果吸收，不再阻塞 closeout
- `docs/scenarios-SPEC.md` 与 `scenarios/crafter/SPEC.md` 现已同步到 H-5 后的真实 cross-scenario / scenario-specific contract

## 3. Stage H 目标

Stage H 用于验证：
- Stage G 已落地 framework abstractions 是否足以承接第二个 scenario
- Crafter 能否在保持 release authority 与 framework ownership 边界不变的前提下完成 scenario landing
- multi-dimensional outcome、skill provenance、PersistenceHierarchy、stability_metrics trace consumption 能否在 Crafter 世界中被真实行使

Stage H 实际完成顺序：
- `H-0` contract migration and skeleton
- `H-1` drive preset and sensor preset
- `H-2` action set / anchor policy / outcome observers
- `H-3` persistence hierarchy and outcome integration
- `H-4` prior skill set
- `H-0F` judgment-layer de-Linuxification（authorized framework follow-up）
- `H-5` runner / end-to-end validation / closeout

## 4. 当前 planning activation 完成项

当前已完成：
- 将 Stage H startup instruction、progress、blockers、roadmap、scenario specs 收口到同一口径
- 完成 Crafter scenario 从 wrapper skeleton 到 end-to-end runtime path 的全部 landed slices
- 用第二 scenario 验证 Stage G framework/scenario 边界的 sufficiency

## 4.1 H-0 完成情况

### 已完成内容
- 已新建 `scenarios/crafter/` skeleton，并补齐 wrapper / observation / action surface baseline
- 已落地 framework-agnostic Crafter wrapper：
  - `scenarios/crafter/wrapper/env_wrapper.py`
  - `scenarios/crafter/wrapper/observation.py`
  - `scenarios/crafter/wrapper/semantic_local_view.py`
  - `scenarios/crafter/wrapper/evaluator_surface.py`
- 已落地 17-action enum / metadata surface：
  - `scenarios/crafter/actions/registry.py`
- 已新增 `tests/scenarios/crafter/test_wrapper_smoke.py`

### 验证结果
- wrapper smoke：通过（Crafter 未安装时保留 skip）
- freeze tests：通过
- full regression：通过

## 4.2 H-1 完成情况

### 已完成内容
- 已落地 Crafter 5-drive family：`metabolic / safety / recovery / acquisition / capability`
- 已落地 Crafter sensor bundle：
  - `scenarios/crafter/sensors/avatar_state.py`
  - `scenarios/crafter/sensors/inventory.py`
  - `scenarios/crafter/sensors/local_view.py`
- `activate_crafter_scenario()` 已注册 Crafter drive preset 与 sensor provider bundle
- 已新增：
  - `tests/scenarios/crafter/test_drive_preset.py`
  - `tests/scenarios/crafter/test_sensors.py`
  - `tests/scenarios/crafter/test_fairness_contract.py`

### 验证结果
- Crafter H-1 targeted tests：通过
- freeze tests：通过
- full regression：通过

## 4.3 H-2 完成情况

### 已完成内容
- 已落地 Crafter action / anchor / outcome bundles：
  - `scenarios/crafter/actions/compatibility.py`
  - `scenarios/crafter/anchors/policy.py`
  - `scenarios/crafter/outcome_observers/compatibility.py`
- 已验证 Crafter anchor admission 进入 framework 的 pre-generative `ActionDomain` seam
- 已验证 Crafter outcome interpretation 可以产出 `OutcomeVector`
- 已新增：
  - `tests/scenarios/crafter/test_actions.py`
  - `tests/scenarios/crafter/test_anchors.py`
  - `tests/scenarios/crafter/test_outcome_observers.py`

### 验证结果
- Crafter H-2 targeted tests：通过
- freeze tests：通过
- full regression：通过

## 4.4 H-3 完成情况

### 已完成内容
- 已落地 Crafter persistence hierarchy：
  - `scenarios/crafter/persistence/hierarchy.py`
  - `scenarios/crafter/persistence/__init__.py`
- activation path 已切到 Crafter-specific hierarchy
- 已验证 Crafter `OutcomeVector` 的多维字段可保留到 learning artifact
- 已新增：
  - `tests/scenarios/crafter/test_persistence_hierarchy.py`
  - `tests/scenarios/crafter/test_learning_integration.py`

### 验证结果
- Crafter H-3 targeted tests：通过
- freeze tests：通过
- full regression：通过

## 4.5 H-4 完成情况

### 已完成内容
- 已落地 Crafter prior-skill surface：
  - `scenarios/crafter/prior_skills/compatibility.py`
  - `scenarios/crafter/prior_skills/__init__.py`
- 已验证 Crafter prior registry 生成带 `SkillProvenance` 的 scenario prior records
- 已验证 survival / resource priors 投影到既有 `observe_first / stabilize_first / escalate_first` candidate-profile vocabulary
- 已新增：
  - `tests/scenarios/crafter/test_prior_skills.py`
  - `tests/scenarios/crafter/test_skill_provenance.py`
  - `tests/scenarios/crafter/test_prior_guided_candidates.py`

### 验证结果
- Crafter H-4 targeted tests：通过
- freeze tests：通过
- full regression：通过

## 4.6 H-0F（authorized follow-up）

### 已完成内容
- 去除了 `eva/l1_sensing/` judgment / sensing seam 与 `eva/l2_drive/pressure_projection.py` 中的 Linux-shaped dimension-name coupling
- 建立 scenario-owned dimension spec 注册与消费路径
- Linux-specific rate context / dimension content 已迁回 `scenarios/linux_runtime/`
- Crafter 与 Linux 现都通过同一 dimension seam 进入 snapshot → pressure projection 路径

### 验证结果
- targeted tests：通过
- scoped seam grep：无残余 Linux 维度字面量
- full regression：通过

## 4.7 H-5 完成情况

### 已完成内容
- 已新增 Crafter canonical runner：
  - `runners/run_crafter.py`
- 已在 framework 补齐最小 generic seam：
  - `eva/l1_sensing/sensing.py`
  - `eva/l1_sensing/patrol.py`
  - `eva/kernel/main.py`
  - `eva/kernel/lifecycle.py`
- 现支持 runner-owned `agent_observation` 通过 shared-facts seam 进入 patrol sensing path
- 已把 Crafter action execution 从 synthetic payload 收口为 wrapper-backed execution，并把 Crafter delta 字段透传到 response history / response summary：
  - `achievement_delta`
  - `inventory_delta`
  - `life_delta`
  - `visible_threat_count`
- 已实现 bounded episode reset 语义：Crafter env `done=True` 时立即 reset，下一个 patrol 读取新 episode observation
- 已新增 install-independent H-5 runtime validation：
  - `tests/integration/test_crafter_runtime.py`
- 已补充 Crafter targeted tests：
  - `tests/scenarios/crafter/test_actions.py`
  - `tests/scenarios/crafter/test_sensors.py`
- 已把 Crafter runtime 接到 `tests/stability_metrics/test_cli_smoke.py` 的 optional live smoke path；未安装 `crafter` 时以 skip 收口

### 当前边界
- H-5 仍保持 bounded compatibility vocabulary，不扩新 L3 release surface
- Crafter live runtime 仍依赖本机可安装 `crafter` 包；安装不可用时只跳过 live smoke，不影响 install-independent regression
- generic framework 只增加 shared-facts injection 与 action-runtime delegation，不承接 Crafter-specific policy

### 验证结果
- `python -m unittest tests.scenarios.crafter.test_actions`：通过
- `python -m unittest tests.scenarios.crafter.test_sensors`：通过
- `python -m unittest tests.integration.test_crafter_runtime`：通过
- `python -m unittest tests.integration.test_main_runtime`：通过
- `python -m unittest tests.integration.test_linux_alignment`：通过
- `python -m unittest tests.integration.test_patrol_turn_flow`：通过
- `python -m unittest tests.integration.test_lifecycle_patrol_learning`：通过
- `python -m unittest tests.stability_metrics.test_cli_smoke`：通过（Crafter live smoke 当前本机 `skipped=1`）
- full regression：`python -m unittest discover -s tests -t .` → `285 tests`, `OK`, `skipped=2`

## 5. 当前实现前 gate

Stage H 现已完成所有原定前置 gate：
- Stage G exit review 已明确落账
- Stage H startup instruction / progress / blockers / roadmap 口径已统一
- scenario specs 已同步到 H-5 landed contract
- `current-intake.md` 已滚动到 H-5 closeout

## 6. 下一 gate

- **回到 intake-first 纪律下评估 post-Stage-H 下一 slice**
- 已启动一个 review-driven hardening slice，用于收紧 Crafter `pressure_type` 语义、复用 framework pressure-type lookup、纠正 `task_progress` 投影，并把 Crafter scalar outcome 权重显式化；非阻塞 follow-up 记录见 `maintainer/development/stage-h-followups.md`
