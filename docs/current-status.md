# Current Status

## Overview

`eva-agent` now exposes a framework-separated EVA runtime with one primary Linux runtime and one bounded Crafter validation runtime. The repository now has:

- a framework-owned runtime spine under `eva/`
- scenario-owned runtime packages under `scenarios/linux_runtime/` and `scenarios/crafter/`
- per-scenario startup paths under `runners/`

The current public architecture entry points are:
- [Framework implementation](eva-framework-implementation.md)
- [Scenario contract](scenarios-SPEC.md)
- [Linux runtime scenario](../scenarios/linux_runtime/SPEC.md)
- [Crafter scenario](../scenarios/crafter/SPEC.md)

This page is a public status summary. It describes what is already real in the repository.

## Current public posture

The repository currently ships one primary reference runtime: **Linux runtime**.

It also now includes a second bounded Crafter scenario path used to validate the cross-scenario framework seam end to end. That means the codebase is no longer organized as one mixed implementation document pretending to describe both framework and world-specific content at the same time. Instead:

- `eva/` owns structural runtime mechanisms
- `scenarios/linux_runtime/` owns Linux-specific content
- `scenarios/crafter/` owns Crafter-specific content
- `runners/run_linux.py` and `runners/run_crafter.py` are explicit startup paths
- scenario activation, persistence-hierarchy registration, and runner-owned observation injection are explicit fail-fast seams

## What Stage G and Stage H established

### Framework side

The framework now owns:
- kernel runtime loop, cadence, instance legitimacy, and persistence boundaries
- the active-scenario seam in `eva/scenario_bundle.py`
- the explicit persistence-target hierarchy seam in `eva/persistence_targets/`
- L1 sensing registry contracts
- the generic runner-owned shared-facts injection seam used by scenario sensing when filesystem-only facts are not sufficient
- L2 drive preset seam and generic drive-update surface
- L3 structural dataclasses, multi-dimensional outcome contracts, skill provenance/registry surfaces, and mediated execution / learning seams
- append-only authority and release-token validation

### Scenario side

The Linux runtime scenario owns:
- concrete drives
- concrete sensors
- concrete actions
- concrete anchor admission policy
- concrete outcome interpretation
- concrete prior-skill / habit shaping policy

The Crafter scenario now also owns:
- concrete drives
- concrete sensors
- concrete actions
- concrete anchor admission policy
- concrete outcome interpretation
- concrete prior-skill policy
- a scenario-specific persistence hierarchy
- a wrapper-backed runtime path that feeds bounded observations into the same framework loop

### Runner side

Startup assembly is explicit:
- `runners/run_linux.py` activates the Linux scenario, registers the Linux persistence hierarchy, and calls the generic framework loop
- `runners/run_crafter.py` activates the Crafter scenario, supplies runner-owned `agent_observation` into the sensing seam, and reuses the same generic framework loop

## Current capability summary

### Implemented and structurally landed

- heartbeat-first runtime loop
- instance legitimacy and bounded continuous execution
- explicit scenario activation and persistence-hierarchy registration
- normalized L1 sensing contract with scenario-provided sensors
- drive-native internal state with scenario-provided drive preset
- pre-generative anchor domain construction with scenario-provided admission policy
- mediated response execution with scenario-provided action vocabulary
- append-only learning records with scenario-provided scalar-plus-vector outcome interpretation
- habit-bias and habit-skill shaping with provenance-aware framework skill registries
- architecture-neutral `stability_metrics/` trace consumer
- bounded Crafter end-to-end runtime integration through runner-owned observation injection and wrapper-backed action execution

### Intentionally still narrow

- Linux remains the primary shipped runtime; Crafter is currently a bounded validation scenario rather than a broad second deployment target
- bounded compatibility-style response vocabulary rather than a broad tool ecosystem
- no generic scenario loader / validator yet
- no full L4 self-model or L5 social runtime yet

## Recommended reading order

For external readers, the cleanest reading order is:

1. `docs/eva-framework-implementation.md`
2. `docs/scenarios-SPEC.md`
3. `scenarios/linux_runtime/SPEC.md`
4. `scenarios/crafter/SPEC.md`
5. this page

For historical context only:
- `docs/archive/eva-agent-full-implementation-v0.5.md`

## Practical summary

`eva-agent` is currently best understood as a **framework-separated EVA runtime with one primary Linux runtime and one Crafter validation scenario that now runs end to end through the same framework seam**.

The important architectural fact is no longer just that lower layers exist. It is that framework ownership, scenario ownership, and runner assembly are explicitly separated in code and documentation, and that the same bounded framework loop now carries more than one scenario shape without changing release authority.
