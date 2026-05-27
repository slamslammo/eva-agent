# Current Intake

## Active Item

`crafter-refactor-pr1` — CrafterStatePacket + raw feasibility

Coordination owner: `B-codex-2`
Branch: `crafter-refactor-pr1-statepacket-feasibility`
Plan source: `/Users/mojiawen/Documents/claude_projects/eva-coordination/plans/crafter-refactor-detailed-plan-rev1.md`

## Intake

1. Layer touched:
   - Primary: `l3_deliberation` input context for Crafter live LLM prompting.
   - Scenario-owned support: Crafter perception packet and raw action feasibility.

2. Canonical owners:
   - `scenarios/crafter/state_packet.py`
   - `scenarios/crafter/actions/feasibility.py`
   - `runners/run_crafter.py`
   - `eva/l3_deliberation/reasoning/llm_candidate_producer.py` as a generic injection seam only
   - Tests under `tests/scenarios/crafter/` and `tests/l3_deliberation/reasoning/`

3. Owner class:
   - Stable scenario owner plus a narrow framework producer seam.
   - This PR-1 slice must not change anchor release policy, mediator authority, bridge selection, or raw-action producer semantics.

4. Slice type:
   - Current approved crafter-refactor slice: PR-1 only.
   - Do not enter PR-2 anchor action-domain refactor, PR-3 raw-action LLM producer, or PR-4 bridge executor cleanup.

5. Required behavior boundaries:
   - `CrafterStatePacket` is perception context, not a planner.
   - Packet may include facts: life panel, rates, facing, local grid, inventory, visible object locations, salience, recent outcomes, available actions, world-facts ref.
   - Packet must not select goals, choose directions, rank actions, or expose preferred actions.
   - `feasible_raw_actions` filters only world-impossible actions, not unwise actions.
   - Existing profile-action vocab remains compatible until later PRs retire it.

6. Frozen tests / required verification:
   - `tests/scenarios/crafter/test_state_packet.py`
   - `tests/scenarios/crafter/test_feasibility.py`
   - `tests/l3_deliberation/reasoning/test_llm_candidate_producer.py`
   - `tests/integration/test_crafter_runtime.py`
   - Broader Crafter scenario tests and full regression if focused tests pass.

7. Docs to sync:
   - `maintainer/development/current-intake.md` for this intake.
   - No public docs expected in PR-1 unless an external contract changes.

## Acceptance Notes

PR-1 is complete only when:

- StatePacket includes `schema_version` and `raw_observation_ref`;
- live LLM prompt can receive life / water / local_view / facing / inventory / available_actions;
- `state_packet.py` contains no target selection, pathfinding, ranking, preferred action, or strategy fallback;
- `feasible_raw_actions` exposes raw Crafter actions with only physical impossibility filtered;
- legacy profile vocab tests remain green;
- task is handed back as `G2_REQUESTED` for architecture review.

## Implementation Result

- Added `CrafterStatePacket` builder with `schema_version`, `raw_observation_ref`, life values, rates, facing, local grid, inventory, visible water/food/threat facts, salience, recent outcomes, available raw actions, and world-facts ref.
- Added `feasible_raw_actions(observation)` alongside the legacy profile vocab. It uses the same world-fact feasibility gate and leaves no-requirement raw actions available.
- Added an optional `state_context_fn` seam to `LLMCandidateProducer`; absent by default, so non-Crafter/model-off behavior is unchanged.
- Wired live Crafter runner to inject the scenario-owned StatePacket into the LLM prompt while keeping the old profile-action hint producer semantics until PR-3.
- Verified `state_packet.py` has no strategy-key fields and no target/path/rank/preferred/direction/score/fallback/policy terms.

Verification:

- `python3.11 -m pytest tests/scenarios/crafter/test_state_packet.py tests/scenarios/crafter/test_feasibility.py tests/l3_deliberation/reasoning/test_llm_candidate_producer.py tests/integration/test_crafter_runtime.py` -> 28 passed
- `python3.11 -m pytest tests/scenarios/crafter tests/l3_deliberation/reasoning tests/integration/test_crafter_runtime.py` -> 197 passed
- `python3.11 -m pytest` -> 546 passed
- `git diff --check` -> passed
