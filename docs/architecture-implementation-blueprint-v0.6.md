# EVA-Agent Architecture Implementation Blueprint v0.6

**Status**: prospective engineering blueprint
**Role**: integrated current baseline for implementation — not "v0.5 + v0.6 patch"
**Inherits**: v0.5 baseline as historical reference (`docs/eva-agent-full-implementation-v0.5.md`), not as required preamble
**Scope**: Part I — Framework Architecture (kernel → L1 → L2 → L3 → anchor → runtime loop)
**Companion**: Part II (scenario architecture), Part III (theoretical placeholders), Part IV (invariants + validation + deployment)

---

## Table of Contents

- [§1 Introduction: the integrated baseline](#s1)
- [§2 Overall architecture: framework + scenario](#s2)
- [§3 Kernel: life-rhythm authority](#s3)
- [§4 L1: homeostatic sensing](#s4)
- [§5 L2: drive layer](#s5)
- [§6 L3: adaptive deliberation](#s6)
- [§7 Anchor: pre-generative constraint](#s7)
- [§8 Runtime closed loop](#s8)

---

## §1 Introduction: the integrated baseline {#s1}

### §1.1 Blueprint nature

This blueprint is the **integrated current baseline for implementation**. It does not describe what v0.5 established then layer on v0.6 additions — it re-states each layer from the ground up as the current state of the EVA architecture after v0.6 structural refinement.

The v0.5 archive (`docs/eva-agent-full-implementation-v0.5.md`) is retained as historical reference. The blueprint body does not depend on it as a prerequisite.

### §1.2 The two things v0.6 does

v0.6 does two structurally distinct things. These are the organizing spine of this entire blueprint.

**1. Framework/scenario split** — structural re-cut. `eva/` holds runtime authority and structural invariants; `scenarios/<name>/` holds world-specific content. The two zones communicate through `RuntimeScenarioBundle`. The framework never imports scenario modules directly. The scenario never mints release authority or rewrites append-only artifacts.

**2. Mechanism refinement embedded along the spine** — not a feature-delta appendix. Rate-sensing tier metadata is embedded in §4 L1. Four-layer memory is embedded in §6 L3. Semantic→L2 constraint is embedded in §5 L2. Inherited priors are embedded in §6 L7. Anchor three-layer distinction is embedded in §7.

The mechanisms are not listed in the introduction and then referenced from the body. They are embedded where they belong.

### §1.3 Theory and code sources

EVA theory v0.6: [eva-theory repository](https://github.com/slamslammo/eva-theory/blob/main/THEORY/v0.6-integrated.md).

Key code paths:
- Kernel: `eva/kernel/main.py`, `eva/kernel/lifecycle.py`, `eva/kernel/instance.py`, `eva/kernel/state.py`
- L1: `eva/l1_sensing/sensor_registry.py`
- L2: `eva/l2_drive/drive_registry.py`
- L3: `eva/l3_deliberation/reasoning/`, `eva/l3_deliberation/peer_circuit/`, `eva/l3_deliberation/memory/`
- Anchor: `eva/anchor/domain_restriction.py`, `eva/anchor/structural.py`, `eva/anchor/dynamic.py`
- Scenario seam: `eva/scenario_bundle.py`
- Inherited priors: `inheritance_distillation/` (independent top-level package)

---

## §2 Overall architecture: framework + scenario {#s2}

### §2.1 Two-layer structure

```
┌─────────────────────────────────────────────────────────┐
│                    SCENARIO LAYER                       │
│  (world-specific content, provided by scenarios/<name>/) │
│  DrivePreset · Sensors · Actions · Anchors ·            │
│  OutcomeObservers · PriorSkillBundle                    │
└──────────────────────────┬──────────────────────────────┘
                           │ RuntimeScenarioBundle seam
┌──────────────────────────▼──────────────────────────────┐
│                   FRAMEWORK LAYER                        │
│  (eva/ — scenario-agnostic runtime authority)           │
│  Kernel · L1 Sensing · L2 Drive · L3 Deliberation ·    │
│  Anchor System · Mediator · Memory Registries           │
└─────────────────────────────────────────────────────────┘
```

The seam is not organizational convenience. It is a structural commitment: the framework must remain reusable across scenarios, and the scenario must remain subordinate to framework runtime authority.

### §2.2 Dependency direction

```
L5 Social Layer (reserved)
L4 Self-Model (reserved interfaces)
L3 Deliberation → L2 Drive → L1 Sensing → Kernel
```

Higher layers depend on lower ones. Lower layers must not depend on higher-level reasoning semantics. `v0.5 §2 / v0.6 §2`

### §2.3 Framework boundary rules

| Boundary rule | Meaning |
|---|---|
| Kernel owns cadence | heartbeat must not be displaced by work |
| L2 owns drive state | L3 and above read broadcast only; no rewrites |
| Anchor pre-generates restriction | candidates formed inside `A'(s)`, not filtered after |
| Mediator owns release | reasoning cannot directly trigger execution |
| Audit / memory / learning on separate tracks | no collapse into one store |
| Scenario provides content | scenario must not mint release authority or rewrite append-only artifacts |

### §2.4 RuntimeScenarioBundle seam

The seam is defined by `RuntimeScenarioBundle` (in `eva/scenario_bundle.py`). The framework activates exactly one bundle at a time. The bundle provides six surfaces:

| Surface | Framework owns | Scenario owns |
|---|---|---|
| `drive_preset` | `DriveRegistry`, drive-update semantics, broadcast | concrete drive family, dimension mapping |
| `sensors` | `SensorRegistry`, normalized `SensorOutput` | sensor builders, dimension specs |
| `actions` | mediated release, execution structure, `ToolRegistry` | action vocabulary, posture, handlers |
| `anchors` | `ActionDomain`, structural/dynamic anchor handling | admission policies, restriction-reason vocabulary |
| `outcome_observers` | learning-record structure, append-only track | outcome semantics, expected-outcome labels |
| `prior_skills` | dataclasses, skill registry, append-only learning track | experience summary, habit derivation, prior content |

The framework owns the data structures these surfaces fill. The scenario owns the policies that populate them.

---

## §3 Kernel: life-rhythm authority {#s3}

### §3.1 Kernel role

Kernel is the condition for the agent to remain the same continuous instance. It is not infrastructure as an afterthought. It is the heartbeat-first authority that makes the entire architecture coherent across restarts and contention.

### §3.2 Heartbeat-first loop

Kernel separates the main loop into two structurally distinct units:

- **`tick`**: fixed-interval life-sign sampling. Refreshes lease, samples runtime state, writes `runtime_state`, appends heartbeat event. `tick` must not be blocked by ordinary work.
- **`turn`**: one bounded work slice between ticks. If a turn runs longer than the tick interval, it does not compress the next tick.

Heartbeat is not "something done when there is time." It is the primary temporal authority. `v0.5 §3.2 / v0.6 §3`

### §3.3 Instance legitimacy

Long-running agents need explicit instance validity. EVA-agent projects this into a single boolean `instance_valid`, backed by three mechanisms:

- **lock**: OS-level single-holder guarantee
- **generation**: monotonic takeover version
- **lease**: heartbeat-refreshed expiry

All three combine to determine legitimacy. If validity is lost, ordinary turns stop and the system falls back to minimal yield behavior.

### §3.4 Two persistence patterns

- **Atomic current state**: overwrite-in-place for "what am I now?" — `runtime_state`, `drive_state`
- **Append-only history**: immutable event stream for "what has happened?" — `events/`

These two patterns protect both fast recovery and historical fidelity. They must not be mixed.

### §3.5 Communication semantics

Kernel provides the transport substrate for two distinct communication forms:

- **Event channel**: discrete, past-tense happenings; push semantics; enters append-only events
- **Drive broadcast**: continuous, present-tense state; pull semantics; read by downstream layers as environment

The semantic ownership of `drive_state` and `drive_broadcast` remains in L2. Kernel provides only the transport substrate.

### §3.6 Persistence target hierarchy

Kernel exposes a persistence target contract (`eva/persistence_targets/`) for registering which state artifacts map to which persistence levels:

- **Levels 1–4**: framework-owned (runtime state, audit, episodic, semantic)
- **Levels 5–7**: reserved for future (theoretical placeholder; mechanisms reserved for future versions)

---

## §4 L1: homeostatic sensing {#s4}

### §4.1 L1 role

L1 is where the agent first formally knows: **what state am I in right now?** It detects deviation from viable ranges and routes signals by urgency before deeper interpretation.

### §4.2 SensorRegistry

L1 uses a formal `SensorRegistry` rather than hardcoded metrics. All sensors normalize into a shared `SensorOutput` contract. The scenario provides specific sensor builders; the framework owns the registry and collection semantics. `v0.5 §4.1 / v0.6 §4`

### §4.3 State and rate: two views of every metric

Every meaningful metric has two views:

- **State**: current value
- **Rate**: direction and speed of change

State-only systems react after threshold crossing. State-plus-rate systems can anticipate approach to thresholds. `v0.5 §4.2 / v0.6 §4`

### §4.4 Rate sensing with tier metadata

v0.6 introduces explicit rate-sensing tier metadata on dimension specs. Each declared sensor dimension carries a tier classification that is declared by the scenario's dimension specs and enforced at the sensing layer:

| Tier | Meaning | Behavior when sensor unavailable |
|---|---|---|
| `required` | agent viability depends on this dimension | fallback to explicit unknown signal; not silently skipped |
| `recommended` | useful for deliberation quality | may degrade gracefully |
| `optional` | enrichment signal | may be omitted without functional impact |

This prevents silent degradation in required-tier dimensions and makes graceful degradation explicit rather than implicit.

### §4.5 Three urgency categories

Signals are classified cheaply and early:

- **threat**: urgency signal → fast path → L2 reflex arc
- **status**: normal signal → slow path → L2 drive update → L3 deliberation
- **background**: low-urgency signal → slow path only

### §4.6 Fast / slow path split

Classification becomes structural through two parallel routes:

- **Fast path**: `threat` → L2 reflex arc → mediated release → execution, without L3 deliberation
- **Slow path**: `status` / `background` → L2 drive update → L3 deliberation → mediator → execution

The fast path is narrowly bounded. It does not bypass mediator-owned release authority. It exists only for pre-defined, low-complexity, life-boundary responses.

### §4.7 L1 boundary

- L1 owns standardized sensing and routing
- L1 does not depend on L3 interpretation
- L2 owns drive updates derived from L1 signals

---

## §5 L2: drive layer {#s5}

### §5.1 L2 role

If L1 tells the agent what state it is in, L2 determines the **internal environment it is currently immersed in**.

**Drive is not a command. It is a continuous context.**

### §5.2 DriveRegistry

Drive is explicitly injected at design time. The scenario provides the concrete drive family and dimension mapping through the bundle's `drive_preset`. The framework owns the `DriveRegistry`, drive-update semantics, and read-only broadcast.

### §5.3 Continuous intensity

Each drive is a continuous value, not a discrete switch. This supports accumulation, decay, and smooth downstream biasing.

### §5.4 Time dynamics

L2 owns drive time dynamics:

- **update** from new L1 signals
- **decay** when relevant stimulation fades
- **recovery** when conditions improve

### §5.5 Drive broadcast: state, not command

L3 does not receive instructions from L2. It reads a drive environment. The same reasoning process produces different candidates under different drive conditions because the environment differs — not because a different command was pushed.

**Rule**: L3 and higher layers read `drive_broadcast` only. L2 is the sole write owner of drive state. No upper layer may rewrite drive state.

### §5.6 Pressure projection

L2 may expose read-side projections (pressure summary, viability gap) for downstream consumption, but these projections must not replace `drive_state` as the L2-owned model.

### §5.7 Reflex arc

L2 also contains a formal fast path for minimal urgent responses (distress persistence, yield, conservative shrink, heartbeat protection). This path bypasses L3 deliberation but remains narrowly bounded and does not bypass mediator release authority.

### §5.8 Semantic memory → L2 drive-weight path constraint

**Constraint**: semantic memory must NOT participate in L2 drive weight updates. This boundary preserves the drive read-only invariant. A future safe-path evaluation for semantic → L2 drive-weight semantics is deferred (Stage I follow-up #2). Until that path is evaluated and enabled, semantic memory participates only in L3 deliberation. `v0.6 §5 new`

---

## §6 L3: adaptive deliberation {#s6}

### §6.1 L3 role

L3 is the first layer where the agent acquires a full adaptation-and-learning loop. It is where experience begins to matter beyond original design-time encoding. L3 owns: four-layer memory, reasoning core, peer circuit / mediator, tool edge, outcome / RPE / habit, and inherited priors.

### §6.2 Four-layer memory

v0.6 makes the memory layer explicit with four distinct surfaces. Each has a defined role and integration boundary.

#### Working memory

- **Scope**: within-cycle only; not persisted
- **Role**: assembles current context from `drive_broadcast` (via `DeliberationInput`), episodic hints, semantic hints, procedural/habit shortcuts, inherited priors, and outcome traces
- **Boundary**: advisory-only. Shapes candidates and reasoning context; no release authority
- **Assembly**: all inputs are advisory modifiers, not commands

#### Episodic memory

- **Storage**: append-only trace (`cognitive_memory_stub.jsonl` / `learning_outcomes.jsonl`)
- **Role**: salient cross-cycle experience trace; salience weighted by drive state at encoding time
- **Retrieval**: relevance-anchored; contextual similarity + salience weighting
- **Integration**: retrieved episodic hints enter working memory as advisory context
- **Encoding trigger**: post-outcome, shaped by RPE

#### Semantic memory

- **Storage**: append-only extracted regularity store (`semantic_memory.jsonl`)
- **Role**: extracted regularities from episodes; a higher-order record of stable patterns
- **Integration**: retrieved semantic hints enter working memory as advisory context; may apply a small bounded modifier to candidate value judgment
- **Constraint**: semantic memory participates in L3 deliberation only. It does NOT feed L2 drive weights (see §5.8)
- **Encoding trigger**: episodic-to-semantic extraction (not automatic in v0.6; reserved for future)

#### Procedural memory

- **Storage**: condition-matched action patterns through the existing habit-track substrate (`habit_bias.jsonl`)
- **Stage I implementation choice**: v0.6 adopts **path (b)** from the startup instruction review — formalize and slightly extend the existing habit path rather than adding a dedicated `procedural_memory.jsonl`. The backing store is `habit_bias.jsonl`; the procedural-memory read surface is `derive_habit_skills()` / `habit_skill_registry()` / `shape_candidates_with_habit_track()`
- **Role**: stored condition → action mappings that reduce deliberative cost
- **Integration**: `derive_habit_skills()` produces habit-skill summaries; `shape_candidates_with_habit_track()` applies candidate shaping as a shortcut (shorten candidate set, reorder preference)
- **Constraint**: procedural shaping may narrow or reorder candidates, but **must not own release authority** and **must not bypass the mediator gate**
- **Blueprint commitment**: the blueprint commits to "procedural memory condition-action patterns must be explicit, bounded, and gate-kept by the mediator" — it does not commit to a standalone `procedural_memory.jsonl` store. `v0.6 §6 new`

#### Memory layer integration summary

| Layer | Owner | Persisted | L3 integration |
|---|---|---|---|
| Working memory | framework | no | direct assembly input |
| Episodic memory | framework | yes | relevance retrieval → working memory |
| Semantic memory | framework | yes | bounded candidate prior modifier → working memory |
| Procedural memory | framework (habit-track backing) | yes | habit shaping → candidate set |

### §6.3 Reasoning core

The reasoning core is where the LLM sits, but it is **not** the final decision authority. It forms candidates, not actions.

Three functions:
- **Working memory integration**: assembles current context and retrieved memory hints into deliberation input
- **Value judgment**: scores candidates under current drive weighting (with bounded learned overlay and inherited prior modifier)
- **Conflict detection**: detects tension between drives and routes to structural resolution

The output is a ranked candidate set, not an execution order.

### §6.4 Peer circuit / basal ganglia

EVA-agent separates "what seems reasonable" from "what is actually selected." That independent selection authority is the peer circuit.

It is parallel to reasoning, not subordinate to it.

Its role: select among candidates, gate release timing, carry pathway updates shaped by outcome. It owns candidate selection and default-inhibition timing, but does not itself authorize external side effects.

### §6.5 Mediator and tool edge: mediated release

**Mediator** is the independent release authority. No candidate acquires external side effects without mediator approval.

Mediator responsibilities: checking current runtime/release conditions, preserving execution boundary discipline, ensuring release facts are formally recorded.

**Tool edge** is the only legitimate route by which the agent produces external side effects. It is organized through a framework-owned `ToolRegistry` with explicit side-effect classes.

There are only two execution paths:
1. **mediated path**: ordinary / habitual / deliberative side effects
2. **mediated reflex fast path**: narrow life-boundary responses from L1/L2 fast path

Release token is required. Reasoning cannot directly trigger execution.

### §6.6 Outcome / RPE / Habit

Execution is not the end of the loop.

**Outcome observation**: tool outputs are normalized into structured `OutcomeVector` (canonical multi-dimensional contract). The scenario's outcome observer provides expected-outcome labels and semantic interpretation.

**RPE computation**: reward prediction error compares predicted vs actual outcome. Measures discrepancy / surprise, not generic "goodness." Evaluated relative to predicted vs observed outcome under current drive and continuity context.

**RPE feeds two targets**: pathway weighting / selection bias, and memory encoding / habit shaping.

**Habit track**: repeated positive outcomes for similar `(situation, action)` patterns may crystallize into habit-skills through `habit_track.py`. These reduce deliberative cost but do not bypass release boundaries.

### §6.7 Inherited priors L3 mechanism

Inherited priors are a **fifth source of capability** (alongside: design-time priors, episodic retrieval, semantic hints, procedural/habit shortcuts). They enable same-scenario cross-lifecycle capability reuse.

#### Distillation pipeline (offline)

```
append-only trace files
  → invariance validation (structural invariants preserved)
  → same-scenario regularity extraction
  → DistilledPriorBundle.json (with provenance metadata)
```

The distillation pipeline is implemented in `inheritance_distillation/`, an **independent top-level package** that does not import framework or scenario modules. This is a deliberate architectural choice: distillation lives outside `eva/` and `scenarios/` to prevent framework or scenario code from accidentally depending on distilled artifacts.

#### Runtime loading (online)

```
DistilledPriorBundle.json
  → InheritedPriorRegistry (framework-owned, loaded via load_inherited_prior_registry())
  → surfacing in working memory (matched by situation_key via InheritedPriorRegistry.for_situation())
  → habit track shaping (merged into existing habit-path shaping)
  → value judgment bias (applied as small bounded inherited_prior_bias when prior is sufficiently strong)
```

#### Current scope: same-scenario only

**Current implementation is same-scenario only.** The `load_inherited_prior_registry()` function enforces scenario matching at bundle load time (line 269: rejects any bundle whose `scenario` field does not match the expected scenario). Cross-scenario inherited prior transmission is explicitly deferred.

This means:
- A `DistilledPriorBundle.json` generated from Linux runtime runs is usable only by future Linux runtime activations
- Crafter inherited priors (if any) are isolated to Crafter
- Cross-scenario prior transfer requires a future Stage evaluation of safety and semantics

#### Provenance

Inherited priors carry source and distillation provenance metadata. This enables future audit and attribution.

#### Constraints

- Inherited priors may tune operational expectations; may not redefine what counts as legitimate operation
- Anchors still constrain admission
- Mediator still owns release
- Cross-scenario transmission is deferred `v0.6 §6 new`

### §6.8 Exploration as growth driver

The design of exploration as an explicit growth driver is not yet complete. This section is a placeholder pointing to the theoretical work in Part III.

---

## §7 Anchor: pre-generative constraint {#s7}

### §7.1 Anchor role

Anchor answers: **what candidate domain is even allowed to be visible now.** It acts before candidate generation. It does not own a layer-style cognitive state. It shrinks the action domain before generation.

Anchor is distinct from mediator: Anchor governs what may be generated; mediator governs what may be released.

### §7.2 Formal meaning

`G(s) → A'(s) ⊆ A(s)`

The critical point is positional: `A'(s)` is not the leftover after filtering. It is the **only visible domain at generation time**.

Implications:
1. Candidate generators read only the restricted domain
2. Tool registry defines potential capability, not current visible capability
3. Mediator handles release, not domain shrinkage
4. Terminal validation exists only as defense in depth

### §7.3 Capability restriction vs parameter-domain restriction

Anchor operates in at least two ways:

1. **Capability restriction**: some capabilities do not enter the current candidate domain at all
2. **Parameter-domain restriction**: even allowed capabilities have bounded target, intensity, rate, and scope

### §7.4 Three-layer distinction

v0.6 refines anchor into three layers by stability and source:

| Layer | Stability | Source | Code implementation |
|---|---|---|---|
| **Structural anchors** | stable hard boundaries | continuity constraints, deployment capability, side-effect class, execution boundary, integrity | `apply_structural_anchor()` in `eva/anchor/structural.py` — framework-owned; defines `A(s)` outer envelope |
| **Constitutional policies** | semi-stable | scenario-owned admission policies, runtime gate state, instance validity projection | `AnchorPolicyBundle.admit_candidates()` — scenario-owned via bundle seam |
| **Dynamic / emergent overlays** | transient | recent outcomes, bounded learning feedback, current L1 signals | `apply_dynamic_anchor()` in `eva/anchor/dynamic.py` + habit-track shaping — framework-owned; narrows from `A(s)` → `A'(s)` within envelope |

The title "three-layer distinction" is retained as the theoretical commitment. The body reflects that the code has two concrete distinct anchor implementations (structural + dynamic) plus a scenario-owned constitutional policy layer through the bundle seam.

Dynamic anchors may tighten or reorder the visible domain, but never extend beyond the structural envelope.

### §7.5 Structural vs dynamic implementation

- **Structural anchors**: framework-owned `ActionDomain` construction in `eva/anchor/domain_restriction.py`. Stable domain boundaries.
- **Constitutional policies**: scenario-owned through the bundle's `AnchorPolicyBundle`. Admission logic and restriction-reason vocabulary.
- **Dynamic overlays**: runtime-constructed, transient. Derived from L1 signals, recent outcomes, and bounded learning feedback.

### §7.6 Relation to other layers

- **Kernel**: decides whether the agent may still operate legitimately
- **L1**: reports what is happening
- **L2**: changes tendencies and urgency
- **L3**: reasons only inside `A'(s)`

Anchor is what makes "constraint before generation" structurally real.

---

## §8 Runtime closed loop {#s8}

### §8.1 Loop overview

The runtime loop is the continuous process by which the agent sustains existence, adapts to its environment, and grows from experience.

```
kernel heartbeat (tick / turn)
  → L1 sensing (rate-aware, tier-classified)
  → L2 drive update + broadcast
  → L3 deliberation:
       working-memory assembly:
         1 × real-time channel (DeliberationInput, containing L1 sensing + L2 drive broadcast)
         + 5 × memory retrievals:
           episodic hint (CognitiveMemoryStub retrieval via recent_cognitive_memory_stub_traces())
           semantic hint (SemanticMemory retrieval via recent_semantic_memory())
           procedural/habit shortcut (HabitSkill + HabitBias summary via derive_habit_skills(), backed by habit_bias.jsonl)
           inherited prior hint (InheritedPriorRegistry.for_situation())
           outcome trace (recent_learning_outcomes(), with two fallback paths: response_history then cognitive_memory_stub traces)
       anchor-restricted candidate formation
       value judgment (drive-weighted + learned overlay + inherited prior bias)
       peer-circuit selection
       mediator release token
  → Tool Edge execution (mediated path OR mediated reflex fast path)
  → Outcome observation (normalized OutcomeVector)
  → RPE computation (surprise = actual − expected)
  → Memory encoding:
       episodic encoding (salience-weighted)
       semantic storage (append-only; L2-weight path deferred)
       habit track update (crystallization when pattern repeats)
  → next-cycle context
```

**Why 6 inputs, not 7**: the DeliberationInput carries both L1 sensing data and L2 drive broadcast in the same channel into working-memory assembly — they arrive together and are consumed together. They are one real-time input. The other five are distinct retrieval operations pulling from persistent stores. Total: 1 + 5 = 6.

### §8.2 Sensing → signal → drive

The loop begins with heartbeat cadence and runtime posture, then proceeds through:
- sensing current internal/external conditions
- normalizing into signals with rate metadata and tier classification
- routing by urgency (threat / status / background)
- absorbing into continuous drive state

External input enters this loop as signal, not as direct command.

### §8.3 Drive → candidate shaping

L3 forms candidates under the joint influence of:
- `drive_broadcast`
- working-memory assembly (current context + six inputs)
- anchor-restricted domain `A'(s)`
- inherited prior bias (when matched situation is strong enough)

Candidate formation is environment-shaped, not task-command planning.

### §8.4 Mediator → release → execution

Candidates remain under default inhibition until explicit release. Peer circuit and mediator determine whether and what may be released. Tool edge is the only external execution path.

### §8.5 Outcome → memory / RPE / habit

After execution:
- structured outcome observation
- predicted vs actual comparison
- RPE generation
- episodic encoding (salience-weighted by drive state at encoding time)
- semantic storage (bounded; L2-weight path not yet active)
- habit/skill shaping (pattern repetition may crystallize)

Learning is bounded: it may bias future retrieval, candidate preference, or pathway weighting, but may not rewrite runtime continuity, structural anchors, or release authority.

### §8.6 Invariant summary

| Invariant | Enforcement |
|---|---|
| heartbeat-first | kernel owns cadence; tick / turn structurally separate |
| L2 read-only broadcast | framework enforces; no L3 rewrite path |
| anchor pre-generative | candidates formed inside `A'(s)` only |
| mediator-owned release | reasoning cannot directly trigger execution |
| default inhibition | resting state is inaction |
| audit / memory / learning separation | distinct data tracks |
| scenario subordinate to framework | RuntimeScenarioBundle seam; scenario owns content, framework owns authority |

---

*Part I of IV. Part II covers scenario architecture, bundle contracts, and framework/scenario boundary enforcement.*