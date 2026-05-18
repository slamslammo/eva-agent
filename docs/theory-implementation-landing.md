# Theory → Implementation Landing Map

This document maps major EVA v0.5 and v0.6 commitments to their current implementation locations in `eva-agent`.

It is not a restatement of the theory. Read the `eva-theory` repository for the theory itself. This document answers a narrower question: **where does a given commitment currently land in code, and how complete is that landing?**

Each entry includes:

- **Theory reference** — the relevant v0.5 or v0.6 section
- **Implementation location** — the owning code or scenario surface
- **Completeness** — `production`, `partial`, `skeleton`, or `deferred`
- **Notes** — current boundary or limitation

## L1 — Homeostatic Sensing

### State sensing as an explicit architectural layer

- **Theory reference:** v0.5 §6
- **Implementation location:** `eva/l1_sensing/sensor_registry.py`, `eva/scenario_bundle.py`
- **Completeness:** production
- **Notes:** the framework owns the normalized sensing contract and registry; scenarios provide the concrete sensors.

### Rate sensing for active persistence

- **Theory reference:** v0.6 §1.2.1–§1.2.5
- **Implementation location:** `eva/l1_sensing/dimension_specs.py`, `eva/l1_sensing/rate_sensors.py`, scenario dimension declarations
- **Completeness:** production
- **Notes:** the framework carries explicit rate tiers, method declarations, anticipatory-threshold seams, and the explicit unknown fallback shape.

### Status + rate combination in pressure judgment

- **Theory reference:** v0.6 §1.2.4
- **Implementation location:** `eva/l2_drive/pressure_projection.py`
- **Completeness:** production
- **Notes:** urgency is modulated by rate direction, and required-tier dimensions may emit bounded anticipatory pressure when configured.

### Signal architecture with differentiated downstream paths

- **Theory reference:** v0.5 §12
- **Implementation location:** `eva/l1_sensing/signal_bus.py`, `eva/l2_drive/reflex.py`, `eva/l3_deliberation/contracts.py`
- **Completeness:** production
- **Notes:** the current implementation exposes explicit status / threat publication plus a bounded reflex fast path parallel to slower deliberation.

## L2 — Drive Layer

### Drive as context rather than command

- **Theory reference:** v0.5 §7.4
- **Implementation location:** `eva/l2_drive/drive_registry.py`, `eva/l2_drive/pressure_to_drive.py`, `eva/l3_deliberation/contracts.py`
- **Completeness:** production
- **Notes:** drive state is framework-owned and consumed downstream as broadcast context rather than command authority.

### Internal drive update structure

- **Theory reference:** v0.5 §7.5
- **Implementation location:** `eva/l2_drive/drive_registry.py`, scenario `drive_preset.py`
- **Completeness:** production
- **Notes:** concrete drive families remain scenario-owned; update semantics remain framework-owned.

### Suppression and release-boundary discipline

- **Theory reference:** v0.5 §7.8
- **Implementation location:** `eva/l3_deliberation/contracts.py`, `eva/l3_deliberation/tool_edge/`, `eva/l2_drive/reflex.py`
- **Completeness:** production
- **Notes:** higher layers do not directly execute side effects; release remains mediated.

## L3 — Adaptive Deliberation

### Reasoning distinct from release

- **Theory reference:** v0.5 §8.6, v0.5 §15.2
- **Implementation location:** `eva/l3_deliberation/reasoning/`, `eva/l3_deliberation/tool_edge/`, `eva/l3_deliberation/contracts.py`
- **Completeness:** production
- **Notes:** candidate generation, value judgment, release decision, and execution remain distinct surfaces.

### Mediator as action-release authority

- **Theory reference:** v0.5 §8.6.4
- **Implementation location:** `eva/l3_deliberation/peer_circuit/mediator.py`, `eva/l3_deliberation/contracts.py`
- **Completeness:** production
- **Notes:** release authority is treated as a peer-circuit function rather than a reasoning sub-module.

### RPE-like learning as an internal update signal

- **Theory reference:** v0.5 §8.6.4 Function 2, v0.6 §6.3
- **Implementation location:** `eva/l3_deliberation/peer_circuit/rpe.py`
- **Completeness:** production
- **Notes:** current learning records already support canonical `OutcomeVector` payloads; v0.5’s scalar case remains visible as a bounded compatibility surface.

### Habit track / skill crystallization

- **Theory reference:** v0.5 §8.6.4 Function 3
- **Implementation location:** `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/l3_deliberation/memory/skill_library.py`
- **Completeness:** production
- **Notes:** repeated experience can narrow or reorder candidates through the existing mediated path; it does not bypass anchors or release gating.

### Working memory as the in-cycle deliberative surface

- **Theory reference:** v0.5 §8.6.1, v0.6 §3.5.1
- **Implementation location:** `eva/l3_deliberation/reasoning/working_memory.py`
- **Completeness:** production
- **Notes:** the repo treats working memory as an in-cycle assembly surface, with bounded advisory extension rather than release authority.

### Episodic memory participation

- **Theory reference:** v0.5 §8.6.1, v0.6 §3.5.1–§3.5.4
- **Implementation location:** `eva/l3_deliberation/memory/episodic.py`, `eva/l3_deliberation/memory/retrieval.py`, `eva/skills/__init__.py`
- **Completeness:** production
- **Notes:** episodic reuse is assembled from append-only artifacts and fed back into working memory.

### Semantic memory participation

- **Theory reference:** v0.6 §3.5.1–§3.5.4
- **Implementation location:** `eva/l3_deliberation/memory/semantic.py`, `eva/skills/__init__.py`, `eva/l3_deliberation/reasoning/working_memory.py`, `eva/l3_deliberation/reasoning/value_judgment.py`
- **Completeness:** partial
- **Notes:** storage, exact query, retrieval into working memory, and tiny value-judgment bias are landed; store-side windowing/indexing and semantic-to-L2 drive weighting remain open follow-ups.

### Procedural memory participation

- **Theory reference:** v0.6 §3.5.1–§3.5.4
- **Implementation location:** `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/skills/__init__.py`
- **Completeness:** partial
- **Notes:** the procedural surface is explicit, but the current implementation reuses the existing habit track as the practical backing store.

### Inherited priors as an L3 mechanism

- **Theory reference:** v0.6 §3.6.1–§3.6.6, v0.6 Appendix R.8
- **Implementation location:** `eva/skills/__init__.py`, `eva/l3_deliberation/reasoning/working_memory.py`, `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/l3_deliberation/reasoning/value_judgment.py`, `inheritance_distillation/`, scenario `prior_skills/inherited.py`
- **Completeness:** production
- **Notes:** same-scenario distillation, loading, and bounded advisory participation are landed; cross-scenario transmission is not.

### Multi-dimensional outcome and drive-conditioned evaluation

- **Theory reference:** v0.6 §6.1–§6.5
- **Implementation location:** `eva/l3_deliberation/contracts.py`, `eva/l3_deliberation/reasoning/value_judgment.py`, `eva/l3_deliberation/peer_circuit/rpe.py`, scenario outcome observers
- **Completeness:** production
- **Notes:** the canonical `OutcomeVector` is framework-owned, while concrete outcome interpretation remains scenario-owned.

## Anchor system

### Anchors as pre-generative structural constraints

- **Theory reference:** v0.5 §11.1–§11.4
- **Implementation location:** `eva/anchor/domain_restriction.py`, scenario anchor bundles through `eva/scenario_bundle.py`
- **Completeness:** production
- **Notes:** the framework owns the structural action-domain surface; scenarios own admission policy and concrete reason vocabularies.

### Developmental distinction inside anchor talk

- **Theory reference:** v0.5 §11.5
- **Implementation location:** `eva/anchor/domain_restriction.py`, scenario anchor policies
- **Completeness:** partial
- **Notes:** the code clearly separates structural mechanism from field policy, but the fuller emergent-overlay story remains narrower than the theory’s long-term framing.

## Persistence targets and continuity semantics

### Explicit persistence hierarchy

- **Theory reference:** v0.6 §2.1–§2.4
- **Implementation location:** `eva/persistence_targets/__init__.py`, scenario persistence hierarchies, runners
- **Completeness:** production
- **Notes:** lower persistence levels are explicit runtime structure in the shipped scenarios.

### Higher persistence target levels

- **Theory reference:** v0.6 §2.2, v0.6 §7.2
- **Implementation location:** no runtime owner yet
- **Completeness:** deferred
- **Notes:** Levels 5–7 remain theory-side placeholders rather than runtime mechanisms.

## Capability sources and provenance

### Capability-source tracking and provenance discipline

- **Theory reference:** v0.6 §3.1–§3.4
- **Implementation location:** `eva/skills/__init__.py`, scenario prior-skill bundles
- **Completeness:** partial
- **Notes:** current runtime records explicitly carry provenance and already distinguish scenario / experience / inherited contributions, but the full broader taxonomy is not yet active as separate runtime-owned capability streams.

## Structural invariants versus operational content

### Framework/scenario separation as the current operational boundary

- **Theory reference:** v0.6 §4.1–§4.4
- **Implementation location:** `eva/scenario_bundle.py`, `docs/eva-framework-implementation.md`, `docs/scenarios-SPEC.md`
- **Completeness:** production
- **Notes:** the repo’s current public architecture is explicitly organized around framework-owned invariants and scenario-owned operational content.

## Observable stability

### Architecture-neutral observable stability surface

- **Theory reference:** v0.6 §5.1–§5.4
- **Implementation location:** `stability_metrics/`
- **Completeness:** production
- **Notes:** the trace-consuming stability profile module is landed as an architecture-neutral measurement surface.

### Comparative Stability Hypothesis evaluation program

- **Theory reference:** v0.6 §5.5–§5.8
- **Implementation location:** no experiment program landed yet
- **Completeness:** deferred
- **Notes:** the theory-side hypothesis is now measurable in principle, but the comparative baseline program is later work.

## Reserved / deferred commitments

### Exploration as growth driver

- **Theory reference:** v0.6 §1.4.1–§1.4.6
- **Implementation location:** no dedicated runtime mechanism yet
- **Completeness:** deferred
- **Notes:** Stage I deliberately left this outside scope even though the theory now specifies it.

### L4 self-model and L5 social-layer runtime

- **Theory reference:** v0.5 §9–§10, v0.6 §7.2
- **Implementation location:** no active runtime owner yet
- **Completeness:** deferred
- **Notes:** these remain later-layer commitments, not current runtime surfaces.

### Cross-scenario inherited-prior transmission

- **Theory reference:** v0.6 §3.6.3, v0.6 §3.6.6
- **Implementation location:** no active runtime owner yet
- **Completeness:** deferred
- **Notes:** the current implementation keeps inherited-prior transfer same-scenario only.

## Reading note

If you want the current state of a capability, read [capability-inventory.md](capability-inventory.md). If you want the exact field-local behavior of Linux runtime or Crafter, read the scenario `SPEC.md` files. This document is the bridge between theory language and implementation ownership.