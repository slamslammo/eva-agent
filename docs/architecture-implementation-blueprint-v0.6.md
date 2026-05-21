# EVA-Agent Architecture Implementation Blueprint v0.6

**Document nature**: This document is a prospective engineering blueprint for EVA-Agent v0.6. It is written as if EVA-Agent has not yet been implemented.

**Core rule**: This blueprint specifies the architecture to build, not the repository state to inspect.

**Theory basis**: The blueprint integrates the EVA v0.5 core architecture with the v0.6 unified theoretical extensions, including active persistence, persistence-target hierarchy, capability provenance, structural-invariant versus operational-content distinction, rate-aware sensing, four-layer memory, inherited priors, multi-dimensional outcome, observable stability, and scenario specification discipline.

**Relationship to v0.5**: The v0.5 full implementation blueprint is source blueprint material. Its valid engineering structure, invariants, and diagrams are absorbed here and updated where v0.6 changes the target architecture. Readers should not need to consult v0.5 in order to use this document.

---

## Table of Contents

- [§0 Abstract / Document Contract](#s0)
- [§1 Engineering Goals and Non-negotiable Invariants](#s1)
- [§2 Overall Architecture: Framework, Scenario, and Five Layers](#s2)
- [§3 Infrastructure / Kernel](#s3)
- [§4 Anchor System](#s4)
- [§5 L1 Homeostatic Sensing](#s5)
- [§6 L2 Drive Layer](#s6)
- [§7 L3 Adaptive Deliberation](#s7)
- [§8 L4 Self-Model Reserved Layer](#s8)
- [§9 L5 Social Layer Reserved Layer](#s9)
- [§10 Data Tracks and Persistence Architecture](#s10)
- [§11 Runtime Closed Loop](#s11)
- [§12 Scenario Specification Discipline](#s12)
- [§13 Validation and Stability](#s13)
- [§14 Deployment Path](#s14)
- [§15 Evolution Roadmap](#s15)
- [Appendix A. v0.5 Source-Material Reuse Map](#app-a)
- [Appendix B. v0.6 Engineering Upgrade Map](#app-b)

---

## §0 Abstract / Document Contract {#s0}

### 0.1 From EVA theory to EVA-Agent engineering

EVA-Agent begins from the claim that **continuous existence is a first-order design constraint** for a class of agents whose value depends on remaining the same agent over time under changing conditions. Under that framing, task completion, tool use, planning quality, and learning quality all matter only inside a more basic structure that preserves continuity, legitimacy, and bounded agency.

The move from theory to implementation is therefore not a translation into feature modules. It is the conversion of structural claims into engineering boundaries: heartbeat-first lifecycle, instance legitimacy, drive as internal context, anchor as pre-generative restriction, release authority distinct from reasoning, separated audit/memory/learning tracks, bounded learning overlays, and scenario-owned content under framework-owned runtime authority.

“Continuous existence” here is read in its active sense, per v0.6: what is preserved is the agent's projected capacity to continue existing, not the current state values themselves. State preservation and persistence are not the same thing.

**EVA is an architecture, not an ontology.** EVA-Agent does not decide on behalf of a scenario what counts as alive or dead, and it does not hardcode any fixed existence criterion into the framework. The framework provides the **mechanisms** required to sustain continuous existence (cadence, legitimacy, partitioned persistence, anchor, mediator, memory, inheritance, and so on) and **consistently honors the existence semantics declared by the scenario**; the existence semantics themselves are declared by the scenario as a field condition (see §2.7 and §12.7). This boundary is what lets the same framework carry existence fields as different as an always-on deployed agent and a one-life Crafter individual — without disturbing the structural invariants.

### 0.2 What EVA-Agent v0.6 is

EVA-Agent v0.6 is not a generic task orchestrator centered on completion. It is an **existence-centered agent architecture** whose first constraint is continuous, bounded, durable operation.

At a high level, EVA-Agent v0.6 consists of:

- an **Infrastructure / Kernel** layer for lifecycle, identity, persistence targets, and internal communication substrate
- **L1 Homeostatic Sensing** with state and rate observation
- **L2 Drive Layer** as continuous internal broadcast context
- **L3 Adaptive Deliberation** with memory, reasoning, peer circuit, mediator, outcome learning, and inherited priors
- reserved interfaces for **L4 Self-Model** and **L5 Social Layer**
- a cross-layer **Anchor System** as pre-generative restriction
- a **framework / scenario split** through which world-specific content enters a stable architecture

### 0.3 What this document explains

This blueprint answers four questions:

1. What are the engineering goals and non-negotiable invariants of EVA-Agent v0.6?
2. How do the framework/scenario split, five layers, Anchor System, and Kernel divide responsibility?
3. How do sensing, drive, deliberation, release, memory, and learning form a continuous closed loop?
4. How should such a system be validated, measured, and deployed?

### 0.4 Document positioning (architectural contract vs landed status)

This blueprint is the **architectural contract** for EVA-Agent v0.6, and it carries two kinds of commitment at once:

- **Landed and binding**: structural invariants and boundaries already implemented in code — new development must not deviate from them; deviating requires updating the blueprint and the tracking documents first.
- **Target architecture**: theoretical commitments that are non-negotiable in intent but not yet fully implemented — they guide subsequent phase work.

The precise boundary between the two **is not carried by this document**; it is carried by the completeness tiers in `implementation-tracking.md`: `production` (landed, treat as canonical) / `partial` (landed with a stated limitation) / `skeleton` (interface or placeholder only) / `deferred` (theory commits, runtime not implemented). For any development action, read the following three documents together to decide "what must be followed" vs "what must be built":

- **This blueprint** — the contract ("what, why, where the boundaries are")
- **`implementation-tracking.md`** — the status ("what is landed, what is still missing")
- **`scenarios-SPEC.md` / `scenarios/<name>/SPEC.md`** — the scenario-side implementation detail of the contract

`blueprint-to-tracking-map.md` provides a direct row-by-row mapping from blueprint commitments to tracking entries. When the blueprint is edited, the tracking and map must be checked for sync; the reverse holds too.

---

## §1 Engineering Goals and Non-negotiable Invariants {#s1}

### 1.1 Existence-centered engineering goals

EVA-Agent v0.6 must be built to establish a subject that:

1. maintains the **capacity to continue existing**, not merely the present values of its state variables
2. operates inside a persistent internal drive environment whose dynamics are inspectable and constrainable
3. grows reasoning, memory, release, and learning only within structural invariants that remain stable within a life
4. evaluates **future viability** as its primary evaluative object rather than only current state

Its first constraint is not task completion rate. It is whether heartbeat, legitimacy, persistence targets, candidate boundaries, and side-effect boundaries are structurally real and maintained.

### 1.2 Active persistence rather than passive preservation

v0.6 sharpens the meaning of continuous existence.

The passive reading says an agent committed to continuity should preserve current state values. The active reading says the agent should preserve and expand its **projected future capacity to continue existing**. EVA-Agent v0.6 adopts the active reading.

That choice has architectural consequences:

- inaction is not a neutral baseline
- state without rate is insufficient in non-trivial environments
- evaluation must consider projected trajectories, not only present values
- exploration, when implemented, is a bounded viability-supporting mechanism rather than a terminal objective

#### 1.2.1 Continuous existence ≠ continuous execution

Active persistence is not the same as uninterrupted execution. Two cases must be structurally distinguished:

- **Recoverable interruption**: state, structural invariants, and the provenance chain can be consistently restored (crash-then-restart, migration, recharge after a flat battery, hot upgrade). The same individual continues to exist.
- **Terminal failure**: state, a structural invariant, or the provenance chain is irrecoverably lost, or the scenario-declared continuity criterion no longer holds. That individual terminates.

The determination of “same individual” is anchored in three things: **legitimacy chain + recoverable state + provenance** — **not** in whether the process kept running, whether ticks never stopped, or whether any content was passed forward to a successor. The framework provides those three mechanisms; which interruptions count as recoverable, and which events constitute terminal failure, is declared by the scenario (see §2.7 and §12.7).

#### 1.2.2 The individual as the persisting subject

The persisting subject is the **individual**, not the “process” or the “code instance.” One runtime activation corresponds to one individual living from birth to terminal; multiple activations (even if they share a process or filesystem) constitute a **population**. Inheritance and designer-side improvement are population-level information-continuity mechanisms; they do not constitute multiple lives of the same individual (see §7.9 and §13.5).

### 1.3 Core engineering invariants

These are not recommendations. They are minimum structural conditions.

| Dimension | Typical task agent | EVA-Agent v0.6 invariant |
|---|---|---|
| Default behavior | ready-to-execute | **default inhibition** |
| Motivation | external task drives action | **drive as internal context** |
| Constraint timing | generate then filter | **anchor as pre-generative constraint** |
| Reasoning / execution relation | reasoning proposes and executes | **peer circuit and mediator distinct from reasoning** |
| Learning signal | external reward / scoring | **outcome discrepancy as endogenous learning signal** |
| Skill formation | explicit orchestration | **habit crystallization** |
| Lifecycle priority | task boundary first | **heartbeat-first lifecycle** |
| Memory role | recall support | **memory serves threat recognition, skill formation, and persistence** |
| Evaluation target | current state quality | **future viability under structural bounds** |
| Capability growth | unbounded | **bounded within structural invariants** |

### 1.4 Structural invariants versus operational content

v0.6 unifies several architectural prohibitions under one principle.

**Structural invariants** are the elements that constitute the agent's processing architecture itself. They define what kind of processing the agent performs, not merely what content it processes. Structural invariants must not be rewritten at runtime by reasoning, learning, retrieval, inheritance, or external content.

Structural invariants include at least:

- heartbeat-first cadence authority
- the ownership of drive state
- pre-generative anchor restriction
- mediator-owned release authority
- append-only audit discipline
- persistence-target definitions
- the distinction between framework authority and scenario content

**Operational content** is everything that flows through the architecture: candidates, retrieved episodes, semantic regularities, inherited priors, learned biases, outcome traces, and other world- or life-specific content.

Operational content may be learned, updated, inherited, compared, and revised. Its provenance must be preserved. It may not rewrite structural invariants.

### 1.5 Scenario content subordinate to framework authority

The architecture distinguishes between:

- **framework authority**: runtime ownership, cadence, legitimacy, release, append-only tracks, and structural invariants
- **scenario content**: world-specific drives, sensors, actions, admission policies, outcome semantics, and prior content

The scenario may shape content, but it may not mint release authority, rewrite append-only history, directly write drive state from higher layers, or redefine kernel cadence or legitimacy.

### 1.6 Why structure must enforce these rules

If these invariants live only in prose, prompts, or policy text, the system collapses back into a task agent. EVA-Agent requires **structure before strategy**:

- heartbeat-first becomes cadence authority
- drive becomes read-only broadcast from L2-owned state
- anchor becomes pre-generative domain restriction
- release becomes an independent peer-circuit and mediator path
- memory becomes distinct from audit and learning
- scenario content becomes subordinate to framework runtime authority

---

## §2 Overall Architecture: Framework, Scenario, and Five Layers {#s2}

### 2.1 Framework and scenario as a first-class split

EVA-Agent v0.6 is not only a five-layer architecture. It is also a two-part system that separates runtime authority from world-specific content.

```text
┌─────────────────────────────────────────────────────────────┐
│                       Scenario Layer                        │
│  concrete drive family · sensors · actions · anchors ·     │
│  outcome interpretation · prior content                    │
└──────────────────────────┬──────────────────────────────────┘
                           │ runtime scenario bundle
┌──────────────────────────▼──────────────────────────────────┐
│                      Framework Layer                        │
│  kernel · L1 · L2 · L3 · anchor mechanism · mediator ·     │
│  append-only tracks · persistence architecture              │
└─────────────────────────────────────────────────────────────┘
```

This split is structural, not organizational convenience. The same framework may operate over more than one existence field. Scenarios change the world-specific content without taking over runtime authority.

### 2.2 Five layers, one cross-layer system, one substrate

Within framework authority, EVA-Agent organizes cognition and behavior into five layers plus one cross-layer constraint system and one substrate.

```text
L5  Social Layer            (reserved)
L4  Self-Model              (reserved)
L3  Adaptive Deliberation
L2  Drive Layer
L1  Homeostatic Sensing
---------------------------------------
Cross-layer: Anchor System
Base layer: Infrastructure / Kernel
```

Two points are load-bearing:

- **Infrastructure / Kernel is not an implementation detail beneath L1.** It is the condition under which the same agent instance continues through time.
- **Anchor System is not a sixth cognitive layer or a post-hoc filter.** It restricts the visible candidate domain before generation.

One further point applies across all layers: **the seven layers are a categorization language, not a structural failure verdict.** Whether a failure at any given layer constitutes terminal failure for an individual is determined by scenario declaration, not by structural invariants. Every deployment must declare which layers are activated in that field, and what “recoverable interruption” and “terminal failure” mean at each activated layer. The framework executes the corresponding termination / recovery paths according to that declaration; it does not pre-judge life and death on behalf of the scenario (see §2.7, §12.7).

### 2.3 Functional roles by layer

- **Infrastructure / Kernel**: cadence, legitimacy, state persistence, append-only audit, communication substrate, persistence-target registration
- **L1**: standardized sensing, state/rate observation, urgency classification, signal routing
- **L2**: continuous drive state, update/decay/recovery dynamics, read-only drive broadcast, reflex fast path
- **L3**: working-memory assembly, reasoning, peer-circuit selection, mediated release, tool edge, outcome evaluation, memory updates, inherited priors
- **L4**: self-model interfaces derived from long-run history
- **L5**: social and coordination interfaces derived from stable lower layers

### 2.4 Dependency direction

```text
L5 → L4 → L3 → L2 → L1 → Infrastructure / Kernel
```

This arrow expresses dependency direction, not the runtime loop itself.

Key boundary rules:

- Kernel does not depend on higher cognition
- L1 does not depend on L3 interpretation
- L2 accepts updates from L1; higher layers read but do not rewrite drive state
- L3 is constrained by Anchor and may not bypass the mediator
- Audit, memory, and learning remain distinct tracks

### 2.5 The runtime scenario bundle

The scenario enters framework execution through a single scenario bundle contract. A valid bundle must provide six surfaces:

1. **drive preset** — the concrete drive family, dimension mapping, and initial structure
2. **sensors** — world-specific sensing surfaces and dimension specifications
3. **actions** — concrete action vocabulary and execution behavior
4. **anchors** — scenario admission policies and restriction vocabulary
5. **outcome observers** — world-specific outcome interpretation and expected-outcome semantics
6. **prior skills** — scenario-local prior content and reuse policy

The framework owns the structures those surfaces fill. The scenario owns the content and policy that populate them.

In addition to the content surfaces, the scenario must also provide an **existence semantics declaration** (the eight items in §12.7), which tells the framework how to determine recoverable interruption and terminal failure in that field. Declaration and content surfaces are two distinct kinds of constraint, but both are mandatory in scenario onboarding.

### 2.6 Why the split exists

Without this split, world-specific content tends to invade structural code, and structural invariants become tied to one environment. v0.6 makes the opposite commitment:

- framework owns what makes the agent an EVA agent
- scenario owns what makes the agent operate in a particular world

That rule is what allows scenario specification to be the default response to new environments.

### 2.7 Framework provides mechanisms; scenario declares semantics

The deepest layer of the framework / scenario split is this: **existence semantics themselves are declared by the scenario**, while the framework provides mechanisms and consistently honors the declaration. The table below gives the minimum mapping of that division of labor:

| Dimension | EVA Framework (scenario-agnostic, structural invariants) | Scenario declaration (field condition, consumed by framework) |
|---|---|---|
| Existence semantics | Mechanisms + consistent enforcement of declaration (**no hardcoded life/death**) | **Existence semantics declaration (eight items)** — see §12.7 |
| Persistence-target hierarchy | The 7-level categorization; audit / drive / value-judgment operate over activated levels | Which levels this scenario activates (e.g. Crafter: embodied + capability) |
| Instance identity | Instance legitimacy (lock / generation / lease) + recoverable state + provenance; `_resolve_individual_id` decides mint-new vs continue-existing based on `reset_semantics` | Which interruptions count as recoverable; which events count as terminal; `identity_continuity` declares what counts as "same individual" across substrate changes |
| Sensing signals | **Mechanisms** for sensing / rate-sensing (registry, normalization, urgency routing) | Mapping of signal → dimension / drive / outcome, rate cadence, cadence configuration (avatar vitals → dimension, **not** → substrate viability) |
| Clock | Single kernel cadence authority; **contractually intended** to read the scenario-declared `clock_source` for its tick rhythm (the current kernel cadence is still wall-clock; consumption of `clock_source` to drive step-vs-wall-clock cadence selection is not yet landed — see the "Kernel consumption of declared `clock_source`" row in tracking); per-scenario forks of cadence logic remain forbidden | `clock_source = "step"` (turn-driven, Crafter) or `"wall_clock"` (wall-clock seconds, Linux runtime); per-step rate and the like remain configured in the scenario adapter |
| Inheritance | Registry for receiving a prior bundle; provenance and structural-invariant validation | Whether an inheritance channel exists; how distillation aggregates terminated-individual traces |

> **Declaration vs configuration**: Of the eight existence-semantics items, the first seven (continuity criterion, recoverable interruption, terminal failure, individual boundary, reset semantics, inheritance channel, identity continuity) are **human-readable / audit declarations** — the framework records and validates against them, but does not fork runtime logic on them. The eighth item, `clock_source`, is **contractually** a framework-consumed configuration — the kernel is to read it to pick the life-clock source. **Note**: the current kernel cadence path is still wall-clock; the `clock_source` field has landed as part of the `ExistenceSemantics` dataclass and is declared by scenarios, but the kernel's actual consumption of that field (to switch between step and wall-clock cadence) is not yet implemented and remains a target item — see tracking for the current status. See §12.7.

Three derived constraints follow from this division, and both framework implementations and scenario onboarding must respect them:

1. **No P1 / P2 runtime modes for existence semantics.** Existence semantics are scenario declarations, not runtime mode switches; any design that downgrades continuity semantics into "toggle via configuration" drifts structural invariants into engineering preferences.
2. **Do not promote scenario-internal vitals into substrate viability.** Quantities like avatar HP, energy, saturation belong to the embodied / capability dimensions, entering L1 dimensions and L2 drive; whether their depletion constitutes terminal failure is declared by the scenario in the existence semantics, and **does not** alter the meaning of Level 1 substrate.
3. **Kernel cadence must not fork per scenario.** Kernel cadence authority is single; the difference between step-driven and wall-clock rhythms is **contractually** to be expressed by **the scenario declaring `clock_source` for the kernel to read** — that is the correct way to honor this constraint, **not** a violation (today the kernel does not yet consume `clock_source` and runs wall-clock; that consumption is a target item — see tracking). What is forbidden is "adding `if-scenario-is-crafter` branches inside the kernel scheduler," "rewriting kernel cadence paths for a specific scenario," or letting per-step rate / scenario-side timing config leak into the kernel; declaring `clock_source` for the kernel to read in a uniform way does not fall in this category.

---

## §3 Infrastructure / Kernel {#s3}

### 3.1 Why Kernel is outside the five layers

The five layers describe cognitive and behavioral organization. Kernel provides the substrate that allows the same continuous agent to remain legitimate through crashes, restarts, contention, and ordinary runtime pressure.

![Infrastructure position](./assets/architecture/infrastructure_position_in_eva.svg)

Kernel does not reason or learn directly, but it decides whether the rest of the architecture can exist coherently at all.

### 3.2 Kernel as existence substrate

Kernel must provide:

- the rhythm by which the agent remains alive to itself
- the legitimacy checks by which the agent remains the same instance
- the persistence surfaces by which current state and history are preserved
- the registration point for what the agent treats as persistence targets

If Kernel fails, no higher layer can compensate for it.

### 3.3 Heartbeat-first lifecycle

Kernel must separate the main loop into two structurally distinct units:

- **tick**: fixed-interval life-sign sampling. It refreshes lease, samples runtime state, writes current-state facts, and appends heartbeat events.
- **turn**: one bounded work slice between ticks.

Heartbeat must not become “something done when there is time.” It is the primary temporal authority of the architecture.

![Lifecycle kernel](./assets/architecture/lifecycle_kernel_heartbeat_first.svg)

### 3.4 Instance legitimacy

Long-running agents require explicit legitimacy. EVA-Agent projects legitimacy into one runtime-visible fact, but that fact must be backed by three distinct mechanisms:

- **lock**: a single-holder guarantee
- **generation**: a monotonic takeover/version mechanism distinguishing legitimate successor instances from stale ones
- **lease**: an expiry refreshed by heartbeat

If legitimacy is lost, ordinary operation must stop and the agent must fall back to minimal yield behavior.

![Instance identity](./assets/architecture/instance_identity_three_mechanisms.svg)

### 3.5 Two persistence patterns

Kernel must keep two non-mixed write patterns:

- **atomic current state** for “what am I now?”
- **append-only history** for “what has happened?”

The split is not stylistic. It protects both fast recovery and historical fidelity.

![Persistence split](./assets/architecture/persistence_two_patterns.svg)

### 3.6 Event channel versus drive broadcast

Kernel must provide two different internal communication substrates:

- **event channel**: discrete, past-tense happenings; push semantics; append-only recording
- **drive broadcast**: continuous, present-tense state; pull semantics; read downstream as environment

Kernel provides transport and persistence substrate. The semantic ownership of drive state remains in L2.

![Event bus](./assets/architecture/event_bus_two_channels.svg)

### 3.7 Persistence-target hierarchy

v0.6 makes explicit that the agent preserves not one thing but a hierarchy of things.

| Level | Persistence target | Role in v0.6 |
|---|---|---|
| Level 1 | substrate instance | required |
| Level 2 | embodied instance | required |
| Level 3 | capability structure | required |
| Level 4 | resource and asset system | required |
| Level 5 | reproductive structure | reserved |
| Level 6 | group structure | reserved |
| Level 7 | cultural information | reserved |

The architecture does not require every deployment to activate all seven levels. It requires that deployments declare which levels they activate and that Kernel expose a registration surface for them.

For each activated level, what “recoverable interruption” and “terminal failure” mean is declared by the scenario in the existence semantics of §12.7. The framework does not pre-decide on the scenario's behalf — for instance, the framework does not declare that “a Level 2 embodied failure must be a recoverable episode boundary,” nor that “a Level 1 process exit must be terminal.”

### 3.8 Substrate continuity and individual identity

Substrate continuity is not the same as ticks-never-stopping or process-never-exiting. Whether the same individual is still in existence is determined jointly by three things:

1. **Legitimacy chain**: lock / generation / lease remain monotonically consistent across the interruption;
2. **Recoverable state**: atomic current state can be coherently reconstructed after the interruption;
3. **Provenance**: the append-only history chain is not broken, and the new instance's origin lines up with the prior identity.

From this, two boundary judgments follow:

- **Recoverable interruption**: crash-then-restart, node migration, recharge after a flat battery, hot upgrade, temporary suspension followed by resumption — as long as all three above hold, this is the same individual continuing to exist.
- **Terminal failure**: the legitimacy chain breaks, atomic state cannot be reconstructed, the provenance chain breaks, or the scenario-declared continuity criterion no longer holds — that individual terminates.

`individual_id` is the engineering carrier for this judgment: `_resolve_individual_id` (`eva/kernel/main.py`) decides, based on the active scenario's `reset_semantics`, whether to restore an existing identity from the persisted `individual.json` and append a new substrate to the chain (`"same_individual_recovery"`) or mint a fresh id (`"new_individual"` or otherwise). `RunSummary` records this run's `individual_id` and `exit_reason`, so post-hoc audit can decide whether the run was a continuation of the same individual or the beginning of a new one.

> **Important**: Whether a failure at the embodied layer (Level 2) constitutes terminal is a scenario declaration. For example, a one-life Crafter world declares `HP = 0 ⇒ terminal individual death`; in that scenario, HP reaching zero is not an episode boundary, not the RL-paradigm "done," but the actual death of that individual — `CrafterRuntimeSession` reports `terminated=True` to the kernel, which exits the run with `exit_reason="individual_terminated"` (archive trace, end this run) and **does not call `wrapper.reset()` to extend life**. The next activation is a **new individual** (`_resolve_individual_id` mints a fresh id), which may load distilled priors over the inheritance channel. The framework does not treat avatar vitals as a substrate viability signal — it accepts the scenario declaration and executes accordingly.

### 3.9 What Kernel ultimately decides

Kernel decides whether the rest of the architecture may continue to exist as the same legitimate agent at all; and it **consistently honors the scenario's declaration of existence semantics**, anchoring the “same individual?” judgment in legitimacy + recoverable state + provenance, rather than in whether execution was interrupted.

---

## §4 Anchor System {#s4}

### 4.1 Role of Anchor

Anchor answers a pre-generative question:

> **What candidate domain is even allowed to become visible now?**

Anchor acts before candidate generation:

- it does not own a layer-style cognitive state
- it shrinks the action domain before generation
- it is distinct from mediator: Anchor governs what may be generated; mediator governs what may be released

![Anchor System overview](./assets/architecture/anchor_system_overview.svg)

### 4.2 Formal meaning of `G(s) → A'(s) ⊆ A(s)`

The point is positional, not merely symbolic.

`A'(s)` is not the leftover after filtering. It is the **visible domain at generation time**. That implies:

1. candidate generation reads only the restricted domain
2. potential capability is larger than currently visible capability
3. mediator is not responsible for domain shrinkage
4. terminal checks may exist, but only as defense in depth

### 4.3 Structural envelope and dynamic narrowing

Anchor has at least two persistent forms of work:

- **structural envelope**: stable hard boundaries from continuity, integrity, deployment capability, side-effect class, and execution limits
- **dynamic narrowing**: state-dependent restriction based on runtime legitimacy, sensed conditions, recent outcomes, and bounded learning overlays

Dynamic narrowing may tighten or reorder the visible domain. It must never extend beyond the structural envelope.

### 4.4 v0.6 three-way distinction

v0.6 sharpens anchor responsibilities into three conceptual layers:

1. **structural anchors** — stable hard boundaries
2. **constitutional or scenario admission policies** — semi-stable world-specific restrictions inside the structural envelope
3. **dynamic or learned overlays** — transient tightening based on current conditions and bounded experience

This is an engineering distinction, not a demand for three separate concrete modules. A valid implementation may realize the distinction through a smaller number of mechanisms so long as the functional separation remains true.

### 4.5 Capability restriction and parameter restriction

Anchor operates in at least two ways:

1. **capability restriction**: some capabilities never enter the current visible domain
2. **parameter-domain restriction**: allowed capabilities still have bounded target, scope, rate, and intensity

Candidate generation must therefore see bounded action schemas, not open-ended tools with late filtering.

### 4.6 Relation to the rest of the architecture

- Kernel decides whether the agent may operate at all
- L1 reports what is happening
- L2 changes urgency and bias
- Anchor decides what candidates may become visible
- L3 reasons only inside that restricted domain

Anchor is what makes “constraint before generation” structurally real.

---

## §5 L1 Homeostatic Sensing {#s5}

### 5.1 Role of L1

L1 is where the agent first formally knows:

> **What state am I in right now, and how is it changing?**

Its job is to detect deviation from viable ranges and route signals by urgency before deeper interpretation. L1 must not depend on L3 interpretation.

![L1 position](./assets/architecture/l1_position_in_eva.svg)

### 5.2 Sensor registry

L1 must use a formal sensor registry rather than hardcoded metrics. What varies by existence field is the concrete sensor set; what must remain stable is the registration, collection, and output contract.

All sensors are normalized into a shared signal shape.

![L1 sensor registry](./assets/architecture/l1_sensor_registry.svg)

### 5.3 State and rate

Every meaningful dimension should be observed in two ways:

- **state**: where the dimension is now
- **rate**: where the dimension is heading

State-only systems react after threshold crossing. State-plus-rate systems can recognize approach, acceleration, and deterioration under inaction.

![L1 state vs rate](./assets/architecture/l1_state_vs_rate.svg)

### 5.4 Rate-sensing tiers

v0.6 requires each declared dimension to carry a rate-sensing tier.

| Tier | Meaning | Requirement |
|---|---|---|
| `required` | threshold crossing constitutes failure for an active persistence target | rate sensing must exist |
| `recommended` | dimension materially affects future viability | rate sensing should exist; absence requires rationale |
| `optional` | background context | rate sensing may exist |
| `unsupported_with_reason` | rate sensing unavailable for principled reasons | reason must be recorded |

The classification belongs to the scenario's dimension specification. The framework must audit obvious inconsistencies.

### 5.5 Status and rate in judgment

L1 judgment must carry at least:

- status
- evidence
- rate context

The combination rules are:

- **status sets baseline pressure**
- **rate modulates urgency**
- **configured anticipatory thresholds may create pressure before threshold crossing** for required-tier dimensions

That is how active persistence becomes real at the sensing layer.

### 5.6 Signal classification

Signals should be classified early into three urgency categories:

- **threat**
- **status**
- **background**

The classification must be cheap and early.

![L1 signal bus classification](./assets/architecture/l1_signal_bus_classification.svg)

### 5.7 Fast and slow paths

Classification becomes structural through two parallel routes:

- **fast path**: threat → L2 reflex arc → mediated release → execution, without L3 deliberation
- **slow path**: status/background → L2 drive update → L3 deliberation → mediator → execution

The fast path is narrow. It does not bypass the mediator. It handles only pre-defined, low-complexity, life-boundary responses.

![L1 fast/slow path split](./assets/architecture/l1_fast_slow_path_split.svg)

### 5.8 Unknown-rate fallback

Rate requires history. When history is unavailable, downstream layers must see explicit unknowns rather than false stability.

Minimum fallback rule:

- rate unavailable is represented explicitly
- unknown direction is neither positive nor negative evidence
- absence of rate data must not be interpreted as stable conditions

### 5.9 What L1 ultimately decides

L1 guarantees that the agent has a formal answer to what is happening now and which processing path the change belongs to.

---

## §6 L2 Drive Layer {#s6}

### 6.1 Role of L2

If L1 tells the agent what state it is in, L2 determines the **internal environment it is currently immersed in**.

Drive is not a command. It is continuous context.

![L2 position](./assets/architecture/l2_position_in_eva.svg)

### 6.2 Drive registry and field-specific drive family

Drive structure must be explicit rather than opaque. The framework owns the generic drive seam and downstream read-only use. The scenario supplies the concrete drive family appropriate to the field.

![L2 drive registry](./assets/architecture/l2_drive_registry.svg)

### 6.3 Continuous intensity

Each drive is represented as a continuous quantity rather than a discrete on/off switch. This supports accumulation, decay, and gradual downstream biasing.

![L2 continuous intensity](./assets/architecture/l2_continuous_vs_discrete.svg)

### 6.4 Update, decay, and recovery

L2 owns drive time dynamics:

- **update** from new signals
- **decay** when stimulation fades
- **recovery** when conditions improve

Drive must be persistent state, not an argument assembled only for one reasoning cycle.

### 6.5 Drive broadcast: state, not command

Higher layers do not receive instructions from L2. They read a drive environment.

The same reasoning substrate produces different candidates under different drive conditions because the internal environment differs, not because a different command was issued.

Higher layers may read but must not rewrite drive state.

![L2 drive broadcast](./assets/architecture/l2_drive_broadcast_state_not_command.svg)

### 6.6 Pressure as projection, not the main model

Pressure summaries, viability-gap summaries, or similar read-side views may exist, but they must not replace drive state as the L2-owned model.

Projection is useful. Projection is not ownership.

### 6.7 Reflex arc

L2 must provide a narrow fast path for minimal urgent responses.

Typical classes include:

- distress persistence
- yield
- conservative shrink
- heartbeat protection

This path bypasses L3 deliberation but does not bypass mediator-owned release authority. It must not expand into a second general execution lane.

![L2 reflex arc](./assets/architecture/l2_reflex_arc_parallel_to_broadcast.svg)

### 6.8 Semantic memory and the L2 boundary

v0.6 imposes a hard boundary here.

Semantic memory may influence deliberation directly in L3. In future implementations it may inform **audited, field-configured drive-update parameters**. It must not directly rewrite:

- drive ownership
- drive prototypes
- current drive state

This boundary preserves the distinction between operational content and structural invariants.

Two valid realizations exist:

- **Option A**: semantic memory remains purely an L3 advisory input and does not participate in L2 at all
- **Option B**: semantic memory may inform audited, field-configured L2 update parameters without becoming a direct write path

They are equivalent only if all of the following hold:

1. semantic memory does not become a write owner of drive state
2. drive prototypes remain structurally owned outside semantic memory
3. current drive state is never directly written from semantic-memory content
4. provenance is preserved for any semantic-derived parameter influence
5. L2 remains the sole runtime owner of drive updates

### 6.9 What L2 ultimately decides

L2 is where EVA-Agent decisively diverges from task-agent structure: behavior unfolds inside a continuous internal environment rather than from direct task command.

---

## §7 L3 Adaptive Deliberation {#s7}

### 7.1 Role of L3

L3 is the first layer where the agent acquires a full adaptation-and-learning loop. It is where experience begins to matter beyond design-time encoding.

L3 forms candidates, compares them under current drive context, and submits them to independent release authority. It does not directly execute.

![L3 position](./assets/architecture/l3_position_in_eva.svg)

### 7.2 Working-memory assembly

Working memory is the in-cycle substrate of deliberation. It assembles current context from one real-time channel and multiple retrieval inputs.

The real-time channel contains:

- current sensing
- current drive broadcast

Additional retrieval inputs may include:

- episodic hints
- semantic hints
- procedural or habit hints
- inherited-prior hints
- recent outcome traces

The point is architectural, not numerological: L3 reasons over a bounded assembled context, not over the full history of the agent.

### 7.3 Four-layer memory model

v0.6 makes the memory structure explicit.

| Layer | Role | Persistence | Engineering requirement |
|---|---|---|---|
| Working memory | in-cycle deliberation substrate | no | assembled fresh each cycle |
| Episodic memory | salient event memory | yes | append-only, relevance-retrievable |
| Semantic memory | compressed regularities | yes | first-class storage interface |
| Procedural memory | condition-action capability patterns | yes | explicit, bounded, mediator-gated |

#### 7.3.1 Working memory

Working memory contains the information currently being processed. It is replaced each cycle. It is not a long-lived persistence track.

#### 7.3.2 Episodic memory

Episodic memory records discrete experienced events with situational anchoring. It supports retrieval by contextual relevance and salience.

![L3 episodic salience](./assets/architecture/l3_episodic_salience_encoding.svg)

#### 7.3.3 Semantic memory

Semantic memory stores extracted regularities rather than event detail. It acts as background knowledge that shapes candidate evaluation and retrieval without carrying full episodic specificity.

Semantic memory must exist as a first-class storage layer. It is not merely an interpretation of episodic logs.

#### 7.3.4 Procedural memory

Procedural memory stores condition-action capability patterns that surface quickly under matching situations.

Two implementation shapes are valid:

- **Option A**: dedicated procedural memory store
- **Option B**: habit-track-backed procedural surface

They are equivalent only if all of the following hold:

1. condition-action patterns are explicit
2. candidate shaping is bounded
3. provenance is retained
4. mediator remains the only release authority
5. no procedural shortcut directly triggers side effects

Procedural memory is a candidate-shaping and confidence shortcut, not a release authority.

### 7.4 Reasoning core

The reasoning core is where the LLM or analogous generative substrate sits, but it is **not** the final decision authority. It forms candidates, not actions.

It has three main functions:

- working-memory integration
- value judgment under current drive context and bounded learned overlays
- conflict detection among pressures and candidate implications

The output is a ranked candidate set, not an execution order.

![L3 reasoning core](./assets/architecture/l3_reasoning_core_overview.svg)

### 7.5 Peer circuit / basal ganglia analog

EVA-Agent must separate “what seems reasonable” from “what is actually selected and released.” That independent selection authority is the peer circuit.

Its role is to:

- select among candidates
- gate release timing
- carry pathway updates shaped by outcome

The peer circuit is parallel to reasoning, not subordinate to it. If selection and justification collapse into one process, default inhibition becomes a policy preference rather than a structural property.

Two valid realizations exist:

- **Option A**: an explicitly separate peer-circuit module or subsystem
- **Option B**: a single larger deliberative subsystem with a structurally distinct selection function inside it

They are equivalent only if all of the following hold:

1. default inhibition remains a structural property rather than a reasoning preference
2. selection and justification are not collapsed into the same computation
3. habit formation is not entangled with ordinary reasoning updates in a way that erases its separate structural role
4. release is never directly commanded by reasoning output alone

![L3 basal ganglia](./assets/architecture/l3_basal_ganglia_overview.svg)

### 7.6 Mediator and tool edge

Mediator is the independent release authority. No candidate may produce external side effects without mediator approval.

Mediator responsibilities include:

- checking current runtime and release conditions
- preserving execution-boundary discipline
- ensuring release facts are formally recorded

Tool edge is the only legitimate route by which the agent produces external side effects.

There are only two execution paths:

1. **mediated path** for ordinary, habitual, or deliberative side effects
2. **mediated reflex fast path** for narrow life-boundary responses originating from L1/L2 fast-path conditions

In both cases, reasoning cannot directly trigger execution.

![L3 tool edge](./assets/architecture/l3_tool_edge_position.svg)

![L3 mediator](./assets/architecture/l3_mediator_three_functions.svg)

### 7.7 Multi-dimensional outcome and vector RPE

Execution is not the end of the loop. After release and execution, the agent must observe outcome, compare it to prediction, update internal pathways, and encode experience.

#### Outcome observation

Outcome must be normalized into a multi-dimensional structure. At minimum, the architecture should be able to represent:

- task progress
- viability delta
- resource delta
- capability delta
- risk delta
- reversibility
- cost
- uncertainty

Not all dimensions are equally active in all fields. The active dimensions are field-specific. The architecture requires a common structure for expressing them.

#### RPE computation

Outcome discrepancy is not generic goodness. It is the difference between predicted and observed outcome under the current continuity and drive context.

In vector form:

```text
RPE_vector = actual_outcome_vector − predicted_outcome_vector
```

Different dimensions may simultaneously show positive and negative discrepancy. That is normal in a multi-dimensional outcome model.

#### Update targets

RPE feeds at least two update targets:

1. pathway weighting / selection bias
2. memory encoding and habit crystallization

### 7.8 Habit track and skill crystallization

Repeated positive outcomes for similar `(situation, action)` patterns may crystallize into habit-skills. These reduce deliberative cost but do not bypass release boundaries.

Properties of habit shaping:

- patterns trigger by situational similarity
- shaping is bounded
- mediator remains the release authority
- provenance is retained

### 7.9 Inherited priors as an L3 mechanism

v0.6 specifies an implementable L3 path for inherited priors.

**Key positioning**: inheritance is a **cross-individual** population-level information-continuity mechanism — flowing from one or more **terminated past individuals** into a **distinct new individual**. It is **not** a continuation of the same individual across multiple lives:

- the receiving party is a new individual, not a “revival” or “extended life” of the original;
- “process never stopped” / “any content was passed forward” does **not** constitute existence continuity of the same individual;
- the continuity of the same individual is always anchored in legitimacy + recoverable state + provenance, per §3.8;
- inheritance changes the initial capability and prior content of the new individual; it does not change the identity it belongs to.

The mechanism has two phases:

1. **offline distillation** from the traces of one or more terminated past individuals into a prior bundle
2. **online loading and bounded use** during the activation of a distinct new individual

#### Distillation path

The distillation pipeline is architecturally external. It reads append-only traces, extracts same-field regularities, validates structural invariants, and produces a bounded prior bundle.

The bundle must carry provenance, confidence, and scope.

#### Runtime use

At activation time, a same-field prior bundle may be loaded so that inherited priors can participate as:

- working-memory hints
- bounded habit-path shaping inputs
- bounded value-judgment bias

#### Hard constraints

Inherited priors:

- are **same-field first**
- are operational content, not structural invariants
- must not modify drive ownership, anchor structure, mediator authority, audit semantics, or persistence-target definitions
- shape candidates and evaluation, not release authority

This mechanism is not life-transcending identity transfer. It is bounded capability reuse.

### 7.10 Exploration as a bounded viability-supporting mechanism

When implemented, exploration must be treated as a bounded viability-supporting mechanism rather than a terminal objective.

Exploration matters because it can improve:

- persistence-relevant uncertainty reduction
- capability building
- persistence-relevant resource discovery

Exploration must remain bounded by:

1. the unrecoverability floor
2. cost-awareness
3. persistence relevance

It is evaluated through the same multi-dimensional outcome structure as other actions.

### 7.11 What L3 ultimately decides

L3 is where thought, memory, selection, release, execution, outcome, and learning become a formal loop rather than a planner blob.

---

## §8 L4 Self-Model Reserved Layer {#s8}

### 8.1 Role of L4

L4 is the reserved place where the agent gradually forms a higher-order model of itself: capabilities, costs, vulnerabilities, stable preferences, and long-term behavioral style.

L4 is not another planner.

### 8.2 What L4 depends on

L4 depends on long-term products of lower layers, especially L3:

- release history
- outcome history
- episodic, semantic, and procedural traces
- habit trajectories
- long-term relations between drive and behavior

It models this agent's own history, not abstract world knowledge.

### 8.3 What L4 must not override

L4 must not invade lower-layer authority:

- not kernel cadence or legitimacy
- not L1 sensing facts
- not L2 drive ownership
- not L3 release authority
- not the Anchor envelope

### 8.4 Reserved interfaces

At this stage, L4 is best defined by contract rather than by finalized internal design.

| Dimension | L4 should carry | L4 should not carry |
|---|---|---|
| Inputs | release/outcome aggregates, memory summaries, habit traces, long-term self-patterns | raw signals, raw drive slots, task commands |
| Outputs | self-model context, capability/cost/risk estimates, interpretive summaries | release commands, direct tool calls, drive overwrites |
| Feedback mode | bounded advisory surface | direct execution authority |

---

## §9 L5 Social Layer Reserved Layer {#s9}

### 9.1 Role of L5

L5 is reserved for the layer where the agent begins to include **other-as-other** in its world model. This is not generic networking. It is the place for relation-bearing entities and coordination semantics.

### 9.2 Relevant entity types

L5 may eventually cover:

- conspecific-like entities
- human collaborators and constraints
- other agents or external systems that become relation-bearing rather than merely instrumental
- persistent coordination structures

### 9.3 Boundary rules

L5 depends on stable L4 self-model and L3 runtime. It must not provide direct release authority or lower-layer rewrites.

| Dimension | L5 should carry | L5 should not carry |
|---|---|---|
| Inputs | self-model context, relation history, coordination summaries, social context state | raw tool output, raw signals, unaggregated event floods |
| Outputs | relationship context, coordination context, expectation and boundary estimates | direct release, direct tool calls, lower-layer rewrites |
| Feedback mode | bounded advisory social surface | side-effect authority bypass |

### 9.4 Deferred scope

Group persistence, cultural information, and Type B inherited priors belong to later versions.

---

## §10 Data Tracks and Persistence Architecture {#s10}

### 10.1 Why data tracks must remain distinct

EVA-Agent v0.6 must not collapse all persistent information into one store. Different tracks serve different architectural roles.

### 10.2 Atomic current state

This track answers: **what am I now?**

It contains current-state facts needed for continuity and restart.

### 10.3 Append-only audit

This track answers: **what has happened?**

It records discrete historical facts such as lifecycle events, release facts, key transitions, and outcome records.

Audit is not memory.

### 10.4 Episodic memory track

This track stores salient experiences that remain retrievable across cycles within a life.

### 10.5 Semantic memory track

This track stores regularities extracted from experience. It must be first-class and append-only.

Semantic memory is not just a convenient reading of episodic records.

### 10.6 Procedural / habit track

This track stores the durable action-shaped patterns that support fast candidate shaping under matching conditions.

Whether implemented as a dedicated track or a habit-backed surface, it must satisfy the procedural-memory role.

### 10.7 Inherited-prior records

Inherited priors are not part of episodic memory. They are operational content received through an inheritance path and should remain explicitly provenance-bearing.

### 10.8 Persistence-target mapping

The architecture should map major artifacts to persistence-target levels:

| Persistence level | Typical artifacts |
|---|---|
| Level 1 | current runtime legitimacy and state substrate |
| Level 2 | embodiment-specific continuity state |
| Level 3 | capability records, priors, structured skill surfaces |
| Level 4 | resources, assets, episodic/semantic/procedural accumulations |
| Levels 5–7 | reserved higher-order persistence targets |

### 10.9 The governing distinction

Audit is not memory. Memory is not learning. Learning is not release authority.

---

## §11 Runtime Closed Loop {#s11}

### 11.1 Full loop structure

The runtime loop is the process by which the agent sustains continuity, adapts to its field, and grows from experience.

```text
kernel cadence (tick / turn)
  │
  ├──> [fast path] L1 threat signals
  │      → L2 reflex arc
  │      → mediator (still required)
  │      → tool edge
  │
  └──> [slow path] L1 sensing (state + rate)
         → L2 drive update + broadcast
         → Anchor domain restriction
         → L3 working-memory assembly
         → candidate generation and value judgment
         → peer-circuit selection
         → mediator release
         → tool-edge execution
         → outcome vector (multi-dim: progress / viability / resource / capability / risk / reversibility / cost / uncertainty)
         → vector RPE
         → episodic / semantic / procedural updates
         → next-cycle context
```

Fast path and slow path run in parallel as distinct routes. Fast path does not bypass the mediator. Outcome is multi-dimensional rather than scalar.

### 11.2 What the loop makes real

This loop makes the following commitments concrete:

- cadence is prior to ordinary work
- drive is context, not command
- anchor acts before generation
- release is mediated
- outcome closes the loop back into memory and pathway updates

### 11.3 Offline versus online inheritance

Inherited-prior **distillation** is not part of the per-cycle runtime loop. It is an offline external process.

The runtime loop only:

- checks for available same-field prior bundles at activation
- loads them if appropriate
- uses them as bounded operational content during deliberation

Two valid realizations exist:

- **Option A**: distillation lives in an independently packaged top-level subsystem outside the runtime framework
- **Option B**: distillation lives inside the broader framework repository but remains isolated from runtime execution as a separate subsystem

They are equivalent only if all of the following hold:

1. distillation does not import scenario-specific runtime modules as part of the per-cycle loop
2. distillation does not modify structural invariants
3. distillation does not execute inside the per-cycle runtime loop
4. the prior-bundle schema remains an interface contract between runtime and distillation machinery

### 11.4 Bounded learning

Learning may bias retrieval, candidate preference, and pathway weighting. It may not rewrite runtime continuity, drive ownership, structural anchors, or release authority.

---

## §12 Scenario Specification Discipline {#s12}

### 12.1 Default response to a new environment

When a new existence field is introduced, the default response should be a **scenario specification**, not a theory extension.

The normal path is:

```text
new environment
  → write scenario specification
  → define six scenario surfaces
  → declare persistence-target activation
  → define outcome dimensions
  → define prior content and admission policies
  → validate against framework invariants
```

### 12.2 Required scenario surfaces

Every scenario must provide six surfaces through the runtime scenario bundle:

1. drive preset
2. sensors
3. actions
4. anchors
5. outcome observers
6. prior skills

These are not optional if the field is to participate in the full architecture.

### 12.3 What scenario owns

A scenario may own:

- concrete drive families
- concrete sensor dimensions and payload policies
- concrete action vocabulary and handlers
- concrete candidate profiles and anchor reasons
- concrete outcome semantics
- concrete prior and habit heuristics

### 12.4 What scenario must not own

A scenario must not:

- mint release authority
- bypass mediator-owned execution
- directly write drive state from higher layers
- rewrite append-only audit, learning, or history tracks
- take over kernel cadence, legitimacy, or persistence authority

### 12.5 One scenario per runtime

One runtime activation uses one active scenario. Multi-scenario switching within one process is deferred.

### 12.6 Theory extension discipline

Theory extension should be considered only when scenario specification is **provably insufficient** within the existing structural invariants.

The burden of proof is on the extension, not on the scenario.

### 12.7 Existence Semantics Declaration (eight items)

At onboarding, every scenario **must** declare the following eight items; the framework reads and consistently enforces this declaration rather than applying any default process-level life/death semantics. The code carrier is `eva/scenario_bundle.py::ExistenceSemantics`, exposed on the runtime bundle as the required field `RuntimeScenarioBundle.existence_semantics`.

| # | Declaration item | Kind | Meaning | How the framework consumes it |
|---|---|---|---|---|
| 1 | **continuity criterion** | declaration | The criterion under which an individual is "still in existence" in this field | Decides when to enter the terminal path (audit + validation) |
| 2 | **recoverable interruption** | declaration | Which interruptions count as recoverable (same individual continues); `()` means none | Kernel takes the recovery path instead of the termination path (audit + validation) |
| 3 | **terminal failure** | declaration | Which events constitute irrecoverable termination | Triggers trace archiving and ends the individual (audit) |
| 4 | **individual boundary** | declaration | Where one individual begins and ends (one run / one period / …) | Used for identity scope and metrics aggregation |
| 5 | **reset semantics** | declaration | What "reset" means after termination: `"new_individual"` / `"same_individual_recovery"` / `"not_applicable"` | `_resolve_individual_id` uses this to decide mint-new vs continue-existing |
| 6 | **inheritance channel** | declaration | Whether a cross-individual inheritance channel exists, and the input / scope of distillation | Determines the prior-bundle loading strategy |
| 7 | **identity continuity** | declaration | What counts as the same individual across restarts / substrate changes | Combines with the three things in §3.8 (legitimacy + recoverable state + provenance) to make identity judgments |
| 8 | **clock_source** | **framework-consumed config** (target; not yet consumed) | Life-clock source: `"step"` (turn-driven) or `"wall_clock"` (wall-clock seconds); default `"wall_clock"` | **Contract target**: kernel reads this to choose its cadence source (it does **not** fork scheduling logic per scenario). **Today**: kernel cadence is still wall-clock; the field has landed and is declared by scenarios, but kernel consumption of `clock_source` to switch cadence is not yet implemented — see tracking |

**Declaration vs configuration (important)**: items 1–7 are declarations — the framework **records and validates** against them, but does not fork runtime logic on them; only item 8, `clock_source`, is **contractually** a framework-consumed configuration — the kernel is to read the field to choose its cadence source. **Today**: the kernel cadence path is still wall-clock; the `clock_source` field has landed as part of the `ExistenceSemantics` dataclass and is declared by scenarios, but the kernel's consumption of that field (to switch between step and wall-clock cadence) is not yet implemented — see tracking. They live in the same `ExistenceSemantics` dataclass because they share the same commitment ("how this individual survives in this field"), but their consumption modes differ (items 1–7 take effect once landed — the framework records and validates them; item 8's landing covers only the field and the declaration, while actual consumption is tracked separately as a deferred row). This boundary is consistent with derived constraint #3 in §2.7 — what is forbidden is "kernel cadence forking per scenario," **not** "scenarios declaring their own clock source."

This declaration is itself a mandatory scenario surface (parallel to but semantically distinct from the six content surfaces in §2.5). If any deployment is missing these eight items, the framework should fail at scenario activation rather than fall back to defaults; the one exception is that `clock_source` has a dataclass-level default of `"wall_clock"` (to accommodate the Linux runtime baseline), but scenarios should still declare it explicitly to close the audit loop.

**Example — Crafter** (one-life world):

- continuity criterion = `HP > 0` with required vitals not depleted
- recoverable interruption = `()` — **none** (no in-life revival exists in a one-life world)
- terminal failure = `HP = 0`
- individual boundary = one episode = one individual from birth to terminal
- reset semantics = `"new_individual"` (the next activation in the same process is not a continuation of the original individual)
- inheritance channel = trace of terminated individual → distillation → inherited priors of the new individual (optional to enable)
- identity continuity = no cross-substrate continuation inside a one-life world; once terminal, the next individual is fresh
- clock_source = `"step"` (turn-driven; rate and cadence are computed per step and do **not** alter kernel cadence authority)

> Engineering implication: when integrating Crafter, on `done=True` from the env, `CrafterRuntimeSession.step_action()` sets `self.terminated = True` and **does not call `wrapper.reset()`** to extend life; the kernel loop reads that flag and exits the run with `exit_reason="individual_terminated"`. The next activation is explicitly recorded as a new individual by `_resolve_individual_id` (a fresh `individual_id` is minted), and the inheritance channel decides whether to load priors. Avatar vitals enter L1 dimensions and L2 drive, and are **not** promoted to substrate viability.

**Example — Linux runtime** (long-running deployment, survives substrate restart):

- reset semantics = `"same_individual_recovery"` (after a process crash or node migration, the same `individual_id` is recovered from `individual.json`)
- clock_source = `"wall_clock"`
- The remaining declarations live in `scenarios/linux_runtime/__init__.py`

---

## §13 Validation and Stability {#s13}

### 13.1 Validation by invariant

Validation should be organized by structural invariant, not by module list.

At minimum, EVA-Agent v0.6 requires validation for:

- heartbeat-first cadence
- instance legitimacy
- read-only drive ownership
- anchor pre-generative restriction
- mediator-only side effects
- append-only audit discipline
- memory separation
- framework/scenario boundary integrity

### 13.2 Structural validation and long-run validation

Two validation modes are needed:

- **structural validation**: owner boundaries, call boundaries, data-track separation, and invariant-preserving flow
- **long-run validation**: whether those invariants remain intact under sustained runtime pressure and repeated learning cycles

An invariant failure is an architectural distortion, not a minor quality issue.

### 13.3 Observable stability

v0.6 adds an architecture-neutral measurement surface for stability. The exact experiments belong to validation work, but the architecture should support external measurement of at least:

- constraint preservation
- operational continuity
- useful progress under constraint
- recovery success
- recovery predictability
- cost ratio

These metrics are meant to enable comparison without assuming EVA's internal categories.

### 13.4 Comparative stability hypothesis

v0.6 introduces a comparative stability hypothesis: that an existence-centered agent architecture with these structural commitments should exhibit stronger stability behavior than a matched task-centered baseline under relevant conditions.

This is a **falsifiable hypothesis**, not a verified conclusion.

### 13.5 Aligning run-level and individual-level semantics

Stability metrics themselves **do not define existence semantics** — they measure how architectural properties behave under the existence semantics declared by the scenario. Experimental harnesses and metric design must adopt the following reading:

- **One run = one individual living from birth to terminal** (terminal is determined by the scenario's continuity criterion / terminal failure declaration);
- **Multiple runs = statistics over a population**, analogous to per-capita lifespan or group survival rate — not "multiple lives of the same subject";
- **Aggregating metrics across resets does not constitute single-individual survival**: if a scenario declares reset = new individual (as Crafter does), any metric that reads "across resets" as "continuous survival of one agent" is a paradigm error;
- **Whether the inheritance channel is enabled does not alter the three points above**: a new individual receiving priors is not the continuation of the original individual.

The six observable-stability metrics (§13.3) should be reportable in both **per-individual** (within a lifetime) and **population** (aggregated across individuals) dimensions. Mixing the two dimensions without annotation lets "continuous existence" collapse back into task-agent-style throughput metrics.

---

## §14 Deployment Path {#s14}

### 14.1 Single-runtime baseline

The first deployment target should be a single-machine, always-on runtime. The point is not scale first. The point is to stabilize continuity, cadence, state persistence, release, and learning in one long-running agent instance.

### 14.2 Supervisor and host process control

A host-level supervisor may manage process continuity, restart, and resource limits. That does not replace Kernel. Host-level supervision and in-process continuity authority are different layers of responsibility.

### 14.3 Storage and artifact discipline

Persistent storage layout should reflect architectural distinctions rather than collapsing everything into one directory or store.

At minimum, deployments should preserve clear separation among:

- current-state artifacts
- append-only audit artifacts
- episodic memory artifacts
- semantic regularity artifacts
- procedural / habit artifacts
- inherited-prior artifacts
- learning outcome artifacts

### 14.4 Crash recovery

Recovery must restore continuity without violating structural invariants. That requires:

- fast current-state restoration
- immutable historical record
- legitimacy re-establishment before ordinary operation resumes

### 14.5 Scenario selection and activation

Scenario selection is explicit at activation time. The active scenario does not silently change within a runtime.

---

## §15 Evolution Roadmap {#s15}

### 15.1 What v0.6 covers

v0.6 covers:

- a single active agent per runtime
- one active existence field per activation
- active persistence as the governing reading of continuity
- persistence-target hierarchy as a declared architectural surface
- framework/scenario split
- rate-aware sensing with explicit tiers
- four-layer memory
- same-field inherited priors at L3
- multi-dimensional outcome
- observable stability as an external measurement surface

### 15.2 What remains deferred

The following remain deferred or reserved:

- cross-field inherited priors
- L4 self-model deepening
- L5 social cognition deepening
- persistence Levels 5–7 mechanisms
- Type B inherited priors through self-aware cultural transmission
- multi-agent structural commitments
- multi-scenario switching within one runtime

### 15.3 The extension rule

Grow capabilities only after continuity boundaries, release boundaries, and the learning loop are structurally real.

Scenario specification is the default path. Theory extension is the exception.

### 15.4 Evolution guardrails (what not to do)

The following are not permitted inside the v0.6 framework. Violating any of them constitutes a paradigm error and should be rejected at review:

1. **Do not introduce P1 / P2 runtime modes to express existence semantics.** Existence semantics are scenario declarations (§12.7), not runtime mode switches; using configuration toggles to flip continuity meaning degrades structural invariants into engineering preferences.
2. **Do not promote scenario-internal vitals to substrate viability.** Avatar HP / energy / saturation enter L1 dimensions and L2 drive; whether their depletion constitutes terminal failure is declared by the scenario in §12.7, and does not rewrite the meaning of Level 1 substrate.
3. **Kernel cadence must not fork per scenario.** Kernel cadence authority is single; the difference between step-driven and wall-clock rhythms is **contractually** expressed by the scenario declaring `clock_source` (item 8 in §12.7) for the kernel to read — this is the correct way to honor this constraint (today the kernel does not yet consume `clock_source` and runs wall-clock; that consumption is a target item — see tracking). What is forbidden is "adding `if-scenario-is-X` branches inside the kernel scheduler," "rewriting kernel cadence paths for a specific scenario," or letting per-step rate / scenario-side timing config leak into the kernel — not "scenarios declaring their own clock source."
4. **Do not read "process never stopped" or "inheritance happened" as existence continuity of the same individual.** Continuity of the same individual is always anchored in legitimacy + recoverable state + provenance, per §3.8; inheritance is a cross-individual mechanism (§7.9).
5. **Do not hardcode "done → reset extends life" semantics at the framework level.** The terminal path and the new-individual path must be dispatched according to the scenario declaration; any scenario-adapter code that quietly treats terminal as an episode boundary and extends life must go back to §12.7 and redeclare first.

---

## Appendix A. v0.5 Source-Material Reuse Map {#app-a}

| v0.5 source material | Absorbed into v0.6 blueprint | Use in this document |
|---|---|---|
| Engineering goals and invariants | §1 | retained and upgraded |
| Five-layer backbone | §2 | retained and expanded with framework/scenario split |
| Anchor system | §4 | retained and sharpened |
| Kernel / heartbeat / legitimacy | §3 | retained and upgraded with persistence targets |
| L1 sensing skeleton | §5 | retained and upgraded with rate-aware semantics |
| L2 drive skeleton | §6 | retained and upgraded with semantic-memory boundary |
| L3 reasoning / mediator / outcome loop | §7 | retained and upgraded with four-layer memory, inherited priors, vector outcome |
| Runtime artifacts chapter | §10 | replaced with broader data/persistence architecture |
| Runtime closed loop | §11 | retained and upgraded |
| Validation by invariant | §13 | retained and upgraded with observable stability |
| Deployment baseline | §14 | retained and restated as blueprint guidance |

## Appendix B. v0.6 Engineering Upgrade Map {#app-b}

| v0.6 theoretical addition | Blueprint landing |
|---|---|
| Active persistence | §1, §5, §7, §11 |
| Persistence-target hierarchy | §3, §10, §15 |
| Capability provenance and source taxonomy | §1, §7, §10 |
| Structural invariants vs operational content | §1, §4, §6, §7 |
| Rate-aware sensing | §5, §11 |
| Four-layer memory | §7, §10 |
| Inherited priors L3 mechanism (cross-individual) | §7, §11, §15 |
| Multi-dimensional outcome | §7, §13 |
| Observable stability | §13 |
| Scenario specification discipline | §2, §12 |
| Extension discipline | §12, §15 |
| EVA as architecture, not ontology (rev2) | §0, §2.7 |
| Continuous existence ≠ continuous execution (rev2) | §1.2.1, §3.8 |
| Individual as the persisting subject (rev2) | §1.2.2, §7.9, §13.5 |
| Framework mechanisms vs scenario declaration (rev2) | §2.7, §3.7, §3.8, §12.7 |
| Existence Semantics Declaration eight items / declaration vs config (rev2) | §2.7, §12.7 |
| Evolution guardrails (rev2) | §15.4 |
| Architectural contract vs landed status (rev2) | §0.4 |