# Capability Inventory

This document is the flat capability view of `eva-agent`: what capabilities exist, what tier each capability currently has, and where the owning code or scenario surface lives.

For theory commitments and section references, see [theory-implementation-landing.md](theory-implementation-landing.md). For scenario-local detail, see the scenario `SPEC.md` files.

## Completeness tiers

Each capability is classified into exactly one tier:

- **production** — implemented in the current repository, exercised through the current runtime surfaces, and stable enough to be treated as part of the canonical architecture
- **partial** — implemented, but with an explicit limitation, narrower field coverage, or an open follow-up that materially affects how broadly the capability should be read
- **skeleton** — a framework-owned interface or placeholder exists, but the practical capability surface is still minimal
- **deferred** — theory commits to it, or the docs track it as a future item, but the runtime does not currently implement it

## Framework capabilities

### Runtime authority and scenario assembly

- **Bounded heartbeat / tick / turn runtime loop — production**  
  Owners: `eva/kernel/main.py`, `eva/kernel/lifecycle.py`
- **Instance legitimacy, startup/shutdown handling, and append-only runtime artifacts — production**  
  Owners: `eva/kernel/instance.py`, `eva/kernel/state.py`
- **Explicit scenario activation through one runtime bundle seam — production**  
  Owners: `eva/scenario_bundle.py`
- **Runner-owned startup assembly for shipped scenarios — production**  
  Owners: `runners/run_linux.py`, `runners/run_crafter.py`

### L1 homeostatic sensing

- **Normalized sensor registry and sensing contract — production**  
  Owners: `eva/l1_sensing/sensor_registry.py`, `eva/scenario_bundle.py`
- **Scenario-declared dimension specifications with rate-sensing tier metadata — production**  
  Owners: `eva/l1_sensing/dimension_specs.py`, scenario `dimensions/` declarations
- **Rate-aware sensing with explicit unknown fallback — production**  
  Owners: `eva/l1_sensing/rate_sensors.py`, `eva/l1_sensing/dimension_specs.py`
- **Signal publication with explicit status / threat classification — production**  
  Owners: `eva/l1_sensing/signal_bus.py`

### L2 drive and pressure handling

- **Drive preset and drive-update seam — production**  
  Owners: `eva/l2_drive/drive_registry.py`, `eva/l2_drive/pressure_to_drive.py`
- **Pressure projection with urgency modulation and bounded anticipatory pressure — production**  
  Owners: `eva/l2_drive/pressure_projection.py`
- **Protective reflex fast path parallel to slower deliberation — production**  
  Owners: `eva/l2_drive/reflex.py`

### Anchor and mediated release

- **Framework-owned action domain and pre-generative restriction surface — production**  
  Owners: `eva/anchor/domain_restriction.py`
- **Scenario-owned anchor admission policy through the active bundle seam — production**  
  Owners: `eva/scenario_bundle.py`, `scenarios/linux_runtime/anchors/`, `scenarios/crafter/anchors/`
- **Mediated candidate filtering, selection, and execution path — production**  
  Owners: `eva/l3_deliberation/tool_edge/tool_registry.py`, `eva/l3_deliberation/tool_edge/executors.py`
- **Runtime-only release token boundary — production**  
  Owners: `eva/l3_deliberation/contracts.py`

### L3 deliberation, learning, and memory

- **Canonical deliberation input contract — production**  
  Owners: `eva/l3_deliberation/contracts.py`
- **Drive-weighted candidate assessment with bounded learned overlays — production**  
  Owners: `eva/l3_deliberation/reasoning/value_judgment.py`, `eva/l3_deliberation/peer_circuit/rpe.py`
- **Append-only learning outcome records with canonical `OutcomeVector` support — production**  
  Owners: `eva/l3_deliberation/contracts.py`, `eva/l3_deliberation/peer_circuit/rpe.py`, scenario outcome observers
- **Habit shaping and skill crystallization through the habit track — production**  
  Owners: `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/l3_deliberation/memory/skill_library.py`
- **Advisory-only working-memory assembly — production**  
  Owners: `eva/l3_deliberation/reasoning/working_memory.py`
- **Model-backed working-memory advisory path with bounded fallback — production**  
  Owners: `eva/kernel/main.py`, `eva/l3_deliberation/reasoning/working_memory.py`
- **Episodic retrieval over append-only artifacts — production**  
  Owners: `eva/l3_deliberation/memory/episodic.py`, `eva/l3_deliberation/memory/retrieval.py`
- **Semantic memory layer — partial**  
  Owners: `eva/l3_deliberation/memory/semantic.py`, `eva/skills/__init__.py`  
  Gap: first-class storage, exact query helpers, and bounded working-memory participation are landed, but store-side windowing / indexing remains open and semantic memory does not yet inform L2 drive-weight semantics.  
  Evidence: `../maintainer/development/stage-i-followups.md`
- **Procedural memory via the existing habit-track substrate — partial**  
  Owners: `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/skills/__init__.py`  
  Gap: the procedural surface is explicit, but the backing track remains `habit_bias.jsonl` rather than a distinct dedicated procedural store.  
  Evidence: `eva-framework-implementation.md`
- **Same-scenario inherited-prior distillation pipeline — production**  
  Owners: `inheritance_distillation/`
- **Same-scenario inherited-prior loading and bounded deliberation participation — production**  
  Owners: `eva/skills/__init__.py`, `eva/l3_deliberation/reasoning/working_memory.py`, `eva/l3_deliberation/peer_circuit/habit_track.py`, scenario `prior_skills/inherited.py`
- **Capability provenance-carrying skill registries — partial**  
  Owners: `eva/skills/__init__.py`, scenario prior-skill bundles  
  Gap: provenance is explicit on current scenario / experience / inherited records, but the broader theory-side source taxonomy is not yet fully active as distinct runtime sources.  
  Evidence: `eva/skills/__init__.py`

### Persistence and observability

- **Explicit persistence hierarchy contract — production**  
  Owners: `eva/persistence_targets/__init__.py`
- **Scenario-owned activation of lower persistence levels in shipped runtimes — production**  
  Owners: `scenarios/linux_runtime/persistence/`, `scenarios/crafter/persistence/`
- **Architecture-neutral stability profile calculation from trace files — production**  
  Owners: `stability_metrics/`
- **Comparative stability evaluation program — deferred**  
  Measurement surface exists, but the comparative baseline/experiment program is a later validation trajectory rather than a landed runtime capability.

### Additional framework-adjacent capabilities

- **Generic scenario loader / validator — deferred**  
  The repository uses explicit runner assembly rather than a generic loader.
- **Multi-scenario runtime switching inside one running process — deferred**
- **Exploration-as-growth mechanism — deferred**  
  Tracked theory-side in v0.6 §1.4 and explicitly left outside Stage I scope.
- **L4 self-model runtime — deferred**
- **L5 social-layer runtime — deferred**
- **Persistence target Levels 5–7 activation — deferred**

## Scenario capabilities

### Linux runtime scenario

- **Primary Linux runtime deployment — production**  
  Owners: `scenarios/linux_runtime/`, `runners/run_linux.py`  
  Reference: `../scenarios/linux_runtime/SPEC.md`
- **Linux-specific drive family, sensors, bounded action vocabulary, anchors, outcome observers, and prior-skill policy — production**  
  Reference: `../scenarios/linux_runtime/SPEC.md`
- **Same-scenario inherited-prior reuse for Linux-qualified bundles — production**  
  Reference: `../scenarios/linux_runtime/SPEC.md`

### Crafter scenario

- **Bounded end-to-end Crafter runtime through the shared framework loop — partial**  
  Owners: `scenarios/crafter/`, `runners/run_crafter.py`  
  Gap: the Crafter path is a real landed second scenario, but it is still documented as a bounded validation runtime rather than a broad second deployment target.  
  Reference: `../scenarios/crafter/SPEC.md`
- **Crafter-specific drives, sensors, bounded action bridge, anchors, outcome observers, persistence hierarchy, and prior-skill policy — production within the bounded Crafter field**  
  Reference: `../scenarios/crafter/SPEC.md`
- **Crafter trajectory-aware sensing and bounded anticipatory pressure for required-tier dimensions — production**  
  Reference: `../scenarios/crafter/SPEC.md`

## Deferred and watched items

The following items are explicitly being carried forward rather than treated as missing by accident:

- **Semantic-memory store-side windowing / indexing — deferred follow-up**  
  Source: `../maintainer/development/stage-i-followups.md`
- **Semantic memory participation in L2 drive-weight semantics — deferred follow-up**  
  Source: `../maintainer/development/stage-i-followups.md`
- **Working-memory interface signature review — watched follow-up**  
  Source: `../maintainer/development/stage-i-followups.md`
- **Cross-scenario inherited-prior distillation and reuse — deferred**
- **Comparative Stability Hypothesis experiments — deferred**
- **Exploration as growth driver — deferred**
- **Persistence target Levels 5–7 — deferred**
- **L4 self-model deepening — deferred**
- **L5 social cognition deepening — deferred**

If a capability is not listed above as `deferred`, `partial`, or `skeleton`, this document is asserting that the capability is already part of the currently landed repository surface.