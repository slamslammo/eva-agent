# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Round 1.B-3 — Semantic Memory → Drive Impact Overlay (W5)

### Status
- **implementation complete** — sub-slices A → B+C → D landed
- 357 / 357 tests pass
- Stage I follow-up #2 resolved
- pending **G3-3B architect review** before moving to Round 1.C
- progress: `maintainer/development/round-1b-3-progress.md`

### Round 1.B closeout summary
With Round 1.B-3 landing, **Round 1.B is structurally complete**:
- 1.B-1 (framework de-Linuxification): 6 framework files made scenario-neutral
- 1.B-2 (Crafter exploration drive): v0.6.1 §4 landed for Crafter
- 1.B-3 (semantic → drive overlay): Stage I followup #2 closed
- Cumulative regression: 357 / 357 tests (was 285 before Round 1.A; +72 new tests over Round 1.A/B)
- Zero Linux scenario behavioral regressions
- Round 1.D long-run tuning queue tracked in progress docs

### Change intake
- **Change title**: Round 1.B-3 — wire semantic memory into the drive_impact_schema overlay path (bounded safe-path implementation of v0.6.1 §2.5 / Stage I followup #2)
- **Goal**:
  - Extend the existing `_effective_drive_impact_schema` blend pipeline with a new `semantic_impact_overlay` step that consumes the same `semantic_patterns` already in `working_memory_context`.
  - Bounded contribution: `MAX_SEMANTIC_OVERLAY_BLEND = 0.15`, `MIN_SEMANTIC_OVERLAY_CONFIDENCE = 0.7`.
  - Semantic memory begins shaping which drives a candidate is expected to satisfy — not just whether to pick it.
- **Change type**: framework capability landing (single file, single function added + one function extended)
- **Companion directive**: `maintainer/development/round-1b-3-semantic-drive-impact-overlay-startup-instruction.md`

### Ownership
- **Layer**: `eva/l3_deliberation/reasoning/value_judgment.py` only
- **Owner class**: stable framework owner — extending an existing canonical seam

### Realignment stage
- Not a realignment; capability landing.

### Boundary check
- **Affected contracts**:
  - `_effective_drive_impact_schema` returns the same shape but may now emit `"semantic_impact_overlay"` reason tag
  - Candidates may receive slightly amplified positive drive impacts when matching high-confidence semantic patterns
- **Hard boundaries preserved**:
  - drive read-only broadcast (overlay touches impact_schema only)
  - existing `_semantic_pattern_bias` learning_bias path unchanged
  - existing `build_learned_impact_overlay` path unchanged
  - negative impacts NEVER weakened by semantic overlay
  - no scenario changes
  - no schema changes to SemanticMemoryRecord
  - no L2 drive layer changes

### Verification
- **Freeze tests**:
  - all `eva/l2_drive/`, `eva/anchor/`, `eva/kernel/`, `eva/l1_sensing/`, `eva/scenario_bundle/` (broad)
  - all `tests/scenarios/`
  - Round 1.A/1.B-1/1.B-2 new tests
  - `tests/l3_deliberation/reasoning/test_value.py` (assertion-data updates allowed only if blend behavior demonstrably shifts a previously-tested case; default expectation: pass without changes since `working_memory_context.semantic_patterns` is empty or absent in most tests)
- **Additional tests to add**:
  - `tests/l3_deliberation/reasoning/test_semantic_drive_overlay.py` (6 tests covering presence, threshold, no-op, smaller-than-learned, drive-levels-untouched, reason-recorded)
- **Need full regression?** yes

### Docs sync
- `docs/implementation-tracking.md` — "Semantic memory → L2 drive-weight semantics" → production (safe-path)
- `docs/implementation-tracking-zh.md` — mirror
- `docs/blueprint-to-tracking-map.md` — same row
- `maintainer/development/stage-i-followups.md` — followup #2 resolved
- `maintainer/development/round-1b-3-progress.md` — new
- `maintainer/development/current-intake.md` — closeout

### Go / no-go
- **Can implementation start now?** yes
- **Halt conditions**: Linux behavior breaks beyond the documented safe-path contribution; or any non-semantic-pattern test starts failing.
