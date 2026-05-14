# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Change intake

- **Change title**: Post-Stage-H review hardening for Crafter pressure semantics and outcome projection
- **Goal**: 在不改变 release authority、framework ownership 与 bounded compatibility release surface 的前提下，落实 Stage H review 中的 4 个 fix-now 项：收紧 Crafter dimension `pressure_type` 语义、消除 pressure-type lookup 的双重真相源、纠正 Crafter `task_progress` 计算、把 Crafter scalar `outcome_delta` 权重显式化；同时补充 Stage H follow-up 记录与 Crafter SPEC 说明。
- **Change type**: bugfix

## Ownership

- **Layer**: `l1_sensing`, `l2_drive`, `l3_deliberation`, `scenarios`
- **Canonical owner**: `scenarios/crafter/dimensions/__init__.py` 作为 Crafter dimension pressure-type owner；`eva/l2_drive/pressure_projection.py` 作为 framework pressure projection lookup owner；`scenarios/crafter/outcome_observers/compatibility.py` 作为 Crafter outcome projection owner；`tests/scenarios/crafter/` 作为 Crafter review-fix verification owner；`maintainer/development/stage-h-followups.md` 与 `scenarios/crafter/SPEC.md` 作为 review closeout record owner
- **Touched current files**: `maintainer/development/current-intake.md`, `maintainer/development/stage-h-followups.md`, `maintainer/development/stage-h-progress.md`, `scenarios/crafter/dimensions/__init__.py`, `eva/l2_drive/pressure_projection.py`, `scenarios/crafter/outcome_observers/compatibility.py`, `scenarios/crafter/SPEC.md`, `tests/scenarios/crafter/test_sensors.py`, `tests/scenarios/crafter/test_outcome_observers.py`
- **Owner class**: stable

## Realignment stage

- **Stage**: `other`
- **If other, why**: 这是 Stage H closeout 后的 review-driven hardening slice，不属于既有 R1 / R2 / R3 realignment，也不扩新 capability stage

## Boundary check

- **Affected contracts**:
  - scenario-owned dimension -> pressure-type registration contract
  - framework pressure projection lookup contract
  - Crafter outcome observer `task_progress` / scalar projection contract
  - Crafter scenario spec / maintainer follow-up record contract
- **Hard boundaries to preserve**:
  - heartbeat-first
  - default inhibition
  - anchor pre-generation
  - drive read-only
  - mediated release
  - append-only artifact discipline
- **Why this change does not widen a transitional owner**: 改动只是在已落地的 stable framework/scenario seam 上收紧语义一致性与文档口径，没有扩展 compatibility bridge、没有放松 mediator / release-token 边界，也没有把 Crafter-specific policy 反推回 framework

## Verification

- **Freeze tests**:
  - `tests/integration/test_main_runtime.py`
  - `tests/integration/test_linux_alignment.py`
  - `tests/integration/test_patrol_turn_flow.py`
  - `tests/integration/test_lifecycle_patrol_learning.py`
  - `tests/scenarios/crafter/test_sensors.py`
  - `tests/scenarios/crafter/test_outcome_observers.py`
  - `tests/scenarios/crafter/test_learning_integration.py`
- **Additional tests**:
  - `tests/l1_sensing/test_judgment.py`
- **Need full regression?** yes
- **Regression note**: 本 slice 需要先跑 Crafter targeted + framework freeze tests，再跑标准全量回归 `python -m unittest discover -s tests -t .`

## Docs sync

- **Docs to update**:
  - `docs/current-status.md`
  - `maintainer/development/roadmap.md`
  - related `phase-*.md`
- **Docs actually needed for this change**:
  - `maintainer/development/current-intake.md`
  - `maintainer/development/stage-h-followups.md`
  - `maintainer/development/stage-h-progress.md`
  - `scenarios/crafter/SPEC.md`

## Intake status

- 当前检查点：**post-Stage-H review hardening in progress**
- blocker 文档：`maintainer/development/stage-h-blockers.md`
- 下一 gate：**完成 4 个 review fix-now 项、补 follow-up 文档、通过 targeted + full regression，然后再做 commit / push**
