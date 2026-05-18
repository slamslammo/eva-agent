# EVA-Agent Architecture Implementation Blueprint v0.6

**Status**: prospective engineering blueprint
**Inherits**: v0.5 baseline (`docs/eva-agent-full-implementation-v0.5.md`)
**Scope**: Part I — Framework Architecture (kernel → L1 → L2 → L3 → anchor → runtime loop)
**Companion**: Part II (scenario architecture), Part III (v0.6 new features), Part IV (invariants + validation + deployment)

---

## §1 Introduction: v0.5 Baseline and v0.6 Structural Adjustment

### 1.1 What this document is

This is a **prospective** engineering blueprint: theory → complete engineering design → implementation guidance. It does not describe what is currently implemented — that is tracked in [`docs/implementation-tracking.md`](implementation-tracking.md). It describes what the architecture **should** look like when fully implemented to EVA v0.6 specification.

### 1.2 v0.5 baseline

EVA v0.5 (documented in full in [`docs/eva-agent-full-implementation-v0.5.md`](eva-agent-full-implementation-v0.5.md)) established the existence-centered agent architecture:

- continuous existence as first-order constraint
- heartbeat-first lifecycle (`tick` / `turn`)
- L1 homeostatic sensing, L2 drive as contextual broadcast, L3 adaptive deliberation
- Anchor as pre-generative constraint `G(s) → A'(s) ⊆ A(s)`
- mediator-owned release authority
- default inhibition
- RPE-based learning and habit crystallization
- separated audit, memory, and learning tracks

### 1.3 The v0.6 structural adjustment: framework/scenario split

The core v0.6 change from v0.5 is the **architectural separation of framework and scenario**.

In v0.5, EVA-agent was a monolithic agent architecture. In v0.6, the architecture is split into two distinct ownership zones:

- **Framework** (`eva/`): owns runtime authority and structural invariants. It is scenario-agnostic. It provides the heartbeat loop, sensing contracts, drive broadcast semantics, deliberation structures, anchor mechanism, mediated release, append-only artifacts, and memory layer registries.
- **Scenario** (`scenarios/<name>/`): owns world-specific content. It provides drive families, sensor dimensions, action vocabulary, anchor admission policies, outcome observers, and prior-skill heuristics for a specific embedded world (e.g., Linux shell, Crafter game).

The two zones communicate through a defined seam: the `RuntimeScenarioBundle` contract. The framework reads from the bundle; it never imports scenario-specific modules directly. The scenario provides content; it never mints release authority or rewrites append-only artifacts.

This split is not an organizational convenience. It is a structural commitment: the framework must remain reusable across scenarios, and the scenario must remain subordinate to framework runtime authority.

### 1.4 v0.6 new features beyond the v0.5 baseline

Beyond the framework/scenario split, v0.6 introduces or formalizes:

| Feature | Type | Location in this doc |
|---|---|---|
| Rate sensing with tier metadata (required / recommended / optional) | new mechanism | §4 |
| Four-layer memory (working / episodic / semantic / procedural) | new formalization | §6.1 |
| Semantic memory bounded from L2 drive weights | new constraint | §6.1 |
| Inherited priors L3 mechanism (offline distillation + runtime loading) | new mechanism | §6.6 |
| Exploration as growth driver | deferred design note | §6.7 |
| Anchor three-layer distinction (mechanism / constitutional / emergent overlay) | refined | §7 |
| Comparative Stability Hypothesis | deferred design note | Part III |
| Persistence target Levels 5–7 | deferred | Part III |

### 1.5 Theory source

EVA theory v0.6: [eva-theory repository](https://github.com/slamslammo/eva-theory/blob/main/THEORY/v0.6-integrated.md).

---

## §2 Overall Architecture: Two-Part Structure

### 2.1 Framework + Scenario

```text
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

### 2.2 Dependency direction

```text
L5 Social Layer (reserved)
L4 Self-Model (reserved interfaces)
L3 Deliberation → L2 Drive → L1 Sensing → Kernel
```

Higher layers depend on lower ones. Lower layers must not depend on higher-level reasoning semantics.

### 2.3 Framework boundary rules

| Boundary rule | Meaning |
|---|---|
| Kernel owns cadence | heartbeat must not be displaced by work |
| L2 owns drive state | L3 and above read broadcast only; no rewrites |
| Anchor pre-generates restriction | candidates formed inside `A'(s)`, not filtered after |
| Mediator owns release | reasoning cannot directly trigger execution |
| Audit / memory / learning on separate tracks | no collapse into one store |
| Scenario provides content | scenario must not mint release authority or rewrite append-only artifacts |

### 2.4 Framework/scenario seam: RuntimeScenarioBundle

The seam is defined by `RuntimeScenarioBundle` (in `eva/scenario_bundle.py`). The framework activates exactly one bundle at a time. The bundle provides six surfaces:

1. `drive_preset` — drive types, dimension mapping, default update strategy
2. `sensors` — ordered L1 sensor spec builders
3. `actions` — action names, posture mappings, candidate construction, filtering, selection, execution handlers
4. `anchors` — candidate profile names, schema defaults, admission logic, restriction-reason logic
5. `outcome_observers` — expected-outcome labels, post-action evaluation, learning-content payload
6. `prior_skills` — situation matching, habit bias, inherited prior loading

The framework owns the data structures these surfaces fill. The scenario owns the policies that populate them.

---

## §3 Kernel / Infrastructure

### 3.1 Role

Kernel is the condition for the agent to remain the same continuous instance. It is not "infrastructure as an afterthought." It is the heartbeat-first authority that makes the entire architecture coherent across restarts and contention.

### 3.2 Lifecycle: heartbeat-first loop

Kernel separates the main loop into:

- **`tick`**: fixed-interval life-sign sampling. Refreshes lease, samples runtime state, writes `runtime_state`, appends heartbeat event. `tick` must not be blocked by ordinary work.
- **`turn`**: one bounded work slice between ticks. If a turn runs longer than the tick interval, it does not compress the next tick.

Heartbeat is not "something done when there is time." It is the primary temporal authority.

### 3.3 Instance legitimacy

Long-running agents need explicit instance validity. EVA-agent projects this into a single boolean `instance_valid`, backed by three mechanisms:

- **lock**: OS-level single-holder guarantee
- **generation**: monotonic takeover version
- **lease**: heartbeat-refreshed expiry

All three combine to determine legitimacy. If validity is lost, ordinary turns stop and the system falls back to minimal yield behavior.

### 3.4 Persistence: two non-mixed patterns

- **Atomic current state**: overwrite-in-place for "what am I now?" — `runtime_state`, `drive_state`
- **Append-only history**: immutable event stream for "what has happened?" — `events/`

These two patterns protect both fast recovery and historical fidelity.

### 3.5 Communication semantics

Kernel provides the transport for two distinct communication forms:

- **Event channel**: discrete, past-tense happenings; push semantics; enters append-only events
- **Drive broadcast**: continuous, present-tense state; pull semantics; read by downstream layers as environment

The semantic ownership of `drive_state` and `drive_broadcast` remains in L2. Kernel provides only the transport substrate.

### 3.6 Persistence target hierarchy

Kernel exposes a persistence target contract (`eva/persistence_targets/`) for registering which state artifacts map to which persistence levels:

- Levels 1–4: framework-owned (runtime state, audit, episodic, semantic)
- Levels 5–7: reserved for future (theoretical placeholder; mechanisms reserved for future versions)

---

## §4 L1: Homeostatic Sensing

### 4.1 Role

L1 is where the agent first formally knows: **what state am I in right now?** It detects deviation from viable ranges and routes signals by urgency before deeper interpretation.

### 4.2 Sensor Registry

L1 uses a formal `SensorRegistry` rather than hardcoded metrics. All sensors normalize into a shared `SensorOutput` contract. Scenario provides specific sensor builders; framework owns the registry and collection semantics.

### 4.3 State and rate: two views of every metric

Every meaningful metric has two views:

- **State**: current value
- **Rate**: direction and speed of change

State-only systems react after threshold crossing. State-plus-rate systems can anticipate approach to thresholds.

### 4.4 Rate sensing with tier metadata (v0.6 new)

v0.6 introduces explicit rate-sensing tier metadata on dimension specs. Each declared sensor dimension carries a tier classification:

| Tier | Meaning | Behavior when sensor unavailable |
|---|---|---|
| `required` | agent viability depends on this dimension | fallback to explicit unknown signal; not silently skipped |
| `recommended` | useful for deliberation quality | may degrade gracefully |
| `optional` | enrichment signal | may be omitted without functional impact |

Tier metadata is declared by the scenario's dimension specs and enforced at the sensing layer. This prevents silent degradation in required-tier dimensions and makes graceful degradation explicit rather than implicit.

### 4.5 Signal Bus: three urgency categories

Signals are classified cheaply and early:

- **threat**: urgency signal → fast path → L2 reflex arc
- **status**: normal signal → slow path → L2 drive update → L3 deliberation
- **background**: low-urgency signal → slow path only

### 4.6 Fast / slow path split

Classification becomes structural through two parallel routes:

- **Fast path**: `threat` → L2 reflex arc → mediated release → execution, without L3 deliberation
- **Slow path**: `status` / `background` → L2 drive update → L3 deliberation → mediator → execution

The fast path is narrowly bounded. It does not bypass mediator-owned release authority. It exists only for pre-defined, low-complexity, life-boundary responses.

### 4.7 Boundary

- L1 owns standardized sensing and routing
- L1 does not depend on L3 interpretation
- L2 owns drive updates derived from L1 signals

---

## §5 L2: Drive Layer

### 5.1 Role

If L1 tells the agent what state it is in, L2 determines the **internal environment it is currently immersed in**.

**Drive is not a command. It is a continuous context.**

### 5.2 Drive Registry

Drive is explicitly injected at design time. Scenario provides the concrete drive family and dimension mapping through the bundle's `drive_preset`. Framework owns the `DriveRegistry`, drive-update semantics, and read-only broadcast.

### 5.3 Continuous intensity

Each drive is a continuous value, not a discrete switch. This supports accumulation, decay, and smooth downstream biasing.

### 5.4 Time dynamics

L2 owns drive time dynamics:

- **update** from new L1 signals
- **decay** when relevant stimulation fades
- **recovery** when conditions improve

### 5.5 Drive broadcast: state, not command

L3 does not receive instructions from L2. It reads a drive environment. The same reasoning process produces different candidates under different drive conditions because the environment differs — not because a different command was pushed.

**Rule**: L3 and higher layers read `drive_broadcast` only. L2 is the sole write owner of drive state. No upper layer may rewrite drive state.

### 5.6 Pressure projection

L2 may expose read-side projections (pressure summary, viability gap) for downstream consumption, but these projections must not replace `drive_state` as the L2-owned model.

### 5.7 Reflex arc

L2 also contains a formal fast path for minimal urgent responses (distress persistence, yield, conservative shrink, heartbeat protection). This path bypasses L3 deliberation but remains narrowly bounded and does not bypass mediator release authority.

### 5.8 Semantic memory → L2 drive-weight path

**Constraint (v0.6 new)**: semantic memory must NOT participate in L2 drive weight updates. This boundary preserves the drive read-only invariant. A future safe path evaluation for semantic → L2 drive-weight semantics is deferred (Stage I follow-up #2). Until then, semantic memory participates only in L3 deliberation.

---

## §6 L3: Adaptive Deliberation

### 6.1 Role

L3 is the first layer where the agent acquires a full adaptation-and-learning loop. It is where experience begins to matter beyond original design-time encoding. L3 owns: 4-layer memory, reasoning core, peer circuit / mediator, tool edge, outcome/RPE/habit, and (as v0.6 new) inherited priors.

### 6.2 Four-layer memory (v0.6 new formalization)

v0.6 makes the memory layer explicit with four distinct surfaces, each with a defined role and integration boundary.

#### Working Memory

- **Scope**: within-cycle only; not persisted
- **Role**: assembles current context from `drive_broadcast`, current signals, retrieved episodic hints, retrieved semantic hints, retrieved procedural hints, and (v0.6 new) inherited priors
- **Boundary**: advisory-only. Shaping candidates and reasoning context; no release authority
- **Assembly**: all five retrieval inputs are advisory modifiers, not commands

#### Episodic Memory

- **Storage**: append-only trace (`episodic_memory.jsonl` or equivalent)
- **Role**: salient cross-cycle experience trace; salience weighted by drive state at encoding time
- **Retrieval**: relevance-anchored; contextual similarity + salience weighting
- **Integration**: retrieved episodic hints enter working memory as advisory context
- **Encoding trigger**: post-outcome, shaped by RPE

#### Semantic Memory

- **Storage**: append-only extracted regularity store (`semantic_memory.jsonl` or equivalent)
- **Role**: extracted规律性 from episodes; a higher-order record of stable patterns
- **Integration**: retrieved semantic hints enter working memory as advisory context; may apply a small bounded modifier to candidate value judgment
- **Constraint**: semantic memory participates in L3 deliberation only. It does NOT feed L2 drive weights (preserves drive read-only boundary; see §5.8)
- **Future**: store-side windowing and indexing are deferred (Stage I follow-up #1)
- **Encoding trigger**: episodic-to-semantic extraction (not automatic in v0.6; reserved for future)

#### Procedural Memory

- **Storage**: condition-matched action patterns through habit track substrate (`habit_bias.jsonl`)
- **Role**: stored condition → action mappings that reduce deliberative cost
- **Integration**: `derive_habit_skills()` produces habit-skill summaries; `shape_candidates_with_habit_track()` applies candidate shaping as a shortcut (shorten candidate set, reorder preference)
- **Constraint**: procedural shaping may narrow or reorder candidates, but **must not own release authority** and **must not bypass the mediator gate**
- **Note**: v0.6 procedural memory uses the existing habit-track as its substrate rather than a separate procedural store (see [`docs/eva-framework-implementation.md`](docs/eva-framework-implementation.md) §Stage I Procedural Memory)

#### Memory layer integration summary

| Layer | Owner | Persisted | L3 integration |
|---|---|---|---|
| Working memory | framework | no | direct assembly input |
| Episodic memory | framework | yes | relevance retrieval → working memory |
| Semantic memory | framework | yes | bounded candidate prior modifier → working memory |
| Procedural memory | framework | yes (habit track) | habit shaping → candidate set |

### 6.3 Reasoning Core

The reasoning core is where the LLM sits, but it is **not** the final decision authority. It forms candidates, not actions.

Three functions:

- **Working Memory integration**: assembles current context and retrieved memory hints into deliberation input
- **Value Judgment**: scores candidates under current drive weighting (with bounded learned overlay and inherited prior modifier)
- **Conflict Detection**: detects tension between drives and routes to structural resolution

The output is a ranked candidate set, not an execution order.

### 6.4 Peer Circuit / Basal Ganglia

EVA-agent separates "what seems reasonable" from "what is actually selected." That independent selection authority is the peer circuit.

It is parallel to reasoning, not subordinate to it.

Its role:
- select among candidates
- gate release timing
- carry pathway updates shaped by outcome

It owns candidate selection and default-inhibition timing, but does not itself authorize external side effects.

### 6.5 Mediator and Tool Edge: mediated release

**Mediator** is the independent release authority. No candidate acquires external side effects without mediator approval.

Mediator responsibilities:
- checking current runtime / release conditions
- preserving execution boundary discipline
- ensuring release facts are formally recorded

**Tool Edge** is the only legitimate route by which the agent produces external side effects. It is organized through a framework-owned `ToolRegistry` with explicit side-effect classes.

There are only two execution paths:
1. **mediated path**: ordinary / habitual / deliberative side effects
2. **mediated reflex fast path**: narrow life-boundary responses from L1/L2 fast path

Release token is required. Reasoning cannot directly trigger execution.

### 6.6 Outcome / RPE / Habit

Execution is not the end of the loop.

**Outcome observation**: tool outputs are normalized into structured `OutcomeVector` (canonical multi-dimensional contract). Scenario's outcome observer provides expected-outcome labels and semantic interpretation.

**RPE computation**: reward prediction error compares predicted vs actual outcome. Measures discrepancy / surprise, not generic "goodness." Evaluated relative to predicted vs observed outcome under current drive and continuity context.

**RPE feeds two targets**:
- pathway weighting / selection bias
- memory encoding / habit shaping

**Habit track**: repeated positive outcomes for similar `(situation, action)` patterns may crystallize into habit-skills through `habit_track.py`. These reduce deliberative cost but do not bypass release boundaries.

### 6.7 Inherited Priors L3 Mechanism (v0.6 new)

Inherited priors are a fifth source of capability (alongside: design-time priors, episodic retrieval, semantic hints, procedural/habit shortcuts). They enable same-scenario cross-lifecycle capability reuse.

#### Distillation pipeline (offline)

```
append-only trace files
  → invariance validation (structural invariants preserved)
  → same-scenario regularity extraction
  → DistilledPriorBundle.json (with provenance metadata)
```

The distillation pipeline is implemented in `inheritance_distillation/`. It does not import framework or scenario modules.

#### Runtime loading (online)

```
DistilledPriorBundle.json
  → InheritedPriorRegistry (framework-owned)
  → surfacing in working memory (matched by situation_key)
  → habit track shaping (merged into existing habit-path shaping)
  → value judgment bias (applied as small bounded inherited_prior modifier when prior is sufficiently strong)
```

#### Constraints

- Inherited priors may tune operational expectations; may not redefine what counts as legitimate operation
- Anchors still constrain admission
- Mediator still owns release
- Cross-scenario inherited-prior transmission is **deferred**

#### Provenance

Inherited priors carry source and distillation provenance metadata. This enables future audit and attribution.

---

## §7 Anchor System

### 7.1 Role

Anchor answers: **what candidate domain is even allowed to become visible now.** It acts before candidate generation. It does not own a layer-style cognitive state. It shrinks the action domain before generation.

Anchor is distinct from mediator: Anchor governs what may be generated; mediator governs what may be released.

### 7.2 Formal meaning

`G(s) → A'(s) ⊆ A(s)`

The important point is positional: `A'(s)` is not the leftover after filtering. It is the **only visible domain at generation time**.

Implications:
1. Candidate generators read only the restricted domain
2. Tool registry defines potential capability, not current visible capability
3. Mediator handles release, not domain shrinkage
4. Terminal validation exists only as defense in depth

### 7.3 Capability restriction and parameter-domain restriction

Anchor operates in at least two ways:

1. **Capability restriction**: some capabilities do not enter the current candidate domain at all
2. **Parameter-domain restriction**: even allowed capabilities have bounded target, intensity, rate, and scope

### 7.4 Three-layer distinction (v0.6 refinement)

v0.6 refines anchor into three layers:

| Layer | Stability | Source | Role |
|---|---|---|---|
| **Structural anchors** | stable hard boundaries | continuity constraints, deployment capability, side-effect class, execution boundary, integrity | defines `A(s)` — the outer envelope |
| **Constitutional policies** | semi-stable | scenario-owned admission policies, runtime gate state, instance validity projection | narrows from `A(s)` → `A_mid(s)` |
| **Dynamic / emergent overlays** | transient | recent outcomes, bounded learning feedback, current L1 signals | further narrows to `A'(s)` within envelope |

Dynamic anchors may tighten or reorder the visible domain, but never extend beyond the structural envelope.

### 7.5 Structural vs dynamic anchor implementation

- **Structural anchors**: framework-owned `ActionDomain` construction in `eva/anchor/domain_restriction.py`. Stable domain boundaries.
- **Constitutional policies**: scenario-owned through the bundle's `AnchorPolicyBundle`. Admission logic and restriction-reason vocabulary.
- **Dynamic overlays**: runtime-constructed, transient. Derived from L1 signals, recent outcomes, and bounded learning feedback.

### 7.6 Relation to other layers

- **Kernel**: decides whether the agent may still operate legitimately
- **L1**: reports what is happening
- **L2**: changes tendencies and urgency
- **L3**: reasons only inside `A'(s)`

Anchor is what makes "constraint before generation" structurally real.

---

## §8 Runtime Closed Loop

### 8.1 Loop overview

The runtime loop is the continuous process by which the agent sustains existence, adapts to its environment, and grows from experience.

```
kernel heartbeat (tick / turn)
  → L1 sensing (rate-aware, tier-classified)
  → L2 drive update + broadcast
  → L3 deliberation:
       working-memory assembly (drive + signals + retrieved episodic + retrieved semantic + retrieved procedural + inherited priors)
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
       habit track update (crystallization)
  → next-cycle context
```

### 8.2 Sensing → signal → drive

The loop begins with heartbeat cadence and runtime posture, then proceeds through:
- sensing current internal/external conditions
- normalizing into signals with rate metadata and tier classification
- routing by urgency (threat / status / background)
- absorbing into continuous drive state

External input enters this loop as signal, not as direct command.

### 8.3 Drive → candidate shaping

L3 forms candidates under the joint influence of:
- `drive_broadcast`
- working-memory assembly (current context + 5 retrieval inputs)
- anchor-restricted domain `A'(s)`
- inherited prior bias (when matched situation is strong enough)

Candidate formation is environment-shaped, not task-command planning.

### 8.4 Mediator → release → execution

Candidates remain under default inhibition until explicit release. Peer circuit and mediator determine whether and what may be released. Tool Edge is the only external execution path.

### 8.5 Outcome → memory / RPE / habit

After execution:
- structured outcome observation
- predicted vs actual comparison
- RPE generation
- episodic encoding (salience-weighted by drive state at encoding time)
- semantic storage (bounded; L2-weight path not yet active)
- habit/skill shaping (crystallization when pattern repeats)

Learning is bounded: it may bias future retrieval, candidate preference, or pathway weighting, but may not rewrite runtime continuity, structural anchors, or release authority.

### 8.6 Invariant summary

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
