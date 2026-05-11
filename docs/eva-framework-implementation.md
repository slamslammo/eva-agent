# EVA Framework Implementation

**Status**: Landed framework boundary after Stage G capability landing  
**Scope**: Framework code under `eva/`  
**Companion documents**: `docs/scenarios-SPEC.md`, `scenarios/linux_runtime/SPEC.md`  
**Historical reference**: `docs/archive/eva-agent-full-implementation-v0.5.md`

---

## Purpose

This document describes the framework mechanisms that are already implemented in the repository. It covers the structural runtime that remains constant across scenarios and the seams through which scenario-owned content is activated.

It does not specify Linux-only drives, sensors, actions, anchor rules, outcome labels, or prior-skill heuristics. Those belong in scenario documents.

## Current framework boundary

The framework currently owns the following runtime surfaces.

### 1. Kernel runtime authority

The kernel owns the bounded runtime loop, cadence, instance legitimacy, and persistence boundaries.

Canonical framework entrypoints:
- `eva/kernel/main.py` — generic `run_runtime()` loop and compatibility CLI entry
- `eva/kernel/lifecycle.py` — heartbeat / tick / turn authority
- `eva/kernel/instance.py` — instance legitimacy
- `eva/kernel/state.py` — current-state and append-only artifact writes
- `eva/kernel/config.py` — runtime configuration contracts

### 2. Active scenario seam

The framework exposes one active-scenario activation seam in `eva/scenario_bundle.py`.

It defines:
- `RuntimeScenarioBundle`
- `SensorPolicyBundle`
- `ActionPolicyBundle`
- `AnchorPolicyBundle`
- `OutcomeObserverBundle`
- `PriorSkillBundle`

A running agent uses one active bundle at a time. The framework reads scenario policy through this seam instead of importing scenario-specific modules across the codebase.

### 3. L1 framework mechanism

The framework keeps the registry and collection contracts for sensing:
- `SensorSpec`
- `SensorOutput`
- `SensingContext`
- `SensorRegistry`

These live in `eva/l1_sensing/sensor_registry.py`.

The framework owns the normalized sensing contract and collection ordering. Concrete sensor providers come from the active scenario bundle.

### 4. L2 drive mechanism

The framework keeps the generic drive seam in `eva/l2_drive/drive_registry.py`:
- `DrivePreset`
- `DriveUpdatePolicy`
- default preset registration / resolution

The framework still owns drive update semantics, read-only downstream consumption, and the invariant that higher layers do not write drive state directly. Concrete drive families and dimension mappings come from the active scenario.

### 5. L3 structural mechanisms

The framework owns the structure of:
- anchor-time `ActionDomain` construction in `eva/anchor/domain_restriction.py`
- response candidate / filter / selection dataclasses in `eva/l3_deliberation/tool_edge/tool_registry.py`
- mediated execution path in `eva/l3_deliberation/tool_edge/executors.py`
- learning outcome records and learned-impact overlay in `eva/l3_deliberation/peer_circuit/rpe.py`
- the canonical multi-dimensional `OutcomeVector` contract in `eva/l3_deliberation/contracts.py`
- skill provenance and registry types in `eva/skills/__init__.py`
- the persistence-target hierarchy contract in `eva/persistence_targets/__init__.py`
- habit-bias and habit-skill summary dataclasses in `eva/l3_deliberation/memory/skill_library.py`

The framework therefore owns the structure of deliberation, mediated release, append-only learning records, read-side learning overlays, explicit persistence-target lookup, and skill provenance. Concrete policy inside those structures comes from the active scenario.

### 6. Append-only and authority boundaries

The framework remains the owner of:
- current runtime state writes
- append-only event and audit writes
- mediated release authority
- runtime-only release-token validation
- the rule that scenario content may shape candidates and interpretation, but may not bypass release or rewrite history

## What the framework does not own

The framework does not own:
- concrete drive names or dimension mappings
- concrete sensor dimensions or payload policies
- concrete action names, postures, or handlers
- scenario-specific candidate profiles or anchor reason vocabularies
- scenario-specific expected-outcome labels
- scenario-specific prior-skill or habit derivation policy
- per-scenario startup assembly

Those belong in `scenarios/<name>/` and `runners/run_<name>.py`.

## Current compatibility surfaces

Stage G intentionally keeps a small set of framework-owned compatibility wrappers that delegate scenario policy through the active bundle:
- `eva/l1_sensing/state_sensors.py`
- `eva/l2_drive/drive_registry.py`
- `eva/anchor/domain_restriction.py`
- `eva/l3_deliberation/tool_edge/tool_registry.py`
- `eva/l3_deliberation/tool_edge/executors.py`
- `eva/l3_deliberation/peer_circuit/rpe.py`
- `eva/l3_deliberation/memory/skill_library.py`

These files are part of the framework boundary. Their job is to preserve structural ownership while avoiding scattered direct imports of a specific scenario.

## Runner and activation model

A runner activates a scenario bundle before calling the generic framework loop.

Current shipped example:
- `runners/run_linux.py` activates `scenarios/linux_runtime`, registers the Linux persistence hierarchy, and then calls `eva.kernel.main.run_runtime()`

A running runtime must explicitly activate a scenario bundle before using scenario-dependent framework features, and scenario-owned startup assembly is responsible for registering the matching persistence hierarchy. `eva/kernel/main.py` remains a compatibility entry, but there is no silent fallback when no scenario has been activated.

## Not yet landed as framework features

The following concepts are not documented here as implemented framework features:
- a generic scenario loader / validator
- concrete L4 self-model or L5 social-layer runtime implementations

The top-level `stability_metrics/` package is a landed companion module, and `eva/l3_deliberation/contracts.py`, `eva/persistence_targets/`, and `eva/skills/` already contain implemented framework seams. This document keeps those surfaces in the current-boundary sections above rather than listing them as future work.

## Boundary rule

If a mechanism must preserve cadence, instance legitimacy, mediated release, append-only history, or cross-scenario structure, it belongs in the framework.

If a capability changes with the world the agent is embedded in, it belongs in a scenario.
