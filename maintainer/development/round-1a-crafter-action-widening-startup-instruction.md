# Round 1.A — Crafter Action-Resolution Widening — Startup Instruction for Claude Code

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.A startup — Crafter action-resolution widening (Option α, within existing 3-profile vocabulary)

**Companion documents** (must be read before starting):
- `.claude/plans/federated-snacking-engelbart.md` — full Round 1 plan and context for why this slice exists
- `scenarios/crafter/SPEC.md` — current Crafter scope (Stage H landed state)
- `maintainer/development/stage-h-progress.md` — Stage H closeout (line 170: "bounded compatibility vocabulary" was intentional Stage H trade-off)
- `docs/architecture-implementation-blueprint-v0.6.md` §4 (anchors), §7.3 (memory), §7.9 (provenance) — target architecture boundaries to respect
- `eva/l3_deliberation/reasoning/conflict_detection.py:47-50` — framework-level 3-profile whitelist (the boundary we do NOT cross in this slice)

---

## 1. What this work is and is not

This is **Round 1.A — the foundation slice for Round 1**. After Stage I closeout, the Crafter agent's candidate generation is hardcoded to 3 actions (noop / sleep / do) out of 17 defined Crafter game actions. This means:
- Prior skills are defined but dead code (`select_response_action` never consults them)
- 22 Crafter achievements are unreachable (agent cannot chop, place, or craft)
- `task_progress` is always 0 in learning outcomes
- The agent's behavior surface is "stay alive doing nothing meaningful"

This was an intentional Stage H scope-narrowing to focus on framework boundary validation, **but the widening was never scheduled as a Stage H followup**. Round 1.A resolves this.

**What Round 1.A is**:
- Widen `build_integrity_response_candidates` to read its inputs (pressure, runtime_state, observation) and emit context-resolved concrete actions
- Wire `CRAFTER_STARTUP_PRIOR_DEFINITIONS` into candidate resolution so prior skills actually influence which actions appear
- Wire habit bias and inherited prior bias into `select_response_action` so accumulated experience and inheritance actually shape selection
- Keep all this within the existing 3-profile vocabulary (`observe_first / stabilize_first / escalate_first`)
- Produce a Crafter agent that demonstrably chops, mines, places, crafts — i.e., that actually plays Crafter

**What Round 1.A is NOT**:
- Not adding new candidate profiles. The framework whitelist at `conflict_detection.py:47-50` stays untouched. (That is Option β, deferred.)
- Not building a Crafter-specific action abstraction outside the profile vocabulary. (That is Option γ, deferred.)
- Not adding exploration drive. That is Round 1.B (W3).
- Not adding semantic → L2 drive path. That is Round 1.B (W5).
- Not adding semantic memory indexing. That is Round 1.C (W4).
- Not modifying any file under `eva/`. Framework code is untouched.
- Not modifying `scenarios/linux_runtime/`. Linux behavior is bit-exact equivalent.
- Not adding new action vocabulary — all 17 actions are already defined in `scenarios/crafter/actions/compatibility.py:36-54` as `ALL_ACTIONS`.
- Not changing release authority, mediator default inhibition, or anchor admission boundaries.
- Not changing `OutcomeVector` schema or `_build_execution_payload` — they already handle the full action surface correctly.

The reason for this strict boundary: Round 1.B (exploration drive, semantic→drive) is only meaningful on top of an agent that can actually take diverse actions. Round 1.A is the gate. Keeping Round 1.A within scenario boundaries means no framework risk during this foundational work.

---

## 2. Exit criterion

Round 1.A is complete when **all** of the following hold:

### Behavioral
- A smoke run via `python -m runners.run_crafter --max-ticks 200` shows the agent selecting **more than 3 distinct concrete actions** across the run (verify by inspecting response_history.jsonl `selected_action` field).
- At least one Crafter achievement is unlocked in an integration test run (verify by `achievement_delta > 0` appearing in `response_history.jsonl` or `learning_outcomes.jsonl`).
- At least one `learning_outcomes.jsonl` record shows `task_progress > 0`.
- A demonstrably prior-skill-driven test: given a contrived `agent_observation` with a visible resource AND an acquisition-relevant prior in the active bundle, the selected action is the acquisition-relevant action (e.g., `do` toward the resource or a `move_*` toward it), not a generic `noop`.
- A demonstrably habit-driven test: given accumulated `habit_bias` favoring one specific concrete action under a given situation_key, that action is preferred over alternative actions of the same profile.

### Engineering
- Full regression: all existing tests pass after Round 1.A. Existing tests that asserted "exactly 3 candidates" or "always noop/sleep/do" are expected to need updates; those updates must change only assertion data (the assertion of widened behavior), not test logic structure.
- New tests added (see §5).
- `git diff --name-only main...` shows zero modifications under `eva/`.
- `git diff --name-only main...` shows zero modifications under `scenarios/linux_runtime/`.
- Linux smoke run via `python -m runners.run_linux --max-ticks 200` produces equivalent traces to a pre-Round-1.A baseline run.

### Documentation
- `scenarios/crafter/SPEC.md` §H-2 actions section updated to reflect widened candidate resolution.
- `docs/implementation-tracking.md` Crafter row reflects post-1.A capability state.
- `maintainer/development/stage-h-followups.md` appended with a note that "widening was identified post-Stage-H and addressed in Round 1.A".
- `maintainer/development/round-1a-progress.md` written and closed.
- `maintainer/development/current-intake.md` closeout updated.

---

## 3. Scope target state

After Round 1.A, the Crafter action resolution path looks like:

```
build_integrity_response_candidates(pressure, runtime_state, observation, priors, habit_summary)
  ↓
  for each profile in {observe_first, stabilize_first, escalate_first}:
      resolve concrete action(s) appropriate to this profile in this context
      attach provenance: which prior / habit drove the resolution (if any)
  ↓
  list[ResponseCandidate]  (may contain multiple candidates per profile)

select_response_action(pressure, runtime_state, candidates, decisions, habit_bias, inherited_prior)
  ↓
  score each candidate using:
      base profile fit (current 3-profile mapping)
      habit bias for (situation_key, candidate.action) if present
      inherited prior bias if matches
      drive impact under current pressure
  ↓
  pick highest-scoring; record reasons
```

### Files in scope (Crafter scenario only)

**Primary**:
- `scenarios/crafter/actions/compatibility.py` — main widening; rebuild `build_integrity_response_candidates` and `select_response_action`
- `scenarios/crafter/prior_skills/compatibility.py` — wire `CRAFTER_STARTUP_PRIOR_DEFINITIONS` into candidate resolution; currently this file checks profile membership only (line 23-24); extend to surface specific action recommendations per profile per context
- `scenarios/crafter/prior_skills/bundle.py` — if needed, expose context-aware accessors on the prior bundle

**Test files**:
- `tests/scenarios/crafter/test_actions.py` — extend to cover widened resolution; existing "exactly 3 candidates" assertions will need updating
- `tests/scenarios/crafter/test_prior_skills.py` — extend to validate prior → resolution path
- `tests/scenarios/crafter/test_prior_guided_candidates.py` — this currently tests projection onto profile vocabulary; extend to test concrete-action resolution
- `tests/scenarios/crafter/test_outcome_observers.py` — verify outcome observer handles full action set (it already should, but add coverage)
- `tests/integration/test_crafter_runtime.py` — extend to validate achievement unlock during integration run
- New: `tests/scenarios/crafter/test_action_widening_smoke.py` — smoke test for the new behavior

### Files NOT in scope (do not modify)

**Framework** (eva/):
- `eva/l3_deliberation/reasoning/conflict_detection.py` — 3-profile whitelist stays
- `eva/l3_deliberation/tool_edge/` — release path unchanged
- `eva/l2_drive/` — drive layer unchanged
- `eva/l1_sensing/` — sensing unchanged
- `eva/anchor/` — anchor surface unchanged
- `eva/kernel/` — kernel / state / runtime loop unchanged
- `eva/scenario_bundle.py` — bundle contract unchanged
- `eva/skills/` — skill type definitions unchanged

**Other scenarios**:
- `scenarios/linux_runtime/` — entire Linux scenario must be bit-exact equivalent

---

## 4. Implementation slices

Recommended order. Each slice should be a separate commit.

### A-1: Failing tests pinning target behavior

Before any implementation changes, add failing tests that pin down what "widened" means. This commit's tests will fail, demonstrating the gap.

Tests to add (all in `tests/scenarios/crafter/`):

- `test_action_widening_smoke.py::test_candidate_set_exceeds_three_under_acquisition_pressure` — construct a scenario state with acquisition pressure + visible resource; assert candidate set includes at least one concrete action beyond noop/sleep/do.
- `test_action_widening_smoke.py::test_prior_skill_shapes_candidate_resolution` — construct state with an acquisition prior active; assert the resolved escalate_first action is acquisition-relevant, not generic do.
- `test_action_widening_smoke.py::test_habit_bias_drives_selection` — construct state with synthetic habit_bias favoring a specific concrete action; assert selection picks that action over equally-eligible alternatives.

These tests should fail on the current `main`. Commit them as `failing tests for Round 1.A widening`.

### A-2: Profile-to-action mapping table

Add a profile-to-eligible-actions mapping inside `scenarios/crafter/actions/compatibility.py`:

```python
PROFILE_ELIGIBLE_ACTIONS = {
    "observe_first":   (NOOP, MOVE_LEFT, MOVE_RIGHT, MOVE_UP, MOVE_DOWN),
    "stabilize_first": (SLEEP, NOOP),
    "escalate_first":  (DO, PLACE_STONE, PLACE_TABLE, PLACE_FURNACE, PLACE_PLANT,
                         MAKE_WOOD_PICKAXE, MAKE_STONE_PICKAXE, MAKE_IRON_PICKAXE,
                         MAKE_WOOD_SWORD,  MAKE_STONE_SWORD,  MAKE_IRON_SWORD),
}
```

Suggested rationale to encode as comments:
- `observe_first`: low-impact, exploratory or wait-and-see actions. Movement counts as observe because it costs little and surfaces new information.
- `stabilize_first`: maintenance / recovery actions. Sleep is the canonical case; noop is allowed under stabilize when no action is preferable to a risky one.
- `escalate_first`: actions that change the world state — direct action `do` (which can attack, chop, mine depending on context), placement, and crafting.

This commit just adds the mapping table + small accessor helper. No behavior change yet.

### A-3: Context-aware candidate generation

Rebuild `build_integrity_response_candidates` to:
1. Stop using `del pressure, runtime_state`.
2. Read `pressure.evidence` to understand current pressure reason.
3. Read `runtime_state` for current life_state and any cached observation context.
4. Read inherited prior bundle from runtime context (if available; degrade gracefully if not).
5. For each profile, generate one or more candidates whose concrete actions are selected from `PROFILE_ELIGIBLE_ACTIONS[profile]` based on:
   - Pressure reason (e.g., `inventory_sparse` favors `do` and `place_*`; `health_critical` favors `sleep`)
   - Prior skill recommendations (`CRAFTER_STARTUP_PRIOR_DEFINITIONS`)
   - Available observation cues (e.g., visible threat increases preference for combat-relevant escalate)
6. Attach provenance to each candidate (`reason` field) indicating why this concrete action was chosen for this profile.

Constraint: never return zero candidates. If no context-appropriate concrete action exists for a profile, fall back to the original mapping (observe_first→noop, stabilize_first→sleep, escalate_first→do).

This is the heart of the slice. After this commit, the failing A-1 tests for candidate-set size should start passing. The selection-related tests still fail.

### A-4: Habit + prior bias in selection

Rebuild `select_response_action` to:
1. Read habit_bias entries from working_memory / state (passed in via `bridge_policy` if needed; or via a new parameter — see Stage I followup #3 watch on parameter accumulation; prefer adding a single optional payload param over many positional params).
2. For each candidate, compute a score combining:
   - Drive impact (using existing `value_judgment` machinery if accessible, or a small local approximation if pulling that in widens scope too much)
   - Habit bias for (situation_key, candidate.action)
   - Inherited prior bias
3. Select highest-scoring candidate; record selection reason in `selected_action_reason`.

After this commit, the failing A-1 test for habit-driven selection should pass.

### A-5: Outcome observer compatibility check

Verify (do not modify unless necessary) that `scenarios/crafter/outcome_observers/compatibility.py` correctly:
- Computes `achievement_delta > 0` when an `make_*` or `place_*` action unlocks an achievement
- Computes `capability_delta` for the new action set
- Computes `task_progress` from achievements

Add tests for these paths if not already covered. If a real bug surfaces, fix it; otherwise document that no change was needed.

### A-6: Integration test

Extend `tests/integration/test_crafter_runtime.py` to:
- Run for at least 200 turns (more if needed)
- Assert at least 4 distinct selected_action values across the run
- Assert at least one achievement unlocked OR at least one positive task_progress recorded

This is the live confirmation that the widening works end-to-end.

### A-7: Manual smoke

After the integration test passes, run:
```
python -m runners.run_crafter --max-ticks 500
```
and inspect:
- `<runtime_dir>/response_history.jsonl` — distinct selected_action count, achievement_delta values
- `<runtime_dir>/learning_outcomes.jsonl` — task_progress values
- `<runtime_dir>/deliberation_audit.jsonl` — selection reasons

Document findings in `round-1a-progress.md`.

### A-8: Docs sync + closeout

- Update `scenarios/crafter/SPEC.md` §H-2 actions section.
- Update `docs/implementation-tracking.md` — Crafter row reflects widened state; add a note about action-resolution widening if appropriate.
- Update `docs/implementation-tracking-zh.md` to match.
- Append note to `maintainer/development/stage-h-followups.md` that widening was identified post-Stage-H and resolved in Round 1.A.
- Write `maintainer/development/round-1a-progress.md` capturing slice-by-slice progress and final state.
- Update `maintainer/development/current-intake.md` to closeout state.
- Note in `.claude/plans/federated-snacking-engelbart.md` that Round 1.A is complete (architect will confirm; do not self-mark gates).

---

## 5. Tests

### Tests to freeze (must continue passing without logic modification)

- `tests/kernel/`
- `tests/l1_sensing/`
- `tests/l2_drive/`
- `tests/l3_deliberation/` (all subdirectories)
- `tests/anchor/`
- `tests/scenarios/linux_runtime/` (all)
- `tests/scenarios/crafter/test_drive_preset.py`
- `tests/scenarios/crafter/test_sensors.py`
- `tests/scenarios/crafter/test_anchors.py`
- `tests/scenarios/crafter/test_persistence_hierarchy.py`
- `tests/scenarios/crafter/test_skill_provenance.py`
- `tests/scenarios/crafter/test_wrapper_smoke.py`
- `tests/scenarios/crafter/test_learning_integration.py`
- `tests/stability_metrics/`
- `tests/inheritance_distillation/`

### Tests that will need assertion updates (allowed)

These tests currently assert behavior that is intentionally changing:
- `tests/scenarios/crafter/test_actions.py` — assertions about candidate set size and content
- `tests/scenarios/crafter/test_outcome_observers.py` — may need to add cases for the wider action set; existing assertions on noop/sleep/do remain valid
- `tests/scenarios/crafter/test_prior_skills.py` — assertions about prior effects (currently asserting "exists but inert")
- `tests/scenarios/crafter/test_prior_guided_candidates.py` — assertions about candidate guidance
- `tests/integration/test_crafter_runtime.py` — may need to extend turn count and add wider-action assertions

Changes to these tests must be assertion-data changes, not logic-structure changes. If a test cannot pass with only assertion-data updates, that's a sign of unintended scope expansion — pause and review.

### New tests to add

- `tests/scenarios/crafter/test_action_widening_smoke.py` (new file) — at minimum the three tests described in slice A-1
- Coverage extensions in the existing test files for the new resolution paths

---

## 6. Boundary / invariants

These must be preserved through Round 1.A. Violation is a stop condition.

### Framework-level invariants (untouched in this slice)

- Heartbeat-first lifecycle (`eva/kernel/main.py`)
- Instance legitimacy (`eva/kernel/instance.py`)
- 3-profile candidate vocabulary (`eva/l3_deliberation/reasoning/conflict_detection.py:47-50`)
- Mediator default inhibition + selective release (`eva/l3_deliberation/peer_circuit/mediator.py`)
- Anchor pre-generative restriction (`eva/anchor/domain_restriction.py`)
- Release token boundary (`eva/l3_deliberation/contracts.py`)
- Append-only artifact discipline (no schema changes, no new persistence files in this slice)
- Drive read-only broadcast (`eva/l2_drive/drive_registry.py`)

### Scenario-level boundaries

- Linux scenario behavior bit-exact equivalent (verified by Linux smoke + Linux test suite passing)
- Crafter scenario contract: still uses `RuntimeScenarioBundle` + sensor/action/anchor/outcome/prior bundles in the same shapes
- Crafter agent observation contract unchanged (no semantic / no absolute coordinates / no hidden state)

### Banned changes in this slice

- No new dependencies (no new imports from outside the existing module graph)
- No new persistence files or schema changes
- No changes to `eva/` (verify with git diff)
- No changes to `scenarios/linux_runtime/` (verify with git diff)
- No new threads, async, or signal handling (the graceful interrupt is Round 1.D-1, not 1.A)

---

## 7. Architect gates

### Gate G1 — pre-implementation intake review

Before starting slice A-1, write a change intake into `maintainer/development/current-intake.md` following the existing template structure. The intake must explicitly state:
- Layer: `scenarios/crafter/` (not framework)
- Canonical owners touched
- Profile vocabulary unchanged
- Tests to freeze (per §5)
- Docs to sync (per §4 A-8)

Present the intake to the architect. Architect approves G1 before implementation starts.

### Gate G2 — post-1.A smoke review

After slice A-7 (manual smoke), present:
- A concrete count of distinct selected_action values from the smoke run
- An example trace excerpt showing an achievement unlock
- A summary of which prior skills demonstrably influenced behavior
- The diff `git diff main -- 'eva/' 'scenarios/linux_runtime/'` showing no changes there

Architect approves G2 before moving to Round 1.B.

---

## 8. Notes and known gotchas

### `select_response_action` parameter accumulation

This function currently takes `(pressure, runtime_state, candidates, decisions, bridge_policy)`. Round 1.A needs to add habit_bias + inherited_prior. Stage I followup #3 has working_memory interface signature on watch; the same concern applies here. **Recommendation**: introduce a single optional `selection_context: dict` payload rather than multiple positional/keyword params, so we don't accumulate the same debt this function had to avoid.

### Conflict detection profile whitelist

`conflict_detection.py:47-50` will reject any candidate with profile outside `{observe_first, stabilize_first, escalate_first}`. We are NOT touching this. All Round 1.A candidates must have one of these three profiles in their `parameter_domain["candidate_profile"]`.

### Working-memory context payload

The `working_memory_context["inherited_priors"]` field is the canonical source for inherited prior bias at this seam (see `scenarios/crafter/SPEC.md` §"Stage I I-4 inherited-prior reuse"). The working memory adapter assembles this. Round 1.A should consume it, not modify it.

### Habit bias source

Habit bias entries live in `habit_bias.jsonl` and are read by working memory assembly (`eva/l3_deliberation/reasoning/working_memory.py`). They are surfaced into the deliberation path as `habit_summary` entries. Round 1.A should consume the latest habit summaries via the existing working memory surface — do not add a new read path.

### Outcome observer is the existing surface

The wrapper-level `_build_execution_payload` (lines 158-185 in `actions/compatibility.py`) already computes the full delta vector correctly for any action. Verify by reading; do not modify.

### Crafter outcome confidence

Stage H followup #3 notes that Crafter outcome confidence is currently placeholder. This is **out of scope for Round 1.A**. If you observe that placeholder confidence is causing learning to misfire after widening, add a finding to `round-1a-progress.md` rather than fixing in this slice.

---

## 9. Recommended starting flow

1. Read companion documents listed in the header.
2. Read full content of `scenarios/crafter/actions/compatibility.py`, `prior_skills/compatibility.py`, `prior_skills/bundle.py`.
3. Read the three relevant test files: `test_actions.py`, `test_prior_skills.py`, `test_prior_guided_candidates.py`.
4. Write the intake into `current-intake.md` and request G1 approval.
5. After G1 approval, proceed slice by slice (A-1 → A-8). Each slice is one commit.
6. After A-7 smoke, request G2 approval.

---

## 10. References

- This plan: `.claude/plans/federated-snacking-engelbart.md`
- v0.6 blueprint: `docs/architecture-implementation-blueprint-v0.6.md`
- Crafter SPEC: `scenarios/crafter/SPEC.md`
- Stage H closeout: `maintainer/development/stage-h-progress.md`, `maintainer/development/stage-h-followups.md`
- Stage I followups (parameter accumulation concern): `maintainer/development/stage-i-followups.md` §3
- Framework profile whitelist: `eva/l3_deliberation/reasoning/conflict_detection.py:47-50`
- Existing candidate generation: `scenarios/crafter/actions/compatibility.py:62-73`
- Existing selection: `scenarios/crafter/actions/compatibility.py:98-121`
- Action vocabulary already defined: `scenarios/crafter/actions/compatibility.py:13-54`
- Wrapper execution path: `scenarios/crafter/actions/compatibility.py:124-185`
