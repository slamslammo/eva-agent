# Current Intake

## Active Item

`crafter-refactor-pr2` — anchor A'(s) pre-generative raw action domain

Coordination owner: `B-codex-2`
Branch: `crafter-refactor-pr2-anchor-domain`
Plan source: `/Users/mojiawen/Documents/claude_projects/eva-coordination/plans/crafter-refactor-detailed-plan-rev1.md`

## Intake

1. Layer touched:
   - Primary: `anchor`
   - Scenario-owned surface: Crafter raw action-domain admission

2. Canonical owners:
   - `scenarios/crafter/anchors/policy.py`
   - `scenarios/crafter/anchors/__init__.py`
   - `tests/scenarios/crafter/test_anchors.py`

3. Owner class:
   - Stable scenario anchor owner.
   - Legacy profile admission remains as transitional compatibility until PR-3/PR-4 consume the raw action domain and retire the old bridge path.

4. Slice type:
   - Current approved crafter-refactor slice: PR-2 only.
   - Do not enter PR-3 raw-action LLM producer or PR-4 bridge executor cleanup.

5. Required behavior boundaries:
   - Anchor output is an unordered action set plus `restriction_reasons`.
   - No `rank`, `preferred_action`, `score`, or `direction_hint` in the new raw action-domain contract.
   - Water/food critical restrict to movement actions; `do` must not enter just because water/food is visible or faced.
   - Water not visible still admits the full movement set, not a chosen direction.
   - Threat-visible response may admit `do` because the world mechanism for combat uses `do`.
   - Feasibility remains world-fact only and is intersected into A'(s).

6. Frozen tests / required verification:
   - `tests/scenarios/crafter/test_anchors.py`
   - `tests/scenarios/crafter/test_feasibility.py`
   - `tests/scenarios/crafter/test_state_packet.py`
   - Broader Crafter scenario tests and full regression if focused tests pass.

7. Docs to sync:
   - `maintainer/development/current-intake.md` for this intake.
   - No public docs expected in PR-2 unless an external contract changes.

## Acceptance Notes

PR-2 is complete only when:

- `build_crafter_action_domain(agent_state, observation)` returns raw A'(s) as an unordered set;
- water/food critical domains exclude `do`, `sleep`, and `noop`;
- water not visible produces the movement set without selecting a direction;
- threat visible produces movement plus `do`;
- energy critical with no threat admits `sleep`;
- normal domains are feasibility-filtered raw actions;
- task is handed back as `G2_REQUESTED` for architecture review.

## Implementation Result

- Added scenario-owned `CrafterActionDomain` with `action_set: frozenset[str]` and `restriction_reasons`.
- Added `build_crafter_action_domain(agent_state, observation)` as the PR-2 A'(s) raw action-domain builder.
- Intersects A'(s) with `feasible_raw_actions(observation)` while keeping feasibility world-fact-only.
- Pins water/food critical domains to movement actions only; `do` is excluded even when water/food is visible or faced.
- Pins water-not-visible exploration to the same movement set, so anchor does not choose a direction.
- Pins threat-visible response to movement plus `do`, and energy-critical/no-threat to `sleep`.
- Legacy profile admission remains transitional compatibility until PR-3/PR-4 consume the new raw action domain.

Verification:

- `python3.11 -m pytest tests/scenarios/crafter/test_anchors.py tests/scenarios/crafter/test_feasibility.py tests/scenarios/crafter/test_state_packet.py` -> 17 passed
- `python3.11 -m pytest tests/scenarios/crafter tests/l3_deliberation/reasoning tests/integration/test_crafter_runtime.py` -> 203 passed
- `python3.11 -m pytest` -> 552 passed
- `git diff --check` -> passed
