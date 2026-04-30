# EVA-agent Full Implementation

## 0. Abstract

### 0.1 From EVA theory v0.5 to EVA-agent

EVA-agent starts from [EVA theory v0.5](https://github.com/slamslammo/eva-theory/blob/main/THEORY/v0.5-integrated.md). Its primary claim is not that an agent should become a better task executor, but that **continuous existence** must come first. A viable agent must first have its own heartbeat, internal drive environment, candidate-generation boundaries, release boundaries, memory, and learning loop. Task handling happens only inside those boundaries.

So the move from theory to implementation is not a translation into feature modules. It is the conversion of structural claims into engineering boundaries: heartbeat-first lifecycle, instance validity, drive as internal context, anchors as pre-generative restriction, reasoning distinct from release, separated audit/memory/learning tracks, and outcome-driven RPE/habit loops.

### 0.2 What EVA-agent is

EVA-agent is not a general-purpose task orchestrator centered on completion. It is an **existence-centered agent architecture** whose first constraint is continuous, bounded, durable operation.

At a high level, EVA-agent consists of:

- an **Infrastructure / Kernel** layer for lifecycle, identity, persistence, and internal buses
- **L1 Homeostatic Sensing**
- **L2 Drive Layer**
- **L3 Adaptive Deliberation**
- reserved interfaces for **L4 Self-Model** and **L5 Social Layer**
- a cross-layer **Anchor System**

### 0.3 What this document explains

This document describes the **full EVA-agent v0.5 implementation architecture**, not the current repository status. It answers four questions:

1. What are the engineering goals and invariants of EVA-agent?
2. How do the five layers, Anchor System, and Infrastructure divide responsibility?
3. How do sensing, drive, deliberation, release, memory, and learning form a continuous loop?
4. How should such a system be validated and deployed?

---

## 1. Engineering Goals and Invariants

### 1.1 Existence-centered engineering goals

EVA-agent is built to establish a subject that:

1. maintains continuous existence,
2. operates inside a persistent internal drive environment,
3. grows reasoning, memory, release, and learning on top of that structure.

Its first constraint is not task completion rate, but whether heartbeat, instance validity, ownership boundaries, candidate boundaries, and side-effect boundaries are structurally real.

### 1.2 Core engineering invariants

These are not recommendations. They are minimum structural conditions.

| Dimension | Typical task agent | EVA-agent invariant |
| --- | --- | --- |
| Default behavior | ready-to-execute | **default inhibition** |
| Motivation | external task drives action | **drive as internal context** |
| Constraint timing | generate then filter | **anchor as pre-generative constraint** |
| Reasoning/execution relation | reasoning proposes and executes | **peer circuit distinct from reasoning** |
| Learning signal | external reward/scoring | **RPE as endogenous learning signal** |
| Skill formation | explicit orchestration | **habit crystallization** |
| Lifecycle priority | task boundary first | **heartbeat-first lifecycle boundary** |
| Memory role | recall support | **memory serves threat recognition and skill formation** |

### 1.3 Why code structure must enforce them

If these invariants live only in prompts or policy text, the system collapses back into a task agent. EVA-agent requires **structure before strategy**:

- heartbeat-first becomes `tick` / `turn` authority
- drive becomes read-only broadcast from L2-owned state
- anchor becomes pre-generative domain restriction
- release becomes an independent mediator path
- memory becomes separated audit / cognitive / learning tracks

---

## 2. Overall Architecture

### 2.1 Five layers, one cross-layer constraint system, one infrastructure base

```text
L5  Social Layer
L4  Self-Model
L3  Adaptive Deliberation
L2  Drive Layer
L1  Homeostatic Sensing
----------------------------------
Cross-layer: Anchor System
Base layer: Infrastructure / Kernel
```

Two points matter immediately:

- **Infrastructure / Kernel is not an implementation detail before L1.** It is the condition for the system to remain the same continuous agent instance.
- **Anchor System is not a sixth layer or a post-hoc safety filter.** It restricts candidate space before generation.

### 2.2 Functional roles by layer

- **Infrastructure / Kernel**: lifecycle arbitration, instance identity/validity, persistence, append-only events, runtime boundary
- **L1**: standardized sensing, state/rate observation, signal publication, threat/status/background routing
- **L2**: continuous drive state, update/decay/recovery, read-only drive broadcast, reflex arc
- **L3**: reasoning, memory, peer-circuit selection, mediated release, tool edge, outcome evaluation, RPE, habit formation
- **L4**: higher-order self-model interfaces
- **L5**: social/coordination interfaces

### 2.3 Dependency direction and boundaries

```text
L5 → L4 → L3 → L2 → L1 → Infrastructure / Kernel
```

Higher layers depend on lower ones. Lower layers must not depend on higher-level reasoning semantics.

This arrow expresses dependency direction, not the runtime closed loop itself; the runtime loop is described separately in Section 11.

Key boundary rules:

- Kernel does not depend on high-level cognition.
- L1 does not depend on L3 interpretation.
- L2 accepts updates from L1, not rewrites from L3.
- L3 is constrained by Anchor and cannot bypass mediator/tool edge.
- Audit trail and cognitive memory are distinct data tracks.

### 2.4 Theory-to-engineering mapping

| Theory claim | Engineering realization |
| --- | --- |
| continuous existence first | Infrastructure / Kernel authority, heartbeat-first, instance validity |
| drive as contextual broadcast | L2 Drive Layer + read-only `drive_broadcast` |
| anchors as pre-generative constraints | Anchor System, restricted domain `A'(s) ⊆ A(s)` |
| release distinct from reasoning | L3 peer circuit / mediator separated from reasoning core |
| immutable audit distinct from memory | append-only events separate from L3 memory |
| reflex and deliberation coexist | L1/L2 fast path alongside L3 slow path |
| learning from outcome discrepancy | outcome evaluation, RPE, habit crystallization |
| higher layers depend on history | L4/L5 depend on L3 memory, release, and outcome history |

---

## 3. Anchor System

### 3.1 Position of Anchor

Anchor answers: **what candidate domain is even allowed to become visible now**.

It acts before candidate generation:

- it does not own a layer-style cognitive state
- it shrinks the action domain before generation
- it is distinct from mediator: Anchor governs what may be generated; mediator governs what may be released

![Anchor System overview](./assets/architecture/anchor_system_overview.svg)

### 3.2 Structural anchors and dynamic anchors

Anchor contains two forms of restriction:

- **Structural anchors**: stable hard boundaries from continuity, deployment capability, side-effect class, execution boundary, and integrity constraints
- **Dynamic anchors**: state-dependent narrowing from runtime gate, instance validity, L1 signals, recent outcomes, and bounded learning feedback

Dynamic anchors may tighten or reorder the visible domain, but never extend beyond the structural envelope.

### 3.3 Capability restriction and parameter-domain restriction

Anchor operates in at least two ways:

1. **Capability restriction**: some capabilities do not enter the current candidate domain at all
2. **Parameter-domain restriction**: even allowed capabilities have bounded target, intensity, rate, and scope

Candidate generation therefore sees bounded action schemas, not open-ended tools.

### 3.4 Formal meaning of `G(s) -> A'(s) ⊆ A(s)`

The important point is positional, not symbolic: `A'(s)` is not the leftover after filtering. It is the **only visible domain at generation time**.

That implies:

1. candidate generators read only the restricted domain
2. tool registry defines potential capability, not current visible capability
3. mediator handles release, not domain shrinkage
4. terminal validation may exist only as defense in depth

### 3.5 Relation to kernel, L1, L2, and L3

- **Kernel** decides whether the agent may still operate legitimately
- **L1** reports what is happening
- **L2** changes tendencies and urgency
- **L3** reasons only inside `A'(s)`

Anchor is what makes “constraint before generation” structurally real.

---

## 4. Infrastructure / Kernel

### 4.1 Why it is outside the five cognitive layers

The five layers describe cognitive and behavioral organization. Infrastructure / Kernel provides the body that allows the same agent instance to continue existing through crashes, restarts, and contention.

![Infrastructure position](./assets/architecture/infrastructure_position_in_eva.svg)

### 4.2 Lifecycle Kernel: the heartbeat-first rhythm source

Lifecycle Kernel exists to guarantee that heartbeat is not displaced by work.

It separates the main loop into:

- **`tick`**: fixed-interval life-sign sampling; refreshes lease, samples runtime state, writes `runtime_state`, appends heartbeat event
- **`turn`**: one bounded work slice between ticks

Heartbeat must not become “something done when there is time.”

![Lifecycle kernel](./assets/architecture/lifecycle_kernel_heartbeat_first.svg)

### 4.3 Instance Identity: am I still the valid me?

Long-running agents need explicit instance legitimacy. EVA-agent projects this into a single boolean `instance_valid`, backed by three mechanisms:

- **lock**: OS-level single-holder guarantee
- **generation**: monotonic takeover version
- **lease**: heartbeat-refreshed expiry

All three combine to determine legitimacy. If validity is lost, ordinary turns stop and the system falls back to minimal yield behavior.

![Instance identity](./assets/architecture/instance_identity_three_mechanisms.svg)

### 4.4 Persistence: two different write modes

Persistence is split into two non-mixed patterns:

- **Atomic current state**: overwrite-in-place with atomic replacement for “what am I now?”
- **Append-only history**: immutable event stream for “what has happened?”

This split protects both fast recovery and historical fidelity.

![Persistence split](./assets/architecture/persistence_two_patterns.svg)

### 4.5 Event Bus: two distinct communication semantics

Infrastructure must provide two separate internal communication forms:

- **Event channel**: discrete, past-tense happenings; push semantics; goes into append-only events
- **Drive broadcast**: continuous, present-tense state; pull semantics; read by downstream layers as environment

Drive must not be delivered as an instruction stream.

More precisely, Infrastructure / Kernel provides the transport, publication, and persistence substrate for these communication forms, while the semantic ownership of `drive_state` and `drive_broadcast` remains in L2.

![Event bus](./assets/architecture/event_bus_two_channels.svg)

### 4.6 What this layer ultimately decides

Infrastructure / Kernel does not reason or learn directly, but it decides whether the rest of the architecture can exist coherently at all.

---

## 5. L1: Homeostatic Sensing

### 5.1 Responsibility boundary

L1 is where the agent first formally knows: **what state am I in right now?**

Its job is to detect deviation from viable ranges and route signals by urgency before deeper interpretation.

![L1 position](./assets/architecture/l1_position_in_eva.svg)

### 5.2 Sensor Registry

L1 uses a formal sensor registry rather than hardcoded metrics. Deployment environments differ; what must be stable is the registration and output contract.

All sensors are normalized into a shared signal shape.

![L1 sensor registry](./assets/architecture/l1_sensor_registry.svg)

### 5.3 State and rate

Every meaningful metric should be seen in two ways:

- **State**: current value
- **Rate**: direction and speed of change

State-only systems react after threshold crossing. State-plus-rate systems can anticipate approach to thresholds.

![L1 state vs rate](./assets/architecture/l1_state_vs_rate.svg)

### 5.4 Signal publication contract

L1 standardizes the input surface before downstream use. A signal contract should stabilize:

- common shape
- ownership boundary
- downstream consumption semantics

Downstream layers should depend on the formal signal surface, not raw sensing details.

### 5.5 Signal Bus

Signals are first classified, then interpreted.

Three categories are sufficient at this stage:

- **threat**
- **status**
- **background**

This classification must be cheap and early.

![L1 signal bus](./assets/architecture/l1_signal_bus_classification.svg)

### 5.6 Fast / slow path split

Classification becomes structural through two parallel routes:

- **Fast path**: threat → L2 reflex arc → execution, without L3
- **Slow path**: status/background → L2 drive update → L3 deliberation → mediator → execution

![L1 fast/slow split](./assets/architecture/l1_fast_slow_path_split.svg)

### 5.7 Relation to kernel and L2

- Kernel owns cadence and runtime validity
- L1 owns standardized sensing and routing
- L2 owns drive updates derived from L1 signals

### 5.8 What this layer ultimately decides

L1 ensures the agent has a formal, reliable answer to what is happening now and which processing path that change belongs to.

---

## 6. L2: Drive Layer

### 6.1 Responsibility boundary

If L1 tells the agent what state it is in, L2 determines the **internal environment it is currently immersed in**.

Drive is not a command. It is a continuous context.

![L2 position](./assets/architecture/l2_position_in_eva.svg)

### 6.2 Drive Registry

Drive is explicitly injected at design time rather than allowed to emerge opaquely. This makes long-term motivational structure inspectable and constrainable.

Default EVA-agent drive families are ordered and bounded rather than improvised at runtime.

![L2 drive registry](./assets/architecture/l2_drive_registry.svg)

### 6.3 Continuous intensity

Each drive is represented as a continuous value, not a discrete pressure switch. This supports accumulation, decay, and smooth downstream biasing.

![L2 continuous intensity](./assets/architecture/l2_continuous_vs_discrete.svg)

### 6.4 Update, decay, and recovery

L2 owns drive time dynamics:

- **update** from new signals
- **decay** when relevant stimulation fades
- **recovery** when conditions improve

Drive must be a persistent internal state, not a temporary inference parameter.

### 6.5 Drive broadcast: state, not command

L3 does not receive instructions from L2. It reads a drive environment. The same reasoning process produces different candidates under different drive conditions because the environment differs, not because a different command was pushed.

Upper layers may read but must not rewrite drive state.

![L2 drive broadcast](./assets/architecture/l2_drive_broadcast_state_not_command.svg)

### 6.6 Reflex arc

L2 also contains a formal fast path for minimal urgent responses:

- distress persistence
- yield
- conservative shrink
- heartbeat protection

This path bypasses L3 but remains narrowly bounded. It exists only for pre-defined, low-complexity, life-boundary responses, and must not expand into a second general execution channel.

![L2 reflex arc](./assets/architecture/l2_reflex_arc_parallel_to_broadcast.svg)

### 6.7 Pressure is projection, not the main model

Pressure, viability-gap, or similar summaries may exist as read-side projections, but must not replace `drive_state` as the L2-owned model.

### 6.8 Relation to L1, L3, and Anchor

- L1 supplies signals
- L2 owns drive updates and broadcast
- L3 reads drive broadcast only
- Anchor still limits the candidate domain regardless of drive intensity

### 6.9 What this layer ultimately decides

L2 is where EVA-agent decisively diverges from task-agent structure: behavior unfolds inside a continuous internal environment rather than from direct task command.

---

## 7. L3: Adaptive Deliberation

### 7.1 Responsibility boundary

L3 is the first layer where the agent acquires a full adaptation-and-learning loop. It is where experience begins to matter beyond original design-time encoding.

![L3 position](./assets/architecture/l3_position_in_eva.svg)

L3 consists of:

- **Memory**
- **Reasoning Core**
- **Peer Circuit / Basal Ganglia**
- **Tool Edge**
- plus the post-execution loop of **Outcome / RPE / Habit**

### 7.2 Memory

L3 memory is the first formal storage of personal experience.

It has at least two distinct stores:

- **Episodic Memory**: salient experiences
- **Skill Library**: crystallized repeated successful patterns

![L3 memory overview](./assets/architecture/l3_memory_overview.svg)

#### 7.2.1 Episodic memory and salience

Memories are not stored equally. Encoding is weighted by current drive state, producing **salience** that affects retention and retrieval priority.

![L3 episodic salience](./assets/architecture/l3_episodic_salience_encoding.svg)

#### 7.2.2 Retrieval

Retrieval depends on both:

- contextual similarity
- salience weighting

This is not simple text recall; it is context-shaped recovery of experience.

#### 7.2.3 Skill Library and crystallization

Repeated positive outcomes for similar `(situation, action)` patterns may crystallize into a lighter-weight habitual track. Such skills reduce deliberative cost but do not bypass release boundaries.

![L3 skill library](./assets/architecture/l3_skill_library_crystallization.svg)

![L3 memory boundary](./assets/architecture/l3_memory_two_stores_boundary.svg)

### 7.3 Reasoning Core

Reasoning Core is where the LLM sits, but it is **not** the final decision authority. It forms candidates, not actions.

It has three functions:

- **Working Memory**: integrates current context and produces candidates/predictions
- **Value Judgment**: scores candidates under current drive weighting
- **Conflict Detection**: detects tension between drives and routes conflict to structural resolution

![L3 reasoning core](./assets/architecture/l3_reasoning_core_overview.svg)

![L3 working memory](./assets/architecture/l3_working_memory_llm_position.svg)

![L3 value judgment](./assets/architecture/l3_value_judgment_drive_weighted.svg)

![L3 conflict detection](./assets/architecture/l3_conflict_detection_routing.svg)

The output is a ranked candidate set, not an execution order.

### 7.4 Peer Circuit / Basal Ganglia

EVA-agent separates “what seems reasonable” from “what is actually selected and released.” That independent selection authority is the peer circuit, biologically analogous to basal ganglia.

It is parallel to reasoning, not subordinate to it.

Its role is to:

- select among candidates
- gate release timing
- carry pathway updates that can be shaped by outcome

It owns candidate selection and default-inhibition timing, but does not itself authorize external side effects.

![L3 basal ganglia](./assets/architecture/l3_basal_ganglia_overview.svg)

### 7.5 Tool Edge and mediated release

Tool Edge is the only legitimate route by which the agent produces external side effects.

Before a tool call, a candidate must pass through a **formal release boundary**. Even a selected candidate still needs mediator approval before execution.

Peer Circuit / Basal Ganglia determines which candidate acquires release intent; mediator determines whether that release intent receives side-effect authorization.

![L3 tool edge](./assets/architecture/l3_tool_edge_position.svg)

Mediator responsibilities include:

- checking current runtime/release conditions
- preserving execution boundary discipline
- ensuring release facts are formally recorded

![L3 mediator](./assets/architecture/l3_mediator_three_functions.svg)

Tool access is organized through a registry with explicit side-effect classes.

![L3 tool registry](./assets/architecture/l3_tool_registry_side_effects.svg)

There are only two paths:

- **mediated path** for ordinary/habitual/deliberative side effects
- **reflex-exempt path** for narrow life-boundary responses already defined by L1/L2

### 7.6 Outcome, RPE, and habit

Execution is not the end of the loop. After release and tool execution, EVA-agent observes outcome, compares it to prediction, updates internal pathways, and may encode the experience into memory or skill trajectories.

#### Outcome observation

Tool outputs are normalized into structured outcomes.

![L3 outcome observation](./assets/architecture/l3_outcome_observation.svg)

#### RPE computation

A reward prediction error compares predicted and actual outcome. It measures discrepancy or surprise, not generic “goodness.” It is evaluated relative to predicted versus observed outcome under the current drive and continuity context, not as a generic reward-maximization score.

![L3 RPE computation](./assets/architecture/l3_rpe_computation.svg)

#### Two update targets

RPE feeds at least two targets:

- pathway weighting / selection bias
- memory and habit-related encoding

![L3 RPE two targets](./assets/architecture/l3_rpe_two_update_targets.svg)

#### Complete learning loop

![L3 complete learning loop](./assets/architecture/l3_complete_learning_loop.svg)

### 7.7 What this layer ultimately decides

L3 is where **thought, memory, selection, release, execution, outcome, and learning** become a formal loop rather than a single planner blob.

![L3 full loop](./assets/architecture/l3_full_collaboration_loop.svg)

---

## 8. L4: Self-Model Interfaces

### 8.1 Responsibility boundary

L4 is not another planner. It is the reserved place where the agent gradually forms a higher-order model of itself:

- capabilities
- costs
- risks
- stable preferences
- vulnerabilities
- long-term behavioral style

### 8.2 What it depends on

L4 depends on long-term products of lower layers, especially L3:

- release history
- outcome history
- episodic/cognitive memory
- skill/habit traces
- long-term relations between drive and behavior

It models **this agent's own history**, not abstract world knowledge.

### 8.3 What it must not override

L4 must not invade lower-layer authority:

- not kernel cadence or validity
- not L1 sensing facts
- not L2 drive ownership
- not L3 release authority
- not Anchor envelope

### 8.4 Reserved interfaces

At this stage, L4 is best defined by contract rather than by a finalized internal implementation.

| Dimension | L4 should carry | L4 should not carry |
| --- | --- | --- |
| Inputs | release/outcome aggregates, memory summaries, habit traces, long-term self-patterns | raw signals, raw drive slots, task commands |
| Outputs | self-model context, capability/cost/risk estimates, interpretive summaries | release commands, tool calls, drive overwrites |
| Feedback mode | bounded advisory surface | direct execution authority |

### 8.5 Why internal detail remains reserved

L4's position is structurally established, but detailed owner design should wait until lower-layer memory/learning semantics are stable enough to support it.

---

## 9. L5: Social Layer Boundaries

### 9.1 Responsibility boundary

L5 is where the agent begins to include **other-as-other** in its world model. This is not generic networking or a feature list for multi-agent integration. It is the reserved place for relation-bearing entities and coordination semantics.

Relevant object types include:

- conspecific-like entities
- human collaborators/constraints
- other agents or external systems that become relation-bearing rather than merely instrumental
- persistent coordination structures

### 9.2 Relation to L4, L3, and external systems

- **L4** provides self-model context needed for stable social positioning
- **L3** still owns candidate formation, release, execution, and learning
- **External systems** are not automatically social objects; some remain tools or environment inputs

### 9.3 Boundary distinctions

L5 should preserve distinctions among:

- **conspecifics**
- **humans**
- **other agents / external systems**

Not all “others” belong to one interaction category.

### 9.4 Reserved interfaces

Like L4, L5 is currently best defined by contract.

| Dimension | L5 should carry | L5 should not carry |
| --- | --- | --- |
| Inputs | self-model context, long-term relation history, coordination summaries, social context state | raw tool output, raw signals, unaggregated event floods |
| Outputs | relationship context, coordination context, responsibility/boundary/expectation estimates | direct release, direct tool calls, lower-layer state rewrites |
| Feedback mode | bounded advisory social surface | side-effect authority bypass |

### 9.5 Why internal detail remains reserved

L5 depends on stable L4/L3 history and should not be prematurely expanded into a generic multi-agent control center.

---

## 10. Runtime Artifacts and State Objects

### 10.1 `runtime_state`

`runtime_state` is the minimal current-state object for the agent's ongoing operating posture. It should include at least:

- heartbeat/cadence posture
- instance validity projection
- turn permissibility
- life-state / conservative posture
- other minimum runtime-boundary facts

It is not a catch-all state bag.

### 10.2 `drive_state`

`drive_state` is L2's main state object:

- current drive intensities
- trends
- update/decay/recovery results
- stable internal environment surface

It is distinct from `drive_broadcast`, which is the canonical read surface exposed downstream.

### 10.3 `external_life_snapshot`

This is a stable cross-layer snapshot of external life-relevant conditions. It is not the same thing as raw L1 signals; it is a more persistent current projection of external viability context.

### 10.4 `events`

`events` represent append-only historical fact:

- lifecycle events
- key transitions
- release facts
- execution outcomes
- replay/audit-relevant discrete happenings

They are not cognitive memory.

### 10.5 Candidate, release, and learning artifacts

Beyond core state and events, the runtime needs artifacts for the L3 loop.

- **Candidate artifacts**: suggestions, prediction hints, conflict exposures, local reasoning traces
- **Release artifacts**: release decisions, release logs, execution-edge metadata, side-effect metadata
- **Learning artifacts**: episodic items, salience encodings, skill summaries, learning/habit traces

### 10.6 Data-layer distinctions

EVA-agent should maintain at least four distinct tracks:

1. **Main state**: current owned state such as `runtime_state`, `drive_state`, `external_life_snapshot`
2. **Projection surfaces**: read-side views such as `drive_broadcast` or pressure summaries
3. **Audit/event stream**: append-only historical facts
4. **Cognitive/learning artifacts**: episodic items, skill traces, learning outputs

These tracks must not be collapsed into one.

---

## 11. Runtime Closed Loop

### 11.1 Sensing → signal → drive

The loop begins with heartbeat cadence and runtime posture, then proceeds through:

- sensing current internal/external conditions
- normalizing them into signals
- routing by urgency
- absorbing them into continuous drive state

Signals shape internal environment before anything becomes action.

External task input also enters this loop as signal, not as direct command.

### 11.2 Drive → candidate shaping

L3 forms candidates under the joint influence of:

- `drive_broadcast`
- runtime gate context
- current signals
- retrieved memory
- Anchor-restricted domain

Candidate formation is environment-shaped, not task-command planning.

### 11.3 Mediator → release → execution

Candidates remain under default inhibition until explicit release occurs. Peer circuit and mediator determine whether and what may be released, and Tool Edge is the only external execution path.

### 11.4 Outcome → memory / RPE / habit

After execution, the loop continues through:

- structured outcome observation
- expected vs actual comparison
- RPE generation
- memory encoding
- habit/skill shaping

Learning is **bounded**. It may bias future retrieval, candidate preference, or pathway weighting, but may not rewrite runtime continuity, structural anchors, or release authority.

### 11.5 Full loop

```text
heartbeat / runtime posture
-> sensing
-> signal routing
-> drive update
-> candidate shaping
-> peer-circuit selection
-> mediated release
-> tool-edge execution
-> outcome evaluation
-> memory / RPE / habit
-> next-cycle context
```

This is what makes EVA-agent continuously existent in more than just process uptime.

---

## 12. Validation and Invariant Tests

Validation should be organized by invariants, not by arbitrary module lists.

### 12.1 Heartbeat-first

Tests should verify:

- ordinary work cannot indefinitely block `tick`
- `tick` / `turn` are structurally separate
- heartbeat cadence survives high load, long deliberation, or long tool execution
- life-boundary tightening shrinks ordinary work first

### 12.2 Instance validity

Tests should verify:

- lock, generation, and lease are all real and independently meaningful
- invalid instances stop ordinary release
- downstream code reads legitimacy projection rather than self-declaring validity

### 12.3 Read-only drive

Tests should verify:

- `drive_state` and `drive_broadcast` are distinct
- L2 is the only write owner of drive
- L3 and higher layers can only read broadcast surfaces
- compatibility or higher layers cannot rewrite L2 state

### 12.4 Anchor pre-generative restriction

Tests should verify:

- candidate generators receive `A'(s)`, not full `A(s)`
- capability and parameter restrictions take effect before generation
- post-hoc deny logic is not the primary constraint mechanism
- reflex paths remain narrow rather than becoming privilege bypasses

### 12.5 Mediator-only side effects

Tests should verify:

- reasoning cannot directly trigger external execution
- mediator is the real release gate
- Tool Edge is the only legal side-effect boundary
- no helper, script, or compatibility path bypasses mediator

### 12.6 Audit / memory separation

Tests should verify:

- audit remains append-only
- cognitive memory is not a raw copy of audit
- retrieval reads memory substrate rather than audit-as-database
- learning/habit artifacts remain distinct from both main state and audit

### 12.7 Structural validation and long-run validation

Two kinds of validation are required:

- **Structural validation**: owner boundaries, call boundaries, I/O surfaces, data-track separation
- **Long-run validation**: whether those boundaries remain intact over time under real runtime pressure and learning accumulation

Invariant failure should be treated as **architectural distortion**, not as a minor quality issue.

---

## 13. Deployment and Implementation Shape

### 13.1 Single-machine always-on baseline

The first deployment baseline should be a **single-machine, long-running agent service**.

The initial goal is not distributed scale. It is to stabilize:

- continuous existence
- sustained cadence
- state/event writeback
- release/outcome/memory/habit accumulation in one agent instance

### 13.2 Supervisor / systemd

A host-level process supervisor such as `systemd` should manage service continuity. This does not replace Lifecycle Kernel.

- **Supervisor/systemd**: host-level process persistence
- **Lifecycle Kernel**: in-process heartbeat-first continuity

These are different layers of continuity.

### 13.3 Runtime directory and artifact conventions

A long-running agent needs explicit artifact separation at the filesystem/runtime level. At minimum, it should distinguish:

- main state artifacts
- append-only audit/event artifacts
- cognitive/episodic memory artifacts
- learning/habit artifacts
- compatibility projections
- runtime/process support artifacts

Artifact boundaries should reflect architecture boundaries, not the other way around.

### 13.4 Deployment path from reference implementation

A reasonable implementation path is:

1. **Reference implementation**: prove heartbeat-first, validity, L1/L2/L3 boundaries, mediated side-effect path
2. **Stable continuous runtime baseline**: prove long-running single-instance persistence and closed-loop accumulation
3. **Higher-layer expansion**: only then expand L4/L5 on top of stable lower-layer structure

Deployment evolution should follow the same principle as the architecture: continuity and boundaries first, capabilities second.

---

## 14. Conclusion

### 14.1 EVA-agent as an engineering instance of EVA v0.5

EVA-agent matters because it does not start from an existing task-agent framework and then add safety, memory, and tools around it. It starts by structurally inverting the usual order:

- continuous existence before task handling
- drive before command
- Anchor before candidate generation
- release boundary distinct from reasoning
- audit, memory, and learning on separate tracks
- habit as a product of outcome feedback rather than only explicit programming

It turns EVA v0.5 from theory into module boundaries, state boundaries, persistence boundaries, execution boundaries, and deployment boundaries.

### 14.2 What problems it addresses

EVA-agent is meant to address several structural failures of default task-agent design:

- task priority overriding life boundary
- external tasks masquerading as internal motivation
- generate-then-filter action structures
- reasoning and release collapsed into one path
- logs, memory, and learning blended together

In place of that, it proposes a continuous, bounded, self-shaping agent architecture.

### 14.3 Future evolution

Future work should proceed along the established structural spine:

- continue stabilizing the L1/L2/L3 closed loop
- refine bounded learning, drive dynamics, and memory/habit separation
- gradually realize L4 without violating lower-layer authority
- gradually realize L5 without reducing it to a generic multi-agent feature list
- evolve from reference implementation toward richer always-on deployments without breaking the established invariants

The core rule remains the same: **grow capabilities only after the subject structure, continuity boundaries, and learning loop are already real**.
