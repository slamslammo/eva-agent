# Round 1.B-1 Progress — Framework Drive Semantics De-Linuxification

## Status

- **Implementation**: complete (sub-slices A → B → C → D → E all landed)
- **Regression**: 343 / 343 tests pass after each sub-slice
- **Docs sync**: in progress
- **G3-1B gate**: pending architect review

## Goal recap

Round 1.B-1 resolved six Linux-coupled drive-semantics residues in framework
reasoning + memory + state layers. After this slice, framework code no longer
treats ``"integrity"`` as a magic-string for "the action-triggering drive";
all reasoning, memory routing, and pressure projection are scenario-neutral.

Linux behavior is bit-equivalent or has documented theoretically-grounded
behavior changes in narrow corner cases (curiosity-high-no-threat now
correctly engages release pressure per v0.6.1 §4 exploration semantics).

## Sub-slice record

### 1.B-1-a: Fix A — `_drive_weighted_score` iterates declared drives

- **File**: `eva/l3_deliberation/reasoning/value_judgment.py:133-152`
- **Change**: replaced hardcoded iteration `for drive_name in ("survival", "integrity", "continuity", "curiosity")` with `for drive_name, impact in drive_impact_schema.items()`. Iteration now walks whatever drives the candidate actually declared impact for.
- **Linux equivalence**: bit-equivalent. Old code did `drive_levels.get(name, 0.0) * drive_impact_schema.get(name, 0.0)` for each hardcoded name. New code does `drive_levels.get(name, 0.0) * impact` for each declared name. Any drive NOT in `drive_impact_schema` contributed `0` under the old code anyway (because `drive_impact_schema.get(name, 0.0) == 0`). The two are mathematically identical when given Linux drive vocabulary.
- **Crafter unlock**: candidates declaring impact on `metabolic / safety / recovery / acquisition / capability` now contribute to drive-weighted scoring instead of silently scoring zero.
- **Tests added**: `tests/l3_deliberation/reasoning/test_drive_scoring_scenario_neutrality.py` — 7 tests covering unit-level scoring (positive, negative, missing, empty schema) and integration through `assess_candidates`.

### 1.B-1-b: Fix B — withhold gate generalized

- **File**: `eva/l3_deliberation/reasoning/conflict_detection.py:96-103`
- **Constant added**: `DRIVE_LEVEL_RELEASE_THRESHOLD = 0.3` (with explanatory comment)
- **Change**: replaced `if top_drive != "integrity" and threat_count <= 0:` with `if top_drive_level < DRIVE_LEVEL_RELEASE_THRESHOLD and threat_count <= 0:`. The gate now triggers when the top drive's level is below the release threshold (any scenario's drive vocabulary works), not when the top drive name fails to match the Linux-specific ``"integrity"`` magic-string.
- **Helper added**: `_coerce_drive_level(value)` at module bottom — clamps any payload value to [0, 1] with a 0 fallback.
- **Linux equivalence**: operationally equivalent. Any realistic Linux state with `top_drive == "integrity"` has integrity level ≥ 0.3 (otherwise some other drive would have overtaken as top). Corner case where Linux integrity is the top drive but its level is < 0.3 is a degenerate state that essentially does not occur in production.
- **Crafter unlock**: Crafter agents with any high drive (metabolic / safety / acquisition etc. at 0.3+) can now release without requiring a threat signal.
- **Tests added**: `tests/l3_deliberation/reasoning/test_conflict_detection_scenario_neutrality.py` — 6 tests covering Crafter acquisition-high-passes, all-low-still-withholds, Linux integrity-high-passes, Linux integrity-low-now-withholds (documented behavior change), threat-alone-passes, drive_levels=None-defensive.

### 1.B-1-c: Fix C — score adjustments generalized + reason tag rename

- **File**: `eva/l3_deliberation/reasoning/conflict_detection.py:107-127`
- **Constant added**: `HIGH_DRIVE_PROJECTION_THRESHOLD = 0.5`
- **Changes**:
  - `stabilize_first` boost (+0.75): fires when `top_drive_level >= HIGH_DRIVE_PROJECTION_THRESHOLD` (was `top_drive == "integrity"`)
  - `observe_first` boost (+0.25): fires when `top_drive_level < HIGH_DRIVE_PROJECTION_THRESHOLD` (was `top_drive != "integrity"`)
  - `escalate_first` boost (+1.0): fires when `top_drive_level >= HIGH_DRIVE_PROJECTION_THRESHOLD` (was `top_drive == "integrity"`)
- **Reason tag rename**:
  - `integrity_projection_for_stabilize_first` → `high_drive_projection_for_stabilize_first`
  - `non_integrity_projection_for_observe_first` → `low_drive_projection_for_observe_first`
  - `integrity_projection_for_escalate_first` → `high_drive_projection_for_escalate_first`
- **Reason tag consumers**: verified via grep that these tags are only consumed by tests (no production analyzer / stability_metrics consumer reads them). Tests updated to new tag names (`test_conflict_detection.py:82`, `test_conflict_detection.py:120`, `test_value.py:82`).
- **Linux equivalence**: operationally equivalent. Linux `top_drive == "integrity"` typically implies integrity level ≥ 0.5 in any state where the projection boost was meaningful.

### 1.B-1-d: Fix F — working_memory routing generalized

- **Files**:
  - `eva/l3_deliberation/memory/working_memory_adapter.py:101-127`
  - `eva/l3_deliberation/memory/working_memory_model_client.py:115-141`
- **Per-module constants**: `_HIGH_DRIVE_ROUTING_THRESHOLD = 0.5` (adapter) and `_HIGH_DRIVE_CLIENT_THRESHOLD = 0.5` (model client). Kept module-local to avoid cross-module coupling.
- **Per-module helpers**: `_coerce_drive_level(value)` added to each file. Mirrors the helper in `conflict_detection.py`.
- **Changes**:
  - Adapter: `elif top_drive == "integrity":` → `elif top_drive_level >= _HIGH_DRIVE_ROUTING_THRESHOLD:` — routes to `stabilize_first` based on level, not name.
  - Model client: `elif conservative_mode or top_drive == "integrity":` → `elif conservative_mode or top_drive_level >= _HIGH_DRIVE_CLIENT_THRESHOLD:` — preserves the OR-with-conservative-mode semantic.
- **Reason tag rename** (adapter only):
  - `integrity_pressure_prefers_stabilization` → `high_drive_pressure_prefers_stabilization`
  - `top_drive_integrity` → `top_drive_high:{top_drive}` (formatted with the actual drive name, more informative)
- **Linux equivalence**: same logic as B/C. Existing adapter / client tests updated to supply explicit `drive_levels` (the pre-fix tests used `drive_levels={}` which under new logic would route to `observe_first`).
- **Tests added**: `tests/l3_deliberation/memory/test_working_memory_routing_scenario_neutrality.py` — 7 tests covering both adapter and model client across Crafter high, Linux high, low drive, conservative mode.

### 1.B-1-e: Fix D + E — explicit error on malformed deserialization

- **File**: `eva/kernel/state.py:248-260` and `eva/kernel/state.py:320-331`
- **Changes**:
  - `ActivePressure.from_dict`: `type=str(payload.get("type", "continuity"))` → `type=str(payload["type"])`. Missing `type` field now raises `KeyError`.
  - `DriveState.from_dict`: `drive_type=str(payload.get("drive_type", "survival"))` → `drive_type=str(payload["drive_type"])`. Missing `drive_type` field now raises `KeyError`.
- **Linux equivalence**: bit-equivalent for any well-formed production payload. The defaults were never reached in practice — production `to_dict` always writes these fields. The fix simply makes the failure mode loud rather than silent.
- **Tests added**: `tests/kernel/test_state_deserialization_errors.py` — 4 tests covering both classes' error semantics + round-trip sanity for non-Linux drive vocabulary.

## Documented behavior changes (not regressions)

Three Linux tests required test-data updates to keep their original intent under the new scenario-neutral semantics. None required test-logic structure changes.

| Test | Pre-fix data | Post-fix data | Why |
|---|---|---|---|
| `test_threat_signal_without_integrity_top_drive_still_allows_release` | `survival: 0.8` | `survival: 0.35` | Test intent: "release works for non-integrity top drive." Under new logic, `survival: 0.8` produces `high_drive_projection_for_stabilize_first` instead of the old observe-first boost. Lowering to 0.35 keeps the test exercising the low-drive observe-first branch as intended. |
| `test_default_inhibition_withholds_without_release_pressure` | `curiosity: 0.8` | `curiosity: 0.2` | Test intent: "no release pressure → withhold." Under new logic, `curiosity: 0.8` IS release pressure (per v0.6.1 §4 exploration semantics). Lowering to 0.2 puts the test back in "no pressure" territory. |
| `test_run_deliberation_emits_no_memory_stub_without_threat_or_release` | `curiosity: 0.8` | `curiosity: 0.2` | Same reasoning as above — preserves the "withhold → no stub" test intent under new release semantics. |

These are **principled behavior changes** that align Linux with v0.6.1 §4: high curiosity-style drive levels now constitute legitimate release pressure (which is precisely what Round 1.B-2 / W3 will leverage when adding the explicit exploration drive to Crafter).

The `test_linux_low_integrity_no_threat_now_correctly_withholds` corner-case test in `test_conflict_detection_scenario_neutrality.py` documents this asymmetry explicitly: under the OLD code, integrity-very-low-no-threat passed the gate purely because the name matched ``"integrity"``; under the NEW code it correctly withholds because no real pressure exists.

## Files changed

### Modified (framework, 5 files)
- `eva/l3_deliberation/reasoning/value_judgment.py`
- `eva/l3_deliberation/reasoning/conflict_detection.py`
- `eva/l3_deliberation/memory/working_memory_adapter.py`
- `eva/l3_deliberation/memory/working_memory_model_client.py`
- `eva/kernel/state.py`

### Modified (existing test assertion updates, 6 files)
- `tests/l3_deliberation/reasoning/test_value.py` (1 reason tag rename + 1 data update)
- `tests/l3_deliberation/reasoning/test_conflict_detection.py` (2 reason tag renames)
- `tests/l3_deliberation/memory/test_working_memory_adapter.py` (1 tag rename + 1 data update)
- `tests/l3_deliberation/memory/test_working_memory_model_client.py` (1 data update)
- `tests/l3_deliberation/peer_circuit/test_mediator.py` (1 data update)
- `tests/l3_deliberation/memory/test_stub.py` (1 data update)

### Added (new tests, 4 files)
- `tests/l3_deliberation/reasoning/test_drive_scoring_scenario_neutrality.py` (7 tests)
- `tests/l3_deliberation/reasoning/test_conflict_detection_scenario_neutrality.py` (9 tests)
- `tests/l3_deliberation/memory/test_working_memory_routing_scenario_neutrality.py` (7 tests)
- `tests/kernel/test_state_deserialization_errors.py` (4 tests)

### Maintainer docs (added)
- `maintainer/development/round-1b-1-framework-drive-semantics-de-linuxification-startup-instruction.md`
- `maintainer/development/round-1b-1-progress.md` (this file)

### Not modified
- `scenarios/` (any) — verified via `git diff main -- 'scenarios/'` shows zero Round-1.B-1 changes
- `eva/l2_drive/` — drive layer untouched
- `eva/anchor/`, `eva/l1_sensing/`, `eva/scenario_bundle.py`, `eva/kernel/main.py`, `eva/kernel/lifecycle.py`, `eva/kernel/instance.py`, `eva/kernel/config.py` — all untouched

## Verification log

| Step | Result |
|---|---|
| 1.B-1-a fix + tests | 7 new tests pass; full regression 323/323 |
| 1.B-1-b/c fix + tests | 9 new tests pass; full regression 332/332 (3 existing Linux tests required data updates per documented semantic shift) |
| 1.B-1-d fix + tests | 7 new tests pass; full regression 339/339 (2 existing adapter/client tests required data updates for drive_levels) |
| 1.B-1-e fix + tests | 4 new tests pass; full regression 343/343 |
| Final regression | **343 / 343 OK** |
| `git diff main -- 'scenarios/'` for Round 1.B-1 only | empty (Crafter SPEC changes shown in diff are from Round 1.A, not 1.B-1) |

## Round 1.B-1 exit criteria status

| Criterion | Status |
|---|---|
| Linux full suite passes | ✅ 343/343 |
| Crafter `_drive_weighted_score` non-zero on Crafter vocab | ✅ test_drive_scoring_scenario_neutrality |
| Crafter conflict_detection accepts non-integrity high drives | ✅ test_conflict_detection_scenario_neutrality |
| Crafter working_memory routing engages stabilize on high drive | ✅ test_working_memory_routing_scenario_neutrality |
| `from_dict` raises on missing required field | ✅ test_state_deserialization_errors |
| Zero scenario / Linux scenario / L2 / anchor / kernel-runtime changes | ✅ verified via git diff |

## Surfaced for future follow-up (not blocking)

1. **`top_drive == "integrity"` checks in other code paths**: I did a broad scan but only found name-based magic-string checks in the 6 locations addressed here. If any future paths surface, fix them at point of discovery per the same pattern.

2. **`top_drive == "integrity"` in `_situation_key` construction (working_memory_adapter line 115 area)**: there's a `working_memory_adapter.py:115 elif top_drive == "integrity":` style check that the adapter uses for memory routing — that's been fixed. The `situation_key` building elsewhere doesn't carry similar coupling.

3. **`pressure.type == "integrity"` checks**: separate from this fix's scope. These check pressure TYPE (a framework-level pressure category) not drive type. Crafter scenarios have their own pressure types (safety, metabolic, etc.). These checks may still be appropriate where they appear (e.g., L1 routing for integrity-class pressures); audit recommended but not blocking Round 1.B-2.

4. **Threshold constants duplicated across files**: `_HIGH_DRIVE_ROUTING_THRESHOLD` / `_HIGH_DRIVE_CLIENT_THRESHOLD` / `HIGH_DRIVE_PROJECTION_THRESHOLD` are three module-local constants with the same value (0.5). Kept local to avoid cross-module coupling. If they ever need to differ, the per-module home is right; if they should be locked together, promote to a shared module. Not urgent.

## Ready for Round 1.B-2

The exploration drive (W3) in Round 1.B-2 is now unblocked. With Fix A in place, an `exploration` drive in `scenarios/crafter/drive_preset.py` will contribute to candidate scoring whenever its level is non-zero. With Fix B/C in place, exploration drive being high (in healthy / no-threat moments) will pass the release gate and engage the observe-first or escalate-first projection paths. With Fix F in place, working_memory routing will respect exploration as a real drive.

The Crafter agent will finally have the structural conditions necessary for "agent acts from internal exploration pull in low-pressure healthy moments" — the v0.6.1 §4 commitment.
