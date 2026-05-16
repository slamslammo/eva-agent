# Stage I Progress — v0.6.1 implementation

## Status
- architect exit review passed
- Stage I closed

## Stage objective
Stage I operationalizes v0.6.1 §1–§3 within the architect-approved scope and prioritizes the fullest in-scope Crafter capability landing that improves sustainable runtime behavior.

Stage I is **not** optimizing for per-feature minimum viable landings. Within the bounds of:
- `THEORY/v0.6-extension.md`
- `THEORY/v0.6.1-extension.md`
- `maintainer/development/v0.6.1-stage-i-startup-instruction.md`

the working interpretation is:

> Prefer the most complete in-scope implementation that materially improves Crafter's sustainable end-to-end runtime loop, while preserving EVA structural constraints and Linux scenario stability.

## Explicitly deferred in Stage I
- exploration as growth driver (`v0.6.1` §4)
- L4/L5 mechanisms
- cross-scenario inherited priors
- broad docs reorganization

## Stage runtime success criteria
- [x] Crafter is trajectory-aware, not just status-aware
- [x] Crafter pressure is differentiated and rate-modulated
- [x] Crafter startup priors are canonicalized with provenance
- [x] Crafter memory layers participate in runtime, not storage only
- [x] Crafter can reuse same-scenario inherited priors across lives
- [x] Linux remains behaviorally stable
- [x] No append-only schema break
- [x] No mediator / anchor / persistence-structure violation
- [x] Deferred items remain explicitly deferred

---

## Crafter sustainable-runtime chain status

| Capability chain | Stage H baseline | Stage I target | Current status | Evidence |
|---|---|---|---|---|
| Trajectory-aware sensing | partial / placeholder-heavy | real required-tier rate sensing | completed locally | required-tier Crafter dimensions now emit real `rate_context` from previous snapshots; targeted + full regression green |
| Pressure differentiation | weak | differentiated + urgency-modulated | completed for I-1 scope | scenario-qualified `pressure_id`; urgency modulation; bounded anticipatory pressure for fast-degrading required-tier dimensions |
| Prior substrate | distributed implicit | canonicalized provenance-complete | completed locally | canonical Crafter startup bundle and runtime prior registry landed; targeted + full regression green (`295 passed, 2 skipped`) |
| Episodic reuse | partial | relevance retrieval confirmed | completed locally | explicit `EpisodicMemoryRegistry` now maps the current append-only episodic traces into working-memory retrieval; targeted memory/reasoning and integration regressions green (`64 passed, 1 warning`; `23 passed`) |
| Semantic participation | missing / weak | live runtime participation | completed locally | `semantic_memory.jsonl` plus semantic query/registry helpers landed; matching entries now surface in working memory and add a tiny bounded candidate prior modifier |
| Procedural reuse | habit bias only | conditional fast surfacing if in-scope | completed locally | Stage I chose path (b): keep `habit_bias.jsonl` as the procedural backing track, formalize it as `ProceduralMemoryRegistry`, and keep candidate shaping mediator-gated |
| Inter-life inherited reuse | missing | same-scenario bundle load/use | completed locally | top-level `inheritance_distillation/` landed; scenario-owned bundle loading and bounded working-memory / habit-path / value-bias participation validated |
| Structural safety | preserved | preserved | preserved | no mediator / anchor / persistence-structure owner drift in I-1/I-3 landings; I-4 remains bounded to advisory inherited priors |
| Linux stability | stable | stable | validated through Stage I close | targeted I-3 regressions passed (`23 passed`); I-4 inherited-prior and Linux-alignment regressions passed (`25 passed` integration / `81 passed` targeted overlap); latest full-suite validation passed (`323 passed`) |

---

## Slice I-0 — Crafter signal semantics cleanup

### Status
- completed; approved at Stage I exit

### Theory mapping
- v0.6:
  - multi-dimensional outcome interpretation
  - operational-content discipline
- v0.6.1:
  - judgment-side distinction between status, unknown rate, and urgency relevance
- Startup instruction:
  - Section 2 / I-0 followups
  - per-slice workflow
  - hard constraints and whitelist

### Slice objective
Stabilize Crafter's sensing / pressure / outcome semantics before all later Stage I work.

### Crafter runtime impact
- Before:
  - pressure typing under-differentiated
  - confidence placeholder-heavy
  - local view mapping too collapsed
- After:
  - differentiated pressure semantics
  - confidence derived from uncertainty
  - local-view signals routed across appropriate drives
- Why this matters for sustainable runtime:
  - later rate sensing, memory, and inherited-prior work must not be built on noisy or underspecified base signals

### Linux preservation check
- Result:
  - passed
- Evidence:
  - targeted Linux patrol regression green (`tests/l1_sensing/test_patrol.py`, `tests/integration/test_patrol_turn_flow.py`)
  - full suite green (`292 passed, 2 skipped`)
- Allowed differences:
  - additive / format-justified only

### Tests
- New:
  - scenario-qualified pressure-id assertions
  - confidence-from-uncertainty assertions
  - local-view multi-signal decomposition assertions
- Existing:
  - targeted Crafter + pressure + persistence suites green
- Full regression:
  - passed (`292 passed, 2 skipped`)

### Trace / runtime evidence
- Representative Crafter run:
  - targeted runtime integration green (`tests/integration/test_crafter_runtime.py`)
- Representative Linux run:
  - targeted patrol-turn regression green (`tests/integration/test_patrol_turn_flow.py`)
- Key observations:
  - active pressures now use `pressure-{scenario}-{pressure_type}-{reason}`
  - Crafter local-view sensing now projects threat/resource/utility into separate scenario dimensions
  - Crafter confidence now varies with outcome uncertainty rather than fixed placeholders

### Docs synced
- `maintainer/development/current-intake.md`
- `maintainer/development/stage-i-progress.md`
- `scenarios/crafter/SPEC.md`

### Deferred within slice
- no rate-tier rollout beyond cleanup needs
- no memory-layer implementation
- no inherited-prior implementation
- no exploration work

### Risks / followups
- pressure_id consumer breakage
- over-amplified drive activation from local-view decomposition
- low-information confidence remapping

### Review result
- architect review completed at Stage I exit
- outcome: approved at Stage I close
- package: `maintainer/development/stage-i-i0-review-package.md`

---

## Slice I-1 — Real trajectory-aware rate sensing for Crafter

### Status
- completed locally; pending I-0 architect gate bookkeeping

### Slice objective
Implement v0.6.1 rate sensing so Crafter becomes trajectory-aware and not merely status-reactive.

### Crafter runtime impact
- Before:
  - mostly status-reactive response
- After:
  - required-tier dimensions emit real rate context from previous snapshots
  - pressure urgency is modulated by rate direction / magnitude
  - bounded anticipatory pressure can open for healthy but fast-degrading required-tier dimensions
- Why this matters for sustainable runtime:
  - enables earlier intervention before survival-critical degradation fully materializes

### Landed scope
- framework rate helpers now expose canonical v0.6.1 `rate_context` shape with normalized direction, magnitude, and acceleration
- `DimensionSpec` now carries validated rate-tier metadata, aggregation method, and anticipatory threshold seams
- Linux dimension declarations are explicitly tier-classified and preserve prior semantics
- Crafter required-tier avatar dimensions now compute real rate context from previous snapshots with episode-boundary protection
- pressure projection now supports urgency modulation and bounded anticipatory pressure without widening release authority

### Validation
- Targeted regression:
  - `tests/scenarios/crafter/test_sensors.py`
  - `tests/l1_sensing/test_rate_sensors.py`
  - `tests/l1_sensing/test_state_sensors.py`
  - `tests/l1_sensing/test_sensing.py`
  - `tests/l1_sensing/test_judgment.py`
  - `tests/l2_drive/test_pressure.py`
  - `tests/l2_drive/test_drive.py`
  - result: passed
- Full regression:
  - result: passed (`294 passed, 2 skipped`)

### Review result
- no architect gate at close
- outcome: local implementation complete; awaiting I-0 gate bookkeeping before promotion

---

## Slice I-2 — Crafter prior substrate canonicalization

### Status
- completed locally

### Slice objective
Convert distributed implicit Crafter priors into a canonical provenance-complete scenario prior substrate.

### Crafter runtime impact
- Before:
  - startup knowledge distributed across constants and scattered logic
- After:
  - scenario priors are explicit, canonical, and inspectable through one scenario-owned bundle
  - runtime prior registries are derived from the same canonical definitions without changing candidate behavior
- Why this matters for sustainable runtime:
  - memory and inheritance layers need a clean startup-knowledge boundary

### Landed scope
- Crafter startup priors are now centralized in `scenarios/crafter/prior_skills/bundle.py`
- each Crafter startup prior now carries explicit `SkillProvenance` with scenario scope, source paths, and applicability context
- Crafter runtime prior records are now derived from the same canonical bundle used for startup inspection
- Linux prior-skill surface now also exposes explicit startup and runtime prior registries for parity
- framework scenario bundles now expose startup-prior inspection and runtime prior-registry builders through the prior-skill seam

### Validation
- Targeted regression:
  - `tests/scenarios/crafter/test_prior_skills.py`
  - `tests/scenarios/crafter/test_skill_provenance.py`
  - `tests/scenarios/crafter/test_prior_guided_candidates.py`
  - `tests/l3_deliberation/memory/test_skill_library.py`
  - `tests/integration/test_linux_alignment.py`
  - result: passed
- Full regression:
  - result: passed (`295 passed, 2 skipped`)

### Review result
- no architect gate at close
- outcome: local implementation complete

---

## Slice I-3 — Crafter memory layers with real runtime participation

### Status
- completed locally; ready for architect review

### Slice objective
Land four-layer memory in a way that actually participates in Crafter runtime rather than only existing as storage/interface.

### Crafter runtime impact
- Before:
  - weak or partial experience reuse
- After:
  - life-internal experience now influences later decisions through explicit working / episodic / semantic / procedural memory surfaces
  - semantic memory contributes bounded candidate priors through the existing deliberation path
  - procedural memory remains the current habit-path shortcut and stays mediator-gated
- Why this matters for sustainable runtime:
  - sustainable operation requires accumulation and reuse, not one-step reaction only

### Landed scope
- framework memory-layer interfaces now include explicit `WorkingMemory`, `EpisodicMemoryRegistry`, `SemanticMemoryRegistry`, and `ProceduralMemoryRegistry`
- `EvaPaths` and `StateStore` now expose `semantic_memory.jsonl` as a first-class append-only track
- semantic owner helpers now support append/read plus exact query-by-topic and query-by-scope access patterns
- working-memory assembly now retrieves bounded semantic patterns alongside episodic traces, bias summaries, and procedural summaries
- candidate assessment now applies a tiny auditable semantic prior modifier when a retrieved semantic pattern prefers the candidate profile
- procedural memory is explicitly represented through the existing habit path backed by `habit_bias.jsonl`; scenario-qualified provenance now reflects the active runtime scenario instead of Linux-only hardcoding
- semantic-to-L2 drive-weight modification remains deferred in I-3 to preserve the current boundary that higher layers do not rewrite drive-state semantics

### Validation
- Targeted regression:
  - `tests/l3_deliberation/memory/test_episodic.py`
  - `tests/l3_deliberation/memory/test_semantic.py`
  - `tests/l3_deliberation/memory/test_skill_library.py`
  - `tests/l3_deliberation/memory/test_working_memory_adapter.py`
  - `tests/l3_deliberation/reasoning/test_working_memory.py`
  - `tests/l3_deliberation/reasoning/test_value.py`
  - result: passed (`64 passed, 1 warning`)
- Integration regression:
  - `tests/integration/test_lifecycle_patrol_learning.py`
  - `tests/integration/test_main_runtime.py`
  - `tests/integration/test_crafter_runtime.py`
  - `tests/integration/test_linux_alignment.py`
  - result: passed (`23 passed`)
- Full regression:
  - result: passed (`303 passed`)

### Review result
- architect review completed at Stage I exit
- outcome: approved at Stage I close
- package: `maintainer/development/stage-i-i3-review-package.md`

---

## Slice I-4 — Real same-scenario inherited-prior reuse for Crafter

### Status
- completed locally; ready for architect review

### Slice objective
Implement a same-scenario inherited-prior distillation and load path that can influence later Crafter runs.

### Crafter runtime impact
- Before:
  - no inter-life regularity reuse
- After:
  - distilled regularities from prior Crafter lives can inform later runs through the existing deliberation path
  - inherited priors remain bounded candidate-shaping / candidate-bias inputs rather than a second release lane
- Why this matters for sustainable runtime:
  - enables first real cross-life capability accumulation inside L3 without breaking Stage I authority boundaries

### Landed scope
- top-level `inheritance_distillation/` now reads append-only trace bundles, distills same-scenario regularities, validates structural invariants, and writes `DistilledPriorBundle.json`
- `InheritedPriorRecord` / `InheritedPriorRegistry` now form the real framework read surface for loaded inherited priors
- Crafter and Linux both expose scenario-owned inherited-prior loaders with scenario qualification and allowed action/profile filtering
- runtime config and runner activation now support optional inherited-prior bundle paths
- working-memory assembly surfaces exact `situation_key` matches through `inherited_priors`
- inherited priors participate only through the existing habit-path shaping seam and a tiny auditable value-judgment bias

### Validation
- Targeted inherited-prior/runtime regression:
  - `tests/l3_deliberation/memory/test_skill_library.py`
  - `tests/l3_deliberation/reasoning/test_working_memory.py`
  - `tests/l3_deliberation/reasoning/test_value.py`
  - `tests/l3_deliberation/peer_circuit/test_habit_track.py`
  - `tests/scenarios/crafter/test_prior_skills.py`
  - `tests/scenarios/crafter/test_prior_guided_candidates.py`
  - `tests/integration/test_crafter_runtime.py`
  - `tests/integration/test_linux_alignment.py`
  - result: passed (`81 passed`)
- Distillation-tool regression:
  - `tests/inheritance_distillation/test_pipeline.py`
  - `tests/inheritance_distillation/test_validator.py`
  - `tests/inheritance_distillation/test_import_boundary.py`
  - `tests/inheritance_distillation/test_cli_smoke.py`
  - result: passed (`7 passed`)
- Integration regression:
  - `tests/integration/test_main_runtime.py`
  - `tests/integration/test_lifecycle_patrol_learning.py`
  - `tests/integration/test_linux_alignment.py`
  - `tests/integration/test_crafter_runtime.py`
  - result: passed (`25 passed`)
- Full regression:
  - result: passed (`323 passed`)

### Review result
- architect review completed at Stage I exit
- outcome: approved at Stage I close
- package: `maintainer/development/stage-i-i4-review-package.md`
- review action handled as part of Stage I close

---

## Slice I-5 — Crafter runtime readiness audit and Stage I exit

### Status
- completed locally
- architect exit review passed

### Slice objective
Verify that Stage I forms a more complete Crafter runtime chain rather than a set of isolated feature landings.

### Crafter runtime impact
- Before:
  - Stage H scenario integration baseline
- After:
  - Stage I runtime-readiness judgment with chain-level evidence
  - memory-decision integration and inherited-prior boundaries are explicitly audited
- Why this matters for sustainable runtime:
  - confirms that sensing → pressure → priors → memory → inherited reuse forms a coherent loop and documents the remaining bounded deferrals

### Landed scope
- `maintainer/architecture/memory-decision-integration-audit.md` now closes the v0.6.1 §2.5 integration-table audit opened in I-3
- I-4 review-package wording is aligned with the actual workflow so inherited-prior review is handled at Stage I exit rather than as a separate pre-I-5 gate
- Stage I trace compatibility is explicitly checked: `semantic_memory.jsonl` remains additive, learning-outcome `content["scenario"]` remains additive, and `stability_metrics` compatibility remains preserved
- the Stage I exit package is now prepared in `maintainer/development/stage-i-i5-review-package.md`
- this progress record now carries the final Stage I exit judgment and deferred followups

### Validation
- Audit evidence:
  - `maintainer/architecture/memory-decision-integration-audit.md`
  - `maintainer/development/stage-i-i3-review-package.md`
  - `maintainer/development/stage-i-i4-review-package.md`
  - result: completed
- Full regression:
  - result: passed (`323 passed`)
- Coverage judgment:
  - I-5 added no new runtime mechanism; existing targeted slice suites plus the latest full regression were sufficient

### Review result
- architect exit review completed
- outcome: approved; Stage I closed
- package: `maintainer/development/stage-i-i5-review-package.md`

---

## Stage I exit summary

### v0.6.1 commitments operationalized
- [x] §1 rate sensing
- [x] §2 memory layering
- [x] §3 inherited priors L3 path

### Deferred with rationale
- [x] §4 exploration implementation
- [x] semantic memory → L2 drive-weight modification
- [x] dedicated procedural-memory storage beyond `habit_bias.jsonl`
- [x] cross-scenario inherited priors
- [x] broader docs reorganization

### Framework modifications made
- rate-aware sensing and pressure seams for required-tier Crafter dimensions
- explicit startup-prior / runtime-prior provenance surfaces
- explicit working / episodic / semantic / procedural memory interfaces plus `semantic_memory.jsonl`
- same-scenario inherited-prior registry, runtime loading seam, and top-level `inheritance_distillation/` tool

### Linux stability result
- preserved
- no-bundle baseline remains valid
- Linux-only bundle admissibility remains enforced
- latest full regression passed (`323 passed`)

### Crafter runtime-readiness result
- Stage I now provides a coherent bounded chain from sensing and rate-aware pressure through priors, live memory participation, and same-scenario inherited reuse
- inherited priors remain advisory and mediator-/anchor-bounded
- runtime readiness judged sufficient for Stage I exit

### Boundary note on Stage I framework consumption changes
- a small set of Stage I changes landed in `eva/l3_deliberation/` and `eva/kernel/` to consume new memory-layer and inherited-prior seams in the live runtime path
- these were treated at exit review as minor adaptations rather than ownership-widening changes because they did not alter mediator authority, anchor ownership, lifecycle authority, or append-only discipline
- future work that falls on this same whitelist boundary should be escalated explicitly at slice start even if it is expected to qualify as a minor adaptation

### Exit verdict
- architect exit review passed
- Stage I closed
- recommendation: carry forward only the documented deferred items and follow-ups in `maintainer/development/stage-i-followups.md`
