# Blueprint to Tracking Map

This document maps the target-state commitments in `architecture-implementation-blueprint-v0.6.md` to the current implementation-state entries in `implementation-tracking.md`.

It answers one question: **for each blueprint commitment, where is its tracking entry, and what is its current implementation status?**

---

| Blueprint commitment | Tracking entry | Current status | Gap / note |
|---|---|---|---|
| Continuous existence read as active persistence | No single dedicated row | partial | Expressed compositionally through rate-aware sensing, persistence hierarchy, multi-dimensional outcome, and bounded exploration, but not yet tracked as one named row. |
| Heartbeat-first lifecycle | 1.1 `Bounded heartbeat / tick / turn runtime loop` | landed | — |
| Instance legitimacy | 1.1 `Instance legitimacy (lock / generation / lease)` | landed | — |
| Atomic current state vs append-only history | 1.1 `Separated atomic current-state persistence and append-only audit substrate` | landed | — |
| Framework / scenario activation boundary | 1.1 `Explicit scenario activation through RuntimeScenarioBundle` | landed | — |
| Runner-owned startup assembly | 1.1 `Runner-owned startup assembly for shipped scenarios` | landed | — |
| Fast/slow closed-loop runtime composition | 1.1 `Integrated fast/slow closed-loop runtime composition` | landed | — |
| Persistence-target registration surface | 1.1 `Explicit persistence hierarchy contract` | landed | — |
| Persistence Levels 5–7 | 1.1 `Persistence target Levels 5–7` | deferred | Reserved by theory; mechanisms not implemented. |
| Observable stability measurement surface | 1.1 `Architecture-neutral stability profile calculation from trace files` | landed | — |
| Comparative stability hypothesis evaluation program | 1.1 `Comparative Stability Hypothesis evaluation program` | deferred | Metrics exist; comparative experiment program not landed. |
| Sensor registry and normalized sensing contract | 1.2 `Normalized sensor registry and sensing contract` | landed | — |
| Scenario-declared dimension specs with rate metadata | 1.2 `Scenario-declared dimension specifications with rate-sensing tier metadata` | landed | — |
| State + rate sensing with explicit unknown fallback | 1.2 `Rate-aware sensing with explicit unknown fallback` | landed | — |
| Signal publication with threat/status classification | 1.2 `Signal publication with explicit status / threat classification` | landed | Background routing is implied rather than separately named. |
| Drive preset and drive-update seam | 1.3 `Drive preset and drive-update seam` | landed | Update seam is explicit; decay/recovery remain part of the same seam rather than separate tracking rows. |
| Read-only drive broadcast with L2-owned authority | 1.3 `Read-only drive broadcast with L2-owned state authority` | landed | — |
| Pressure projection with urgency modulation | 1.3 `Pressure projection with urgency modulation and bounded anticipatory pressure` | landed | — |
| Protective reflex fast path | 1.3 `Protective reflex fast path parallel to slower deliberation` | landed | — |
| Deliberation input contract | 1.4 `Canonical deliberation input contract` | landed | — |
| Four-layer memory surface | 1.4 `Four-layer memory surface (working / episodic / semantic / procedural)` | partial | Semantic store-side indexing landed in Round 1.C-1; dedicated procedural store remains open. |
| Mediator as independent peer circuit | 1.4 `Mediator as independent peer circuit (default inhibition + selective release)` | landed | — |
| Runtime-only release token boundary | 1.4 `Runtime-only release token boundary` | landed | — |
| Drive-weighted candidate assessment | 1.4 `Drive-weighted candidate assessment with bounded learned overlays` | landed | — |
| L3 reasoning core forms candidates (proposal path) | 1.4 `L3 reasoning proposal path (anchor-bounded proposer shapes the considered candidate set)` | landed (mechanism) | Round 1.E (blueprint §7.4): an anchor-bounded proposer shapes the considered candidate set; model influence rises from a ≤0.12 post-hoc bias to considered-set shaping, still bounded by anchor admission + peer-circuit selection + mediator release. LLM-reasoning long-run validation deferred (§8). |
| Canonical multi-dimensional outcome support | 1.4 `Append-only learning outcome records with canonical OutcomeVector support` | landed | — |
| RPE as internal update signal | 1.4 `RPE-like learning as internal update signal` | landed | Tracking uses “RPE-like” wording; blueprint is stricter about vector semantics. |
| Habit shaping and skill crystallization | 1.4 `Habit shaping and skill crystallization through habit track` | landed | — |
| Advisory-only working-memory assembly | 1.4 `Advisory-only working-memory assembly` | landed | — |
| Model-backed working-memory advisory path | 1.4 `Model-backed working-memory advisory path with bounded fallback` | landed | — |
| Episodic retrieval over append-only artifacts | 1.4 `Episodic retrieval over append-only artifacts` | landed | — |
| Semantic memory as first-class storage and bounded L3 participant | 1.4 `Semantic memory — first-class storage + exact query + bounded L3 participation` | production | Round 1.C-1 (W4) landed the store-side index: process-local in-memory cache eliminates disk re-reads; inverted buckets enable bounded candidate retrieval via `query_semantic_memory_for_situation`. |
| Semantic memory → L2 safe path | 1.4 `Semantic memory → L2 drive-weight semantics` | production | Safe-path landed in Round 1.B-3 (W5): bounded amplification overlay on `drive_impact_schema` (cap 0.15, confidence threshold 0.7); drive read-only boundary preserved. |
| Procedural memory via habit-backed substrate | 1.4 `Procedural memory via existing habit-track substrate` | partial | Explicit surface landed, but not a dedicated procedural store. |
| Working-memory interface review threshold | 1.4 `Working-memory interface signature` | production | Round 1.C-2 (W6) introduced `WorkingMemoryAssemblyLimits` dataclass bundling the four output-size parameters; legacy kwargs preserved for backward compatibility. |
| Anchor pre-generative restriction | 1.5 `Framework-owned action domain and pre-generative restriction surface` | landed | — |
| Scenario-owned anchor admission policy | 1.5 `Scenario-owned anchor admission policy through active bundle seam` | landed | — |
| Capability restriction and parameter-domain restriction | 1.5 `Capability restriction and parameter-domain restriction inside the active action domain` | landed | — |
| Mediated candidate filtering / selection / execution | 1.5 `Mediated candidate filtering, selection, and execution path` | landed | — |
| Anchor three-way distinction | 1.5 `Anchor three-layer distinction (mechanism / constitutional policies / emergent overlays)` | partial | Emergent overlay side remains narrower than theory framing. |
| Same-scenario inherited-prior distillation pipeline | 1.6 `Same-scenario inherited-prior distillation pipeline` | landed | — |
| Same-scenario inherited-prior loading and bounded participation | 1.6 `Same-scenario inherited-prior loading and bounded deliberation participation` | landed | — |
| Capability provenance-carrying skill registries | 1.6 `Capability provenance-carrying skill registries` | partial | Provenance is explicit, but the broader theory-side source taxonomy is not yet active as separate runtime sources. |
| Cross-scenario inherited-prior transmission | 1.6 `Cross-scenario inherited-prior transmission` | deferred | Explicitly deferred. |
| Exploration as growth driver | 1.7 `Exploration as growth driver` | partial | Framework's curiosity-style update path is the mechanism; Crafter scenario landed via Round 1.B-2 (`scenarios/crafter/drive_preset.py` registers ``exploration`` drive; ``COMPATIBILITY_RELEASE_IMPACT`` wires it into candidate scoring). Linux already used the same mechanism via its `curiosity` drive. Cross-scenario hardening and long-run parameter tuning remain. |
| L4 self-model runtime | 1.7 `L4 self-model runtime` | deferred | Reserved only. |
| L5 social-layer runtime | 1.7 `L5 social-layer runtime` | deferred | Reserved only. |
| Generic scenario loader / validator | 1.7 `Generic scenario loader / validator` | deferred | Explicit runner assembly remains the current shape. |
| Multi-scenario runtime switching | 1.7 `Multi-scenario runtime switching inside one process` | deferred | Explicitly out of current scope. |
| Six-surface scenario contract | 2 `RuntimeScenarioBundle`, `SensorPolicyBundle`, `ActionPolicyBundle`, `AnchorPolicyBundle`, `OutcomeObserverBundle`, `PriorSkillBundle` | partial | Five surfaces are production; `PriorSkillBundle` remains partial because provenance-boundary deepening is future work. |
| Scenario-owned persistence registration | 2 `Scenario-owned persistence hierarchy registration` | landed | — |
| Canonical multi-dimensional outcome at contract level | 2 `Canonical multi-dimensional OutcomeVector` | landed | — |
| Framework-owned skill registries with scenario-owned provenance inputs | 2 `Framework-owned skill registries with scenario-owned provenance inputs` | landed | — |
