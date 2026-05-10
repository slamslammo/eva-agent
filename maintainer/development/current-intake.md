# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Change intake

- **Change title**: Phase A Slice A-5 anchor rules separation
- **Goal**: 在保持 Linux runtime 行为、candidate profile names、admission set、restriction reasons、drive impact defaults、release gating 语义、trace 语义、持久化 schema 与测试逻辑不变的前提下，把当前 anchor 里的 Linux-specific profiles、reasons、secondary gates 与 impact defaults 从 framework 侧抽离到 `scenarios/linux_runtime/anchors/`，并保留 framework 侧 `ActionDomain` / wrapper seam。
- **Change type**: refactor

## Ownership

- **Layer**: `anchor`
- **Canonical owner**: `eva/anchor/domain_restriction.py` 保留 framework `ActionDomain` / wrapper seam 与 structural anchor entrypoints；`scenarios/linux_runtime/anchors/` 成为 Linux candidate profiles、high-risk reasons、secondary gates 与 drive impact defaults 的 canonical owner
- **Touched current files**: `maintainer/development/current-intake.md`, `eva/anchor/domain_restriction.py`, `scenarios/linux_runtime/anchors/__init__.py`, `scenarios/linux_runtime/anchors/compatibility.py`, `maintainer/development/phase-a-refactor-progress.md`
- **Owner class**: stable

## Realignment stage

- **Stage**: `other`
- **If other, why**: 这是 `maintainer/development/v0.6-refactor-startup-instruction.md` 定义的 v0.6 Phase A Slice A-5，不属于既有 R1/R2/R3 realignment 收敛动作

## Boundary check

- **Affected contracts**: candidate profile ownership、admission ordering、restriction reasons、high-risk escalation gate、drive impact defaults、runtime-gate projection、structural anchor entrypoint behavior
- **Hard boundaries to preserve**:
  - heartbeat-first
  - instance validity
  - drive read-only
  - anchor pre-generation
  - mediated release
  - append-only artifact discipline
  - no behavior change
  - no persistent schema change
- **Why this change does not widen a transitional owner**: A-5 只迁移 Linux-specific anchor profiles、reasons、secondary gates 与 impact defaults，并保留 framework 侧 `ActionDomain`、schema materialization 与 structural anchor entrypoints；不改变 candidate action，不改变 release authority，也不把 scenario 提升为 reasoning / mediator 写 authority

## Verification

- **Freeze tests**: `tests/anchor/test_domain_restriction.py`, `tests/anchor/test_structural.py`, `tests/l3_deliberation/reasoning/test_candidates.py`, `tests/l3_deliberation/reasoning/test_conflict_detection.py`, `tests/l3_deliberation/reasoning/test_value.py`, `tests/l3_deliberation/peer_circuit/test_mediator.py`, `tests/integration/test_main_runtime.py`, `tests/integration/test_patrol_turn_flow.py`, `tests/integration/test_lifecycle_patrol_learning.py`, `tests/kernel/test_lifecycle.py`
- **Additional tests**: representative runtime trace verification against A-4 baseline summary (ticks/turns, patrol turn count, first patrol execution lane, top drive, deliberation/memory artifact counts)
- **Need full regression?** yes

## Docs sync

- **Docs to update**:
  - `maintainer/development/current-intake.md`
  - `maintainer/development/phase-a-refactor-progress.md`
- **Docs actually needed for this change**: `maintainer/development/current-intake.md` now; progress doc after A-5 verification

## Go / no-go

- **Can implementation start now?** yes
- **If no, what must be clarified first?**:

## Intake status

- 当前检查点：**Phase A Slice A-5 已完成；待 architect review checkpoint**
- 已完成验证：**targeted subset 99 passed；full regression 243 passed；representative runtime trace matched A-4 baseline summary**
- 下一 gate：**mandatory architect review checkpoint**
