# Current Intake

当前激活的本地开发 intake 记录放在这里。

使用方式：
- 开始任何代码实现、重构或 realignment 前，先复制 `change-intake-template.md` 的结构到本文件
- 只保留**当前正在执行**的一项 intake
- 当该项工作完成后，可直接覆盖为下一项 intake；长期事实应回写到正式文档，而不是累计堆在这里

> 这是本地单-Claude 开发阶段的轻量工作入口，不是长期归档文档。

## Round 1.C-1 — Semantic Memory Store-Side Indexing (W4)

### Status
- **implementation complete**
- 366 / 366 tests pass
- Stage I follow-up #1 resolved
- pending **G3-1C architect review** before moving to Round 1.C-2 (W6)
- progress: `maintainer/development/round-1c-1-progress.md`

### Change intake
- **Change title**: Round 1.C-1 — Plan B in-memory inverted index for semantic memory; closes Stage I follow-up #1
- **Goal**:
  - Eliminate disk re-read on every working-memory assembly call
  - Provide pre-filtered candidate lookup via inverted indexes (by `(scenario, situation_key) / (scenario, top_drive) / (scenario, pressure_reason) / topic / scenario`)
  - Keep StateStore + append-only .jsonl artifact discipline untouched
  - Working memory hot path switches from full-list read to indexed query
- **Change type**: framework performance + capability enhancement
- **Companion directive**: `maintainer/development/round-1c-1-semantic-memory-indexing-startup-instruction.md`

### Ownership
- **Primary**: `eva/l3_deliberation/memory/semantic.py` (new `_SemanticIndex` class + helpers + module-level cache)
- **Secondary**: `eva/l3_deliberation/reasoning/working_memory.py` (one call-site update at line 303)
- **Owner class**: stable framework owners

### Boundary check
- **Affected contracts**:
  - `read_semantic_memory(store)` returns same list contract, now cached
  - `append_semantic_memory(store, payload)` same contract, now updates cache
  - New public symbol: `query_semantic_memory_for_situation(store, *, scenario, situation_key, top_drive, pressure_reason)`
  - New test helper: `clear_semantic_memory_cache(store=None)`
- **Hard boundaries preserved**:
  - StateStore unchanged (no schema, no new methods, append-only jsonl untouched)
  - `recent_semantic_memory` scoring algorithm unchanged (only input set narrowed upstream)
  - Linux scenario behavior bit-equivalent
  - Crafter scenario behavior unchanged
  - No new persistence files (in-memory only)
- **Why this change does not widen a transitional owner**:
  - The index is purely internal to `semantic.py`; no contract change to StateStore or any other module
  - The new `query_semantic_memory_for_situation` is additive, not replacing existing API

### Verification
- **Freeze tests**:
  - `tests/l3_deliberation/memory/test_semantic.py` (existing contract)
  - `tests/l3_deliberation/reasoning/test_working_memory.py`
  - All `tests/scenarios/`
  - All other test trees
- **Additional tests to add**:
  - `tests/l3_deliberation/memory/test_semantic_indexing.py` (8 tests covering cold-read, append-visible, scenario filtering, situation_key filtering, cache clear, isolation, equivalence with linear scan, fall-back-to-scenario-bucket safety)
- **Need full regression?** yes (after each slice)

### Docs sync
- `maintainer/development/round-1c-1-progress.md` (new)
- `maintainer/development/current-intake.md` (closeout)
- `maintainer/development/stage-i-followups.md` (#1 → resolved)
- `docs/implementation-tracking.md` (semantic memory row → production)
- `docs/implementation-tracking-zh.md` (mirror)
- `docs/blueprint-to-tracking-map.md` (Four-layer memory + Semantic memory first-class rows)

### Go / no-go
- **Can implementation start now?** yes
- **Halt conditions**: existing semantic / working_memory tests break beyond assertion-data updates; equivalence with linear scan candidates lost.
