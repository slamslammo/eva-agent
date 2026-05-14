# Scenario Contract Specification

**Status**: Landed scenario contract after the Stage G capability landing and Stage H second-scenario validation  
**Scope**: Scenario packages under `scenarios/`  
**Companion documents**: `docs/eva-framework-implementation.md`, `scenarios/linux_runtime/SPEC.md`, `scenarios/crafter/SPEC.md`

---

## Purpose

This document describes the scenario contract that is actually used by the current codebase. A scenario provides the concrete world-specific content that the EVA framework operates over. The framework keeps runtime authority and structural invariants; the scenario supplies the content those structures read.

The current repository contains a primary Linux runtime scenario and a bounded Crafter validation scenario. The contract below is written at the cross-scenario level.

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
- scenario-owned dimension specs when judgment / pressure projection depend on scenario-shaped dimensions

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
- scenario-owned prior records or prior-skill policy that can participate in the framework skill registries with provenance metadata

The framework owns the dataclasses, skill registries, and append-only learning tracks. The scenario owns the concrete policy for summarizing and reusing experience, plus the scenario-local prior content that populates those framework-owned registry surfaces.

## Activation model

One scenario is active for one runtime.

The typical startup pattern is:
1. a runner imports the chosen scenario
2. the runner activates the scenario bundle
3. the runner registers the matching persistence hierarchy
4. if the scenario needs runner-owned observations or env-backed state, the runner provides those facts through the generic runtime hook
5. the runner calls the generic framework loop in `eva.kernel.main.run_runtime()`

The current repository uses `runners/run_linux.py` and `runners/run_crafter.py` as canonical examples.

`eva/scenario_bundle.py` requires explicit activation first. There is no silent fallback when no scenario has been activated, and scenario-owned startup assembly is also responsible for registering the matching persistence hierarchy.

When a scenario needs runner-owned observations instead of filesystem-only sensing, the framework still owns cadence and patrol execution; the runner only supplies extra shared facts to the existing sensing seam.

## What a scenario may own

A scenario may own:
- concrete drive families
- concrete sensor dimensions and payload policies
- concrete action names and side effects
- concrete candidate profiles and anchor reasons
- concrete expected-outcome labels
- concrete prior-skill and habit heuristics
- scenario-local helper modules and documentation
- scenario-local wrapper/runtime adapters that feed bounded observations into the framework loop

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

That per-scenario specification should describe the actual drive set, sensors, actions, anchors, outcome observers, prior-skill policy, and runner/runtime shape shipped for that world.

## Current landed contract surfaces

Beyond the original Phase A assembly seam, the current repository already treats the following as landed cross-scenario contract surfaces:
- explicit scenario activation through `eva/scenario_bundle.py`
- scenario-owned persistence-hierarchy registration paired with activation
- scenario-owned dimension specs for generic judgment / pressure projection
- runner-owned shared-facts injection into the existing sensing seam when required by a scenario
- canonical multi-dimensional outcome records through `eva/l3_deliberation/contracts.py::OutcomeVector`
- framework-owned skill registries with scenario-owned provenance-bearing prior / habit inputs

These are not future placeholders anymore; they are part of the current framework/scenario boundary.

## Current limits of the contract

The current contract is still intentionally smaller than the longer-term EVA design space.

It does not yet provide:
- a general scenario validator
- a separate scenario manifest format
- multi-scenario runtime switching

Those can be added later, but they are not described here as already landed features.
