# Scenario Contract Specification

**Status**: Landed scenario contract after the Phase A refactor  
**Scope**: Scenario packages under `scenarios/`  
**Companion documents**: `docs/eva-framework-implementation.md`, `scenarios/linux_runtime/SPEC.md`

---

## Purpose

This document describes the scenario contract that is actually used by the current codebase. A scenario provides the concrete world-specific content that the EVA framework operates over. The framework keeps runtime authority and structural invariants; the scenario supplies the content those structures read.

The current repository ships one concrete scenario, `scenarios/linux_runtime/`, but the contract is written at the cross-scenario level.

## Required scenario assembly

A scenario package must assemble and export one runtime bundle compatible with `eva/scenario_bundle.py`.

The current bundle shape is `RuntimeScenarioBundle`, which contains:
- `drive_preset`
- `sensors`
- `actions`
- `anchors`
- `outcome_observers`
- `prior_skills`

A scenario may organize those parts across helper modules, but these six surfaces are the canonical integration contract in the current repository.

## Required bundle components

### 1. Drive preset

The scenario must provide a `DrivePreset` that defines:
- drive types
- dimension-to-drive mapping
- default drive-update policy inputs
- optional curiosity drive designation

The framework owns drive state updates and downstream read-only broadcast. The scenario supplies the concrete drive family.

### 2. Sensor policy bundle

The scenario must provide sensor builders that return ordered L1 sensor specs.

In the current codebase this includes:
- concrete sensor-spec builders
- an ordered sensor-provider factory used by the framework registry

The framework owns `SensorRegistry`, `SensingContext`, and normalized `SensorOutput`. The scenario owns what gets sensed.

### 3. Action policy bundle

The scenario must provide the concrete response/action policy, including:
- action names
- action posture/state mappings
- candidate construction
- candidate filtering
- final action selection
- concrete execution handler

The framework owns mediated release and execution structure. The scenario owns the concrete action vocabulary and action behavior.

### 4. Anchor policy bundle

The scenario must provide:
- candidate-profile names
- drive-impact defaults used by candidate schemas
- schema admission logic
- restriction-reason logic

The framework owns `ActionDomain` structure and structural/dynamic anchor processing. The scenario owns the concrete scenario admission policy.

### 5. Outcome observer bundle

The scenario must provide:
- expected-outcome labels for release outcomes
- post-action outcome evaluation
- learning-content payload construction

The framework owns learning-record structure and append-only recording. The scenario owns the semantics of what a specific action outcome means in that world.

### 6. Prior-skill bundle

The scenario must provide:
- profile matching for current prior-skill use
- situation-key construction
- habit-bias summarization
- habit-skill derivation
- read-side mapping from learning outcomes back into the current scenario vocabulary

The framework owns the dataclasses and append-only learning tracks. The scenario owns the concrete policy for summarizing and reusing experience.

## Activation model

One scenario is active for one runtime.

The typical startup pattern is:
1. a runner imports the chosen scenario
2. the runner activates the scenario bundle
3. the runner calls the generic framework loop in `eva.kernel.main.run_runtime()`

The current repository uses `runners/run_linux.py` for this role.

`eva/scenario_bundle.py` currently falls back to the Linux bundle when nothing else has been activated. That fallback exists for Phase A compatibility and should not be read as a complete loader system.

## What a scenario may own

A scenario may own:
- concrete drive families
- concrete sensor dimensions and payload policies
- concrete action names and side effects
- concrete candidate profiles and anchor reasons
- concrete expected-outcome labels
- concrete prior-skill and habit heuristics
- scenario-local helper modules and documentation

## What a scenario must not own

A scenario must not:
- mint release authority
- bypass mediator-owned execution
- write framework drive state directly from higher layers
- rewrite append-only audit, learning, or history tracks
- take over kernel cadence, instance legitimacy, or persistence authority

Those remain framework responsibilities even when the scenario provides most of the runtime content.

## Per-scenario documentation

Each scenario should document its concrete content in `scenarios/<name>/SPEC.md`.

That per-scenario specification should describe the actual drive set, sensors, actions, anchors, outcome observers, and prior-skill policy shipped for that world.

## Current limits of the contract

The current Phase A contract is intentionally smaller than the longer-term EVA design space.

It does not yet provide:
- a general scenario validator
- a separate scenario manifest format
- per-scenario persistence-target activation contracts
- multi-scenario runtime switching
- a richer multi-dimensional outcome schema

Those can be added later, but they are not described here as already landed features.
