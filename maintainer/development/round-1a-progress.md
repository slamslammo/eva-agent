# Round 1.A Progress — Crafter Action-Resolution Widening

## Status

- **Implementation**: complete (slices A-1 through A-7 landed)
- **Regression**: 315 / 315 tests pass after each slice
- **Docs sync (A-8)**: in progress
- **G2 gate**: pending architect review

## Goal recap

Round 1.A widened Crafter agent's candidate generation so it can resolve to context-appropriate concrete actions from the existing 17-action vocabulary, rather than the legacy hardcoded 3-action set (noop / sleep / do). The widening stays within the framework-level 3-profile vocabulary (observe_first / stabilize_first / escalate_first) — no framework code modified.

## Slice-by-slice record

### A-1: Failing tests pinning target behavior

- **File**: `tests/scenarios/crafter/test_action_widening_smoke.py` (new)
- **Three tests added**:
  - `test_widening_produces_candidates_beyond_legacy_noop_sleep_do_set`
  - `test_prior_preferred_action_appears_when_eligible_under_profile`
  - `test_habit_bias_drives_selection_among_candidates_of_same_profile`
- **Initial state on current main**: 3/3 fail with `TypeError: unexpected keyword 'candidate_context'` (signature not yet widened)
- **Mid-implementation correction**: test 2 originally asserted `ResponseCandidate.parameter_domain["candidate_profile"]`; ResponseCandidate has no parameter_domain field (it lives on the L3 `Candidate` in `eva/l3_deliberation/contracts.py`, not on `ResponseCandidate` in `eva/l3_deliberation/tool_edge/tool_registry.py`). Test 2 was rewritten to assert profile via candidate `posture` token instead.

### A-2: Profile-to-action mapping table

- **File**: `scenarios/crafter/actions/compatibility.py`
- **Constants added**:
  - `PROFILE_ELIGIBLE_ACTIONS`: profile → eligible concrete-action tuple
  - `PROFILE_DEFAULT_ACTION`: profile → legacy single-action fallback
- **Mapping** (G1-approved):
  - `observe_first`: noop + 4 movement actions
  - `stabilize_first`: sleep + noop
  - `escalate_first`: do + 4 place_* + 6 make_* = 11 actions
- **Behavior change**: none. This commit only introduces the lookup table.
- **Re-exports**: `scenarios/crafter/actions/__init__.py` updated to surface new constants.

### A-3: Context-aware candidate generation

- **File**: `scenarios/crafter/actions/compatibility.py`
- **Signature change**: `build_integrity_response_candidates` now accepts an optional `candidate_context: dict | None` keyword payload. The function reads:
  - `pressure.evidence["reason"]` (and falls back to `candidate_context["pressure_reason"]`)
  - `runtime_state.life_state`
  - `candidate_context["inherited_priors"]`
  - `candidate_context["candidate_profile"]` (lifted from L3 release_context — see below)
- **Resolution helpers**:
  - `_resolve_actions_for_profile`: prior-driven actions first, then pressure-driven, deduplicated
  - `_pressure_driven_actions_for_profile`: pressure-reason heuristic per profile
    - observe + (inventory_sparse / tooling_missing / unknown) → noop + 4 movements
    - observe + (defensive pressure) → noop only
    - stabilize + any → sleep
    - escalate + (inventory_sparse / tooling_missing) → do + 2 pickaxes + 2 placements
    - escalate + (health_critical / threat_visible) → do + 2 swords
    - escalate + (other) → do
- **Profile-aware posture**: `PROFILE_TO_POSTURE` introduced — `crafter_candidate_{observe|stabilize|escalate}`. ResponseCandidate has no parameter_domain field so profile provenance is encoded in the scenario-owned posture token (framework does not interpret posture, only propagates it into traces).
- **Always emits at least one candidate per active profile**: fallback to `PROFILE_DEFAULT_ACTION` if context yielded nothing.
- **L3 profile lift**: `_candidate_context_from_release_context` extracts `release_context["candidate_profile"]` (set by the L3 mediator) and lifts it into `candidate_context["candidate_profile"]` so the bridge's widening can be restricted to the profile L3 actually selected. Without this lift, the bridge would emit candidates across all three profiles even after L3 made a choice.
- **`select_integrity_response` updated** to call `build_integrity_response_candidates(..., candidate_context=...)` with the lifted context.
- **`select_response_action.selected_posture`** changed from `ACTION_TO_POSTURE[selected_action]` (always `"crafter_candidate"`) to `selected_candidate.posture` (now profile-aware). This propagates profile provenance into `response_history.jsonl[*].selected_posture` and `deliberation_audit.jsonl`.
- **Existing test update**: `test_integrity_candidates_are_bounded_and_filterable` previously asserted `["noop", "sleep", "do"]` for a `health_critical` pressure. After A-3 the same pressure yields `["noop", "sleep", "do", "make_wood_sword", "make_stone_sword"]` (defensive escalate widening). Assertion updated; profile-aware posture assertions added.

### A-4: Habit + prior bias in selection

- **File**: `scenarios/crafter/actions/compatibility.py`
- **`select_response_action` rebuilt** to read `bridge_policy["selection_context"]` and score each candidate:
  - Habit-bias contribution: `1.0 + confidence × stability × |bias_strength|` when `(situation_key, candidate.action)` matches a habit summary. Base 1.0 ensures any matched habit reliably outranks zero-bias candidates.
  - Inherited-prior-bias contribution: `0.5 × confidence × |bias_strength|` when `(candidate_profile, candidate.action)` matches a prior. Smaller than habit because inherited priors are weaker evidence than first-hand experience.
  - Components added (not max'd) so habit+prior aligned candidate naturally outranks single-signal candidates.
- **Tie-break**: strict `>` keeps `candidates[0]` order — when no bias applies, the first context-resolved candidate wins (typically the first observe action).
- **Profile recovery**: `_profile_from_posture` reverse-looks-up profile from a candidate's posture token.
- **Selection reason**: when bias applied, `selected_action_reason` becomes `crafter_habit_bias_selection` / `crafter_inherited_prior_bias_selection` / `crafter_habit_bias_inherited_prior_bias_selection`; otherwise `crafter_minimal_selection`. This propagates provenance into traces.
- **Helpers added**: `_selection_context_from_bridge_policy`, `_score_candidate_for_selection`, `_coerce_unit`, `_coerce_bias`.

### A-5: Outcome observer compatibility check

- **File**: `scenarios/crafter/outcome_observers/compatibility.py` (verified, not modified)
- **Verification**: the existing observer correctly handles the wider action set:
  - `capability_score = 1.0 if selected_action.startswith("make_") or selected_action.startswith("place_")`
  - `reversibility = 1.0 if selected_action.startswith("move_") or selected_action == "noop"`
  - `task_progress = achievement_delta if achievement_delta != 0.0 else None`
  - `risk_delta` handles `do` with threat appropriately
- **Existing test coverage** (`tests/scenarios/crafter/test_outcome_observers.py`) already exercises `make_wood_pickaxe` with capability_delta + achievement_delta paths. No additional tests required.
- **Stage H followup #3** (Crafter outcome confidence is hardcoded placeholder) is **explicitly out of scope** for Round 1.A. Recorded here as observed-during-1.A but not addressed.

### A-6: Integration test extension

- **File**: `tests/integration/test_crafter_runtime.py`
- **New test**: `test_widened_candidates_surface_in_runtime_response_history`
- **Validates** that the runtime flow produces:
  - non-trivial `candidate_actions` list in `response_history[-1]`
  - `selected_action` consistently present in `candidate_actions`
  - `selected_posture` carries profile provenance (one of `crafter_candidate_{observe,stabilize,escalate}`)
- **Does NOT assert** that the agent picks specific non-legacy actions at runtime — that requires L3 to choose a non-stabilize profile, which depends on Round 1.B exploration drive (W3) to actually unlock.

### A-7: Manual smoke

- **Command**:
  ```
  python -m runners.run_crafter --runtime-dir /tmp/round-1a-smoke \
    --max-ticks 50 --max-turns 200 --max-runtime-sec 30 \
    --heartbeat-interval 0.2 --recovering-window 0.05 \
    --idle-sleep-sec 0.01 --turn-guard-window 0.01 \
    --shallow-patrol-interval 0.01 --deep-patrol-interval 0.02 \
    --full-report-interval 0.03
  ```
- **Result**: 28 ticks, 200 turns, 198 response_history entries.
- **Findings**:
  - **L3 mediator picked `stabilize_first` in all 198 audits**. Pressures encountered included `capability/tooling_missing` (198×), `acquisition/inventory_sparse` (198×), `safety/threat_nearby` (190×), `metabolic/metabolic_degraded` (73×), but the L3 value-judgment scoring under sustained avatar degradation always converged on stabilize.
  - **Bridge correctly restricted widening to stabilize_first** (`candidate_actions = ["sleep"]` for every entry). Profile constraint works.
  - **Selected posture** = `crafter_candidate_stabilize` for all entries. Profile provenance propagates into traces correctly.
  - **One `achievement_delta = 1.0`** occurred — likely a Crafter "wake_up" achievement from a sleep cycle. The outcome observer correctly recorded it.
  - **Zero achievements requiring escalate** (chop / make / place) were unlocked because L3 never chose escalate. This is the predicted Round 1.A limit — widening is enabled but the L3 mediator's drive-weighted scoring needs Round 1.B's exploration drive to ever pick non-stabilize.
- **Conclusion**: Round 1.A is **necessary but not sufficient** for "Crafter agent actually plays Crafter". Round 1.B's exploration drive (W3) is the unlock for L3 to pick observe_first / escalate_first in low-pressure moments and thereby exercise the full widened action surface.

## Files changed

### Modified
- `scenarios/crafter/actions/compatibility.py` (+~250 LOC including helpers, comments, and docstrings)
- `scenarios/crafter/actions/__init__.py` (+3 LOC for new exports)
- `tests/scenarios/crafter/test_actions.py` (assertion update for widened candidate set + posture assertions)
- `tests/integration/test_crafter_runtime.py` (+~60 LOC for new test)

### Added
- `tests/scenarios/crafter/test_action_widening_smoke.py` (~200 LOC, 3 tests)
- `maintainer/development/round-1a-crafter-action-widening-startup-instruction.md` (startup directive)
- `maintainer/development/round-1a-progress.md` (this file)

### Not modified (verified via `git diff`)
- `eva/` — framework code unchanged
- `scenarios/linux_runtime/` — Linux scenario unchanged

## Verification

- **Full regression after each slice**: `python -m unittest discover -s tests -t .` → 315 / 315 OK
- **A-1 tests fail on current main** with TypeError (signature change required) — confirmed.
- **A-1 tests pass after A-3 (tests 1 + 2) and A-4 (test 3)** — confirmed.
- **Pre-existing assertion update** in `test_integrity_candidates_are_bounded_and_filterable` — accepted as documented in §A-3.
- **Linux smoke** not separately re-run; full regression covers `tests/scenarios/linux_runtime/` and all framework tests.
- **Boundary check**: `git diff main -- 'eva/' 'scenarios/linux_runtime/'` shows zero changes.

## Findings to surface for follow-up (post-Round-1.A)

These are not Round 1.A regressions. They are **architectural facts surfaced during Round 1.A** that the architect should hold in mind when scoping Round 1.B:

1. **L3 mediator's profile choice is currently stabilize-dominated under sustained avatar degradation.** Without an exploration drive that creates positive valence for non-stabilize candidates in low-pressure moments, the agent will continue defaulting to stabilize_first even after Round 1.A widening. This is precisely the gap Round 1.B / W3 is meant to fill.

2. **Stage H followup #3 (placeholder Crafter outcome confidence)** remains open and was not addressed in Round 1.A. After Round 1.B unlocks meaningful action variety, confidence accuracy will start to matter for habit crystallization. Worth scheduling alongside or after W3.

3. **`CRAFTER_STARTUP_PRIOR_DEFINITIONS` priors with `preferred_action="noop"`** (acquisition_observe_noop, capability_observe_noop, default_observe_noop) were originally pointing at noop because that was the only action available. Post-1.A these priors still nominally point at noop. Whether to revise them to point at more semantically aligned actions (e.g., `move_*` for acquisition observation) is a Round 1.B-adjacent decision; not blocking.

4. **`select_response_action` parameter accumulation** — Stage I followup #3 watched parameter accumulation on `working_memory.py`. The same concern applies here: A-4 added a single `selection_context` payload via `bridge_policy` rather than multiple new params. This honored the Stage I watch but the function is now reading from `bridge_policy` payload structure, which itself was carried by `release_context`. The two-level extraction (release_context → bridge_policy → selection_context) is functional but worth a hygiene pass if the indirection grows.

## G2 exit criteria status

| Criterion | Status |
|---|---|
| Smoke run shows > 3 distinct concrete actions across the run | ⚠️ Only `sleep` selected at runtime; widening is structurally in place but L3 picks stabilize → blocked on Round 1.B for runtime selection diversity. **Tests 1+3 of A-1 directly exercise the widened paths and pass.** |
| At least one Crafter achievement unlocked in integration | ✅ One `achievement_delta=1.0` recorded in smoke (likely `wake_up`) |
| At least one `learning_outcomes.jsonl` record with `task_progress > 0` | ⚠️ Achievement was recorded but `task_progress` field semantics need cross-check (handled by outcome_observers/compatibility.py:54 which sets `task_progress = achievement_delta if achievement_delta != 0.0 else None`) |
| Demonstrably prior-skill-driven test | ✅ `test_prior_preferred_action_appears_when_eligible_under_profile` |
| Demonstrably habit-driven test | ✅ `test_habit_bias_drives_selection_among_candidates_of_same_profile` |
| All existing tests pass after Round 1.A | ✅ 315 / 315 |
| `git diff` shows zero modifications under `eva/` | ✅ verified |
| `git diff` shows zero modifications under `scenarios/linux_runtime/` | ✅ verified |
| Linux smoke equivalent to baseline | ✅ Linux tests all pass; no Linux code paths touched |

## G2 architect decision needed

The behavioral exit criterion (> 3 distinct concrete actions at runtime) is partially blocked by an upstream factor (L3 mediator's profile choice under degraded avatar), not by Round 1.A's widening itself. The widening **infrastructure** is fully landed and exercised by direct-call tests. The **runtime expression** of widening will land via Round 1.B's exploration drive (W3).

The architect's decision is: **accept Round 1.A as structurally complete** on this basis and proceed to Round 1.B, OR require a fix to L3 profile selection within Round 1.A. The plan file recommendation is the former — keep Round 1 modular per the original sequencing.
