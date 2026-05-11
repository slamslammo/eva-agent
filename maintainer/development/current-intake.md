# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Change intake

- **Change title**: Stage G G-5 Linux scenario v0.6 alignment audit
- **Goal**: 对当前 shipped Linux runtime scenario 做一次 v0.6 对齐收口审计：检查并修正 `scenarios/linux_runtime/` 的 prior skills、outcome observers、anchor policy 与 persistence hierarchy / trace-output 之间的语义一致性，使其与 G-1 ~ G-4 已落地的 framework structures 完全对齐。当前 slice 不扩 Linux runtime 的任务处理能力，不新增 drives/sensors/actions，不改变 release authority；重点是把现有 Linux content 重新表述为 v0.6-correct 的 scenario，补齐必要的 provenance / persistence declaration / trace compatibility 文档与最小测试校验。
- **Change type**: realignment

## Ownership

- **Layer**: `scenarios/linux_runtime`
- **Canonical owner**: `scenarios/linux_runtime/SPEC.md` 作为 Linux scenario canonical spec；`scenarios/linux_runtime/__init__.py` 作为 bundle assembly owner；`stability_metrics/` 作为 trace validation consumer（如果需要 smoke）
- **Touched current files**: `scenarios/linux_runtime/SPEC.md`, `scenarios/linux_runtime/__init__.py`, `scenarios/linux_runtime/prior_skills/`, `scenarios/linux_runtime/outcome_observers/`, `scenarios/linux_runtime/anchors/`, tests under `tests/integration/`, `tests/l3_deliberation/`, `tests/stability_metrics/`（if needed）; 预计同步 `maintainer/development/current-intake.md` 与 `maintainer/development/stage-g-progress.md`
- **Owner class**: stable scenario alignment

## Realignment stage

- **Stage**: `other`
- **If other, why**: 这是 Stage G `G-5` alignment audit，属于已落地 scenario 的语义收口，不是既有 R1/R2/R3 realignment 分层收敛动作

## Boundary check

- **Affected contracts**:
  - Linux scenario SPEC canonicalization
  - prior skill provenance / registry split semantics
  - outcome observer vector semantics
  - persistence hierarchy declaration in scenario docs
  - trace compatibility for stability metrics
- **Hard boundaries to preserve**:
  - heartbeat-first
  - default inhibition
  - anchor pre-generation
  - drive read-only
  - mediated release
  - append-only artifact discipline
- **Why this change does not widen a transitional owner**: G-5 只收紧并澄清 Linux scenario 语义，不接 Crafter，不引入 Linux task handling，不改变 framework owner 权限，只把现有内容与 G-1~G-4 的框架事实对齐

## Verification

- **Freeze tests**:
  - `tests/integration/test_patrol_turn_flow.py`
  - `tests/integration/test_lifecycle_patrol_learning.py`
  - `tests/l3_deliberation/reasoning/test_value.py`
  - `tests/l3_deliberation/memory/test_working_memory.py`（if naming differs, current working-memory tests)
  - `tests/stability_metrics/test_metrics.py`
- **Additional tests**:
  - Linux scenario SPEC assertions for provenance and persistence declaration consistency
  - trace smoke assertions against `stability_metrics`
  - any minimal regression needed to prove no user-visible scope change
- **Need full regression?** yes

## Docs sync

- **Docs to update**:
  - `maintainer/development/current-intake.md`
  - `maintainer/development/stage-g-progress.md`
  - `scenarios/linux_runtime/SPEC.md`
  - `docs/scenarios-SPEC.md` only if cross-scenario contract wording needs an explicit G-5 note
- **Docs actually needed for this change**:
  - `maintainer/development/current-intake.md`
  - `maintainer/development/stage-g-progress.md`
  - `scenarios/linux_runtime/SPEC.md`

## Go / no-go

- **Can implementation start now?** yes
- **If no, what must be clarified first?**:

## Intake status

- 当前检查点：**G-5 Linux scenario v0.6 alignment audit 已完成实现与 full regression**
- 已完成验证：**targeted G-5 subset 通过；Linux runtime trace smoke 通过；full regression `251 tests, OK`；Linux scenario SPEC 已补齐 Stage G 对齐事实与 persistence / outcome / provenance / stability 说明**
- 下一 gate：**Stage G exit review**
