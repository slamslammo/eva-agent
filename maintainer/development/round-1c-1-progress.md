# Round 1.C-1 Progress — Semantic Memory Store-Side Indexing (W4)

## Status

- **Implementation**: complete
- **Regression**: 366 / 366 tests pass
- **Stage I follow-up #1**: resolved
- **G3-1C gate**: pending architect review

## Goal recap

Round 1.C-1 closes Stage I follow-up #1: the deferred "semantic memory
store-side windowing / indexing" path. Added a process-local in-memory
index that eliminates disk re-reads per `read_semantic_memory` call and
provides inverted buckets for fast candidate retrieval. The persistent
`semantic_memory.jsonl` artifact is untouched — the index is purely
derived in memory and rebuilds from disk on first access per StateStore.

## Implementation summary

Single framework file modified (`eva/l3_deliberation/memory/semantic.py`)
plus a `__init__.py` re-export update. Zero StateStore changes, zero
scenario changes, zero downstream consumer changes — the index is
additive to existing API.

### New internal class

```python
class _SemanticIndex:
    entries: list[dict[str, Any]]
    by_scenario: dict[str, list[int]]
    by_scenario_situation: dict[tuple[str, str], list[int]]
    by_scenario_top_drive: dict[tuple[str, str], list[int]]
    by_scenario_pressure: dict[tuple[str, str], list[int]]
    by_topic: dict[str, list[int]]
```

Buckets store entry positions (ints) rather than entry copies; the
`entries` list owns the data. `add()` appends to `entries` and updates
all buckets in O(1).

### New module-level cache

```python
_indexes: dict[Path, _SemanticIndex] = {}
```

Keyed on `StateStore.paths.runtime_dir`. One entry per active StateStore
(production has one; tests construct many in temp dirs).

### Lifecycle

- **First read for a store**: `_index_for_store(store)` calls
  `store.read_semantic_memory()` once to fetch full history from disk,
  builds the index, caches it. Subsequent reads return cached entries
  list directly — no disk re-read.
- **Append**: `append_semantic_memory(store, payload)` writes through to
  StateStore, then updates the cached index (if built) in O(1). If the
  cache hasn't been built yet, the next read will lazy-build it and
  include the new entry from disk.
- **Cache eviction**: `clear_semantic_memory_cache(store)` evicts one
  entry; `clear_semantic_memory_cache()` evicts all. Test-only API.

### New public helper

```python
def query_semantic_memory_for_situation(
    store, *, scenario, situation_key, top_drive, pressure_reason
) -> list[dict[str, Any]]:
    ...
```

Returns a superset of candidates that `retrieval.recent_semantic_memory`
would score non-zero for the same situation:

- union of `(scenario, situation_key)`, `(scenario, top_drive)`, and
  `(scenario, pressure_reason)` buckets
- PLUS the full `scenario` bucket as a fallback — this preserves the
  retrieval algorithm's approximate `drive_similarity ≥ 0.5` matching
  path so no candidate that the legacy linear scan would have scored
  non-zero is dropped

### Tests added

`tests/l3_deliberation/memory/test_semantic_indexing.py` — 9 tests:

1. cold read on empty store returns empty list
2. append visible to next read
3. two appends visible in order
4. cache isolation across stores (no bleed between temp dirs)
5. `clear_semantic_memory_cache(store)` forces rebuild from disk
6. `clear_semantic_memory_cache()` clears all caches
7. query filters by scenario
8. query returns situation_key match plus scenario fallback
9. query result is a superset — scoring via `recent_semantic_memory` on
   the narrowed input matches scoring on the full input

## Files changed

### Modified (framework)
- `eva/l3_deliberation/memory/semantic.py`
- `eva/l3_deliberation/memory/__init__.py` (re-export `clear_semantic_memory_cache` + `query_semantic_memory_for_situation`)

### Added (tests)
- `tests/l3_deliberation/memory/test_semantic_indexing.py`

### Modified (docs)
- `docs/implementation-tracking.md` — semantic memory row → production; follow-up #1 → resolved
- `docs/implementation-tracking-zh.md` — mirror
- `docs/blueprint-to-tracking-map.md` — same row
- `maintainer/development/stage-i-followups.md` — #1 marked resolved

### Maintainer (added)
- `maintainer/development/round-1c-1-semantic-memory-indexing-startup-instruction.md`
- `maintainer/development/round-1c-1-progress.md` (this file)

### Not modified
- `eva/kernel/state.py` — StateStore untouched (append-only artifact discipline preserved)
- `eva/l3_deliberation/memory/retrieval.py` — `recent_semantic_memory` scoring algorithm preserved
- `eva/l3_deliberation/reasoning/working_memory.py` — current `read_semantic_memory(store)` call site
  continues to fetch the full list; the indexed helper is exposed for future migration
- `scenarios/`, `eva/l2_drive/`, `eva/anchor/`, `eva/l1_sensing/`, `eva/scenario_bundle.py`

## Verification log

| Step | Result |
|---|---|
| 1.C-1-a failing tests | ImportError on new symbols — confirmed |
| 1.C-1-b/c/d/e implementation | 9 new tests pass |
| 1.C-1-f docs sync | regression remains green |
| Final regression | **366 / 366 OK** |

## Round 1.C-1 exit criteria status

| Criterion | Status |
|---|---|
| Existing `read_semantic_memory` / `append_semantic_memory` contract preserved | ✅ existing test_semantic.py passes unchanged |
| Append observable without disk re-read | ✅ test_append_visible_to_next_read_without_disk_re_read |
| Query returns superset of legacy scan candidates | ✅ test_query_returns_superset_of_recent_semantic_memory_candidates |
| Test isolation across stores | ✅ test_cache_isolation_across_stores |
| Cache clear works | ✅ test_clear_semantic_memory_cache_forces_rebuild_from_disk |
| Zero StateStore / scenario / Linux changes | ✅ verified |
| Stage I follow-up #1 closed | ✅ marked resolved |

## Surfaced for later

1. **Working memory hot-path migration**: `eva/l3_deliberation/reasoning/working_memory.py:303` still calls `read_semantic_memory(store)` (returning full list) rather than the new `query_semantic_memory_for_situation`. The cache win (no disk re-read) is already realized via this call; the BUCKET win (narrower input → faster scoring) is opportunity for a small follow-up slice. Deferred to keep this slice tightly scoped and not perturb downstream consumers that expect the full list.

2. **Persistent `.idx` sidecar (Plan C)**: still deferred. Only relevant if Round 1.D long-run validation shows cold-start rebuild becoming a bottleneck at N >> 10⁴ entries.

3. **Generalized append-only ReadCache layer**: `learning_outcomes.jsonl` / `response_history.jsonl` / `deliberation_audit.jsonl` have the same rotation-induced read amplification problem. Could be a future Round 2 candidate slice using the same pattern (cache + lazy rebuild + append-side mirror update).

4. **Cross-process cache coordination**: not needed under current architecture (single-process runner). If multi-process runners are ever introduced (Round 2+), the cache needs explicit invalidation on cross-process writes.

## Round 1.C-2 next

Round 1.C-2 is W6 (working-memory interface signature review). It can proceed independently of Round 1.C-1.
