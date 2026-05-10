# Scenario Contract Specification

**Status**: Skeleton draft for v0.6 refactor
**Scope**: The contract every scenario package in `scenarios/` must satisfy
**Companion documents**: `eva-framework-implementation.md` (framework specification), `scenarios/{name}/SPEC.md` (per-scenario specifications)
**Theoretical reference**: EVA v0.6, Chapter 3 (Capability Sources), Chapter 4 (Structural Invariants vs Operational Content), Chapter 8 (Conditions of Generality)

---

## Purpose of this document

This document specifies what a scenario package must provide and what it must not provide. It is the contract between the EVA framework (specified in `eva-framework-implementation.md`) and any specific scenario (Linux runtime, Crafter, future scenarios).

A scenario package is the engineering form of what v0.6 theory calls an *existence field* (chapter 3). It is the configuration that lets EVA's structural mechanisms operate over a particular world. The framework provides the mechanisms; the scenario provides the content the mechanisms operate over.

Two scenario packages with different content but compliant with this contract produce two different EVA agents that share the same structural framework. This is the engineering manifestation of v0.6's commitment that "EVA's universality is structural universality" (chapter 8.3).

This document defines the contract abstractly. Each scenario implements the contract concretely in its own `scenarios/{name}/SPEC.md` and code.

---

## What a scenario package must provide

A scenario package is a self-contained directory under `scenarios/` that supplies the framework with all content needed to instantiate EVA in the scenario's existence field. The required components are:

### 1. Drive preset

A specification of the drive dimensions active in this scenario, including:

- **Drive types** — the named drive dimensions (between 3 and 8 typically; v0.6 does not impose a fixed count)
- **Drive-to-input mapping** — which sensor signals or computed values feed which drive dimensions
- **Drive update policy parameters** — scenario-appropriate values for decay, severity accumulation, threat bonus, suppression, and recovery (the parameter structure is framework-defined; specific values are scenario-defined)
- **Drive impact schemas for actions** — for each registered action, the drive_impact_schema used in value judgment (cold-start defaults; subject to RPE-driven learning per framework rules)

Drive types must be registered through the framework's drive registry interface. They cannot bypass the registry. The drive read-only invariant applies: nothing in the scenario package writes to drives during runtime; drives are computed by L2 framework logic from the scenario's specified inputs.

### 2. Sensor preset

A specification of the L1 sensors active in this scenario, including:

- **Sensor implementations** — concrete sensor classes that produce signals from environment state
- **Signal classifications** — which signals are threat / status / background, and the conditions for each
- **Rate sensing configuration** — what trajectories the sensors track, with what windows
- **Sensor activation conditions** — when each sensor is active (always, conditional on lifecycle state, etc.)

Sensors must be registered through the framework's sensor registry interface. They cannot inject signals through any other path. Sensor implementations may receive inputs from any source (local state, external API, file system, simulator) but the form of the signal entering the framework is specified by the framework's signal schema.

The framework's interface allows sensors to declare a `source_id` for their signals. In v0.6, this defaults to a local identifier; the field exists to support multi-agent and multi-source scenarios in v0.7+ without interface change.

### 3. Action set

A specification of the actions available in this scenario, including:

- **Action implementations** — concrete action handlers that effect changes in the scenario's environment
- **Side-effect class** — for each action, the category of effect (self-runtime, environment-directed, mixed)
- **Anchor applicability declaration** — for each action, the conditions under which it is admissible (referenced by the scenario's anchor policy)
- **Outcome observer** — for each action, a function that interprets the result of execution into the multi-dimensional outcome vector

Actions must be registered through the framework's tool registry interface. The framework enforces that no action executes without a valid ReleaseToken from the mediator. **A scenario cannot register an action that bypasses the mediator, executes outside the tool-edge path, or directly writes to drive or audit state.** This is a hard constraint; violation means the scenario is non-compliant.

### 4. Anchor policy

A specification of the anchor rules active in this scenario, including:

- **L0 anchor rules** — constitutional anchors specific to this scenario (typically inherited from framework defaults; scenario may extend but not weaken)
- **L1 anchor rules** — physiological / lifecycle anchors specific to this scenario
- **Admission gate definitions** — which conditions admit which candidate profiles into ActionDomain
- **Anchor reason vocabulary** — the named reasons that anchor rules reference

Anchor rules are evaluated by framework anchor system. Their structure (pre-generative restriction, ActionDomain composition, admission gates) is framework-defined; their specific content is scenario-defined.

### 5. Outcome observers

For each action registered in the action set, the scenario must provide an outcome observer function. The observer receives:

- The action that was executed
- The pre-action environment state
- The post-action environment state

And produces a multi-dimensional outcome vector consistent with the framework's OutcomeVector schema. Specific outcome dimension values are scenario-determined (a viability delta in Linux scenario means something different from a viability delta in Crafter scenario), but the schema is uniform.

### 6. Prior skills

A specification of the designer-given prior capabilities the agent has at instantiation in this scenario, including:

- **Recognition skills** — abilities to identify entities, threats, resources in the environment
- **Action skills** — abilities to execute basic operations (these reference action set entries)
- **Procedural skills** — sequences and patterns the agent can follow
- **Heuristic skills** — rules of thumb suggesting actions in common situations
- **Domain knowledge** — facts about the environment relevant to decision-making

Each prior skill must include provenance metadata: source (designer | scenario | external | inherited), confidence, scope (situations under which it applies), mutability (whether individual experience can override it).

**Prior skills support candidate generation, prediction, and value judgment. They do not have release authority.** A prior skill may suggest an action be considered, may inform a predicted outcome, may contribute to a candidate's drive_impact_schema. It cannot cause an action to execute. The mediator's release authority is structural and is not delegable to prior skills.

### 7. Persistence target activation

A specification of which levels of the persistence target hierarchy (v0.6 chapter 2) are active in this scenario, including:

- **Active levels** — which of the seven levels apply
- **Failure conditions per level** — what constitutes failure at each active level
- **Inter-level dependency declarations** — how levels depend on each other in this scenario
- **Transfer / successor channel declarations** — whether and how higher-level targets persist past lower-level failures

Single-agent single-life scenarios typically activate Levels 1-4. Multi-agent and multi-life scenarios may activate more. The framework supports all seven; the scenario declares its subset.

### 8. Viability variables

A specification of what counts as viability state for this scenario, including:

- **Variable list** — the values whose maintenance constitutes viability
- **Threshold definitions** — what counts as critical, degraded, healthy levels
- **Variable-to-persistence-level mapping** — which variables relate to which persistence levels

Viability variables are read by L1 sensors and feed L2 drive computation. They are scenario-specific; the framework does not assume any particular set.

---

## What a scenario package must not provide

The following are hard constraints. A scenario that violates any of them is non-compliant and is not eligible to be loaded by the framework.

### No new release authority

Only the mediator can issue ReleaseTokens. A scenario cannot include any code path that produces a ReleaseToken or grants release authority to any other entity. External knowledge sources (LLMs, external advice systems) supplied by the scenario are operational content sources, not release authorities.

### No mediator bypass

All actions must execute through the tool-edge after ReleaseToken validation. A scenario cannot include action implementations that execute outside this path. Scenario code that performs side effects without going through tool-edge (logging, monitoring, debug output) is permitted only if it does not affect the scenario's environment state in ways that influence subsequent agent decisions.

### No audit / memory / learning track modification

A scenario cannot write to or modify any of the framework's append-only tracks. The tracks are append-only by framework enforcement; a scenario that attempts to modify track contents fails this contract.

A scenario may read its own outputs in the tracks (e.g., for outcome observation purposes), but cannot rewrite history.

### No drive write access from scenario L3 components

Drive state is computed by framework L2 logic. A scenario provides drive preset inputs (what feeds drives) but does not implement drive update logic itself. The drive read-only invariant applies to all scenario-supplied components: prior skills, action implementations, outcome observers, all read drive state but do not write it.

### No structural invariant override

The framework's structural invariants (heartbeat-first, instance validity, anchor pre-generative, mediated release, audit append-only, structural identity preservation) are enforced by the framework regardless of scenario content. A scenario cannot disable, weaken, or work around any of them. A scenario that requires conditions an invariant prohibits is incompatible with EVA.

### No new architectural layers

A scenario cannot introduce new layers in the L1-L5 architecture. The framework has fixed layers; scenarios provide content within those layers. If a scenario would require a new layer, this indicates either the scenario should be implemented differently within existing layers, or the framework needs theoretical extension (per v0.6 chapter 8.5 admission criteria), not a scenario-level workaround.

---

## Provenance discipline

All operational content the scenario provides — prior skills, knowledge embedded in heuristics, training-derived patterns — must carry provenance metadata. The framework enforces provenance preservation through the skill registry and outcome tracking; the scenario must populate provenance fields at the point content enters the framework.

**Provenance fields per skill / heuristic / pattern**:

- `source`: one of `designer | scenario | external | inherited` (only `designer | scenario` available in v0.6; `inherited` is reserved for v0.7+)
- `provenance_detail`: human-readable description of where the content came from
- `confidence`: numerical confidence in the content (0.0–1.0)
- `scope`: declaration of conditions under which the content is intended to apply
- `mutable`: whether individual experience can override / refine this content

When scenario-provided content conflicts with individually acquired experience during runtime, the framework's conflict-rich memory rules apply: both are preserved, the conflict is recorded, the agent's subsequent behavior is determined by the standard candidate / value / mediator pipeline. The scenario cannot specify that its content takes precedence over experience; precedence is a runtime decision the framework makes based on confidence, recency, and drive context.

---

## Forward-compatibility provisions

Scenarios in v0.6 operate in a single-agent, single-life, single-existence-field configuration. Future versions will support additional configurations. The contract reserves interface space for these without requiring v0.6 scenarios to use it:

### Multi-agent reservation

The signal schema includes optional `source_id` and `agent_id` fields. v0.6 scenarios populate these with default values (`local`, `self`). v0.7+ multi-agent scenarios will populate them with meaningful values. The framework accepts both modes.

### Multi-life reservation

The skill registry's `source` field includes the value `inherited` even though v0.6 does not implement inherited prior mechanisms. v0.6 scenarios do not use this value. v0.7+ scenarios that participate in cross-life learning will populate prior skills with `source = inherited` and provide the inheritance receipt event chain.

### Persistence levels 5-7 reservation

The PersistenceTarget abstraction supports all seven levels. v0.6 scenarios typically activate Levels 1-4. v0.7+ scenarios that involve reproduction, group structure, or cultural information will activate the higher levels using the same abstraction.

### Time-scale reservation

The framework's cadence_policy and time_source abstractions allow scenarios to specify their own time scales. v0.6 scenarios typically use software-process time scales. Future scenarios with different time scales (millisecond hardware control, day-scale maintenance cycles) populate the cadence_policy differently without changing framework code.

These reservations are interface-level only. v0.6 does not provide implementations for the reserved capabilities. The point is that v0.6 scenarios do not commit the framework to single-agent / single-life / Levels-1-4 / software-time-only configurations in ways that would prevent the future implementations.

---

## What each scenario's `SPEC.md` must contain

Each scenario package's `SPEC.md` is its concrete specification, derived from this contract. It must contain:

- **Scenario identity**: name, intended use, theoretical reference
- **Drive preset specification**: the actual drive types, mappings, parameters
- **Sensor preset specification**: the actual sensors and their behaviors
- **Action set specification**: the actual actions, side-effect classes, applicability
- **Anchor policy specification**: the actual anchor rules
- **Outcome observer specifications**: per-action observer logic
- **Prior skill specifications**: the actual prior skills with provenance
- **Persistence target activations**: which levels are active and how
- **Viability variable specifications**: what counts as viability state
- **Compliance declaration**: explicit confirmation that the scenario satisfies the contract's prohibitions
- **Forward-compatibility declaration**: which forward-compatibility reservations the scenario uses (typically none in v0.6)

A scenario's `SPEC.md` is read by the framework at instantiation time (via the loader), and it is also human-readable as the documentation of what that scenario contains.

---

## Loading and instantiation

The framework provides a scenario loader that:

1. Reads the scenario package's manifest (typically a Python module that imports the scenario's components)
2. Validates that all required components are present
3. Validates that the scenario satisfies the prohibitions (no new release authority, no mediator bypass, etc. — these are checked statically and at runtime where possible)
4. Registers the scenario's drive preset, sensor preset, action set, anchor policy, outcome observers, prior skills, and persistence target activations with the framework
5. Initializes a runtime configured with the scenario's content

The runner (`runners/run_{scenario}.py`) selects the scenario and invokes the loader. There is one runner per scenario; this is intentional — different scenarios may need different startup procedures, deployment configurations, or external dependencies. The runner is the place where scenario-specific deployment concerns live.

---

## Compliance verification

A scenario is verified compliant by:

1. **Static analysis**: importing the scenario package and checking that all required components are present and well-typed
2. **Contract test suite**: running a framework-provided test suite that verifies the prohibitions hold (no test in the suite can succeed in violating an invariant)
3. **Runtime audit**: during operation, the framework's audit indicators (Chapter 14 of `eva-framework-implementation.md`) detect any runtime violations

The verification mechanism is part of the framework, not the scenario. Scenarios are subjects of verification, not authors of their own verification.

---

## Open questions

Items flagged for resolution during refactor:

- Whether scenario configuration should be Python code, declarative (YAML / TOML), or hybrid
- How to test scenario compliance comprehensively without running the full agent
- Whether multiple scenarios can be active in different processes sharing persistent state, or whether each scenario instantiation is fully isolated
- How scenario versioning works (when a scenario evolves, can old data be read? Does the framework declare which scenario versions it supports?)

These are non-blocking for the refactor. They will be resolved as concrete scenarios are implemented.

---

## Status notes

This skeleton defines the contract that scenarios in `scenarios/` must satisfy. It is the companion to `eva-framework-implementation.md`. Together, the two documents define the framework/scenario boundary precisely enough that the v0.6 refactor can proceed.

Specific scenario specifications (`scenarios/linux_runtime/SPEC.md`, `scenarios/crafter/SPEC.md`, etc.) will be written as part of the refactor, deriving from this contract.
