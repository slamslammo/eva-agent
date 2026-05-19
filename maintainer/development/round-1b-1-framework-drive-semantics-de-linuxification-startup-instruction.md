# Round 1.B-1 — Framework Drive Semantics De-Linuxification — Startup Instruction for Claude Code

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.B-1 startup — framework-level fixes for Linux-coupled drive semantics surfaced during Round 1.A smoke

**Companion documents** (must be read before starting):
- `.claude/plans/federated-snacking-engelbart.md` — Round 1 plan
- `maintainer/development/round-1a-progress.md` — Round 1.A findings; A-7 smoke revealed L3 mediator's stabilize-dominance under sustained avatar degradation, which prompted the broader audit that surfaced the issues this slice resolves
- `eva/l3_deliberation/reasoning/value_judgment.py` (lines 133-144 — bug A)
- `eva/l3_deliberation/reasoning/conflict_detection.py` (lines 96-145 — bugs B and C)
- `eva/l3_deliberation/memory/working_memory_adapter.py` (line 115 — bug F)
- `eva/l3_deliberation/memory/working_memory_model_client.py` (line 131 — bug F)
- `eva/kernel/state.py` (lines 248-260 and 320-331 — bugs D and E)

---

## 1. What this work is and is not

This is **Round 1.B-1**, a **framework-level cleanup slice** that resolves six Linux-coupled drive-semantics residues surfaced when Round 1.A smoke testing revealed Crafter's L3 was misbehaving in ways that traced back to framework code authored Linux-first.

**Core problem**: framework reasoning code (value_judgment, conflict_detection, working_memory adapters) was written assuming Linux's drive vocabulary (`survival, integrity, continuity, curiosity`) and never updated to be scenario-flexible during Stage G/H. Crafter's drives (`metabolic, safety, recovery, acquisition, capability`) are silently ignored or never matched against the special "integrity" string the framework treats as the canonical action-triggering drive.

**What Round 1.B-1 is**:
- Replace hardcoded `("survival", "integrity", "continuity", "curiosity")` iteration in `_drive_weighted_score` with iteration over actually-declared drives (bug **A**, simple implementation oversight)
- Generalize `top_drive == "integrity"` semantic in `conflict_detection.py` to use a scenario-neutral `top_drive_level >= threshold` semantic, preserving Linux behavior bit-equivalent (bugs **B**, **C** — design-level Linux coupling)
- Generalize `top_drive == "integrity"` routing in working_memory paths to use the same scenario-neutral semantic (bug **F**)
- Replace Linux-flavored deserialization defaults in `state.py` with explicit-error or scenario-neutral defaults (bugs **D**, **E**, cosmetic but real Linux residue)
- Add tests that pin Linux behavior equivalence and Crafter behavioral improvements

**What Round 1.B-1 is NOT**:
- Not adding new features. No new drives, no new candidate profiles, no new memory paths.
- Not changing release authority, mediator boundary, anchor admission, or persistence semantics.
- Not adding exploration drive (W3 — that is Round 1.B-2).
- Not adding semantic → drive weight path (W5 — that is Round 1.B-3).
- Not changing the framework's drive-update mechanism in `eva/l2_drive/`.
- Not modifying `eva/scenario_bundle.py` or scenario contracts.
- Not changing the L3 mediator's profile selection logic — that is a separate concern.

The reason this work exists: Round 1.A's smoke run made it clear that the Crafter widening landed correctly but the framework's reasoning layer cannot fully exploit it because Crafter drives are second-class citizens in the reasoning code. Round 1.B-1 makes them first-class.

---

## 2. Exit criterion

Round 1.B-1 is complete when **all** of the following hold:

### Behavioral
- Linux full test suite continues to pass without test-logic modifications (assertion-data updates are acceptable only if the new behavior is provably equivalent — see §6).
- Crafter `_drive_weighted_score` now produces non-zero scores when candidate `drive_impact_schema` and `drive_levels` use Crafter drive names (new test).
- Crafter `conflict_detection.build_candidate_conflict_context` no longer returns `withhold` solely because top_drive ≠ "integrity"; when Crafter's top_drive level is non-trivially high, the disposition becomes `allow` even without threat (new test).
- Crafter `working_memory_adapter` / `working_memory_model_client` reach the previously dead `top_drive == "integrity"` branches under equivalent Crafter conditions (new test).
- `ActivePressure.from_dict` and `DriveState.from_dict` raise a clear error on malformed payloads missing the type/drive_type field, rather than silently defaulting to Linux names (new test).

### Engineering
- Full regression passes after each sub-slice (a → b → c → d → e).
- `git diff --name-only main -- 'scenarios/'` shows zero modifications under scenarios (this is framework-only work).
- Linux scenario behavior bit-equivalent on representative inputs (verified via test_value.py + test_conflict_detection.py existing tests passing unchanged).

### Documentation
- `maintainer/development/round-1b-1-progress.md` written and closed.
- `maintainer/development/current-intake.md` updated to closeout state.
- `docs/implementation-tracking.md` flags reasoning-layer scenario-neutrality as production (not partial).
- `docs/architecture-implementation-blueprint-v0.6.md` cross-check: confirm the blueprint's drive section doesn't carry stale Linux-coupling language; flag any inconsistencies in progress doc.

---

## 3. Scope target state

### Files to modify (framework only)
- `eva/l3_deliberation/reasoning/value_judgment.py` — fix A
- `eva/l3_deliberation/reasoning/conflict_detection.py` — fix B + C
- `eva/l3_deliberation/memory/working_memory_adapter.py` — fix F
- `eva/l3_deliberation/memory/working_memory_model_client.py` — fix F
- `eva/kernel/state.py` — fix D + E

### Files NOT to modify
- `scenarios/` — entire scenario tree must remain untouched
- `eva/l2_drive/` — drive layer untouched
- `eva/scenario_bundle.py` — contract untouched
- `eva/anchor/` — anchor surface untouched
- `eva/kernel/main.py`, `lifecycle.py`, `instance.py`, `config.py` — runtime loop untouched
- `eva/l1_sensing/` — sensing untouched

### Test files to add / extend
- New: `tests/l3_deliberation/reasoning/test_drive_scoring_scenario_neutrality.py` — pins fix A behavior with both Linux and Crafter drive vocabularies
- New: `tests/l3_deliberation/reasoning/test_conflict_detection_scenario_neutrality.py` — pins fix B and C behavior with both vocabularies
- New: `tests/l3_deliberation/memory/test_working_memory_routing_scenario_neutrality.py` — pins fix F behavior
- New: `tests/kernel/test_state_deserialization_errors.py` — pins fix D/E behavior
- Modify if needed: existing `test_value.py`, `test_conflict_detection.py` — only assertion-data updates allowed; logic structure unchanged

---

## 4. Implementation slices

Each sub-slice is a separate commit. Write failing test first, then fix, then verify regression.

### 1.B-1-a: Fix A — `_drive_weighted_score` iterates drive_impact_schema keys

**Failing test first**: in `tests/l3_deliberation/reasoning/test_drive_scoring_scenario_neutrality.py`, assert that a candidate with Crafter-named `drive_impact_schema` and matching Crafter `drive_levels` produces a non-zero `score` after `assess_candidates`. This test currently fails because the framework iterates Linux drive names only.

**Fix**: in `_drive_weighted_score` (lines 133-144), replace:
```python
for drive_name in ("survival", "integrity", "continuity", "curiosity"):
    score += float(drive_levels.get(drive_name, 0.0)) * float(drive_impact_schema.get(drive_name, 0.0))
```
with:
```python
for drive_name, impact in drive_impact_schema.items():
    score += float(drive_levels.get(drive_name, 0.0)) * float(impact)
```

This iterates only over drives the candidate has declared an impact for. For Linux, this set is a subset of the original hardcoded tuple, and any drive not in the candidate's impact_schema would have contributed 0 anyway (since `drive_impact_schema.get(drive_name, 0.0) == 0` for absent keys). **Linux behavior is bit-equivalent.**

**Linux equivalence test**: existing `tests/l3_deliberation/reasoning/test_value.py` must pass without assertion changes.

### 1.B-1-b: Fix B — generalize `top_drive == "integrity"` withhold gate

**Failing test first**: in `tests/l3_deliberation/reasoning/test_conflict_detection_scenario_neutrality.py`, assert that with Crafter drive vocabulary, top_drive="acquisition", drive_levels showing acquisition at 0.5+, and no threat, `build_candidate_conflict_context` returns `allow` (not `withhold`). Currently fails because the existing check `top_drive != "integrity" and threat_count <= 0 → withhold` ignores Crafter drives.

**Design constant**: add `DRIVE_LEVEL_RELEASE_THRESHOLD = 0.3` as module-level constant in `conflict_detection.py` with explanatory comment.

**Fix**: replace lines 96-103 in conflict_detection.py:
```python
if top_drive != "integrity" and threat_count <= 0:
    return CandidateConflictContext(
        candidate_profile=candidate_profile,
        disposition="withhold",
        reasons=tuple([*reasons, "no_release_pressure"]),
    )
```
with:
```python
top_drive_level = _coerce_drive_level(drive_levels.get(top_drive))
if top_drive_level < DRIVE_LEVEL_RELEASE_THRESHOLD and threat_count <= 0:
    return CandidateConflictContext(
        candidate_profile=candidate_profile,
        disposition="withhold",
        reasons=tuple([*reasons, "no_release_pressure"]),
    )
```

Add helper `_coerce_drive_level(value)` that returns `max(0.0, min(1.0, float(value)))` with default `0.0`.

**Linux equivalence reasoning**: In Linux, when `top_drive` is `"integrity"`, the integrity drive's level is virtually always ≥ 0.3 (otherwise it wouldn't be the top drive). The previous boolean check fired whenever `top_drive == "integrity"`, regardless of level. The new check fires whenever `top_drive_level >= 0.3`. For Linux, these conditions are operationally equivalent. **Threshold choice (0.3) chosen as the minimum value such that existing Linux test_value.py / test_conflict_detection.py tests pass without assertion changes.** If 0.3 fails Linux equivalence, lower to 0.25 or 0.2 — but tune empirically, not arbitrarily.

**Crafter equivalence reasoning**: previously Crafter always fell into the withhold branch when threat_count ≤ 0, regardless of drive level. Now Crafter with any drive at 0.3+ will exit the withhold gate and proceed to scoring. This is the intended behavior change.

### 1.B-1-c: Fix C — generalize integrity-specific score adjustments

**Failing test first**: extend `test_conflict_detection_scenario_neutrality.py` to assert that with Crafter drives, score_delta accumulates correctly for stabilize_first / observe_first / escalate_first based on top_drive_level, not on specific drive name.

**Design constants**:
- `HIGH_DRIVE_THRESHOLD = 0.5` — above this is "high pressure"
- `LOW_DRIVE_THRESHOLD = 0.2` — below this is "low pressure"

**Fix**: replace lines 107-127 in conflict_detection.py:
```python
if candidate_profile == anchor_profiles.stabilize_first_profile:
    if top_drive == "integrity":
        score_delta += 0.75
        pressure_reasons.append("integrity_projection_for_stabilize_first")
    if compatibility_pressure_count > 0:
        score_delta += 0.5
        pressure_reasons.append("pressure_projection_for_stabilize_first")
elif candidate_profile == anchor_profiles.observe_first_profile:
    if top_drive != "integrity":
        score_delta += 0.25
        pressure_reasons.append("non_integrity_projection_for_observe_first")
    if compatibility_pressure_count == 0:
        score_delta += 0.25
        pressure_reasons.append("low_pressure_projection_for_observe_first")
elif candidate_profile == anchor_profiles.escalate_first_profile:
    if top_drive == "integrity":
        score_delta += 1.0
        pressure_reasons.append("integrity_projection_for_escalate_first")
```
with:
```python
if candidate_profile == anchor_profiles.stabilize_first_profile:
    if top_drive_level >= HIGH_DRIVE_THRESHOLD:
        score_delta += 0.75
        pressure_reasons.append("high_drive_projection_for_stabilize_first")
    if compatibility_pressure_count > 0:
        score_delta += 0.5
        pressure_reasons.append("pressure_projection_for_stabilize_first")
elif candidate_profile == anchor_profiles.observe_first_profile:
    if top_drive_level < HIGH_DRIVE_THRESHOLD:
        score_delta += 0.25
        pressure_reasons.append("low_drive_projection_for_observe_first")
    if compatibility_pressure_count == 0:
        score_delta += 0.25
        pressure_reasons.append("low_pressure_projection_for_observe_first")
elif candidate_profile == anchor_profiles.escalate_first_profile:
    if top_drive_level >= HIGH_DRIVE_THRESHOLD:
        score_delta += 1.0
        pressure_reasons.append("high_drive_projection_for_escalate_first")
```

**Renamed reason tags**: `"integrity_projection_for_*"` → `"high_drive_projection_for_*"`, `"non_integrity_projection_for_*"` → `"low_drive_projection_for_*"`. These reason tags appear in trace files and may be referenced by stability_metrics or downstream analyzers — verify no production analyzer hardcodes the old tag names. If found, update the analyzer in the same sub-slice. (Likely candidates: `stability_metrics/metrics.py`, but the metrics there don't appear to grep `integrity_projection`.)

**Linux equivalence reasoning**: same as B. When Linux has `top_drive == "integrity"`, its level is virtually always ≥ 0.5 in any state that triggers the old `if top_drive == "integrity"` branch (because integrity is the priority drive). Tune `HIGH_DRIVE_THRESHOLD` empirically if needed.

### 1.B-1-d: Fix F — generalize working_memory routing

**Failing test first**: in `tests/l3_deliberation/memory/test_working_memory_routing_scenario_neutrality.py`, assert that with Crafter top_drive and drive_levels, working_memory_adapter and working_memory_model_client route to the previously-dead `top_drive == "integrity"` branches when Crafter's top_drive level is high.

**Fix**: in `working_memory_adapter.py:115`:
```python
elif top_drive == "integrity":
```
becomes:
```python
elif _is_high_priority_drive_state(top_drive_level):
```
where `_is_high_priority_drive_state(level)` returns `level >= HIGH_DRIVE_THRESHOLD`.

Same change in `working_memory_model_client.py:131`:
```python
elif conservative_mode or top_drive == "integrity":
```
becomes:
```python
elif conservative_mode or _is_high_priority_drive_state(top_drive_level):
```

Both files need access to `top_drive_level`, which means callers must provide it. Check call sites: if level isn't already in scope, look it up from `drive_levels.get(top_drive, 0.0)`. **Verify callers carry the needed info before refactoring**.

**Linux equivalence reasoning**: as before, Linux `top_drive == "integrity"` implies its level is non-trivial; the level-threshold check is operationally equivalent.

### 1.B-1-e: Fix D + E — explicit error on malformed deserialization

**Failing test first**: in `tests/kernel/test_state_deserialization_errors.py`, assert that `ActivePressure.from_dict({})` (missing `pressure_id`, no `type`) raises a clear error rather than silently producing a `type="continuity"` payload.

**Fix**: in `state.py:255`:
```python
type=str(payload.get("type", "continuity")),
```
becomes:
```python
type=str(payload["type"]),
```
With explicit `KeyError` if missing. Or use `str(payload.get("type") or _raise_schema_error("ActivePressure", "type"))` for a cleaner error message.

Same pattern at `state.py:325` for `drive_type`.

**Linux equivalence reasoning**: production code always serializes these fields. The default was only ever reachable via hand-crafted malformed JSON, which should fail loud. **Run regression to confirm no test relied on the silent default.** If a test does, that test is asserting reachable broken behavior and should be updated.

### Closeout

- After all sub-slices pass: write `round-1b-1-progress.md` with slice-by-slice record + Linux equivalence verification log.
- Update `current-intake.md` to closeout state.
- Update `docs/implementation-tracking.md` to mark reasoning-layer scenario-neutrality as production.

---

## 5. Tests

### Tests to freeze (must pass without logic-structure modifications)
- `tests/l2_drive/` (all)
- `tests/l1_sensing/` (all)
- `tests/kernel/` (all except new test file for D/E)
- `tests/anchor/` (all)
- `tests/scenarios/linux_runtime/` (all)
- `tests/scenarios/crafter/` (all — including Round 1.A's test_action_widening_smoke.py)
- `tests/integration/` (all)
- `tests/inheritance_distillation/` (all)
- `tests/stability_metrics/` (all)

### Tests that may need assertion-data updates (allowed)
- `tests/l3_deliberation/reasoning/test_value.py` — score values may shift slightly if Linux drive_impact_schema has zero impact for a drive name the candidate uses but the fix iteration changes which drives contribute. Verify Linux is bit-equivalent first; if not, surface as a finding.
- `tests/l3_deliberation/reasoning/test_conflict_detection.py` — reason tag names changed from `"integrity_projection_for_*"` to `"high_drive_projection_for_*"`. Assertions referring to old names need update. **This is allowed because it's a reason-tag rename, not a behavior change.**
- `tests/l3_deliberation/memory/test_working_memory_adapter.py`, `test_working_memory_model_client.py` — may need adjustment if Linux equivalence requires.

### New tests to add
- `tests/l3_deliberation/reasoning/test_drive_scoring_scenario_neutrality.py` (1.B-1-a)
- `tests/l3_deliberation/reasoning/test_conflict_detection_scenario_neutrality.py` (1.B-1-b + 1.B-1-c)
- `tests/l3_deliberation/memory/test_working_memory_routing_scenario_neutrality.py` (1.B-1-d)
- `tests/kernel/test_state_deserialization_errors.py` (1.B-1-e)

---

## 6. Boundary / invariants

### Must preserve through Round 1.B-1
- All framework runtime invariants (heartbeat-first, instance legitimacy, mediator default inhibition, anchor pre-generative restriction, release token boundary, append-only artifact discipline)
- Drive read-only broadcast — DriveStateTable / DriveBroadcast structure unchanged
- 3-profile candidate vocabulary at framework level — conflict_detection's profile whitelist untouched
- L2 drive update mechanism (`eva/l2_drive/` untouched)
- Scenario bundle contract (`eva/scenario_bundle.py` untouched)
- Linux scenario behavior bit-equivalent (verified by Linux test suite + structural reasoning per slice)
- Crafter scenario behavior (Round 1.A widening) unchanged at scenario level

### Banned changes
- No new module dependencies
- No new persistence files or schema changes (D/E fix changes error behavior, not schema)
- No changes to `scenarios/`
- No changes to release authority or anchor admission

---

## 7. Architect gates

### Gate G1-1B (pre-implementation)
- Write change intake for Round 1.B-1 into `current-intake.md`
- Request architect approval before sub-slice 1.B-1-a starts

### Gate G2-1B (post-1.B-1-a, mid-slice checkpoint)
- After Fix A lands and regression passes, report Linux equivalence verification result before moving to 1.B-1-b
- Architect can redirect at this checkpoint if Linux equivalence fails

### Gate G3-1B (post-1.B-1-e, slice complete)
- Present full regression result + Linux equivalence verification log + 5 sub-slice summary
- Architect approves Round 1.B-1 closeout before Round 1.B-2 starts

---

## 8. Threshold-tuning protocol

Three thresholds need empirical tuning:
- `DRIVE_LEVEL_RELEASE_THRESHOLD` (1.B-1-b) — recommended starting value 0.3
- `HIGH_DRIVE_THRESHOLD` (1.B-1-c, 1.B-1-d) — recommended starting value 0.5
- `LOW_DRIVE_THRESHOLD` (1.B-1-c, may not be needed depending on final design) — recommended starting value 0.2

**Tuning rule**: choose the maximum threshold that keeps **all existing Linux tests passing without assertion-data modifications**. If 0.5 breaks Linux for HIGH_DRIVE_THRESHOLD, try 0.6, 0.65, 0.7 — tune in 0.05 increments until Linux is happy. If no value works, the fix is design-broken and needs rethinking — surface to architect.

Threshold values should be promoted to module-level constants with clear comments explaining their empirical anchor.

---

## 9. Recommended starting flow

1. Read companion documents listed in the header.
2. Read full content of `value_judgment.py`, `conflict_detection.py`, `working_memory_adapter.py:100-150`, `working_memory_model_client.py:120-150`, and `state.py:240-340`.
3. Write the change intake into `current-intake.md` and request G1-1B approval.
4. Proceed sub-slice 1.B-1-a → 1.B-1-b → 1.B-1-c → 1.B-1-d → 1.B-1-e. Each is one commit.
5. Run full regression after each sub-slice. Stop and escalate if Linux equivalence fails.
6. After 1.B-1-e, write `round-1b-1-progress.md` and request G3-1B.

---

## 10. References

- This plan: `.claude/plans/federated-snacking-engelbart.md`
- v0.6 blueprint: `docs/architecture-implementation-blueprint-v0.6.md`
- Round 1.A progress (motivation): `maintainer/development/round-1a-progress.md`
- Bug A location: `eva/l3_deliberation/reasoning/value_judgment.py:133-144`
- Bug B location: `eva/l3_deliberation/reasoning/conflict_detection.py:96-103`
- Bug C location: `eva/l3_deliberation/reasoning/conflict_detection.py:107-127`
- Bug F location: `eva/l3_deliberation/memory/working_memory_adapter.py:115` and `eva/l3_deliberation/memory/working_memory_model_client.py:131`
- Bug D location: `eva/kernel/state.py:248-260`
- Bug E location: `eva/kernel/state.py:320-331`
