# Linux Runtime Scenario Specification

**Status**: Landed concrete scenario after the Phase A refactor  
**Scope**: `scenarios/linux_runtime/`  
**Framework companion**: `docs/eva-framework-implementation.md`  
**Cross-scenario contract**: `docs/scenarios-SPEC.md`

---

## Purpose

This document specifies the concrete Linux runtime scenario that is currently shipped in the repository.

It is the canonical owner for Linux-specific runtime content. The framework keeps lifecycle, release, append-only, and structural authority; this scenario provides the concrete content that fills those framework seams.

## Scenario identity

- **Scenario name**: `linux_runtime`
- **Intended world**: one long-running EVA process observing and protecting its own local runtime directory and host-local operating context
- **Canonical runner**: `runners/run_linux.py`
- **Activation surface**: `scenarios/linux_runtime/__init__.py`

## Runtime bundle

The scenario exports `LINUX_RUNTIME_SCENARIO_BUNDLE` from `scenarios/linux_runtime/__init__.py`.

That bundle provides six concrete content areas:
- drive preset
- sensors
- actions
- anchors
- outcome observers
- prior skills

## 1. Drive preset

The Linux runtime scenario currently defines four drives in `scenarios/linux_runtime/drive_preset.py`:
- `survival`
- `integrity`
- `continuity`
- `curiosity`

Current dimension mapping:
- `resource_state -> survival`
- `runtime_integrity -> integrity`
- `anomaly_accumulation -> integrity`
- `host_continuity -> continuity`

The scenario also provides the current default `DriveUpdatePolicy` used by the framework drive layer.

## 2. Sensors

The Linux runtime scenario currently provides four concrete sensor dimensions.

### Host continuity
- owner: `scenarios/linux_runtime/sensors/heartbeat.py`
- dimension: `host_continuity`
- current payload focus: process continuity, restart history, schedule drift

### Runtime integrity
- owner: `scenarios/linux_runtime/sensors/runtime.py`
- dimension: `runtime_integrity`
- current payload focus: instance validity, runtime writability, runtime-state presence, events presence, lock presence, heartbeat age, recent yield/distress counts

### Resource state
- owner: `scenarios/linux_runtime/sensors/resource.py`
- dimension: `resource_state`
- current payload focus: runtime-path existence, runtime writability, disk free bytes

### Anomaly accumulation
- owner: `scenarios/linux_runtime/sensors/anomaly.py`
- dimension: `anomaly_accumulation`
- current payload focus: recent errors, yields, distress events, restarts, aggregate anomaly count

Ordered provider assembly lives in `scenarios/linux_runtime/sensors/__init__.py`.

## 3. Actions

The Linux runtime scenario currently provides a bounded compatibility response vocabulary in `scenarios/linux_runtime/actions/compatibility.py`.

Current action names:
- `recheck_runtime_integrity`
- `shrink_to_conservative_mode`
- `escalate_integrity_risk`

Current response mode default:
- `pressure_led_compatibility`

Current execution intent:
- recheck local runtime integrity
- temporarily shrink to conservative mode when allowed
- escalate to a human-review or safer boundary when the runtime cannot act safely

These actions execute only through the framework’s mediated tool-edge path.

## 4. Anchor policy

The Linux runtime scenario currently provides candidate-schema admission policy in `scenarios/linux_runtime/anchors/compatibility.py`.

Current candidate profiles:
- `observe_first`
- `stabilize_first`
- `escalate_first`

Current high-risk escalation reasons:
- `runtime_files_missing`
- `runtime_not_writable`
- `recent_distress_detected`

Current secondary gate rule:
- `escalate_first` is admitted only for the configured high-risk reasons and critical severity

Current heartbeat narrowing rule:
- when the heartbeat window is very near, schema admission narrows to `stabilize_first`

The framework owns `ActionDomain`; this scenario owns which schemas enter it for Linux runtime conditions.

## 5. Outcome observers

The Linux runtime scenario currently provides outcome interpretation in `scenarios/linux_runtime/outcome_observers/compatibility.py`.

It owns:
- expected-outcome labels for mediated release outcomes
- observed-outcome evaluation from response execution payloads
- learning-content payload construction for append-only learning records

Current expected-outcome labels include:
- `improve_information_under_pressure`
- `stabilize_or_relieve_pressure`
- `escalate_for_safety_under_pressure`
- `bounded_pressure_response`
- `wait_for_safer_boundary`
- `no_external_change`

## 6. Prior skills and habit shaping

The Linux runtime scenario currently provides read-side prior-skill and habit policy in `scenarios/linux_runtime/prior_skills/compatibility.py`.

It owns:
- situation-key construction from `top_drive`, `life_state`, and `pressure_reason`
- habit-bias summarization from accumulated learning outcomes
- habit-skill derivation under bounded evidence / stability / confidence thresholds
- candidate-profile matching for the current scenario vocabulary
- provenance metadata for scenario-owned prior skill records and experience-derived habit records

Current matching profiles are:
- `observe_first`
- `stabilize_first`
- `escalate_first`

The current scenario is still bounded to one runtime. It does not implement inherited priors beyond the framework placeholder registry, and it does not claim ownership of any release authority.

## 7. Persistence / stability alignment

Stage G introduced an explicit framework `PersistenceHierarchy` and a separate `stability_metrics` trace-only module.

For Linux runtime, the scenario currently aligns as follows:
- Level 1 activation: host / instance continuity via heartbeat and instance validity
- Level 4 activation: runtime artifact substrate via runtime path writability/readability constraints
- `stability_metrics` consumes the scenario trace output rather than in-memory framework state

The Linux scenario does not activate Levels 5-7.

## 8. Startup and activation

The canonical Linux startup path is:
- `python -m runners.run_linux`

`runners/run_linux.py` activates `activate_linux_runtime_scenario()` and then delegates into the generic framework runtime loop.

`eva.kernel.main` remains usable as a compatibility entry, but the scenario-owned canonical startup path is the runner.

## 9. Alignment notes for Stage G

This scenario is aligned with the Stage G framework contracts as follows:
- **Outcome contract**: Linux outcome observers return the vector-aware learning record shape while preserving scalar `outcome_delta` semantics on `viability_delta.level_1`
- **Skill contract**: prior and habit policy is split across framework registry surfaces with provenance metadata; scenario-owned policy remains read-side only
- **Persistence contract**: Linux activates Level 1 continuity and Level 4 artifact substrate, while keeping Levels 5-7 inactive
- **Stability contract**: trace output is consumable by `stability_metrics` without importing EVA internals
- **Activation contract**: explicit runner activation remains the only canonical startup path

The scenario remains narrow and does not claim broader task-handling capability.

## 10. What this scenario does not own

This scenario does not own:
- heartbeat cadence authority
- instance legitimacy
- append-only audit or event write authority
- release-token minting or validation
- generic framework dataclasses for response selection, learning records, or habit summaries

Those remain framework concerns under `eva/`.

## 11. Current scope limit

This scenario is still intentionally narrow.

It is a Linux runtime protection and bounded recovery scenario, not a general desktop automation or broad environment-control scenario. The current action surface and outcome semantics are therefore conservative and tightly scoped.
