# Implementation Tracking

This document tracks where EVA v0.5 and v0.6 theory commitments currently land in `eva-agent` code, and at what completeness level.

It answers: **for a given theory commitment, where is it in code, and how complete is it?**

For the theory itself, read [eva-theory](https://github.com/slamslammo/eva-theory). For architecture at a glance, read [`architecture-overview.md`](architecture-overview.md). For the target-state blueprint, read [`architecture-implementation-blueprint-v0.6.md`](architecture-implementation-blueprint-v0.6.md). For the current framework surface, read [`eva-framework-implementation.md`](eva-framework-implementation.md). For a direct commitment-by-commitment bridge between blueprint and tracking, read [`blueprint-to-tracking-map.md`](blueprint-to-tracking-map.md).

---

## Completeness tiers

Each commitment is classified into exactly one tier. No "in progress" or "soon" — these tiers are stable state assertions:

- **production** — implemented, exercised through current runtime surfaces, stable enough to treat as part of the canonical architecture
- **partial** — implemented but with an explicit, named limitation that materially affects how broadly the capability should be read
- **skeleton** — a framework-owned interface or placeholder exists, but the practical capability surface is minimal
- **deferred** — theory commits to it, or the docs track it as a future item, but the runtime does not currently implement it

---

## 1. Architecture-layer tracking

### 1.1 Kernel and runtime authority

| Component | Code location | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Bounded heartbeat / tick / turn runtime loop | `eva/kernel/main.py`, `eva/kernel/lifecycle.py` | production | — | — |
| Instance legitimacy (lock / generation / lease) | `eva/kernel/instance.py` | production | — | — |
| Separated atomic current-state persistence and append-only audit substrate | `eva/kernel/state.py` | production | — | — |
| Explicit scenario activation through RuntimeScenarioBundle | `eva/scenario_bundle.py` | production | — | — |
| Runner-owned startup assembly for shipped scenarios | `runners/run_linux.py`, `runners/run_crafter.py` | production | — | — |
| Integrated fast/slow closed-loop runtime composition | `eva/kernel/main.py`, `eva/l1_sensing/signal_bus.py`, `eva/l2_drive/reflex.py`, `eva/l3_deliberation/contracts.py` | production | — | — |
| Explicit persistence hierarchy contract | `eva/persistence_targets/__init__.py` | production | — | — |
| Scenario-owned activation of lower persistence levels | `scenarios/linux_runtime/persistence/`, `scenarios/crafter/persistence/` | production | — | — |
| Persistence target Levels 5–7 | — | deferred | Theoretical placeholder; mechanisms reserved for future versions | Later phase |
| Architecture-neutral stability profile calculation from trace files | `stability_metrics/` | production | — | — |
| Comparative Stability Hypothesis evaluation program | — | deferred | Measurement surface exists; comparative experiment program not yet landed | Later phase |

### 1.2 L1 homeostatic sensing

| Component | Code location | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Normalized sensor registry and sensing contract | `eva/l1_sensing/sensor_registry.py`, `eva/scenario_bundle.py` | production | — | — |
| Scenario-declared dimension specifications with rate-sensing tier metadata | `eva/l1_sensing/dimension_specs.py`, scenario `dimensions/` declarations | production | — | — |
| Rate-aware sensing with explicit unknown fallback | `eva/l1_sensing/rate_sensors.py`, `eva/l1_sensing/dimension_specs.py` | production | — | — |
| Signal publication with explicit status / threat classification | `eva/l1_sensing/signal_bus.py` | production | — | — |

### 1.3 L2 drive and pressure handling

| Component | Code location | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Drive preset and drive-update seam | `eva/l2_drive/drive_registry.py`, `eva/l2_drive/pressure_to_drive.py` | production | — | — |
| Read-only drive broadcast with L2-owned state authority | `eva/l2_drive/drive_registry.py`, `eva/l3_deliberation/contracts.py` | production | — | — |
| Pressure projection with urgency modulation and bounded anticipatory pressure | `eva/l2_drive/pressure_projection.py` | production | — | — |
| Protective reflex fast path parallel to slower deliberation | `eva/l2_drive/reflex.py` | production | — | — |

### 1.4 L3 deliberation, peer circuit, and learning

| Component | Code location | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Canonical deliberation input contract | `eva/l3_deliberation/contracts.py` | production | — | — |
| Four-layer memory surface (working / episodic / semantic / procedural) | `eva/l3_deliberation/reasoning/working_memory.py`, `eva/l3_deliberation/memory/`, `eva/skills/__init__.py` | partial | Semantic store-side windowing / indexing not implemented; procedural memory remains habit-backed rather than a dedicated store | Stage I follow-up #1, future evaluation |
| Mediator as independent peer circuit (default inhibition + selective release) | `eva/l3_deliberation/peer_circuit/mediator.py` | production | — | — |
| Runtime-only release token boundary | `eva/l3_deliberation/contracts.py` | production | — | — |
| Drive-weighted candidate assessment with bounded learned overlays | `eva/l3_deliberation/reasoning/value_judgment.py`, `eva/l3_deliberation/peer_circuit/rpe.py` | production | — | — |
| Append-only learning outcome records with canonical `OutcomeVector` support | `eva/l3_deliberation/contracts.py`, `eva/l3_deliberation/peer_circuit/rpe.py`, scenario outcome observers | production | — | — |
| RPE-like learning as internal update signal | `eva/l3_deliberation/peer_circuit/rpe.py` | production | — | — |
| Habit shaping and skill crystallization through habit track | `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/l3_deliberation/memory/skill_library.py` | production | — | — |
| Advisory-only working-memory assembly | `eva/l3_deliberation/reasoning/working_memory.py` | production | — | — |
| Model-backed working-memory advisory path with bounded fallback | `eva/kernel/main.py`, `eva/l3_deliberation/reasoning/working_memory.py` | production | — | — |
| Episodic retrieval over append-only artifacts | `eva/l3_deliberation/memory/episodic.py`, `eva/l3_deliberation/memory/retrieval.py` | production | — | — |
| Semantic memory — first-class storage + exact query + bounded L3 participation | `eva/l3_deliberation/memory/semantic.py`, `eva/skills/__init__.py` | partial | Store-side windowing / indexing not implemented; semantic → L2 drive-weight semantics not implemented | Stage I follow-up #1, #2 |
| Semantic memory → L2 drive-weight semantics | — | deferred | Preserved to maintain drive read-only boundary; minimal safe path evaluation deferred | Stage I follow-up #2 |
| Procedural memory via existing habit-track substrate | `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/skills/__init__.py` | partial | Surface is explicit but backing track remains `habit_bias.jsonl` rather than a dedicated procedural store | Future evaluation |
| Working-memory interface signature | `eva/l3_deliberation/reasoning/working_memory.py` | partial | Multi-parameter assembly is accumulating; interface review threshold approaching | Watch (Stage I follow-up #3) |

### 1.5 Anchors and mediated release

| Component | Code location | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Framework-owned action domain and pre-generative restriction surface | `eva/anchor/domain_restriction.py` | production | — | — |
| Scenario-owned anchor admission policy through active bundle seam | `eva/scenario_bundle.py`, scenario `anchors/` | production | — | — |
| Capability restriction and parameter-domain restriction inside the active action domain | `eva/anchor/domain_restriction.py`, `eva/l3_deliberation/tool_edge/tool_registry.py` | production | — | — |
| Mediated candidate filtering, selection, and execution path | `eva/l3_deliberation/tool_edge/tool_registry.py`, `eva/l3_deliberation/tool_edge/executors.py` | production | — | — |
| Anchor three-layer distinction (mechanism / constitutional policies / emergent overlays) | `eva/anchor/domain_restriction.py`, scenario anchor policies | partial | Mechanism / constitutional policy separation is clear; emergent overlay story is narrower than the theory's long-term framing | Future deepening |

### 1.6 Inherited priors and capability provenance

| Component | Code location | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Same-scenario inherited-prior distillation pipeline | `inheritance_distillation/` | production | — | — |
| Same-scenario inherited-prior loading and bounded deliberation participation | `eva/skills/__init__.py`, `eva/l3_deliberation/reasoning/working_memory.py`, `eva/l3_deliberation/peer_circuit/habit_track.py`, scenario `prior_skills/inherited.py` | production | — | — |
| Capability provenance-carrying skill registries | `eva/skills/__init__.py`, scenario prior-skill bundles | partial | Provenance is explicit on current records; broader theory-side source taxonomy not yet active as distinct runtime sources | Future evaluation |
| Cross-scenario inherited-prior transmission | — | deferred | Same-scenario is landed; cross-scenario requires additional constraint work | Later phase |

### 1.7 Deferred and reserved items

| Component | Theory reference | Completeness | Known limitation | Planned evolution |
|---|---|---|---|---|
| Exploration as growth driver | v0.6 §1.4 | deferred | Theory is specified; runtime mechanism not implemented | Medium-term |
| L4 self-model runtime | v0.5 §9, v0.6 §7.2 | deferred | Reserved interfaces; implementation deferred | Later phase |
| L5 social-layer runtime | v0.5 §10, v0.6 §7.2 | deferred | Reserved interfaces; implementation deferred | Later phase |
| Generic scenario loader / validator | — | deferred | Repository uses explicit runner assembly | Future evaluation |
| Multi-scenario runtime switching inside one process | — | deferred | Not in current scope | Future evaluation |

---

## 2. Scenario contract tracking

Tracks the cross-scenario integration contract. For the full contract specification, see [`scenarios-SPEC.md`](scenarios-SPEC.md).

| Contract component | Code location | Completeness | Known limitation |
|---|---|---|---|
| `RuntimeScenarioBundle` interface | `eva/scenario_bundle.py` | production | — |
| `SensorPolicyBundle` integration | `eva/l1_sensing/sensor_registry.py` | production | — |
| `ActionPolicyBundle` integration | `eva/l3_deliberation/tool_edge/tool_registry.py` | production | — |
| `AnchorPolicyBundle` integration | `eva/anchor/domain_restriction.py` | production | — |
| `OutcomeObserverBundle` integration | `eva/l3_deliberation/contracts.py` | production | — |
| `PriorSkillBundle` integration | `eva/skills/__init__.py` | partial | Provenance boundary deepening is a future item |
| Scenario-owned persistence hierarchy registration | `scenarios/linux_runtime/persistence/`, `scenarios/crafter/persistence/` | production | — |
| Canonical multi-dimensional `OutcomeVector` | `eva/l3_deliberation/contracts.py` | production | — |
| Framework-owned skill registries with scenario-owned provenance inputs | `eva/skills/__init__.py` | production | — |

---

## 3. Per-scenario tracking

### Linux runtime

| Item | Status | Reference |
|---|---|---|
| Primary reference runtime deployment | production | [`scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md) |
| Linux-specific drive family, sensors, bounded action vocabulary, anchors, outcome observers | production | [`scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md) |
| Same-scenario inherited-prior reuse for Linux-qualified bundles | production | [`scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md) |

### Crafter

| Item | Status | Reference |
|---|---|---|
| Bounded end-to-end Crafter runtime through shared framework loop | partial | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) — a real landed second scenario but documented as intentionally bounded in scope |
| Crafter-specific drives, sensors, bounded action bridge, anchors, outcome observers, persistence hierarchy, prior-skill policy | production (within bounded scope) | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) |
| Trajectory-aware sensing and bounded anticipatory pressure for required-tier dimensions | production | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) |

---

## 4. Open follow-ups

The following items are confirmed as carry-forward follow-ups, not accidental gaps:

| Item | Source | Status |
|---|---|---|
| Semantic memory store-side windowing / indexing | Stage I follow-up #1 | open |
| Semantic memory → L2 drive-weight semantics safe path evaluation | Stage I follow-up #2 | open |
| Working-memory interface signature review threshold | Stage I follow-up #3 | watch |

---

## 5. How this document relates to other docs

- **`architecture-overview.md`** — this document's entries are the concrete commitments that the architecture overview maps visually
- **`eva-framework-implementation.md`** — the authoritative source for what the framework currently owns; this tracking document maps those capabilities back to their theory commitments
- **`scenarios-SPEC.md`** — the contract specification for how scenarios integrate with the framework; per-scenario tracking here links to the concrete per-scenario specs
- **Theory → implementation landing** was previously in `theory-implementation-landing.md`; that content is now incorporated here and in `architecture-overview.md`

This document is updated at the close of each stage. Between stages, it reflects the last confirmed state.