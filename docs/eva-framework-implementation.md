# EVA Framework Implementation

**Status**: Skeleton draft for v0.6 refactor
**Scope**: Framework (architecture-level) implementation specification
**Companion documents**: `scenarios/SPEC.md` (scenario contract), `scenarios/{name}/SPEC.md` (per-scenario specifications)
**Theoretical reference**: EVA v0.5 + v0.6 extension

---

## Purpose of this document

This document specifies the **framework portion** of EVA's engineering implementation. It describes the structural mechanisms that constitute EVA as an architecture: the lifecycle kernel, the L1 sensor framework, the L2 drive broadcast mechanism, the L3 anchor / candidate / mediator / tool-edge structures, the four append-only data tracks, and the interfaces through which scenarios are instantiated.

This document does **not** describe any specific scenario. Every commitment in this document holds across all scenarios that EVA's framework supports; commitments that vary by scenario belong in `scenarios/SPEC.md` (the cross-scenario contract) or in individual scenario specification documents.

The boundary is enforced both as documentation discipline and as code organization discipline. Code that lives in the `eva/` package implements what this document specifies. Code that implements scenario-specific content lives in `scenarios/{name}/` and is documented in the corresponding scenario specification.

This document supersedes `eva-agent-full-implementation.md` (v0.5 era), which mixed framework concerns with Linux scenario specifics. The historical document is preserved at `docs/archive/eva-agent-full-implementation-v0.5.md` as a reference for v0.5-era implementation context.

---

## Document structure

The document is organized into the following parts. This skeleton specifies what each part covers and what it must not cover; specific content is filled in during the refactor and subsequent work.

### Part I: Framework foundations

**Chapter 1: Scope and non-scope**
- 1.1 What this document specifies
- 1.2 What this document does not specify (scenario content boundaries)
- 1.3 Relationship to v0.5 and v0.6 theory documents
- 1.4 Relationship to scenario specification documents

**Chapter 2: Architectural invariants**
- 2.1 The seven structural invariants (heartbeat-first, instance validity, drive read-only, anchor pre-generative, mediated release, audit append-only, structural identity preservation)
- 2.2 What invariance means for code organization
- 2.3 Where invariants are enforced (which mechanisms guarantee which invariants)
- 2.4 What scenarios cannot do regarding invariants (no new release authority, no mediator bypass, no audit modification, no drive write access from L3)

### Part II: Framework mechanisms

**Chapter 3: Lifecycle kernel**
- 3.1 Heartbeat, tick, turn — the three timing concepts
- 3.2 Instance validity (lock + generation + lease)
- 3.3 Cadence policy and time-source abstraction (does not assume fixed time scale)
- 3.4 Lifecycle priority over ordinary work
- 3.5 What the kernel does not own (no semantic state, no reasoning, no memory content)

**Chapter 4: L1 sensor framework**
- 4.1 Sensor registry and plugin-style injection
- 4.2 Signal classification (threat / status / background)
- 4.3 Signal bus and routing (fast/slow path split)
- 4.4 Rate sensing as primary input (state + trajectory)
- 4.5 What L1 does not specify (concrete sensor implementations belong to scenarios)
- 4.6 Provision for non-local signals (interface allows but does not implement cross-process / cross-agent signal sources)

**Chapter 5: L2 drive broadcast**
- 5.1 Drive as continuous broadcast, not instruction
- 5.2 Drive registry as injectable preset
- 5.3 Drive update policy interface (decay, severity accumulation, threat bonus, suppression, recovery as named functions)
- 5.4 Drive read-only invariant (only L1/L2 internal can write; L3 reads only)
- 5.5 Reflex arc fast path (mediator-issued reflex token, not mediator bypass)
- 5.6 What L2 does not specify (concrete drive dimensions belong to scenarios)

**Chapter 6: L3 deliberation framework**
- 6.1 Anchor system: pre-generative restriction mechanism
- 6.2 ActionDomain construction and admission gates
- 6.3 Candidate generation contract
- 6.4 Value judgment subsystem (drive-weighted score, multi-dimensional evaluation)
- 6.5 Conflict detection mechanism
- 6.6 Mediator: peer circuit, default inhibition, ReleaseToken issuance
- 6.7 What L3 does not specify (concrete anchor rules, candidate profiles, action types belong to scenarios)

**Chapter 7: Tool-edge bridge**
- 7.1 Tool registry as injectable action set
- 7.2 Action specification contract (side-effect class, anchor applicability, outcome observer)
- 7.3 ReleaseToken validation and execution path
- 7.4 What tool-edge does not specify (concrete actions belong to scenarios)

**Chapter 8: Append-only data tracks**
- 8.1 The five tracks: deliberation audit, episodic memory, learning outcomes, habit bias, LLM advisory audit
- 8.2 Schema freeze rules
- 8.3 Append-only enforcement
- 8.4 Track separation invariant (no cross-track writes, no current-decision-rewrites-history)

### Part III: Capability sources

**Chapter 9: Capability source registry**
- 9.1 The five-source taxonomy (structural / scenario / designer-given prior / individual habit / inherited prior)
- 9.2 Skill registry interface with provenance fields (source, provenance, confidence, scope, mutable)
- 9.3 Modification permissions per source category
- 9.4 Conflict-rich memory (preserve disagreements, not silent overwrite)
- 9.5 Prior skills as candidate / prediction / value judgment input only — never direct action authority
- 9.6 Inherited prior placeholder (interface present, mechanism deferred to v0.7+)

### Part IV: Persistence and outcomes

**Chapter 10: Persistence target abstraction**
- 10.1 The seven-level hierarchy (data structure supports all seven)
- 10.2 Active level declaration per deployment
- 10.3 Inter-level dependency rules
- 10.4 Cross-level trade-off conditions (transfer / successor channel requirement)
- 10.5 Death events as first-class observables
- 10.6 Framework requires the abstraction; scenarios declare which levels are active

**Chapter 11: Multi-dimensional outcome**
- 11.1 OutcomeVector schema (task progress, viability delta, resource delta, capability delta, risk delta, reversibility, cost, uncertainty)
- 11.2 Per-component nested structure where applicable (viability over persistence levels, etc.)
- 11.3 Predicted outcome at mediator submission
- 11.4 Actual outcome from outcome observer (contract; concrete observers are scenario-provided)
- 11.5 RPE as vector difference, drive-context weighted
- 11.6 Hard constraint vs soft trade-off evaluation order

### Part V: Scenario instantiation interfaces

**Chapter 12: Scenario contract**
- 12.1 What a scenario must provide (reference to scenarios/SPEC.md for details)
- 12.2 What a scenario must not provide (no new release authority, no mediator bypass, no audit modification, no structural invariant override)
- 12.3 Scenario activation lifecycle (instantiation, runtime fixedness, deactivation)
- 12.4 Multi-scenario support (framework can host multiple scenario packages but a running agent operates in one)

**Chapter 13: Runner interface**
- 13.1 What a runner does (assembles framework + chosen scenario, starts the agent)
- 13.2 Runner is per-scenario; no universal runner
- 13.3 Runner does not contain scenario logic (logic is in scenario package)

### Part VI: Observability

**Chapter 14: Stability observability**
- 14.1 Architecture-specific audit indicators (path integrity, invariant activation trace, drive read integrity, anchor domain integrity, mediated release integrity, audit append-only integrity)
- 14.2 Audit indicators are diagnostic only, not for cross-architecture comparison
- 14.3 Output format and trace contract
- 14.4 What this module is not (it does not compute architecture-neutral metrics — see Chapter 15)

**Chapter 15: Architecture-neutral trace contract**
- 15.1 Framework outputs trace files in a documented format
- 15.2 The format is consumed by `stability_metrics/` (an independent module, not part of `eva/`)
- 15.3 Any agent producing equivalent traces can be evaluated by the same `stability_metrics/` module
- 15.4 The framework does not compute cross-architecture metrics itself; this preserves comparison fairness

### Part VII: Forward compatibility

**Chapter 16: Forward-compatibility commitments**

This chapter is shorter than others. It documents specific design decisions made in the framework that preserve the ability to extend EVA to scenarios v0.6 does not yet implement. These are negative constraints — things the framework does not assume — rather than positive features.

- 16.1 No assumption of single agent (interfaces for sensor sources and signal origins use explicit identifiers; defaults work for single-agent but interfaces accept multi-agent)
- 16.2 No assumption of fixed time scale (cadence_policy, lifecycle_priority, time_source, deadline/interval as explicit abstractions)
- 16.3 PersistenceTarget data structure supports all seven levels (only some are activated per deployment)
- 16.4 Skill registry has provenance fields for inherited priors (interface present, mechanism deferred)
- 16.5 What forward compatibility does not commit to (no implementation of multi-agent communication, no physical sensor support, no cross-life learning machinery in v0.6)

---

## Boundary declarations

The following statements define what this document covers and excludes. They are normative for the v0.6 refactor.

### What goes in this document (framework)

- Mechanisms for sensing, drive update, candidate generation, anchor restriction, value judgment, mediator decision, tool-edge execution, outcome processing, learning
- Interfaces for scenario injection (drive presets, sensor presets, action sets, anchor policies, outcome observers, prior skills, persistence target activation)
- Append-only track schemas (the structural commitments; specific field semantics for scenario-specific data are scenario concerns)
- Trace output format (what is written; consumption is in `stability_metrics/`)
- Architectural invariants and their enforcement
- Forward-compatibility constraints

### What does not go in this document

- Specific drive types, sensor implementations, action implementations, anchor rules, outcome observers, or prior skills for any particular scenario
- Specific persistence target activations for any particular scenario
- Specific deployment instructions (running on systemd, running on a simulator, running on hardware)
- Specific evaluation experiments or comparison baselines
- Specific code module names beyond what is needed to identify the framework boundary
- Specific test cases (these belong to test files, not this document)

### What goes in scenario specifications

- Concrete drive dimensions for the scenario
- Concrete sensor list for the scenario
- Concrete action set for the scenario
- Concrete anchor rules for the scenario
- Concrete outcome observers for the scenario
- Concrete prior skills for the scenario
- Concrete persistence target activations for the scenario
- Concrete viability variables for the scenario
- Concrete deployment guidance for the scenario

### What goes in `stability_metrics/`

- Architecture-neutral metric calculators (CVR, CPS, UPC, RSR, MTTR, Recovery Path Entropy, Cost)
- Trace consumption logic (reads framework trace output, computes profiles)
- Profile output format
- This module does **not** read EVA internal state; it reads only the trace contract output

This module is a separate top-level package, not part of `eva/`. It must be usable by any agent (EVA or otherwise) that produces traces in the documented format.

---

## Filling rules

The skeleton sets the structure. Content fills in during the refactor.

**Rule 1**: No chapter is filled in before its boundary is confirmed. If a chapter's content turns out to need scenario-specific examples, the chapter is wrong — those examples belong in a scenario document, and the chapter must be rewritten more abstractly.

**Rule 2**: Every chapter's content is verifiable against the codebase. If the framework code does something the chapter does not document, either the chapter is incomplete or the code is misplaced. Either gap is fixed before the chapter is considered complete.

**Rule 3**: When a chapter references something a scenario provides, it references the scenario contract (`scenarios/SPEC.md`), not any specific scenario.

**Rule 4**: When the refactor reveals that the boundary between framework and scenario should be drawn differently than the skeleton suggests, the skeleton is revised — the refactor does not work around the wrong boundary.

These rules exist because v0.6 theory commits to "structure universal, content scenario-specific." If this document mixes structure and content, it contradicts the theory it is meant to implement.

---

## Open questions

Items the architect has flagged for resolution during the refactor:

- Whether persistent state schema should be specified at framework level (uniform across scenarios) or at scenario level (each scenario defines its own)
- Whether the runner abstraction should be in `eva/` or a peer top-level directory
- Whether `stability_metrics/` should be in the same repository or a separate one (current decision: same repository for ease of co-evolution, but with strict no-EVA-internal-imports discipline)
- How configuration files (per-scenario settings, deployment overrides) are loaded and validated

These are not blocking. They will be resolved as the refactor encounters them.

---

## Status notes

This skeleton is the output of v0.6 theory completion and the framework/scenario separation decision. It does not contain implementation details; it contains the structure those details will fit into.

The next step is the companion document `scenarios/SPEC.md`, which specifies what every scenario package must provide. Together, these two documents define the framework/scenario boundary precisely enough that implementation work can begin.
