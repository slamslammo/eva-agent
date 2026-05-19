# Round 1.B-2 — Crafter Exploration Drive (W3) — Startup Instruction for Claude Code

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.B-2 startup — register exploration drive in Crafter scenario; v0.6.1 §4 "exploration as growth driver" landing for Crafter

**Companion documents**:
- `.claude/plans/federated-snacking-engelbart.md` — Round 1 plan
- `maintainer/development/round-1b-1-progress.md` — Round 1.B-1 closeout (framework de-Linuxification, the prerequisite that unblocked W3)
- `scenarios/crafter/drive_preset.py` — Crafter drive preset (the canonical owner being modified)
- `eva/l2_drive/drive_registry.py` — framework drive preset + curiosity-update semantics (re-read; we are NOT modifying this file)
- `eva/l2_drive/drive_state.py` — framework `_curiosity_delta` path (re-read; we are NOT modifying this file)
- `scenarios/crafter/anchors/policy.py` — `COMPATIBILITY_RELEASE_IMPACT` (the canonical owner being modified to include exploration drive impact per profile)

---

## 1. What this work is and is not

This is **Round 1.B-2**, the W3 capability landing in Crafter. After Round 1.B-1 made framework reasoning scenario-neutral, the path is now open for Crafter to register an exploration drive that actually affects agent behavior.

**Core insight**: framework already has a curiosity-style drive update mechanism. `DrivePreset.curiosity_drive_type` plus `_curiosity_delta` in `drive_state.py` together implement "drive recovers in healthy / safe state, suppresses under threat or degraded conditions" — exactly the semantic v0.6.1 §4 demands for exploration. Linux already uses this via `curiosity_drive_type="curiosity"`. Crafter explicitly opted out at Stage H with `curiosity_drive_type=None` and `curiosity_recovery=0.0 / curiosity_suppression=0.0`. We opt back in for Crafter with the exploration name.

**What Round 1.B-2 is**:
- Add `"exploration"` to Crafter's `DRIVE_TYPES`.
- Set `curiosity_drive_type="exploration"` in `CRAFTER_DRIVE_PRESET`.
- Enable `curiosity_recovery` and `curiosity_suppression` in Crafter's `DEFAULT_DRIVE_UPDATE_POLICY` so the framework's curiosity-update path produces meaningful per-tick deltas for exploration.
- Add `exploration` impact values to `COMPATIBILITY_RELEASE_IMPACT` per profile so candidate scoring actually responds to exploration drive level.
- Add tests pinning drive recovery/suppression semantics and scoring impact.

**What Round 1.B-2 is NOT**:
- Not modifying any file under `eva/` — this is **scenario-only**. The framework already has the mechanism.
- Not adding a Crafter dimension that updates exploration drive. Exploration is an internal drive that recovers/suppresses based on overall context, not a specific sensor signal. (This is what `curiosity_delta` already implements.)
- Not changing the 3-profile vocabulary or release authority.
- Not modifying anchor admission policy. Anchor policy stays focused on safety / metabolic / recovery pressure thresholds; exploration shapes scoring inside admitted candidates.
- Not modifying Linux scenario.
- Not adding the W5 semantic→drive path (that is Round 1.B-3).
- Not building exploration-drive-specific sensors / dimensions (a possible Round 2 extension).

---

## 2. Exit criterion

Round 1.B-2 is complete when **all** of the following hold:

### Behavioral
- Crafter drive update: exploration drive **rises by `curiosity_recovery`** when the overall snapshot is healthy with no threat (verified by direct unit test on `update_drive_state`).
- Crafter drive update: exploration drive **falls by `curiosity_suppression`** when threat is present OR overall status is degraded/critical (verified by direct unit test).
- Crafter value judgment: when exploration drive is high (≥ 0.6) and other drives are low, `observe_first` candidates score higher than `stabilize_first` or `escalate_first` (verified by integration test through `assess_candidates`).
- Crafter Linux equivalence: Linux scenario behavior bit-equivalent (Linux drive preset unchanged).

### Engineering
- Full regression passes (target: 343 + ~10 new tests = ~353).
- `git diff main -- 'eva/'` shows zero modifications under framework code.
- `git diff main -- 'scenarios/linux_runtime/'` shows zero modifications.

### Documentation
- `maintainer/development/round-1b-2-progress.md` written and closed.
- `maintainer/development/current-intake.md` updated.
- `scenarios/crafter/SPEC.md` updated to reflect the new drive family (5 → 6 drives).
- `docs/implementation-tracking.md` flags "Exploration as growth driver" as production for Crafter (it stays deferred at the framework / cross-scenario level if applicable).

---

## 3. Scope target state

### Files to modify (Crafter scenario only)
- `scenarios/crafter/drive_preset.py` — add `"exploration"` to `DRIVE_TYPES`; set `curiosity_drive_type="exploration"`; tune `curiosity_recovery` and `curiosity_suppression` to non-zero values
- `scenarios/crafter/anchors/policy.py` — add `exploration` to each profile's `COMPATIBILITY_RELEASE_IMPACT` entry
- `scenarios/crafter/SPEC.md` — document the new drive family and the curiosity-style update semantic

### Files NOT to modify
- `eva/` — entire framework
- `scenarios/linux_runtime/` — Linux scenario
- `scenarios/crafter/sensors/`, `dimensions/`, `actions/`, `outcome_observers/`, `prior_skills/`, `persistence/`, `wrapper/`, `viability/` — Crafter sub-modules other than the two named above

### Test files to add / extend
- New: `tests/scenarios/crafter/test_exploration_drive.py` — direct tests on drive update semantics + scoring impact
- Possibly extend: `tests/scenarios/crafter/test_drive_preset.py` — verify drive family size and curiosity_drive_type
- Existing tests must continue to pass without logic changes; minor data updates allowed if drive-count assertions exist

---

## 4. Implementation slices

Test-first. Each sub-slice one commit.

### 1.B-2-a: Failing tests pinning target behavior

In `tests/scenarios/crafter/test_exploration_drive.py`, add the following tests:

1. **`test_exploration_drive_registered_in_crafter_preset`** — assert `CRAFTER_DRIVE_PRESET.drive_types` contains `"exploration"` and `CRAFTER_DRIVE_PRESET.curiosity_drive_type == "exploration"`.

2. **`test_exploration_recovers_under_healthy_status_no_threat`** — build an `ExternalLifeSnapshot` with overall status `"healthy"`, no threat signals; pass it through `update_drive_state` with a prior table where exploration is at 0.0; assert exploration's new level equals `curiosity_recovery`.

3. **`test_exploration_suppressed_under_threat_signal`** — same as above but with a threat signal in the signal batch; assert exploration's level decreases by `curiosity_suppression`.

4. **`test_exploration_suppressed_under_degraded_overall_status`** — overall status `"degraded"`, no threat; assert suppression still kicks in.

5. **`test_observe_first_scores_higher_when_exploration_is_high`** — go through `assess_candidates` with high exploration drive + low other drives; assert `observe_first`'s score > `stabilize_first`'s and `escalate_first`'s.

These should fail on `main` since exploration isn't registered yet.

### 1.B-2-b: Register exploration drive in Crafter preset

Modify `scenarios/crafter/drive_preset.py`:
- Add `"exploration"` to `DRIVE_TYPES` tuple. Order: append at the end (after "capability").
- Set `curiosity_drive_type="exploration"` in `CRAFTER_DRIVE_PRESET`.
- Tune `DEFAULT_DRIVE_UPDATE_POLICY`:
  - `curiosity_recovery = 0.05` (rises by 5% per tick in healthy state — matches Linux's default)
  - `curiosity_suppression = 0.12` (falls by 12% per tick under threat / degraded — matches Linux's default)
  - Other fields (base_decay, severity_*, threat_bonus) stay at current Crafter values (these apply to non-curiosity drives only).

After this slice, tests 1-4 should pass. Test 5 still fails because exploration has no `drive_impact_schema` value yet.

### 1.B-2-c: Add exploration impact to compatibility release schema

Modify `scenarios/crafter/anchors/policy.py`'s `COMPATIBILITY_RELEASE_IMPACT`:

Proposed values per profile (rationale: observe_first is the canonical exploration action; escalate also gains exploration value; stabilize is anti-exploration):

```python
COMPATIBILITY_RELEASE_IMPACT = {
    OBSERVE_FIRST_PROFILE: {
        "metabolic": 0.1,
        "safety": 0.1,
        "recovery": 0.0,
        "acquisition": 0.4,
        "capability": 0.3,
        "exploration": 0.5,   # observe is the canonical exploration-satisfying action
    },
    STABILIZE_FIRST_PROFILE: {
        # ... existing values ...
        "exploration": -0.05, # stabilize doesn't satisfy exploration
    },
    ESCALATE_FIRST_PROFILE: {
        # ... existing values ...
        "exploration": 0.3,   # escalating engages with the world — moderately exploration-satisfying
    },
}
```

(Existing non-exploration values stay unchanged. Verify by reading the file first; do not guess at the existing values.)

After this slice, test 5 should pass: high exploration × 0.5 (observe) > high exploration × -0.05 (stabilize) or × 0.3 (escalate).

### 1.B-2-d: Docs sync

- Update `scenarios/crafter/SPEC.md` §H-1 drives section to list 6 drives (add exploration) and explain the curiosity-update semantic for exploration.
- Update `docs/implementation-tracking.md`: change "Exploration as growth driver" row's status for Crafter to production (note: framework-level row stays as-is since framework just provides the mechanism; the scenario-level capability lands in Crafter).
- Update `docs/implementation-tracking-zh.md` to mirror.
- Update `docs/blueprint-to-tracking-map.md` row for exploration to reflect the Crafter landing (framework-level deferred → Crafter-level partial/production).
- Write `maintainer/development/round-1b-2-progress.md` documenting each sub-slice.
- Update `current-intake.md` closeout.

---

## 5. Tests

### Tests to freeze (no logic-structure changes)
- All `eva/` tests
- All `scenarios/linux_runtime/` tests
- All `tests/integration/` tests (will be affected at runtime but their assertions should not require updating)
- Round 1.A's `test_action_widening_smoke.py`
- Round 1.B-1's `test_*_scenario_neutrality.py` and `test_state_deserialization_errors.py`

### Tests that may need data updates
- `tests/scenarios/crafter/test_drive_preset.py` — likely asserts the drive family size or contents; expect to add "exploration" to expected list. Minor data update only.
- Possibly some Crafter tests that construct `DriveStateTable` with specific drive lists; those need to include exploration.

### New tests to add
- `tests/scenarios/crafter/test_exploration_drive.py` — the 5 tests outlined above

---

## 6. Boundary / invariants

### Must preserve
- All framework runtime invariants (heartbeat, instance legitimacy, mediator default inhibition, anchor pre-generative restriction, release token boundary, append-only artifact discipline)
- Drive read-only broadcast — adding a new drive type increases the broadcast vocabulary; consumers (L3 reasoning) must handle it via the existing scenario-neutral iteration enabled in Round 1.B-1
- 3-profile candidate vocabulary at framework level — unchanged
- Linux scenario behavior bit-equivalent (verified — Linux drive_preset untouched)
- Crafter agent observation contract — unchanged

### Banned changes
- No new framework dependencies
- No new persistence files or schema changes
- No changes to `eva/`
- No changes to `scenarios/linux_runtime/`

### Acceptable Crafter behavior changes
- Crafter's drive family expands from 5 to 6 drives
- Crafter L3 mediator may now prefer observe_first in low-pressure healthy moments (this is the WHOLE POINT)
- Crafter response_history will start showing more diverse selected_action values once L3 picks observe_first

---

## 7. Architect gates

- **G1-2B** (pre-implementation): write intake into `current-intake.md`; architect confirms scope.
- **G2-2B** (post-1.B-2-c, before docs sync): demonstrate via integration test or smoke that exploration drive is producing observable behavior shifts; architect confirms before docs sync.
- **G3-2B** (closeout): full regression green; progress doc written; architect approves moving to Round 1.B-3 (W5).

---

## 8. Threshold tuning protocol

If `curiosity_recovery = 0.05` proves too slow or too fast in smoke testing (exploration never gets high enough to dominate, or exploration dominates too aggressively):
- Adjust in steps of ±0.02
- Constraint: Linux behavior remains untouched (Linux preset is independent)
- Document chosen value in progress doc with empirical rationale

For exploration impact in `COMPATIBILITY_RELEASE_IMPACT`:
- Start with the proposed values (0.5 / -0.05 / 0.3)
- If observe_first scores aren't surfacing in smoke, increase 0.5 → 0.6 → 0.7
- Constraint: ensure escalate_first under safety pressure still wins (safety: 0.5+ should outweigh exploration: 0.3 when safety drive is high)

---

## 9. Recommended starting flow

1. Read companion documents.
2. Read full content of `scenarios/crafter/drive_preset.py` (47 lines), `scenarios/crafter/anchors/policy.py` (132 lines), and Linux's `drive_preset.py` for comparison (27 lines).
3. Write intake into `current-intake.md`.
4. Sub-slice A → B → C → D, each one commit.
5. Run full regression after each.
6. Run a smoke similar to Round 1.A's A-7 (`python -m runners.run_crafter --max-turns 100 ...`) and capture whether the L3 profile distribution actually shifts away from stabilize-first dominance. **Document the empirical result in the progress doc** — this is the moment of truth for Round 1.B (does exploration drive actually change Crafter's behavior?).
