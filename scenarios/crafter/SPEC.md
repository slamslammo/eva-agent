# Crafter Scenario Specification

**Status**: H-5 bounded runner and end-to-end runtime landed for Stage H  
**Scope**: `scenarios/crafter/`  
**Framework companion**: `docs/eva-framework-implementation.md`  
**Cross-scenario contract**: `docs/scenarios-SPEC.md`

---

## Purpose

This document is the canonical owner for Crafter-specific runtime content.

Stage H uses Crafter as the second scenario that validates whether the post-Stage-G framework boundary is actually scenario-neutral. The current landed state is no longer just a wrapper skeleton. Crafter now has:
- a real scenario bundle
- a real runner
- bounded end-to-end runtime integration through the generic framework loop
- wrapper-backed action execution
- append-only learning / history compatibility
- stability-metrics compatibility

## Scenario identity

- **Scenario name**: `crafter`
- **Intended world**: one EVA runtime embedded into one Crafter environment instance
- **Canonical runner**: `runners/run_crafter.py`
- **Activation surface**: `scenarios/crafter/__init__.py`
- **Crafter version lock**: `1.8.3`

## Landed surfaces

### H-0 wrapper and observation baseline

Current H-0 wrapper owners:
- `scenarios/crafter/wrapper/env_wrapper.py`
- `scenarios/crafter/wrapper/observation.py`
- `scenarios/crafter/wrapper/semantic_local_view.py`
- `scenarios/crafter/wrapper/evaluator_surface.py`

The wrapper remains framework-agnostic:
- it creates and steps a local Crafter env
- it validates the installed env action count against the shared 17-action enum
- it exposes only bounded `agent_observation` to agent-facing layers
- it keeps full semantic / evaluator-only payloads out of the agent-facing surface

The agent observation contract remains:
- schema version: `symbolic_observation_v0`
- observation mode: `visible_state_proxy`
- local view source: wrapper-side semantic crop only

Fairness boundary:
- `agent_observation` must not contain `semantic`
- `agent_observation` must not contain absolute coordinates
- `agent_observation` must not contain evaluator-only debug or hidden state

### H-1 drives and sensors

Current H-1 drive owner:
- `scenarios/crafter/drive_preset.py`

The current Crafter drive family is:
- `metabolic`
- `safety`
- `recovery`
- `acquisition`
- `capability`
- `exploration` — Round 1.B-2 internal growth-driver drive (v0.6.1 §4). Not mapped to any sensor dimension; updated via the framework's curiosity-style ``_curiosity_delta`` path (recovers by ``curiosity_recovery`` in healthy / no-threat states; suppressed by ``curiosity_suppression`` under threat or degraded overall status). Candidate scoring picks it up through the per-profile ``exploration`` entry in ``COMPATIBILITY_RELEASE_IMPACT``.

Current H-1 sensor owners:
- `scenarios/crafter/sensors/avatar_state.py`
- `scenarios/crafter/sensors/inventory.py`
- `scenarios/crafter/sensors/local_view.py`
- `scenarios/crafter/sensors/__init__.py`

Current dimension mapping is intentionally scenario-shaped rather than Linux-shaped:
- `avatar_metabolic -> metabolic`
- `avatar_safety -> safety`
- `avatar_recovery -> recovery`
- `inventory_acquisition -> acquisition`
- `inventory_capability -> capability`
- `local_view_threat -> safety`
- `local_view_resource -> acquisition`
- `local_view_utility -> capability`

Current pressure-type mapping is aligned to the Crafter drive families rather than flattened into one generic bucket:
- `avatar_metabolic -> metabolic`
- `avatar_safety -> safety`
- `avatar_recovery -> recovery`
- `inventory_acquisition -> acquisition`
- `inventory_capability -> capability`
- `local_view_threat -> safety`
- `local_view_resource -> acquisition`
- `local_view_utility -> capability`

The landed local-view decomposition now projects one bounded observation surface into three scenario-owned dimensions:
- `local_view_threat` emits threat-presence semantics for `safety`
- `local_view_resource` emits visible-resource opportunity semantics for `acquisition`
- `local_view_utility` emits visible-utility / tooling-gap semantics for `capability`

This keeps the decomposition at the scenario sensor seam without changing framework drive structure. The sensors still read only the bounded `agent_observation` surface and do not consume evaluator-only or hidden payloads directly.

Stage I I-1 extends this sensing surface from status-only interpretation toward bounded trajectory awareness:
- `avatar_safety`, `avatar_metabolic`, and `avatar_recovery` are the Crafter required-tier rate-sensing dimensions
- those required-tier dimensions now emit real `rate_context` from previous snapshots when same-episode history exists
- rate unavailability stays explicit through the canonical payload shape:
  - `available=False`
  - `direction="unknown"`
  - `magnitude=None`
  - `acceleration=None`
- `inventory_capability` and `inventory_acquisition` are currently recommended-tier only
- `local_view_threat`, `local_view_resource`, and `local_view_utility` are currently optional-tier only

Within current I-1 scope, Crafter pressure projection is also rate-aware:
- pressure urgency now reflects bounded rate direction / magnitude context
- healthy but fast-degrading required-tier dimensions can emit bounded anticipatory pressure
- anticipatory coverage is intentionally limited to the configured required-tier dimensions rather than every Crafter signal

### H-2 actions, anchors, and outcome observers

Current action owners:
- `scenarios/crafter/actions/registry.py`
- `scenarios/crafter/actions/compatibility.py`
- `scenarios/crafter/actions/__init__.py`

Current anchor owners:
- `scenarios/crafter/anchors/policy.py`
- `scenarios/crafter/anchors/__init__.py`

Current outcome-observer owners:
- `scenarios/crafter/outcome_observers/compatibility.py`
- `scenarios/crafter/outcome_observers/__init__.py`

The landed action surface (post Round 1.A widening) resolves to context-appropriate concrete actions within the existing framework profile vocabulary:
- the shared 17-action enum remains the canonical Crafter vocabulary
- the bounded compatibility bridge now resolves the L3-selected `candidate_profile` to one or more concrete actions per the `PROFILE_ELIGIBLE_ACTIONS` table:
  - `observe_first` → `noop` and the four `move_*` actions
  - `stabilize_first` → `sleep` and `noop`
  - `escalate_first` → `do` plus the four `place_*` and the six `make_*` actions
- inside each profile, the resolution reads `pressure.evidence["reason"]` and any `candidate_context["inherited_priors"]` to pick concrete actions:
  - `escalate_first` + `inventory_sparse` / `tooling_missing` → `do` plus pickaxes and table / furnace placement
  - `escalate_first` + `health_critical` / `threat_visible` → `do` plus swords
  - `observe_first` + acquisition pressure → `noop` plus all four movements
- candidate-profile provenance is encoded in the scenario-owned `posture` token (`crafter_candidate_observe` / `crafter_candidate_stabilize` / `crafter_candidate_escalate`)
- `select_response_action` consults `bridge_policy["selection_context"]` for habit and inherited-prior bias, then picks the highest-scoring candidate; without bias the first context-resolved candidate of the active profile is chosen
- release still stays inside the existing framework compatibility surface and does not widen release authority

The landed anchor policy is also intentionally narrow:
- higher safety pressure can admit `escalate_first`
- higher metabolic / recovery pressure narrows toward `stabilize_first`
- lower-pressure states keep `observe_first` available

The landed outcome observer interprets Crafter actions into `OutcomeVector` fields including:
- `task_progress`
- `viability_delta`
- `resource_delta`
- `capability_delta`
- `risk_delta`
- `reversibility`
- `cost`
- `uncertainty`

Crafter confidence is now derived directly from `OutcomeVector.uncertainty` through a bounded linear mapping in `scenarios/crafter/outcome_observers/compatibility.py`, replacing the earlier placeholder-like fixed confidence values.

### H-3 persistence hierarchy and learning integration

Current H-3 persistence owners:
- `scenarios/crafter/persistence/hierarchy.py`
- `scenarios/crafter/persistence/__init__.py`

The current Crafter hierarchy is:
- Level 1: `substrate_instance`
- Level 2: `crafter_avatar_instance`
- Level 3: `crafter_capability_structure`
- Level 4: `crafter_resource_system`

Level 2 is the Crafter avatar's embodied-continuity target. Per the v0.6 rev2 existence-semantics declaration shipped with the Crafter scenario (`eva/scenario_bundle.py::ExistenceSemantics`, populated by `scenarios/crafter/__init__.py`), Crafter is a one-life world: HP reaching zero is the **terminal failure** of one individual, not an episode boundary. When the env returns `done=True`, the runtime takes the terminal path — archive the trace and end this run — rather than resetting the wrapper to extend life. The next activation is explicitly a new individual (see §H-5 for the runtime mechanics and `architecture-implementation-blueprint-v0.6.md` §3.8 / §12.7 for the contract). Earlier Stage-H drafts treated `done=True` as a bounded episode reset; that reading has been superseded by the rev2 declaration.

Crafter learning integration now preserves multi-dimensional outcome fields through the same append-only learning record path used by the framework.

### H-4 prior skills

Current H-4 prior-skill owners:
- `scenarios/crafter/prior_skills/compatibility.py`
- `scenarios/crafter/prior_skills/bundle.py`
- `scenarios/crafter/prior_skills/__init__.py`

The landed Crafter prior layer includes:
- safe recognition priors for visible resources / threats / utilities
- survival priors for water / food / energy / health-driven stabilization
- resource-chain priors for early crafting progression
- action-semantics priors for bounded Crafter actions

These priors project onto the already-landed candidate-profile vocabulary:
- `observe_first`
- `stabilize_first`
- `escalate_first`

Stage I I-2 canonicalizes those startup priors into one scenario-owned bundle:
- `build_crafter_startup_prior_registry()` is the canonical inspection surface for Crafter startup priors
- each startup prior now carries explicit `SkillProvenance` with scenario scope, source paths, and applicability context
- provenance now distinguishes safety escalation, metabolic stabilization, recovery rest, acquisition/capability resource-chain, and baseline action-surface priors
- the runtime context registry remains behavior-preserving and is derived from the same canonical definitions

Each prior carries Crafter scenario provenance through the framework skill types.

### Stage I I-3 memory participation

Current I-3 memory owners and seams:
- framework layer interfaces in `eva/skills/__init__.py`
- working-memory assembly in `eva/l3_deliberation/reasoning/working_memory.py`
- semantic storage/query helpers in `eva/l3_deliberation/memory/semantic.py`
- procedural-memory shaping seam in `eva/l3_deliberation/peer_circuit/habit_track.py`

Crafter runtime participation after I-3 is now explicit:
- working memory is surfaced as the framework `WorkingMemory` / `WorkingMemoryContext` payload assembled on each deliberation turn
- episodic reuse still comes from bounded retrieval over `cognitive_memory_stub.jsonl`, `learning_outcomes.jsonl`, and response-history traces; Crafter does not get a separate scenario-only memory path
- semantic memory now has a first-class append-only `semantic_memory.jsonl` backing track and bounded query surface
- procedural memory is represented through the existing habit path backed by `habit_bias.jsonl`, with scenario-qualified provenance and no release-authority widening

Crafter-specific alignment rules remain narrow:
- semantic retrieval is scenario-qualified, so Crafter entries only match Crafter runtime turns
- situation matching reuses the same `top_drive` / `life_state` / `pressure_reason` semantics already used by the prior/habit path
- semantic memory can only add a tiny auditable candidate prior modifier during value judgment
- procedural memory can narrow or reorder candidates only through the existing mediator-gated deliberation path
- semantic-to-L2 drive-weight modification remains deferred in I-3

### Stage I I-4 inherited-prior reuse

Current I-4 owners and seams:
- `scenarios/crafter/prior_skills/inherited.py`
- `runners/run_crafter.py`
- `eva/l3_deliberation/reasoning/working_memory.py`
- `eva/l3_deliberation/peer_circuit/habit_track.py`
- `eva/l3_deliberation/reasoning/value_judgment.py`
- top-level `inheritance_distillation/`

Crafter runtime participation after I-4 is now explicit:
- `runners/run_crafter.py` can pass an optional `--inherited-priors-path` bundle into scenario activation
- `activate_crafter_scenario()` loads only Crafter-qualified distilled bundles and rejects cross-scenario bundles
- matching inherited priors appear in `working_memory_context["inherited_priors"]` for the exact current `situation_key`
- candidate shaping reuses the normal habit-path seam and marks inherited hints through `habit_hint_source="inherited_prior"`
- value judgment can add only a tiny auditable `inherited_prior_bias`

Crafter-specific I-4 guardrails remain narrow:
- inherited priors are same-scenario only
- inherited priors can suggest only the existing candidate profiles and bounded Crafter action hints (`noop`, `sleep`, `do`)
- inherited priors do not create new candidates, do not widen the release surface, and do not bypass anchors or mediator gating
- distillation remains outside the scenario package and consumes append-only traces rather than runtime internals

### H-0F framework follow-up

Current H-0F companion owners:
- `eva/l1_sensing/dimension_specs.py`
- `eva/scenario_bundle.py`
- `eva/l1_sensing/state_sensors.py`
- `eva/l1_sensing/rate_sensors.py`
- `eva/l2_drive/pressure_projection.py`
- `scenarios/crafter/dimensions/`
- `scenarios/linux_runtime/dimensions/`

This follow-up removed Linux-shaped dimension-name assumptions from the scoped framework seam so Crafter dimensions can flow through the same judgment and pressure-projection path.

### H-5 runner and end-to-end runtime integration

Current H-5 owners:
- `runners/run_crafter.py`
- `scenarios/crafter/actions/compatibility.py`
- `tests/integration/test_crafter_runtime.py`

H-5 lands:
- a real Crafter runner built on the generic `eva.kernel.main.run_runtime()` loop
- a runner-owned `agent_observation` feed into the framework sensing seam
- wrapper-backed Crafter action execution
- bounded Crafter delta propagation into response history and learning records
- terminal individual path when the Crafter env returns `done=True` (v0.6 rev2)

The current runtime shape is:
1. `runners/run_crafter.py` activates the Crafter scenario (the activation includes the `ExistenceSemantics` declaration with `reset_semantics="new_individual"` and `clock_source="step"`)
2. it creates one `CrafterRuntimeSession`
3. at run start, the session does an initial wrapper reset and stores the latest bounded `agent_observation`
4. the runner passes those facts into the generic sensing seam
5. when the compatibility bridge releases a bounded Crafter action, the wrapper steps the env
6. the resulting deltas are recorded through the existing append-only response-history and learning paths
7. if the env step returns `done=True` (Crafter terminal — typically `HP=0`), `CrafterRuntimeSession.step_action()` sets `self.terminated = True`; **the session does not call `wrapper.reset()` to extend life inside the same run**. The kernel loop observes the flag and exits the run with `exit_reason="individual_terminated"`, archiving the trace as one individual's complete lifetime. The next `python -m runners.run_crafter ...` invocation is a new individual, with a fresh `individual_id` minted by `_resolve_individual_id`; that activation may optionally load distilled priors via `--inherited-priors-path` from prior terminated individuals.

### Runtime and learning payload notes

Crafter action execution now records scenario-specific bounded fields including:
- `achievement_delta`
- `inventory_delta`
- `life_delta`
- `visible_threat_count`

Those fields are kept inside the bounded response-history / response-summary contract so the existing learning path can interpret them without widening release authority.

## Verification

Install-independent verification now includes:
- `tests/scenarios/crafter/test_wrapper_smoke.py`
- `tests/scenarios/crafter/test_drive_preset.py`
- `tests/scenarios/crafter/test_sensors.py`
- `tests/scenarios/crafter/test_actions.py`
- `tests/scenarios/crafter/test_anchors.py`
- `tests/scenarios/crafter/test_outcome_observers.py`
- `tests/scenarios/crafter/test_persistence_hierarchy.py`
- `tests/scenarios/crafter/test_learning_integration.py`
- `tests/scenarios/crafter/test_prior_skills.py`
- `tests/scenarios/crafter/test_skill_provenance.py`
- `tests/scenarios/crafter/test_prior_guided_candidates.py`
- `tests/l3_deliberation/reasoning/test_working_memory.py`
- `tests/l3_deliberation/reasoning/test_value.py`
- `tests/l3_deliberation/memory/test_semantic.py`
- `tests/integration/test_crafter_runtime.py`

Optional live verification now includes:
- `python -m runners.run_crafter ...`
- `python -m stability_metrics calculate <runtime_dir>`
- `tests/stability_metrics/test_cli_smoke.py`

In the current local Python 3.11 environment, live Crafter loading is now validated: the local `crafter==1.8.3` / `gym==0.26.2` install can create `crafter.Env`, and the wrapper smoke plus Crafter stability-metrics CLI smoke execute without skip.

## Current limits

The Crafter scenario is still intentionally bounded:
- the compatibility bridge resolves concrete actions inside the existing 3-profile vocabulary (Round 1.A); it does not introduce new candidate profiles
- runtime selection of widened actions depends on the L3 mediator picking a non-stabilize profile, which under sustained avatar degradation requires the exploration drive (Round 1.B / v0.6.1 §4) to land before agent behavior fully exercises the widened surface
- the runner still depends on a locally installable `crafter` package for live env execution
- there is no broader Crafter tool or planner ecosystem yet
- Crafter is currently a validation scenario for the framework seam, not a broad second deployment target

## Trace reference

The Crafter handoff defines the following trace-event vocabulary for this scenario family:
- `episode_start`
- `observation`
- `decision`
- `env_step`
- `outcome`
- `episode_end`
- `error`

The current landed runtime does not mint a separate Crafter-only trace subsystem. Instead, it stays inside the framework append-only event, response-history, learning-outcome, and stability-metrics surfaces.
