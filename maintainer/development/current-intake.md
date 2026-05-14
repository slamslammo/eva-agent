# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Change intake

- **Change title**: Stage H H-5 Crafter runner / end-to-end validation / closeout
- **Goal**: 在保持 release authority、framework ownership 与 bounded compatibility release surface 不变的前提下，完成 `runners/run_crafter.py`、runner-owned shared-facts 注入 seam、wrapper-backed Crafter action execution、bounded episode reset、install-independent end-to-end validation，以及 Stage H closeout 文档同步。
- **Change type**: feature

## Ownership

- **Layer**: `kernel`, `l1_sensing`, `l3_deliberation`, `scenarios`
- **Canonical owner**: `eva/kernel/main.py` 与 `eva/kernel/lifecycle.py` 作为 generic runtime hook owner；`eva/l1_sensing/sensing.py` 与 `eva/l1_sensing/patrol.py` 作为 sensing shared-facts seam owner；`eva/l3_deliberation/tool_edge/history.py` 作为 bounded response-history payload owner；`scenarios/crafter/actions/compatibility.py` 与 `runners/run_crafter.py` 作为 Crafter runtime integration owner；`scenarios/crafter/wrapper/` 继续作为 env wrapper owner；`maintainer/development/stage-h-progress.md` 与 `scenarios/crafter/SPEC.md` 作为 H-5 closeout record owner
- **Touched current files**: `eva/l1_sensing/sensing.py`, `eva/l1_sensing/patrol.py`, `eva/kernel/main.py`, `eva/kernel/lifecycle.py`, `eva/l3_deliberation/tool_edge/history.py`, `scenarios/crafter/actions/compatibility.py`, `runners/run_crafter.py`, `tests/scenarios/crafter/test_actions.py`, `tests/scenarios/crafter/test_sensors.py`, `tests/integration/test_crafter_runtime.py`, `tests/stability_metrics/test_cli_smoke.py`, `docs/current-status.md`, `docs/scenarios-SPEC.md`, `scenarios/crafter/SPEC.md`, `maintainer/development/current-intake.md`, `maintainer/development/stage-h-progress.md`, `maintainer/development/roadmap.md`
- **Owner class**: stable framework follow-up

## Realignment stage

- **Stage**: `other`
- **If other, why**: 这是 Stage H 的 runner / validation / closeout slice，不属于既有 R1 / R2 / R3 realignment，也不是新的 framework capability stage

## Boundary check

- **Affected contracts**:
  - runner -> runtime extra shared facts injection contract
  - patrol sensing shared-facts merge contract
  - scenario-owned Crafter execution payload contract
  - response history / learning outcome Crafter delta propagation contract
  - Crafter runner / stability-metrics end-to-end validation contract
- **Hard boundaries to preserve**:
  - heartbeat-first
  - default inhibition
  - anchor pre-generation
  - drive read-only
  - mediated release
  - append-only artifact discipline
- **Why this change does not widen a transitional owner**: H-5 只增加一个 generic runner-owned shared-facts seam，并把 Crafter action execution 接到既有 wrapper 与 response-history contract；没有放松 mediator / release-token / compatibility bridge 边界，也没有把 Crafter-specific scheduling、release authority 或 direct side-effect control 推回 `eva/`

## Verification

- **Freeze tests**:
  - `tests/integration/test_main_runtime.py`
  - `tests/integration/test_linux_alignment.py`
  - `tests/integration/test_patrol_turn_flow.py`
  - `tests/integration/test_lifecycle_patrol_learning.py`
  - `tests/stability_metrics/test_cli_smoke.py`
  - all landed Crafter tests under `tests/scenarios/crafter/`
- **Additional tests**:
  - `tests.integration.test_crafter_runtime`
  - `tests.scenarios.crafter.test_actions`
  - `tests.scenarios.crafter.test_sensors`
- **Need full regression?** yes
- **Regression note**: targeted suites passed；标准全量回归 `python -m unittest discover -s tests -t .` 已通过，结果为 `285 tests`, `OK`, `skipped=2`。其中可选 live Crafter smoke 继续保持 skip-based 行为，在本机未安装 `crafter` 时不会伪造通过。

## Docs sync

- **Docs to update**:
  - `docs/current-status.md`
  - `docs/scenarios-SPEC.md`
  - `scenarios/crafter/SPEC.md`
  - `maintainer/development/current-intake.md`
  - `maintainer/development/stage-h-progress.md`
  - `maintainer/development/roadmap.md`
- **Docs actually needed for this change**:
  - `docs/current-status.md`
  - `docs/scenarios-SPEC.md`
  - `scenarios/crafter/SPEC.md`
  - `maintainer/development/current-intake.md`
  - `maintainer/development/stage-h-progress.md`
  - `maintainer/development/roadmap.md`

## Intake status

- 当前检查点：**H-5 已完成；Stage H closeout complete**
- blocker 文档：`maintainer/development/stage-h-blockers.md`
- 下一 gate：**回到 intake-first 纪律下评估 post-Stage-H 下一 slice**
