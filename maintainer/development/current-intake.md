# Current Intake

## Active Item

`crafter-refactor-pr0` — framework candidate identity / release / assessment decoupling

Coordination owner: `B-codex-2`
Branch: `crafter-refactor-pr0-framework-decoupling`
Plan source: `/Users/mojiawen/Documents/claude_projects/eva-coordination/plans/crafter-refactor-detailed-plan-rev1.md`

## Intake

1. Layer touched:
   - Primary: `l3_deliberation`
   - Secondary scenario regression surface: Linux runtime tests that share L3 mediator/value judgment

2. Canonical owners:
   - `eva/l3_deliberation/peer_circuit/mediator.py`
   - `eva/l3_deliberation/peer_circuit/goal_directed_track.py`
   - `eva/l3_deliberation/reasoning/conflict_detection.py`
   - `eva/l3_deliberation/reasoning/value_judgment.py`
   - Tests under `tests/l3_deliberation/peer_circuit/`
   - Token bridge regression test under `tests/l3_deliberation/tool_edge/`
   - Linux regression tests under `tests/integration/test_linux_alignment.py`

3. Owner class:
   - Stable framework owner.
   - PR-0 is explicitly the only approved framework-touching slice in the crafter refactor sequence.

4. Slice type:
   - Current approved round slice: PR-0 only.
   - Do not enter PR-1+ behavior, Crafter StatePacket work, anchor domain refactor, LLM raw-action producer, or bridge executor refactor in this slice.

5. Required behavior boundaries:
   - `ReleaseToken` authority identity must be `candidate_id`, not `candidate_profile`.
   - `candidate_profile` remains available as optional scenario/trace metadata; do not delete the profile ecosystem.
   - Mediator remains the sole release authority; default inhibition and token validation remain intact.
   - `assess_candidates` must accept raw-action candidates such as `Candidate(action="move_left")`.
   - Linux candidate/profile semantics must continue to work as scenario metadata.

6. Frozen tests / required verification:
   - Focused unit tests:
     - `tests/l3_deliberation/peer_circuit/test_mediator.py`
     - `tests/l3_deliberation/peer_circuit/test_goal_directed_track.py`
     - relevant `tests/l3_deliberation/reasoning/test_value.py` cases
   - Linux regression:
     - `tests/integration/test_linux_alignment.py`
   - Broader safety pass if focused tests pass:
     - L3 peer-circuit / reasoning tests touched by the identity and assessment path

7. Docs to sync:
   - `maintainer/development/current-intake.md` for this intake.
   - No public docs expected in PR-0 unless implementation reveals a changed external contract.

## Acceptance Notes

PR-0 is complete only when:

- release validation no longer rejects a token because `candidate_id` does not encode an observe/stabilize/escalate profile;
- release validation still rejects mismatched token id, candidate id, or non-release outcome;
- a raw-action candidate can be assessed, selected, and released without a compatibility-release shell;
- Linux alignment tests stay green;
- task is handed back as `G2_REQUESTED` for architecture review.

## Implementation Result

- `ReleaseToken` validation now binds authority to `candidate_id` + deterministic token id + outcome only. `candidate_profile` remains trace/scenario metadata.
- Goal-directed trace helpers now prefer explicit `candidate_profile=...` assessment metadata, with legacy candidate-id suffix parsing retained for existing Linux compatibility candidates.
- Explicit raw-action candidates (`capability="raw_action"` or `candidate_kind="raw_action"`) now enter conflict detection and value judgment without being rejected as `unknown_candidate_action`.
- Tool-edge executor coverage confirms raw candidate-id tokens pass mediated execution validation.

Verification:

- `python3.11 -m pytest tests/l3_deliberation/peer_circuit tests/l3_deliberation/tool_edge tests/l3_deliberation/reasoning/test_value.py tests/integration/test_linux_alignment.py` -> 101 passed
- `python3.11 -m pytest` -> 542 passed
- `git diff --check` -> passed
