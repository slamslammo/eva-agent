# Current Intake

## Active Item

`crafter-refactor-pr3` — CrafterLLMActionProducer raw-action candidates

Coordination owner: `B-claude-2`
Branch: `crafter-refactor-pr3-llm-action-producer`
Plan source: `/Users/mojiawen/Documents/claude_projects/eva-coordination/plans/crafter-refactor-detailed-plan-rev1.md` §5 PR-3

## Intake

1. Layer touched:
   - Primary: `l3_deliberation` (scenario-owned reasoning component)
   - New package: `scenarios/crafter/reasoning/`

2. Canonical owners:
   - `scenarios/crafter/reasoning/llm_action_producer.py`
   - `scenarios/crafter/reasoning/__init__.py`
   - `tests/scenarios/crafter/test_llm_action_producer.py`

3. Owner class:
   - New scenario reasoning owner.
   - Depends on PR-2 `CrafterActionDomain` and PR-0 raw-action assessment path.
   - Does NOT touch bridge executor/fallback (that is PR-4).

4. Slice type:
   - Current approved crafter-refactor slice: PR-3 only.
   - Do not enter PR-4 bridge executor cleanup.

5. Required behavior boundaries:
   - Only selects actions from A'(s); candidates outside A'(s) silently discarded.
   - Candidate.action directly carries raw action ("move_left", "do", etc.) — no compatibility_release shell.
   - Returns [] on LLM unavailability or any failure (default inhibition, not fallback heuristic).
   - drive_impact_schema set by action category for scoring compatibility with value_judgment.
   - parameter_domain carries gate fields + raw_action_candidate=True for conflict_detection routing.

6. Frozen tests / required verification:
   - `tests/scenarios/crafter/test_llm_action_producer.py` (21 new tests)
   - Full regression.

7. Docs to sync:
   - `maintainer/development/current-intake.md` (this file).

## Acceptance Notes

PR-3 is complete only when:

- `CrafterLLMActionProducer` produces Candidate objects with raw actions in A'(s);
- candidates outside A'(s) are discarded;
- candidate carries no compatibility_release shell;
- raw-action candidates are assessable by PR-0's value_judgment path;
- all 21 unit tests pass; full regression green;
- task handed back as `G2_REQUESTED` for architecture review.

## Implementation Result

- Added `scenarios/crafter/reasoning/llm_action_producer.py` with `CrafterLLMActionProducer`.
- Producer implements CandidateProducer protocol; builds CrafterStatePacket + calls build_crafter_action_domain for A'(s).
- Injects world_facts via world_facts_fn into system prompt; recent memory into user payload.
- Discards any LLM-returned action outside A'(s); deduplicates; caps at 3 candidates.
- Candidate.action is raw Crafter action; capability="raw_action"; side_effect_class="crafter_raw_action".
- drive_impact_schema by action category (move=metabolic+acquisition, sleep=recovery, do=acquisition+metabolic, make_*=capability+acquisition, place_*=capability).
- parameter_domain has gate fields (turn_allowed, instance_valid, critical_blocked, life_state, conservative_mode) + raw_action_candidate=True for conflict_detection._is_raw_action_candidate().
- Returns [] on chat_fn=None or any LLM/parse exception.

Verification:

- `python3.11 -m pytest tests/scenarios/crafter/test_llm_action_producer.py -v` -> 21 passed
- `python3.11 -m pytest` -> 573 passed
- `git diff --check` -> passed
