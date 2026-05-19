# Round 1.B-4 Progress — Signal Classification De-coupling

## Status

- **Implementation**: complete
- **Regression**: 396 / 397 tests pass (1 pre-existing l2_drive failure unrelated to this slice; failing on `main` before the slice landed)
- **Behavior verification**: ✅ Crafter exploration drive moved from permanently-0 to max=1.0 / mean=0.398 / 55% of turns non-zero
- **G3-1B-4 gate**: pending architect review

## Goal recap

Round 1.B-4 closes a 7th Linux residue that Round 1.B-1 missed: the
framework's `build_threat_signal` was emitting `class="threat"` for
every active pressure regardless of severity / type. v0.5 Linux era
pressures were almost all integrity-class (runtime-in-trouble) so the
coarse "any pressure = threat" mapping worked. v0.6 Crafter has five
pressure types — `safety`, `metabolic`, `recovery`, `acquisition`,
`capability` — only `safety` is a real imminent threat. The other four
are ongoing optimization pressures that should not trigger
threat-response semantics (curiosity suppression, urgency routing,
memory salience amplification).

## What was modified

### `eva/scenario_bundle.py`
- `SensorPolicyBundle` gains `imminent_threat_pressure_types: tuple[str, ...] = ()` field

### `eva/l1_sensing/signal_bus.py`
- New `build_pressure_signal(snapshot, pressure)` emits `class="pressure"` (parallel to existing `build_threat_signal`)
- `build_patrol_signals` now routes each active pressure to threat-signal or pressure-signal based on scenario config; legacy fallback (no scenario activated) preserves pre-1.B-4 "all pressures = threat" semantic for low-level unit tests
- `SignalDispatchSummary` gains `pressure_signal_count: int = 0`
- `summarize_signal_dispatch` populates the new field

### `scenarios/linux_runtime/__init__.py`
- Declares `imminent_threat_pressure_types` as **all** Linux pressure types (integrity, continuity, resource_state, anomaly_accumulation are all runtime-in-trouble signals); preserves Linux behavior bit-equivalent

### `scenarios/crafter/__init__.py`
- Declares `imminent_threat_pressure_types=("safety",)` — only safety class (zombies, threats in local_view) qualifies as imminent; metabolic / recovery / acquisition / capability flow as `class="pressure"`

## Behavior verification — the critical test

Ran a 3-minute Crafter smoke (local_rule_based) post-fix and compared against the 10-minute Phase 1 (real LLM) data captured pre-fix:

| Metric | Pre-1.B-4 (10min real LLM) | Post-1.B-4 (3min local) |
|---|---|---|
| `has_threat_signal=True` ratio | 200/200 (100%) | 944/1494 (63.2%) |
| `threat_signal_count=0` ratio | 0% | 36.8% — first "quiet" ticks |
| `pressure_signal_count` avg | (field did not exist) | 3.4 |
| **exploration drive max** | 0.000 | **1.000** |
| **exploration drive mean** | 0.0000 | **0.3983** |
| **exploration drive non-zero ratio** | 0% | **55.3%** |
| exploration drive ≥ 0.3 ratio | 0% | 46.3% |
| L3 profile observe_first share | 7.3% | 10.4% |
| achievement_delta total | 1 | 9 |

**Interpretation**: the root cause is fixed. Exploration drive is no
longer being pinned at zero by spurious threat signals; it now
fluctuates normally and accumulates during "quiet" ticks. Achievement
unlocks moved from 1 → 9. Behavior shift is modest at the L3 selection
layer (10.4% observe vs 7.3%) because the scoring path's
`high_drive_projection_for_stabilize_first` boost still dominates under
sustained avatar degradation, but the drive layer is finally
functioning as designed.

## Files changed

### Modified (framework, 3 files)
- `eva/scenario_bundle.py` — `SensorPolicyBundle.imminent_threat_pressure_types` field
- `eva/l1_sensing/signal_bus.py` — split classification + new class enum value + summary count
- _(no changes to `routing.py` / `drive_state.py` / `value_judgment.py` / `encoding.py` / `reflex.py` needed — they all consume `class=="threat"` semantics, which post-fix correctly means "imminent threat")_

### Modified (scenario, 2 files)
- `scenarios/linux_runtime/__init__.py` — declares all pressure types as imminent (Linux equivalence)
- `scenarios/crafter/__init__.py` — declares only safety as imminent

### Modified (test, 1 file)
- `tests/integration/test_patrol_turn_flow.py` — assertion data update (signal_summary now has 6 keys, was 5)

### Added (test, 1 file)
- `tests/l1_sensing/test_signal_classification.py` (5 tests pinning new classification semantics)

### Maintainer (added)
- `maintainer/development/round-1b-4-signal-classification-de-coupling-startup-instruction.md`
- `maintainer/development/round-1b-4-progress.md` (this file)

## Verification log

| Step | Result |
|---|---|
| New tests added | 5 tests pass (imminent vs pressure classification across both scenarios) |
| Pre-existing failure | `test_update_drive_state_accumulates_over_multiple_patrols` was already failing on `main` before this slice (confirmed via `git stash` + isolated run) — unrelated to Round 1.B-4 |
| Regression delta from this slice | **0 new failures**; 1 assertion-data update to existing test (signal_summary key count) |
| Crafter smoke (3min local) | exploration drive max=1.0, mean=0.40, non-zero 55.3% — confirmed root cause fixed |

## Pre-existing test failure (not Round 1.B-4 related)

`tests.l2_drive.test_drive.DriveTests.test_update_drive_state_accumulates_over_multiple_patrols` fails because it calls `update_drive_state` without activating any scenario; the test relies on stale `_DEFAULT_DRIVE_PRESET` state leaking across tests. This was failing on `main` before Round 1.B-4 (verified by `git stash`). Out of scope for this slice — should be fixed in a separate small test-isolation followup.

## Round 1.B-4 exit criteria

| Criterion | Status |
|---|---|
| `class="threat"` now means imminent threat only | ✅ pinned by tests |
| Linux behavior bit-equivalent | ✅ all pressure types declared imminent for Linux; existing Linux tests pass without logic changes |
| Crafter `class="pressure"` emitted for non-safety pressures | ✅ pinned by tests |
| Exploration drive functional in Crafter | ✅ verified by smoke (was 0/0/0, now 1.0/0.40/55.3%) |
| No new persistence schema changes | ✅ |
| No scenario / scenario_bundle owner widening | ✅ field added with default `()`, additive |

## Round 1 status update

| Slice | Status |
|---|---|
| 1.A — Crafter action widening | ✅ landed |
| 1.B-1 — Framework de-Linuxification | ✅ landed (but missed signal-class layer) |
| 1.B-2 — Crafter exploration drive (W3) | ✅ landed |
| 1.B-3 — Semantic → drive overlay (W5) | ✅ landed |
| 1.B-4 — Signal classification de-coupling | ✅ landed (this slice) |
| 1.C-1 — Semantic memory indexing (W4) | ✅ landed |
| 1.C-2 — Working-memory limits dataclass (W6) | ✅ landed |
| 1.D-1/2/3 — Long-run validation infrastructure | ✅ landed |
| Phase 1 — 10min real-LLM verification | ✅ run; surfaced root cause |
| Phase 1.5 — Parameter tuning + drive_state config flag | ✅ landed (within this slice's intake) |
| Phase 2 — HTML viewer | pending |
| 1.D-5 — Actual long-run | now meaningful after 1.B-4 fix |

## What this slice unblocked

Before this fix, a 6h long-run would have produced data reflecting
**buggy framework behavior** — threat suppression dominating every tick,
exploration drive pinned at zero, memory salience over-amplified. The
data would not have answered "how does the EVA agent behave under
sustained operation"; it would have answered "how does the buggy
framework behave".

Post-fix, the same long-run would produce data reflecting the
**designed EVA behavior**. Phase 2 viewer development and Phase 3 6h
long-run now have something real to validate against.

## Surfaced for follow-up

1. **L3 selection still stabilize-dominated**: even with exploration drive
   active, L3 mediator picks stabilize_first 89.6% of turns. The
   `high_drive_projection_for_stabilize_first` boost from Round 1.B-1-c
   may need tuning under sustained avatar degradation. Defer to
   post-Phase-3 D-6 data analysis.

2. **`tests.l2_drive.test_drive` test isolation**: pre-existing failure
   should be cleaned up as a small followup; not blocking.

3. **Drive parameter tuning (Round 1.B-2's surfaced item)**: the
   `curiosity_recovery=0.10 / suppression=0.06 /
   suppress_on_degraded_status=False` configuration was a pre-1.B-4
   attempt. Now that signal classification is fixed, the original Linux
   defaults (0.05 / 0.12) might work fine too. Worth re-evaluating
   during Phase-3 D-6 analysis.
