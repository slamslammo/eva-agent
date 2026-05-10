# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Change intake

- **Change title**: Phase A Slice A-8 documentation migration / archive / boundary sync
- **Goal**: 在不改动 runtime behavior、schema、tests 与 release authority 的前提下，把公开与维护文档更新到 Phase A 已落地的 framework/scenario 边界：`docs/eva-framework-implementation.md` 反映 framework canonical owner，`docs/scenarios-SPEC.md` 反映 scenario contract，新增 `scenarios/linux_runtime/SPEC.md` 反映 Linux scenario canonical owner，`docs/current-status.md` 更新对外入口，`maintainer/development/module-organization-contract.md` 更新 maintainer canonical structure，同时将旧的混合实现文档归档。
- **Change type**: docs

## Ownership

- **Layer**: cross-layer documentation / maintainer boundary contract
- **Canonical owner**: public docs 反映已落地的 framework / scenario / runner boundary；maintainer docs 反映当前 canonical module organization；archive 保留旧混合文档作为历史参考，不再充当主线
- **Touched current files**: `maintainer/development/current-intake.md`, `docs/eva-framework-implementation.md`, `docs/scenarios-SPEC.md`, `docs/current-status.md`, `docs/eva-agent-full-implementation.md`, `maintainer/development/module-organization-contract.md`, `maintainer/development/phase-a-refactor-progress.md`；预计新增 `scenarios/linux_runtime/SPEC.md` 与 `docs/archive/eva-agent-full-implementation-v0.5.md`
- **Owner class**: stable docs sync

## Realignment stage

- **Stage**: `other`
- **If other, why**: 这是 `maintainer/development/v0.6-refactor-startup-instruction.md` 定义的 v0.6 Phase A Slice A-8，不属于既有 R1/R2/R3 realignment 收敛动作

## Boundary check

- **Affected contracts**: framework/scenario 文档边界、runner canonical entry 描述、public status 入口、maintainer module organization canonical owner、archive path for old mixed doc
- **Hard boundaries to preserve**:
  - document landed code reality only
  - no behavior change
  - no persistent schema change
  - no test logic change
  - public docs remain English
  - maintainer docs may remain Chinese
  - archived mixed doc must not remain the canonical reference
- **Why this change does not widen a transitional owner**: A-8 只同步文档到 A-1~A-7 已落地边界，不新增 capability、不回退到旧 mixed owner，也不把 Phase B 设计写成已实现事实

## Verification

- **Freeze checks**: `docs/eva-framework-implementation.md`, `docs/scenarios-SPEC.md`, `scenarios/linux_runtime/SPEC.md`, `docs/current-status.md`, `maintainer/development/module-organization-contract.md`, `docs/archive/eva-agent-full-implementation-v0.5.md`, `docs/eva-agent-full-implementation.md`
- **Additional checks**: path/reference consistency across public docs；archive file exists；current-status no longer points to the mixed doc as canonical
- **Need full regression?** no

## Docs sync

- **Docs to update**:
  - `maintainer/development/current-intake.md`
  - `maintainer/development/phase-a-refactor-progress.md`
  - `docs/eva-framework-implementation.md`
  - `docs/scenarios-SPEC.md`
  - `scenarios/linux_runtime/SPEC.md`
  - `docs/current-status.md`
  - `docs/eva-agent-full-implementation.md`
  - `maintainer/development/module-organization-contract.md`
- **Docs actually needed for this change**: all of the above

## Go / no-go

- **Can implementation start now?** yes
- **If no, what must be clarified first?**:

## Intake status

- 当前检查点：**Phase A Slice A-8 已完成；文档 canonical owner、archive 与 public entry 已同步到已落地代码边界**
- 已完成验证：**archive file 已创建；public docs reference consistency 已检查；`docs/current-status.md` 已切离 mixed doc canonical reference**
- 下一 gate：**准备 Phase A A-1~A-8 完整 review 摘要**
