# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Slice I-5 — Crafter runtime readiness audit and Stage I exit

### Status
- completed locally
- Stage I exit package prepared

### Change intake
- **Change title**: Slice I-5 — Crafter runtime readiness audit and Stage I exit
- **Goal**:
  - Verify that Stage I now forms one coherent Crafter runtime chain rather than isolated feature landings, and prepare the Stage I exit package.
- **Change type**: feature / docs-sync / audit / exit-prep

### Ownership
- **Layer**:
  - `l3_deliberation` read-side audit / Stage-level runtime validation / docs and review closure
- **Canonical owner**:
  - `maintainer/architecture/memory-decision-integration-audit.md` for the integration-table audit
  - `maintainer/development/stage-i-progress.md` for slice and exit tracking
  - `maintainer/development/stage-i-i5-review-package.md` for the architect-facing close package
  - existing framework/scenario docs only if the audit exposes slice-scope drift
- **Touched current files**:
  - `maintainer/development/current-intake.md`
  - `maintainer/development/stage-i-progress.md`
  - new `maintainer/architecture/memory-decision-integration-audit.md`
  - new `maintainer/development/stage-i-i5-review-package.md`
  - `docs/eva-framework-implementation.md`
  - `scenarios/crafter/SPEC.md`
  - `scenarios/linux_runtime/SPEC.md`
  - `tests/integration/` and targeted Stage-I suites only if the audit reveals a concrete missing coverage or narrow implementation gap
- **Owner class**: stable

### Realignment stage
- **Stage**: other
- **If other, why**:
  - This is a Stage I exit-audit slice, not an R1/R2/R3 codebase realignment pass.

### Boundary check
- **Affected contracts**:
  - Stage I runtime-readiness judgment
  - memory-decision integration table interpretation
  - append-only trace schema preservation
  - Linux behavior-preservation evidence
- **Hard boundaries to preserve**:
  - heartbeat-first
  - default inhibition
  - anchor pre-generation
  - drive read-only
  - mediated release
  - append-only artifact discipline
- **Why this change does not widen a transitional owner**:
  - I-5 is expected to audit, verify, and close Stage I rather than expanding scenario or framework responsibilities. Any code change discovered by the audit must remain narrow, justified, and within the existing Stage I whitelist.

### Verification
- **Freeze tests**:
  - `tests/integration/test_main_runtime.py`
  - `tests/integration/test_lifecycle_patrol_learning.py`
  - `tests/integration/test_linux_alignment.py`
  - `tests/integration/test_crafter_runtime.py`
  - `tests/l3_deliberation/memory/test_skill_library.py`
  - `tests/l3_deliberation/reasoning/test_working_memory.py`
  - `tests/l3_deliberation/reasoning/test_value.py`
  - `tests/l3_deliberation/peer_circuit/test_habit_track.py`
  - `tests/scenarios/crafter/test_prior_skills.py`
  - `tests/scenarios/crafter/test_prior_guided_candidates.py`
  - `tests/inheritance_distillation/`
  - `tests/stability_metrics/test_metrics.py`
  - `tests/stability_metrics/test_cli_smoke.py`
- **Additional tests**:
  - new targeted audit/trace-integrity coverage only if I-5 adds executable verification beyond documentation
- **Need full regression?** yes

### Docs sync
- **Docs to update**:
  - `docs/eva-agent-full-implementation.md`
  - `docs/current-status.md`
  - `maintainer/development/development-standards.md`
  - `maintainer/development/module-organization-contract.md`
  - `maintainer/development/codebase-realignment-plan.md`
  - `maintainer/development/roadmap.md`
  - related `phase-*.md`
- **Docs actually needed for this change**:
  - `maintainer/development/stage-i-progress.md`
  - new `maintainer/architecture/memory-decision-integration-audit.md`
  - new `maintainer/development/stage-i-i5-review-package.md`
  - `docs/eva-framework-implementation.md` only if the audit finds Stage-I-scope drift
  - `scenarios/crafter/SPEC.md` only if the audit finds Stage-I-scope drift
  - `scenarios/linux_runtime/SPEC.md` only if the audit finds Stage-I-scope drift

### Go / no-go
- **Can implementation start now?** yes
- **If no, what must be clarified first?**:
