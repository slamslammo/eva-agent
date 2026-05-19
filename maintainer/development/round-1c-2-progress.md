# Round 1.C-2 Progress — Working-Memory Assembly Limits Dataclass (W6)

## Status

- **Implementation**: complete
- **Regression**: 371 / 371 tests pass
- **Stage I follow-up #3**: addressed
- **G3-1C-2 gate**: pending architect review

## Goal recap

Round 1.C-2 closes Stage I follow-up #3 by introducing
`WorkingMemoryAssemblyLimits` dataclass that bundles the four `max_*`
output-size parameters that were accumulating on
`build_working_memory_context` and `build_working_memory_context_from_store`.
Legacy individual kwargs are preserved for backward compatibility — the
`limits` parameter is purely additive.

## Implementation summary

Single framework file modified (`eva/l3_deliberation/memory` was not touched;
this is exclusively `eva/l3_deliberation/reasoning/working_memory.py`).
Zero scenario / kernel / anchor changes.

### New dataclass

```python
@dataclass(frozen=True)
class WorkingMemoryAssemblyLimits:
    max_bias_summaries: int = 2
    max_habit_skills: int = 2
    max_recent_outcomes: int = 3
    max_semantic_patterns: int = 2
```

Default values match the legacy individual kwarg defaults exactly, so
passing no limits is bit-equivalent to omitting all `max_*` arguments
(i.e. existing callers see no behavior change).

### New helper

```python
def _resolve_limits(
    limits: WorkingMemoryAssemblyLimits | None,
    *,
    max_bias_summaries: int = 2,
    max_habit_skills: int = 2,
    max_recent_outcomes: int = 3,
    max_semantic_patterns: int = 2,
) -> WorkingMemoryAssemblyLimits:
    ...
```

Priority order: explicit `limits` argument > legacy individual `max_*`
kwargs > dataclass defaults. Always returns a concrete `WorkingMemoryAssemblyLimits`.

### Signature updates

Both `build_working_memory_context` and `build_working_memory_context_from_store`
gain an optional `limits: WorkingMemoryAssemblyLimits | None = None`
keyword argument. The legacy individual `max_*` kwargs are retained so
all existing callers and tests continue to work without modification.

### Data-source kwargs preserved

The data-source kwargs (`learning_outcomes`, `habit_bias_entries`,
`response_history`, `memory_stubs`, `semantic_entries`) remain individual
keyword arguments. They are conceptually different from output-size
limits — they are inputs that tests need to inject directly to construct
synthetic scenarios. Bundling them would hurt test ergonomics more than
it would clean up the signature.

### Tests added

`tests/l3_deliberation/reasoning/test_working_memory_assembly_limits.py`
— 5 tests:

1. dataclass default values match legacy kwarg defaults
2. `build_working_memory_context` accepts the new `limits` parameter
3. legacy `max_*` kwargs still work (backward compatibility)
4. `limits` takes precedence over legacy kwargs when both supplied
5. `build_working_memory_context_from_store` accepts `limits` symmetrically

## Files changed

### Modified (framework)
- `eva/l3_deliberation/reasoning/working_memory.py` — dataclass + helper + signature updates on two assembly entry points

### Added (tests)
- `tests/l3_deliberation/reasoning/test_working_memory_assembly_limits.py`

### Modified (docs)
- `docs/implementation-tracking.md` — row updated to production; follow-up #3 marked addressed
- `docs/implementation-tracking-zh.md` — mirror
- `docs/blueprint-to-tracking-map.md` — interface row updated
- `maintainer/development/stage-i-followups.md` — #3 marked addressed

### Maintainer (added)
- `maintainer/development/round-1c-2-progress.md` (this file)

### Not modified
- All other framework / scenario / kernel / anchor / L2 / L1 code
- Existing test files (all continue to pass via backward-compatible kwargs)

## Verification log

| Step | Result |
|---|---|
| 1.C-2 failing tests added | ImportError on `WorkingMemoryAssemblyLimits` — confirmed |
| Dataclass + helper + signature updates | 5 new tests pass |
| Full regression | **371 / 371 OK** |
| Backward compatibility | All existing tests pass without modification — verified |

## Round 1.C-2 exit criteria status

| Criterion | Status |
|---|---|
| `WorkingMemoryAssemblyLimits` introduced | ✅ |
| Both assembly entry points accept `limits` parameter | ✅ |
| Default values match legacy kwarg defaults | ✅ pinned by test |
| Legacy kwargs still functional | ✅ pinned by test |
| `limits` takes precedence over legacy kwargs | ✅ pinned by test |
| Zero scenario / kernel / anchor changes | ✅ verified |
| Stage I follow-up #3 closed | ✅ marked addressed |
| Linux + Crafter behavior bit-equivalent | ✅ all existing tests pass |

## Round 1.C is now complete

Round 1.C-1 (W4 semantic memory indexing) and Round 1.C-2 (W6 interface
signature review) are both landed. The framework + scenario stack is now
ready for Round 1.D (long-run validation + Crafter exploration parameter
tuning).

## Round 1 status overall

| Slice | Status |
|---|---|
| 1.A — Crafter action widening | ✅ landed |
| 1.B-1 — Framework drive semantics de-Linuxification | ✅ landed |
| 1.B-2 — Crafter exploration drive (W3) | ✅ landed |
| 1.B-3 — Semantic → drive overlay (W5) | ✅ landed |
| 1.C-1 — Semantic memory indexing (W4) | ✅ landed |
| 1.C-2 — Working-memory limits dataclass (W6) | ✅ landed |
| 1.D — Long-run validation (W1 redefined) | next |

All Stage I follow-ups (#1, #2, #3) now closed.
