# Current Status

## Overview

`eva-agent` has completed the Phase A framework/scenario boundary refactor for its currently shipped runtime. The repository now has:

- a framework-owned runtime spine under `eva/`
- a scenario-owned Linux runtime package under `scenarios/linux_runtime/`
- a per-scenario startup path under `runners/`

The current public architecture entry points are:
- [Framework implementation](eva-framework-implementation.md)
- [Scenario contract](scenarios-SPEC.md)
- [Linux runtime scenario](../scenarios/linux_runtime/SPEC.md)

This page is a public status summary. It describes what is already real in the repository.

## Current public posture

The repository currently ships one concrete scenario: **Linux runtime**.

That means the codebase is no longer organized as one mixed implementation document pretending to describe both framework and world-specific content at the same time. Instead:
- `eva/` owns structural runtime mechanisms
- `scenarios/linux_runtime/` owns Linux-specific content
- `runners/run_linux.py` is the canonical Linux startup path
- `eva.kernel.main` remains available as a compatibility entry

## What Phase A established

### Framework side

The framework now owns:
- kernel runtime loop, cadence, instance legitimacy, and persistence boundaries
- the active-scenario seam in `eva/scenario_bundle.py`
- L1 sensing registry contracts
- L2 drive preset seam and generic drive-update surface
- L3 structural dataclasses and mediated execution / learning seams
- append-only authority and release-token validation

### Scenario side

The Linux runtime scenario now owns:
- concrete drives
- concrete sensors
- concrete actions
- concrete anchor admission policy
- concrete outcome interpretation
- concrete prior-skill / habit shaping policy

### Runner side

Startup assembly is now explicit:
- `runners/run_linux.py` activates the Linux scenario and calls the generic framework loop

## Current capability summary

### Implemented and structurally landed

- heartbeat-first runtime loop
- instance legitimacy and bounded continuous execution
- normalized L1 sensing contract with scenario-provided sensors
- drive-native internal state with scenario-provided drive preset
- pre-generative anchor domain construction with scenario-provided admission policy
- mediated response execution with scenario-provided action vocabulary
- append-only learning records with scenario-provided outcome interpretation
- habit-bias and habit-skill shaping with scenario-provided policy

### Intentionally still narrow

- only one shipped scenario (`linux_runtime`)
- bounded compatibility-style response vocabulary rather than a broad tool ecosystem
- no generic scenario loader / validator yet
- no richer persistence-target abstraction documented as implemented
- no full L4 self-model or L5 social runtime yet

## Recommended reading order

For external readers, the cleanest reading order is:

1. `docs/eva-framework-implementation.md`
2. `docs/scenarios-SPEC.md`
3. `scenarios/linux_runtime/SPEC.md`
4. this page

For historical context only:
- `docs/archive/eva-agent-full-implementation-v0.5.md`

## Practical summary

`eva-agent` is currently best understood as a **framework-separated EVA runtime with one shipped Linux scenario**.

The important architectural fact is no longer just that lower layers exist. It is that framework ownership, scenario ownership, and runner assembly are now explicitly separated in code and documentation.
