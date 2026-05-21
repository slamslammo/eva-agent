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
| Scenario-declared existence semantics (eight-field dataclass, including the `clock_source` field itself) (v0.6 rev2) | `eva/scenario_bundle.py::ExistenceSemantics`, declarations in `scenarios/<name>/__init__.py` | production | Refers only to the dataclass fields landing and the scenarios declaring them; kernel consumption of `clock_source` is tracked separately below | — |
| Individual identity resolution: cross-run continuity vs fresh mint (rev2) | `eva/kernel/main.py::_resolve_individual_id`, `eva/kernel/main.py::RunSummary`, `exit_reason="individual_terminated"` exit path | production | — | — |
| Kernel consumption of declared `clock_source` to select cadence rhythm source (blueprint §2.7 / §12.7 item 8) | — | deferred | The field has landed and scenarios declare it, but the kernel cadence path is still wall-clock and does not switch to step-driven based on `clock_source`; this consumption is a target item | Later phase |
| Integrated fast/slow closed-loop runtime composition | `eva/kernel/main.py`, `eva/l1_sensing/signal_bus.py`, `eva/l2_drive/reflex.py`, `eva/l3_deliberation/contracts.py` | production | — | — |
| Explicit persistence hierarchy contract | `eva/persistence_targets/__init__.py` | production | — | — |
| Scenario-owned activation of lower persistence levels | `scenarios/linux_runtime/persistence/`, `scenarios/crafter/persistence/` | production | — | — |
| Persistence target Levels 5–7 | — | deferred | Theoretical placeholder; mechanisms reserved for future versions | Later phase |
| Architecture-neutral stability profile calculation from trace files | `stability_metrics/` | production | — | — |
| Long-run validation infrastructure (graceful interrupt + periodic hook + validation hook factory) | `eva/kernel/main.py`, `runners/longrun_validation.py` | production | Round 1.D-1/2/3 landed: `RunSummary.exit_reason`, `run_runtime(periodic_hook=...)`, `LongrunTripwire` dataclass + `build_longrun_validation_hook` factory. Closes the blueprint §13.2 long-run invariant validation obligation at the infrastructure level; actual 6h+ runs are user-driven follow-up. | Round 1.D-5/6 (user-driven long runs + report) |
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
| L3 reasoning content beyond candidate-value assembly (model-driven planning / novel-problem reasoning / genuine multi-step inference) | current paths under `eva/l3_deliberation/reasoning/` | skeleton | Current L3 deliberation output comes from drive-weighted candidate assessment + advisory-only working memory (when model-backed, LLM is a bounded advisor capped at ≤0.12 value uplift) + habit/prior/memory inputs; there is no model-driven planning or novel-problem solver, and the reasoning core described in blueprint §7.4 remains a target state | Later phase (once the structural mainline and validation program are mature) |
| Four-layer memory surface (working / episodic / semantic / procedural) | `eva/l3_deliberation/reasoning/working_memory.py`, `eva/l3_deliberation/memory/`, `eva/skills/__init__.py` | partial | Semantic store-side indexing landed in Round 1.C-1 (Stage I follow-up #1 resolved); procedural memory remains habit-backed rather than a dedicated store | Procedural store: future evaluation |
| Mediator as independent peer circuit (default inhibition + selective release) | `eva/l3_deliberation/peer_circuit/mediator.py` | production | — | — |
| Runtime-only release token boundary | `eva/l3_deliberation/contracts.py` | production | — | — |
| Drive-weighted candidate assessment with bounded learned overlays | `eva/l3_deliberation/reasoning/value_judgment.py`, `eva/l3_deliberation/peer_circuit/rpe.py` | production | — | — |
| L3 reasoning core — dlPFC candidate producer (theory v0.5 §8.6.3 / blueprint §7.4) | `eva/l3_deliberation/reasoning/candidate_producer.py`, `eva/l3_deliberation/reasoning/llm_candidate_producer.py`, `eva/l3_deliberation/runtime.py` | production | Round 1.G phase 1: the round-1e reorder-proposer **and** the ≤0.12 advisory are **superseded (drift)** — round-1f proved the proposer causally inert (mediator selection is order-independent max-by-score) and the ≤0.12 advisory harmful (biased selection toward passivity) with no doctrinal basis. Replaced by a `CandidateProducer` seam: `HeuristicCandidateProducer` (deterministic, = `build_candidates`, behavior-preserving default) forms candidates within the anchor-bounded domain; selection (peer-circuit) + release (mediator) authority unchanged. **Phase 2 (a) landed (G2-approved):** the live `LLMCandidateProducer` makes one bounded schema-bound call to annotate each candidate with an `action_hint` — the LLM's causal lever, i.e. the concrete action *within* the drive-locked posture (it never adds/removes candidates or changes the profile, so drive still locks the posture). The selected candidate's hint is threaded into `release_context` by `run_deliberation` and consumed by the Crafter bridge (priority over `PROFILE_DEFAULT_ACTION`/prior); OFC stays frozen (no per-action re-scoring). Causal path proven on live DeepSeek (LLM hint=X → executed=X); any transport/parse failure or model-off degrades to the heuristic, byte-equivalent. | Behavioral quality (LLM choosing infeasible actions when given no inventory/craftability context) is a follow-on iteration, not a wiring gap. |
| Scenario-neutral reasoning, routing, and pressure projection | `eva/l3_deliberation/reasoning/value_judgment.py`, `eva/l3_deliberation/reasoning/conflict_detection.py`, `eva/l3_deliberation/memory/working_memory_adapter.py`, `eva/l3_deliberation/memory/working_memory_model_client.py`, `eva/kernel/state.py` | production | — | Round 1.B-1 de-Linuxified hardcoded ``top_drive == "integrity"`` checks in reasoning + memory routing; drive-weighted scoring and projection thresholds now consult drive levels, not drive names. |
| Append-only learning outcome records with canonical `OutcomeVector` support | `eva/l3_deliberation/contracts.py`, `eva/l3_deliberation/peer_circuit/rpe.py`, scenario outcome observers | production | — | — |
| RPE-like learning as internal update signal | `eva/l3_deliberation/peer_circuit/rpe.py` | production | — | — |
| Habit shaping and skill crystallization through habit track | `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/l3_deliberation/memory/skill_library.py` | production | — | — |
| Advisory-only working-memory assembly | `eva/l3_deliberation/reasoning/working_memory.py` | production | — | — |
| Model-backed working-memory advisory path with bounded fallback | `eva/l3_deliberation/memory/working_memory_model_client.py`, `eva/l3_deliberation/memory/working_memory_adapter.py`, `eva/kernel/main.py` | production | Round 1.7 generalized the live client to a single vendor-neutral OpenAI Chat Completions implementation (`OpenAICompatibleWorkingMemoryModelClient`) configured by `EVA_LLM_*` env vars; legacy Anthropic + DeepSeek vendor classes deleted. Includes transparent retry (5xx / transport_unavailable, exponential backoff) and fallback to local heuristic on exhaustion or 4xx errors. | — |
| Episodic retrieval over append-only artifacts | `eva/l3_deliberation/memory/episodic.py`, `eva/l3_deliberation/memory/retrieval.py` | production | — | — |
| Semantic memory — first-class storage + exact query + bounded L3 participation | `eva/l3_deliberation/memory/semantic.py`, `eva/skills/__init__.py` | production | Store-side indexing landed in Round 1.C-1 (W4): process-local in-memory cache keyed on `StateStore.paths.runtime_dir`, eliminating disk re-reads; inverted buckets over `(scenario, situation_key) / (scenario, top_drive) / (scenario, pressure_reason) / topic / scenario`; new `query_semantic_memory_for_situation` helper returns a candidate superset. The semantic → L2 drive-weight path landed in Round 1.B-3 (W5). | Long-run validation in Round 1.D |
| Semantic memory → L2 drive-weight semantics | `eva/l3_deliberation/reasoning/value_judgment.py` | production | Safe-path implementation: bounded amplification overlay on positive entries of `drive_impact_schema` (cap `MAX_SEMANTIC_OVERLAY_BLEND=0.15`, threshold `MIN_SEMANTIC_OVERLAY_CONFIDENCE=0.7`). Drive read-only broadcast preserved — overlay never modifies drive_levels and never weakens negative impacts. Round 1.B-3 (W5). | Long-run validation in Round 1.D |
| Procedural memory via existing habit-track substrate | `eva/l3_deliberation/peer_circuit/habit_track.py`, `eva/skills/__init__.py` | partial | Surface is explicit but backing track remains `habit_bias.jsonl` rather than a dedicated procedural store | Future evaluation |
| Working-memory interface signature | `eva/l3_deliberation/reasoning/working_memory.py` | production | Round 1.C-2 (W6) addressed Stage I follow-up #3: introduced `WorkingMemoryAssemblyLimits` dataclass bundling the four `max_*` output-size parameters; both assembly entry points accept the new `limits` parameter with legacy kwargs preserved for backward compatibility. | — |

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
| Exploration as growth driver | v0.6 §1.4 / v0.6.1 §4 | partial | Framework mechanism (curiosity-style update path) has existed since Phase A; Crafter scenario landed via Round 1.B-2. Linux retains its existing ``curiosity`` drive. Cross-scenario hardening + parameter tuning under long-run validation remain. | Round 1.D long-run validation |
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
| `ExistenceSemantics` declaration (eight items, required bundle field, v0.6 rev2) | `eva/scenario_bundle.py::ExistenceSemantics`, `scenarios/crafter/__init__.py`, `scenarios/linux_runtime/__init__.py` | production | — |
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
| Crafter-specific drives, sensors, action bridge with context-aware resolution, anchors, outcome observers, persistence hierarchy, prior-skill policy | production (within bounded scope) | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) — Round 1.A widened the compatibility bridge to resolve concrete actions per profile context within the existing 3-profile vocabulary |
| Trajectory-aware sensing and bounded anticipatory pressure for required-tier dimensions | production | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) |
| Crafter existence-semantics declaration + one-life individual-terminal path (v0.6 rev2, supersedes the earlier Stage-H bounded-episode-reset reading) | production | [`scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md) §H-3 / §H-5 — `reset_semantics="new_individual"`, `clock_source="step"`; env `done=True` → `terminated=True` → `exit_reason="individual_terminated"`; no `wrapper.reset()` to extend life |

---

## 4. Open follow-ups

The following items are confirmed as carry-forward follow-ups, not accidental gaps:

| Item | Source | Status |
|---|---|---|
| Semantic memory store-side windowing / indexing | Stage I follow-up #1 | resolved (Round 1.C-1 / W4) |
| Semantic memory → L2 drive-weight semantics safe path evaluation | Stage I follow-up #2 | resolved (Round 1.B-3 / W5) |
| Working-memory interface signature review threshold | Stage I follow-up #3 | addressed (Round 1.C-2 / W6) |
| LLM client generalization to OpenAI Chat Completions (vendor-neutral) | Phase 1.7 | resolved (Round 1.7 a–e) |
| EVA black-box viewer (`observation_tools/`, runtime trace introspection) | Phase 2 V0 | delivered (independent auxiliary tool; reads JSONL trace, no impact on framework / scenarios) |

---

## 5. How this document relates to other docs

- **`architecture-overview.md`** — this document's entries are the concrete commitments that the architecture overview maps visually
- **`eva-framework-implementation.md`** — the authoritative source for what the framework currently owns; this tracking document maps those capabilities back to their theory commitments
- **`scenarios-SPEC.md`** — the contract specification for how scenarios integrate with the framework; per-scenario tracking here links to the concrete per-scenario specs
- **Theory → implementation landing** was previously in `theory-implementation-landing.md`; that content is now incorporated here and in `architecture-overview.md`

This document is updated at the close of each stage. Between stages, it reflects the last confirmed state.