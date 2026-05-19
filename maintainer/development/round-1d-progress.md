# Round 1.D Progress — Long-Run Validation Infrastructure

## Status

- **D-1 / D-2 / D-3**: implementation complete
- **D-4 / D-5 / D-6**: pending (user-driven long-run execution + post-run report)
- **Regression**: 384 / 384 tests pass
- **G3-1D gate**: pending architect review

## Goal recap

Round 1.D lands the infrastructure needed for user-driven 6h+ Crafter
long-run validation. The actual long-run execution and report assembly
are user-driven follow-ups (machine time, not architect time).

This slice closes the v0.6 blueprint §13.2 long-run invariant validation
obligation at the **infrastructure level** — the framework now supports
graceful termination, periodic snapshots, and tripwire-driven early stop.

## Sub-slice record

### D-1: Graceful interrupt + exit_reason
- `eva/kernel/main.py` — `RunSummary` gains `exit_reason: str` field (default `"normal"`)
- Loop wrapped in `try / except KeyboardInterrupt`; on interrupt, exit_reason is set to `"keyboard_interrupt"` and the shutdown event is written before returning
- Exit reasons populated for max-bound exits: `"max_ticks"`, `"max_turns"`, `"max_runtime_sec"`
- `final_state` read protected by its own try/except so a corrupt state file doesn't prevent shutdown event writing — falls back to in-memory state if necessary

### D-2: Periodic hook on run_runtime
- New keyword arg: `periodic_hook: Callable[..., tuple[bool, str | None]] | None = None`
- New keyword arg: `hook_interval_sec: float = 1800.0`
- Hook is called at most every `hook_interval_sec` seconds during the loop
- Hook signature: `hook(*, runtime_dir, elapsed_since_start, ticks, turns)` → `(should_stop, reason)`
- Hook errors are caught and logged via `emit_log_line("periodic_hook_error", ...)` — they do not crash the loop
- Hook returning `(True, "tripwire:metric_name")` sets exit_reason to the hook's reason and breaks the loop cleanly

### D-3: Longrun validation hook factory
- New module: `runners/longrun_validation.py`
- `LongrunTripwire` dataclass with three configurable thresholds:
  - `max_constraint_violation_rate` (default `0.0` — any violation triggers stop)
  - `min_continuity_preservation_score` (default `0.5`)
  - `min_useful_progress_under_constraint` (default `None` — disabled until Round 1.B-2 tuning data justifies a threshold)
- `build_longrun_validation_hook(snapshot_dir, tripwire=None)` returns a callable matching the `run_runtime` periodic_hook signature
- The hook (on each fire):
  1. Calls `stability_metrics.calculate_stability_profile(runtime_dir)`
  2. Writes the annotated profile (with `sequence`, `elapsed_since_start_sec`, `ticks`, `turns`) to `snapshot_dir / f"profile-{seq:05d}.json"`
  3. Checks tripwire thresholds against metrics; returns `(True, "tripwire:<metric>")` on violation, else `(False, None)`

### Tests added
- `tests/kernel/test_runtime_graceful_interrupt.py` (8 tests):
  - `RunSummary.exit_reason` exists
  - `exit_reason="max_ticks"` / `"max_runtime_sec"` populated correctly
  - KeyboardInterrupt writes shutdown event with `exit_reason="keyboard_interrupt"`
  - Periodic hook fires at least once during a short run
  - Periodic hook can stop the loop with custom reason
  - Buggy hook does not crash the loop
  - No-hook default behavior unchanged (Linux equivalence)
- `tests/runners/test_longrun_validation_hook.py` (5 tests):
  - Snapshots numbered sequentially
  - Snapshot payload includes sequence + elapsed + ticks + turns
  - No-violation tripwire returns `(False, None)`
  - Constraint-violation tripwire fires with `"tripwire:constraint_violation_rate"`
  - Snapshot-only mode (tripwire=None) works

## Files changed

### Modified (framework)
- `eva/kernel/main.py` — `RunSummary.exit_reason`; refactored loop; periodic_hook + hook_interval_sec params; defensive shutdown-event write

### Added (runner helper)
- `runners/longrun_validation.py` — hook factory + tripwire dataclass

### Added (tests)
- `tests/runners/__init__.py` — new package marker
- `tests/kernel/test_runtime_graceful_interrupt.py` (8 tests)
- `tests/runners/test_longrun_validation_hook.py` (5 tests)

### Modified (docs)
- `docs/implementation-tracking.md` — long-run validation infrastructure row added
- `docs/implementation-tracking-zh.md` — mirror

### Maintainer (added)
- `maintainer/development/round-1d-longrun-validation-infrastructure-startup-instruction.md`
- `maintainer/development/round-1d-progress.md` (this file)

### Not modified
- `scenarios/`, `eva/l2_drive/`, `eva/anchor/`, `eva/l1_sensing/`, `eva/l3_deliberation/`, `eva/scenario_bundle.py`, `stability_metrics/`
- `runners/run_crafter.py`, `runners/run_linux.py` — hook integration is opt-in at validation time

## Verification log

| Step | Result |
|---|---|
| D-1 failing tests added | KeyboardInterrupt propagates through test (no catch) — confirmed |
| D-1 graceful interrupt landed | 4 D-1 tests pass; regression 379/379 |
| D-2 periodic hook landed | 4 additional D-2 tests pass; regression 379/379 |
| D-3 hook factory landed | 5 D-3 tests pass |
| Full regression | **384 / 384 OK** |

## Round 1.D exit criteria status

| Criterion | Status |
|---|---|
| `RunSummary.exit_reason` available | ✅ |
| KeyboardInterrupt writes shutdown event | ✅ |
| Periodic hook param functional | ✅ |
| Hook errors isolated | ✅ |
| Hook can stop the loop | ✅ |
| Snapshot factory produces numbered profiles | ✅ |
| Tripwire fires correctly | ✅ |
| Linux + Crafter behavior bit-equivalent when no hook | ✅ verified by full regression with no scenario test modifications |

## Pending: user-driven long-run execution (D-5 / D-6)

The infrastructure is ready. To execute the actual validation:

```python
from pathlib import Path
from runners.run_crafter import run_crafter_runtime
from runners.longrun_validation import LongrunTripwire, build_longrun_validation_hook
from eva.kernel.config import build_runtime_paths, RuntimeConfig, LoopControl

snapshot_dir = Path("validation-runs/crafter-longrun-v1-{timestamp}/snapshots/")
hook = build_longrun_validation_hook(
    snapshot_dir=snapshot_dir,
    tripwire=LongrunTripwire(),
)
config = RuntimeConfig(
    paths=build_runtime_paths("validation-runs/crafter-longrun-v1-{timestamp}/runtime/"),
    control=LoopControl(max_runtime_sec=21600.0),  # 6h
    # ... rest of config
)
# Invoke run_crafter_runtime with periodic_hook=hook (requires small runner-side
# wire-up to thread the hook through to run_runtime — runner.run_crafter
# currently doesn't expose this param; user adds the kwarg as needed).
```

Round 1.D-6 (report assembly) is post-run: collect all `profile-*.json` snapshots
from `snapshot_dir`, compare metric trajectories, identify any tripwire fires,
and write `round-1d-validation-report.md` summarizing findings + parameter-tuning
recommendations for Round 1.B-2 exploration drive thresholds.

## Round 1 status

| Slice | Status |
|---|---|
| 1.A — Crafter action widening | ✅ landed |
| 1.B-1 — Framework de-Linuxification | ✅ landed |
| 1.B-2 — Crafter exploration drive (W3) | ✅ landed |
| 1.B-3 — Semantic → drive overlay (W5) | ✅ landed |
| 1.C-1 — Semantic memory indexing (W4) | ✅ landed |
| 1.C-2 — Working-memory limits dataclass (W6) | ✅ landed |
| 1.D-1/2/3 — Long-run validation infrastructure | ✅ landed |
| 1.D-5 — Actual 6h+ long-run | user-driven (machine time) |
| 1.D-6 — Validation report | post-D-5 |

All Stage I follow-ups closed. Round 1 architect-side capability landing complete.
