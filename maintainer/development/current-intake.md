# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Intake status

- 当前进行中：**D-3 explicit L2 drive update semantics**

## Change intake

- **Change title**: D-3 explicit L2 drive update semantics
- **Goal**: 把 L2 drive update 从隐式算术收口为显式命名语义：decay、severity accumulation、threat bonus、curiosity recovery、curiosity suppression，并把 tunable 参数集中到 `drive_registry` 的明确配置面
- **Change type**: feature

## Ownership

- **Layer**: `l2_drive`
- **Canonical owner**:
  - `eva/l2_drive/drive_state.py`
  - `eva/l2_drive/drive_registry.py`
  - `eva/l2_drive/broadcast.py`
- **Touched current files**:
  - named drive update helpers, explicit policy config surface, drive tests, patrol integration assertions if needed
- **Owner class**: stable

## Realignment stage

- **Stage**: `other`
- **If other, why**: 当前属于 Stage D 的新能力切片，不是 Phase C realignment 收口

## Boundary check

- **Affected contracts**:
  - `update_drive_state()` policy surface
  - drive contributor semantics in broadcast/read-side tests
  - patrol-facing drive summary observability
- **Hard boundaries to preserve**:
  - heartbeat-first
  - default inhibition
  - anchor pre-generation
  - drive read-only
  - mediated release
  - append-only artifact discipline
- **Why this change does not widen a transitional owner**:
  - 仅在 canonical L2 owner 内把现有更新逻辑显式化，不新增新的 cross-layer policy shim，也不让下游写回 drive state

## Verification

- **Freeze tests**:
  - `python -m unittest tests.l2_drive.test_drive`
  - `python -m unittest tests.integration.test_patrol_turn_flow`
- **Additional tests**:
  - add one policy-surface assertion covering custom parameters or named helper effects
- **Need full regression?** yes

## Docs sync

- **Docs to update**:
  - `docs/eva-agent-full-implementation.md`
  - `docs/current-status.md`
  - `maintainer/development/current-intake.md`
  - related `phase-*.md`
- **Docs actually needed for this change**:
  - `maintainer/development/current-intake.md`
  - `docs/current-status.md`

## Go / no-go

- **Can implementation start now?** yes
- **If no, what must be clarified first?**:
