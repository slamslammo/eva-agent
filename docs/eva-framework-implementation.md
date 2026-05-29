# EVA Framework Implementation

**Status**: Stage I I-4 same-scenario inherited-prior reuse landed on the Stage G framework boundary  
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

The kernel also consumes the active scenario's `clock_source` (declared in its `ExistenceSemantics`) to choose how cadence accounting advances. `LifecycleRuntime._update_scenario_counters` reads `clock_source` at construction: under `step` it honors the bridge's deferred signal (scenario time advances only on an invoked `env.step`, and a persistent defer streak exits to `needs_human_consecutive_deferred`); under `wall_clock` (default) it enforces `attempt_index == scenario_step_index`. This selection is owned by the **kernel, not the scenario bridge** — per-scenario forks of cadence logic remain forbidden (blueprint §2.7). Choosing the cadence source never freezes heartbeat / lease / liveness; only `scenario_step_index` is gated.

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
- working-memory assembly and bounded advisory attachment in `eva/l3_deliberation/reasoning/working_memory.py`
- episodic / semantic / procedural memory owners under `eva/l3_deliberation/memory/`
- habit-bias and habit-skill summary dataclasses in `eva/l3_deliberation/memory/skill_library.py`
- inherited-prior loading, shaping, and bounded value bias through `InheritedPriorRegistry`, `eva/l3_deliberation/peer_circuit/habit_track.py`, and `eva/l3_deliberation/reasoning/value_judgment.py`

The framework therefore owns the structure of deliberation, mediated release, append-only learning records, read-side learning overlays, explicit persistence-target lookup, Stage I four-layer memory surfaces, and skill provenance. Concrete policy inside those structures comes from the active scenario.

### 6. Append-only and authority boundaries

The framework remains the owner of:
- current runtime state writes
- append-only event and audit writes
- append-only cognitive / learning / habit / semantic memory tracks
- mediated release authority
- runtime-only release-token validation
- the rule that scenario content may shape candidates and interpretation, but may not bypass release or rewrite history

## Stage I four-layer memory model

Stage I I-3 makes the memory layers explicit without widening authority boundaries.

### Layer surfaces
- `WorkingMemory` / `WorkingMemoryContext` in `eva/l3_deliberation/reasoning/working_memory.py`
  - in-cycle only; not persisted
  - assembled from bounded retrieval over append-only artifacts
- `EpisodicMemoryRegistry` in `eva/skills/__init__.py`
  - record surface for relevance-anchored cross-cycle traces
  - current practical backing: `cognitive_memory_stub.jsonl`, `learning_outcomes.jsonl`, and bounded response-history reuse
- `SemanticMemoryRegistry` in `eva/skills/__init__.py`
  - record surface for regularities extracted from episodes
  - current practical backing: `semantic_memory.jsonl`
- `ProceduralMemoryRegistry` in `eva/skills/__init__.py`
  - record surface for condition-matched action patterns
  - current practical backing: `habit_bias.jsonl` through the existing habit path

### Stage I storage mapping

| Layer | Current storage / owner | Stage I status |
|---|---|---|
| Working memory | in-cycle `WorkingMemory` assembly | explicit interface landed |
| Episodic memory | `cognitive_memory_stub.jsonl`, `learning_outcomes.jsonl`, response history retrieval | explicit registry surface landed |
| Semantic memory | `semantic_memory.jsonl` | first-class append-only storage + query interface landed |
| Procedural memory | `habit_bias.jsonl` | explicit registry surface landed via Stage I path (b) |

### Semantic memory in Stage I
- storage path is configured in `eva/kernel/config.py` and persisted through `eva/kernel/state.py`
- owner helpers in `eva/l3_deliberation/memory/semantic.py` support append, read, exact query-by-topic, and exact query-by-scope
- Stage I does **not** implement automatic episodic-to-semantic extraction; semantic storage is provided as a first-class owner and read-side participation seam only
- runtime participation is bounded: matching semantic entries are retrieved into working memory and may add a tiny auditable candidate prior modifier during value judgment

### Procedural memory in Stage I
- Stage I adopts path **(b)** from the startup instruction review: formalize and slightly extend the existing habit path rather than adding a separate `procedural_memory.jsonl`
- `habit_bias.jsonl` remains the backing track
- `derive_habit_skills()` and `habit_skill_registry()` now form the explicit procedural-memory read surface
- `shape_candidates_with_habit_track()` remains the candidate-generation shortcut seam
- procedural shaping can narrow or reorder candidates, but does not own release authority and does not bypass mediator gating

### Integration status by layer
- **Working memory → L3 deliberation**: direct input; landed
- **Episodic memory → L3 deliberation**: relevance retrieval; landed
- **Semantic memory → L3 deliberation**: bounded candidate prior modifier; landed
- **Semantic memory → L2 drive weights**: deferred in I-3 to preserve the existing drive-boundary invariant
- **Procedural memory → L3 deliberation**: candidate shaping / shortcut via habit path; landed

These Stage I memory surfaces remain bounded, append-only compatible, and scenario-qualified where retrieval could otherwise leak across scenarios.

## Stage I inherited-prior reuse

Stage I I-4 adds same-scenario inter-life reuse without creating a second decision lane.

### Framework/runtime boundary
- `InheritedPriorRecord` / `InheritedPriorRegistry` in `eva/skills/__init__.py` are the framework-owned record surfaces for loaded inherited priors
- runtime config in `eva/kernel/config.py` and CLI parsing in `eva/kernel/main.py` now carry an optional `inherited_priors_path`
- scenario activation remains the only place where bundle loading happens; the framework reads inherited priors through the existing active-scenario seam

### Runtime participation
- working-memory assembly in `eva/l3_deliberation/reasoning/working_memory.py` now surfaces `inherited_priors` for the exact current `situation_key`
- `shape_candidates_with_habit_track()` merges inherited-prior hints into the existing habit-path shaping flow
- `assess_candidates()` applies only a tiny auditable `inherited_prior_bias` when a matching prior is strong enough
- inherited priors remain advisory: anchors still bound admission, mediator still owns release, and append-only artifacts remain framework-owned

### Distillation boundary
- `inheritance_distillation/` is now a landed top-level package separate from `eva/` and `scenarios/`
- it reads append-only trace files, extracts same-scenario regularities, validates structural invariants, and writes `DistilledPriorBundle.json`
- it does not import framework or scenario modules

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
