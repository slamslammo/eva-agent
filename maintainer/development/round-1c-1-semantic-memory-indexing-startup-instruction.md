# Round 1.C-1 — Semantic Memory Store-Side Indexing (W4) — Startup Instruction

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.C-1 — W4; closes Stage I follow-up #1

**Companion documents**:
- `.claude/plans/federated-snacking-engelbart.md`
- `maintainer/development/stage-i-followups.md` §1 (the open follow-up this slice resolves)
- `eva/l3_deliberation/memory/semantic.py` (the canonical owner)
- `eva/l3_deliberation/memory/retrieval.py` (existing `recent_semantic_memory` scoring path — preserved)
- `eva/kernel/state.py:644-650` (`StateStore.append_semantic_memory` / `read_semantic_memory`)
- `eva/l3_deliberation/reasoning/working_memory.py:303` (the single real consumer)

---

## 1. What this work is and is not

**Problem**: every working-memory assembly call invokes `read_semantic_memory(store)`, which causes `StateStore._read_jsonl_history` to (a) `glob` the archive directory, (b) read every archived segment, and (c) parse every line. Then `recent_semantic_memory` in retrieval.py iterates the full result in Python. After file rotation, this read-side cost grows with segment count even when the entry count is moderate.

**Scope (Plan B from earlier architect review)**:
- Add a process-local in-memory index in `semantic.py` keyed on `StateStore.paths.runtime_dir`
- Cache the full entries list (so `read_semantic_memory` no longer re-reads disk)
- Build inverted indexes by `(scenario, situation_key) / (scenario, top_drive) / (scenario, pressure_reason) / topic / scenario` for fast candidate-set retrieval
- Provide a new `query_semantic_memory_for_situation(store, *, scenario, situation_key, top_drive, pressure_reason)` helper that returns a pre-filtered candidate list using the inverted indexes (working memory's hot path uses this)
- Preserve existing `read_semantic_memory(store)` / `append_semantic_memory(store, payload)` signatures; both now route through the cache
- Provide `clear_semantic_memory_cache(store=None)` for test isolation

**What W4 is NOT**:
- Not modifying `eva/kernel/state.py` (append-only artifact discipline preserved; index is pure derived in-memory, never persisted)
- Not changing `recent_semantic_memory` scoring algorithm in `retrieval.py` — only the input set is narrowed via the new helper
- Not modifying `SemanticMemoryRecord` schema
- Not adding multi-process / cross-process cache coordination (single-process assumption)
- Not adding a persistent `.idx` sidecar (Plan C, deferred — see Surfaced section)

---

## 2. Exit criterion

### Behavioral
- `read_semantic_memory(store)` returns the same list as before (same entries, same order, same dict contents)
- `query_semantic_memory_for_situation(store, ...)` returns a superset of the candidates that the linear scan in `recent_semantic_memory` would consider non-zero — including the fall-back-to-scenario-bucket safety net for `drive_similarity ≥ 0.5` matches
- `append_semantic_memory(store, payload)` is observable to the next `read_semantic_memory(store)` call without disk re-read
- After file rotation triggered by `_append_jsonl`, the cached entries reflect both pre- and post-rotation state
- `recent_semantic_memory` produces bit-equivalent ranked output for any given input set; only its input set is narrowed (semantic equivalence verified by test)

### Engineering
- Full regression passes (target: 357 + ~8 new tests = ~365)
- `git diff main -- 'eva/kernel/' 'scenarios/' 'eva/anchor/' 'eva/l2_drive/' 'eva/l1_sensing/' 'eva/scenario_bundle.py'` shows zero modifications
- New code is concentrated in `eva/l3_deliberation/memory/semantic.py` and one small call-site update in `eva/l3_deliberation/reasoning/working_memory.py`

### Documentation
- `maintainer/development/round-1c-1-progress.md` written
- `maintainer/development/stage-i-followups.md` — followup #1 marked resolved
- `docs/implementation-tracking.md` — semantic memory row updated to production (windowing landed)
- `docs/implementation-tracking-zh.md` mirror
- `docs/blueprint-to-tracking-map.md` — Four-layer memory surface row + Semantic memory first-class row updated

---

## 3. Scope target state

### Files to modify
- `eva/l3_deliberation/memory/semantic.py` — index class + helpers + cache management
- `eva/l3_deliberation/reasoning/working_memory.py` — switch `read_semantic_memory(store)` call to `query_semantic_memory_for_situation(store, ...)` at line 303

### Files NOT to modify
- `eva/kernel/state.py` (StateStore stays untouched)
- `eva/l3_deliberation/memory/retrieval.py` (`recent_semantic_memory` algorithm preserved; only its input changes upstream)
- `scenarios/`, `eva/l2_drive/`, `eva/anchor/`, `eva/l1_sensing/`, `eva/scenario_bundle.py`

### Tests to add (new file)
- `tests/l3_deliberation/memory/test_semantic_indexing.py`:
  1. Cold-read on empty store returns empty list (and builds an empty index)
  2. Single append → next read returns the entry
  3. Two appends → both visible
  4. Multiple scenarios → query_for_situation filters by scenario
  5. Multiple situation_keys → filtering returns superset including matching keys
  6. Cache invalidation: `clear_semantic_memory_cache(store)` forces rebuild
  7. Test isolation: cache for one store does not bleed into another
  8. Equivalence: query_for_situation returns a superset of what `recent_semantic_memory` scores non-zero (the safety net works)

### Tests freeze
- All `tests/l3_deliberation/memory/test_semantic.py` (the existing tests must continue to pass — they verify the current contract)
- All `tests/l3_deliberation/reasoning/test_working_memory.py`
- All `tests/scenarios/`
- All other tests

---

## 4. Implementation slices

### 1.C-1-a: Failing tests (skeleton index API)
Add the new test file with tests that import the new symbols. They will fail at import (no `query_semantic_memory_for_situation`, `clear_semantic_memory_cache`).

### 1.C-1-b: `_SemanticIndex` + cache infrastructure
Add in `semantic.py`:
```python
class _SemanticIndex:
    def __init__(self):
        self.entries: list[dict[str, Any]] = []
        self.by_scenario: dict[str, list[int]] = {}
        self.by_scenario_situation: dict[tuple[str, str], list[int]] = {}
        self.by_scenario_top_drive: dict[tuple[str, str], list[int]] = {}
        self.by_scenario_pressure: dict[tuple[str, str], list[int]] = {}
        self.by_topic: dict[str, list[int]] = {}

    def add(self, entry: dict[str, Any]) -> None:
        idx = len(self.entries)
        self.entries.append(entry)
        # Update all buckets...
```

Module-level cache keyed on `store.paths.runtime_dir`:
```python
_indexes: dict[Path, _SemanticIndex] = {}

def _index_for_store(store: StateStore) -> _SemanticIndex:
    key = store.paths.runtime_dir
    if key not in _indexes:
        index = _SemanticIndex()
        for entry in store.read_semantic_memory():
            index.add(entry)
        _indexes[key] = index
    return _indexes[key]
```

### 1.C-1-c: Wire append + read through the index
```python
def append_semantic_memory(store, payload):
    store.append_semantic_memory(payload)
    _index_for_store(store).add(dict(payload))

def read_semantic_memory(store):
    return list(_index_for_store(store).entries)
```

### 1.C-1-d: Implement query_semantic_memory_for_situation
```python
def query_semantic_memory_for_situation(
    store, *, scenario, situation_key, top_drive, pressure_reason,
):
    index = _index_for_store(store)
    candidate_idxs: set[int] = set()
    candidate_idxs.update(index.by_scenario_situation.get((scenario, situation_key), []))
    candidate_idxs.update(index.by_scenario_top_drive.get((scenario, top_drive), []))
    candidate_idxs.update(index.by_scenario_pressure.get((scenario, pressure_reason), []))
    candidate_idxs.update(index.by_scenario.get(scenario, []))  # drive_similarity safety net
    return [index.entries[i] for i in sorted(candidate_idxs)]
```

### 1.C-1-e: Add `clear_semantic_memory_cache(store=None)`
For test isolation. If `store=None`, clear all caches.

### 1.C-1-f: Wire into working_memory.py
Change line 303 from `semantic_entries = read_semantic_memory(store)` to:
```python
semantic_entries = query_semantic_memory_for_situation(
    store,
    scenario=...,
    situation_key=...,
    top_drive=...,
    pressure_reason=...,
)
```

Resolve the right fields from existing local variables in `compose_working_memory`. If unclear, fall back to the safer (but slower) `read_semantic_memory(store)` for this slice — and note the wiring as a follow-up.

### 1.C-1-g: Docs sync + closeout

---

## 5. Boundary / invariants

- Append-only `.jsonl` discipline preserved (index is pure derived in-memory)
- StateStore unchanged (no schema, no new methods)
- Linux scenario behavior bit-equivalent
- Crafter scenario behavior unchanged
- Scoring algorithm in `recent_semantic_memory` unchanged
- The query helper returns a SUPERSET of candidates the scoring algorithm needs (because of the scenario-bucket fall-back) — never fewer

---

## 6. Architect gates

- **G1-1C** (pre-implementation): intake written
- **G2-1C** (post-1.C-1-f): regression green; architect confirms ready for docs sync
- **G3-1C** (closeout): full regression + progress doc

---

## 7. Surfaced for later

- **Persistent `.idx` sidecar (Plan C)**: defer. Only consider if Round 1.D long-run validation shows cold-start rebuild becoming a bottleneck.
- **Cross-process cache coordination**: not needed under current single-process runner architecture.
- **Generalized append-only ReadCache layer**: same pattern (memoize + invalidate-on-append) could apply to `learning_outcomes.jsonl` / `response_history.jsonl` / `deliberation_audit.jsonl`. Surface as Round 2 candidate slice.
