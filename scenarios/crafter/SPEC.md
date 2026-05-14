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
- `local_view_state -> safety`

The sensors read the bounded `agent_observation` surface and do not consume evaluator-only or hidden payloads directly.

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

The landed action surface is intentionally narrow:
- the shared 17-action enum remains the canonical Crafter vocabulary
- the bounded compatibility bridge currently selects only `noop`, `sleep`, and `do`
- release still stays inside the existing framework compatibility surface

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

### H-3 persistence hierarchy and learning integration

Current H-3 persistence owners:
- `scenarios/crafter/persistence/hierarchy.py`
- `scenarios/crafter/persistence/__init__.py`

The current Crafter hierarchy is:
- Level 1: `substrate_instance`
- Level 2: `crafter_avatar_instance`
- Level 3: `crafter_capability_structure`
- Level 4: `crafter_resource_system`

Crafter learning integration now preserves multi-dimensional outcome fields through the same append-only learning record path used by the framework.

### H-4 prior skills

Current H-4 prior-skill owners:
- `scenarios/crafter/prior_skills/compatibility.py`
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

Each prior carries Crafter scenario provenance through the framework skill types.

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
- bounded episode reset when the Crafter env returns `done=True`

The current runtime shape is:
1. `runners/run_crafter.py` activates the Crafter scenario
2. it creates one `CrafterRuntimeSession`
3. the session resets the wrapper and stores the latest bounded `agent_observation`
4. the runner passes those facts into the generic sensing seam
5. when the compatibility bridge releases a bounded Crafter action, the wrapper steps the env
6. the resulting deltas are recorded through the existing append-only response-history and learning paths
7. if the env episode ends, the session resets the wrapper immediately so the next patrol sees a fresh observation

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
- `tests/integration/test_crafter_runtime.py`

Optional live verification now includes:
- `python -m runners.run_crafter ...`
- `python -m stability_metrics calculate <runtime_dir>`
- `tests/stability_metrics/test_cli_smoke.py`

If the local `crafter` package is unavailable, live-Crafter smoke remains skip-based rather than fabricating success.

## Current limits

The Crafter scenario is still intentionally bounded:
- the compatibility bridge still uses a narrow release vocabulary
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
