# Architecture Overview

This document is the architecture bird's-eye view for `eva-agent`: what the architecture looks like, how the main modules collaborate, and what the key structural commitments are.

It is not a theory restatement — read [eva-theory](https://github.com/slamslammo/eva-theory) for the theory. It is not a target-state blueprint — read [`architecture-implementation-blueprint-v0.6.md`](architecture-implementation-blueprint-v0.6.md) for the from-scratch architecture to build. It is not an implementation log — read [`eva-framework-implementation.md`](eva-framework-implementation.md) for the current framework surface. This document connects those views by showing the architectural glue: how the pieces fit together and what invariants hold across them.

For scenario-specific content, see [`scenarios-SPEC.md`](scenarios-SPEC.md) and the per-scenario `SPEC.md` files under `scenarios/`.

---

## 1. High-level architecture

### 1.1 Layer structure

EVA-agent implements a five-layer architecture plus a cross-layer constraint system and a kernel base:

```
┌─────────────────────────────────────────────────────────────┐
│  L5  Social Cognition          (reserved for future work)   │
│  L4  Self-Model                (reserved for future work)   │
│  L3  Adaptive Deliberation      reasoning + memory + peer circuit │
│  L2  Drive Layer               drive broadcast + reflex arc  │
│  L1  Homeostatic Sensing       sensor registry + signal bus  │
├─────────────────────────────────────────────────────────────┤
│  Cross-layer: Anchor System     pre-generative constraint    │
│  Base: Kernel                  heartbeat, instance, persistence │
└─────────────────────────────────────────────────────────────┘
```

Each layer addresses a pressure that prior layers cannot absorb:
- **L1** detects threats to viable state (no prior layer can do this)
- **L2** compresses historical regularities into current response bias (L1 is memoryless)
- **L3** enables within-lifetime adaptation when inherited encoding rate is insufficient (L2's encoding rate limit)
- **L4** (future) provides self-prediction from accumulated L3 history
- **L5** (future) represents other agents as such

### 1.2 The framework / scenario split

`eva-agent` implements a framework / scenario boundary:

```
┌─────────────────────────────────────┐
│         Framework (eva/)           │
│  Kernel, L1, L2, L3 structures,    │
│  Anchor mechanism, Mediator,       │
│  Append-only artifacts,            │
│  Memory layer registries,           │
│  Skill provenance registries        │
└──────────────┬──────────────────────┘
               │ RuntimeScenarioBundle
               │ (drive_preset / sensors / actions /
               │  anchors / outcome_observers / prior_skills)
┌──────────────▼──────────────────────┐
│      Scenario Package (scenarios/)  │
│  World-specific content:            │
│  concrete drives, sensors, actions,  │
│  anchor policies, outcome labels,   │
│  prior-skill heuristics             │
└─────────────────────────────────────┘
```

**The framework owns runtime authority and structural invariants.** The scenario owns world-specific content. This is not a soft separation — it is enforced at the code boundary: scenarios may shape candidates and interpretation but may not mint release authority, bypass mediator-owned execution, rewrite append-only history, or take over kernel cadence.

**Why the split exists:** The framework implements the structural properties that make EVA-agent an EVA agent (heartbeat-first, default inhibition, mediated release, append-only tracks). Scenarios implement the world-specific vocabulary the framework operates over. The same framework can carry more than one scenario without the framework's invariants being compromised.

The repository realizes the three-way anchor distinction with two concrete framework-side mechanisms (structural + dynamic) plus the scenario-owned admission policy seam. This is one valid collapse of the v0.6 distinction; the blueprint does not require three separate modules.

### 1.3 Module ownership map

| Module | Owner | Role |
|---|---|---|
| `eva/kernel/` | Framework | Heartbeat loop, instance legitimacy, state persistence |
| `eva/l1_sensing/` | Framework | Sensor registry, rate sensing, signal bus |
| `eva/l2_drive/` | Framework | Drive registry, pressure projection, broadcast |
| `eva/anchor/` | Framework | Domain restriction mechanism |
| `eva/l3_deliberation/peer_circuit/mediator.py` | Framework | Action release authority (default inhibition) |
| `eva/l3_deliberation/peer_circuit/rpe.py` | Framework | RPE learning signal |
| `eva/l3_deliberation/peer_circuit/habit_track.py` | Framework | Habit / skill crystallization |
| `eva/l3_deliberation/memory/` | Framework | Memory layer registries (working / episodic / semantic / procedural) |
| `eva/l3_deliberation/reasoning/` | Framework | Working memory, value judgment |
| `eva/l3_deliberation/tool_edge/` | Framework | Candidate registry, execution path |
| `eva/skills/__init__.py` | Framework | Skill provenance registries, inherited prior loading |
| `scenarios/` | Scenario | World-specific content |
| `runners/` | Runner | Explicit startup assembly per scenario |

---

## 2. The runtime loop

A complete turn follows this flow. "Turn" means one bounded work slice between heartbeat ticks. The kernel owns the tick/turn separation — ordinary work may not block tick.

### 2.1 Flow diagram

```
TICK (kernel)
  └─ refresh lease, sample runtime state, write runtime_state,
      append heartbeat event
  ──────────────────────────────────────────────────────────
  TURN (one bounded work slice)
  │
  ├─ L1: Sensing
  │     sensor registry → normalized SensorOutput
  │     rate sensing (direction + magnitude + acceleration)
  │     signal bus classifies: threat / status / background
  │
  ├─ L2: Drive
  │     signals → drive update (with urgency modulation from rate)
  │     drive broadcast (continuous context, not command)
  │     reflex fast path for threat signals (parallel to deliberation)
  │
  ├─ L3: Deliberation
  │     working memory: current context + retrieved memory
  │     anchor: restricts candidate domain A'(s) ⊆ A(s) before generation
  │     candidates form inside anchor-bounded domain
  │     value judgment scores candidates under drive-weighted context
  │     peer circuit (mediator): default inhibition + selective release
  │     │
  │     (after execution:)
  │     outcome observation → outcome vector
  │     RPE computation (surprise = actual − expected)
  │     memory encoding (salience-weighted episodic)
  │     habit shaping (repeated success → skill crystallization)
  │
  └─ Release
        Mediator-owned release token required for tool-edge execution
        No action reaches the environment without passing through
        the mediator release gate
```

**Whether a turn advances scenario time depends on `clock_source`.** A turn does not always advance scenario time. The kernel reads the active scenario's `clock_source` at construction (the existence-semantics contract, see scenarios-SPEC §7) and accounts for the turn accordingly:

- `wall_clock` (default, e.g. Linux): every turn advances together; the life clock is wall-clock seconds and the kernel keeps `attempt_index == scenario_step_index`.
- `step` (e.g. Crafter): scenario time advances only when the release reaches `env.step(action)`. A turn whose deliberation defers (no valid executable action released) bumps `attempt_index` but leaves `scenario_step_index` unchanged — the next turn re-enters at the **same scenario step** (a retry of that step) rather than a forced advance. The kernel keeps ticking heartbeat throughout; only scenario time pauses, never liveness. A persistent defer streak (default 10) exits to `needs_human_consecutive_deferred` instead of spinning forever.

### 2.2 Critical properties of the loop

**Tick/turn separation is structural.** The kernel owns tick; the turn is one bounded slice. If deliberation blocks tick, the loop is broken — not a performance issue but an architectural violation.

**Drive is context, not command.** L3 reads `drive_broadcast` as an operating environment. The same reasoning process produces different candidates under different drive conditions because the environment differs, not because a different command was pushed. L2 is the only write owner of drive state.

**Anchors operate before generation.** `G(s) → A'(s) ⊆ A(s)` means the candidate domain is restricted before candidates are generated, not after. Actions outside `A'(s)` are not considered, not merely rejected. The reasoning core does not generate candidates outside the anchor-restricted domain.

**Release is mediated.** The mediator (basal ganglia analog) owns action release authority. The resting state is default inhibition. Reasoning generates candidates; the mediator selects and releases. This separation is architectural, not policy-level.

**Learning is bounded.** RPE encodes surprise (deviation from prediction), not raw outcome magnitude. Learning may bias future retrieval, candidate preference, or pathway weighting but may not rewrite structural anchors, release authority, or append-only tracks.

---

## 3. Key structural invariants

These are not recommendations. Violating any of them is an architectural distortion, not a minor quality issue.

### Invariant 1: Default inhibition

The resting action state of the agent is inaction. Every action requires active release of the mediator's inhibition. Reasoning may propose candidates; only the mediator may release them.

Evidence in code: `eva/l3_deliberation/peer_circuit/mediator.py` — `decide_release()` always returns `withhold` unless an allowed assessment is selected. No code path bypasses `decide_release()`.

### Invariant 2: Tick/turn separation

Heartbeat cadence must not be preempted by ordinary deliberation work. The kernel owns `tick`; ordinary work runs in bounded `turn` slices.

Evidence in code: `eva/kernel/lifecycle.py` — the heartbeat loop has bounded turn windows. Any failure of this separation would show as heartbeat gap violations in the runtime artifacts.

### Invariant 3: Drive read-only broadcast

L2 owns `drive_state` writes. All other layers read `drive_broadcast` as context. No component above L2 may write drive state.

Evidence in code: `eva/l2_drive/drive_registry.py` is the only write owner. `eva/l3_deliberation/contracts.py` reads drive broadcast as read-only context.

### Invariant 4: Anchor pre-generative restriction

Candidate generation occurs inside `A'(s)`, not over the full `A(s)` followed by filtering. Post-hoc filtering is a defense-in-depth layer, not the primary constraint mechanism.

Evidence in code: `eva/anchor/domain_restriction.py` constructs `ActionDomain` at anchor time before candidate generation. Candidate generators receive the restricted domain, not the full domain.

### Invariant 5: Append-only artifact discipline

Audit, cognitive, learning, and memory tracks are append-only. Nothing rewrites or truncates these tracks. This protects both historical fidelity and the RPE learning signal's integrity.

Evidence in code: all `*.jsonl` append-only tracks in `stability_metrics/` and `inheritance_distillation/` use append-only write semantics.

### Invariant 6: Framework/scenario boundary

The framework owns runtime authority and structural invariants. Scenarios may shape candidates and provide world-specific vocabulary but may not mint release authority, bypass mediator execution, rewrite append-only tracks, or take over kernel cadence.

Evidence in code: `eva/scenario_bundle.py` defines the integration seam. `eva/l3_deliberation/peer_circuit/mediator.py` is framework-owned. No scenario code can reach execution without passing through the mediator.

### Invariant 7: No cross-scenario state leakage

Retrieval and memory access are scenario-qualified. An agent running in one scenario does not access traces or state from another scenario.

Evidence in code: scenario-specific dimension specs, persistence hierarchies, and skill registries are isolated by scenario bundle activation.

---

## 4. Memory layer architecture (v0.6 §3.5)

EVA-agent implements four memory layers within L3, each with a distinct role:

```
L3 Memory Layers
│
├── Working Memory (in-cycle)
│     Assembly: current sensing + retrieved episodic +
│     retrieved semantic + procedural hints + inherited priors
│     Storage: in-cycle data structures only (not persisted)
│     Owner: `eva/l3_deliberation/reasoning/working_memory.py`
│
├── Episodic Memory (cross-cycle)
│     Content: salient events encoded under high drive activation
│     Storage: `cognitive_memory_stub.jsonl`, `learning_outcomes.jsonl`,
│              bounded response history retrieval
│     Owner: `eva/l3_deliberation/memory/episodic.py`,
│            `eva/l3_deliberation/memory/retrieval.py`
│
├── Semantic Memory (cross-cycle)
│     Content: regularities extracted from episodes
│     Storage: `semantic_memory.jsonl` (first-class append-only track)
│     Owner: `eva/l3_deliberation/memory/semantic.py`
│     Status: store-side windowing / indexing — deferred
│
└── Procedural Memory (cross-cycle)
      Content: condition-matched action patterns
      Storage: `habit_bias.jsonl` via existing habit track
              (no dedicated procedural.jsonl in Stage I)
      Owner: `eva/l3_deliberation/peer_circuit/habit_track.py`,
             `eva/l3_deliberation/memory/skill_library.py`
```

Each layer participates in L3 deliberation through retrieval on relevance. Semantic memory's participation in L2 drive-weight semantics is a deferred follow-up (Stage I follow-up #2), preserved to maintain the drive read-only boundary.

---

## 5. Inherited priors (v0.6 §3.6)

Same-scenario inherited priors allow the agent to access capabilities distilled from previous lives within the same existence field.

**Distillation path** (offline pipeline, runs outside runtime):
```
Append-only trace files
  → `inheritance_distillation/` (top-level package, framework-independent)
  → validates structural invariants
  → extracts same-scenario regularities
  → writes `DistilledPriorBundle.json`
```

**Loading path** (runtime):
```
DistilledPriorBundle.json
  → `eva/skills/__init__.py:load_inherited_prior_registry()`
  → InheritedPriorRegistry
  → working memory: surfaced for exact situation_key match
  → habit track: merged into candidate shaping
  → value judgment: bounded auditable bias when prior is strong
```

**Constraints (v0.6 §3.6.4):**
- Inherited priors may tune operational expectations; they may not redefine what counts as legitimate operation
- Cross-scenario inheritance is not implemented (deferred)
- Provenance is explicit on all skill source records (Stage I)

---

## 6. Mediator and default inhibition

The mediator is the basal ganglia analog's action-release function. It is not a separate layer and not a reasoning sub-module — it is the peer-circuit function of release authority.

**Core functions:**
1. **Default inhibition** — resting state is total action inhibition
2. **RPE as internal learning signal** — surprise = actual − expected; drives pathway weighting
3. **Goal-directed / habit dual track** — novel situations route through deliberation; familiar situations with stable positive RPE route through habit

**Evidence in code:**
`eva/l3_deliberation/peer_circuit/mediator.py` — `decide_release()` applies default inhibition and returns a `ReleaseDecision`. `validate_release_token()` enforces runtime-only release authority before tool-edge execution. No execution path bypasses these functions.

---

## 7. Validation approach

EVA-agent validates by structural invariants, not by module coverage.

| Invariant | Validation method |
|---|---|
| Heartbeat-first | Ordinary work cannot indefinitely block `tick`; `tick`/`turn` are structurally separate |
| Default inhibition | Mediator returns `withhold` unless release is selected; no bypass path exists |
| Drive read-only | `drive_state` and `drive_broadcast` are distinct; L2 is the only write owner |
| Anchor pre-generative | Candidate generators receive `A'(s)`, not full `A(s)` |
| Append-only | No code rewrites or truncates audit/memory/learning tracks |
| Mediator-only release | `validate_release_token()` raises on missing or mismatched token |
| No cross-scenario leakage | Retrieval and memory access are scenario-qualified |

Long-run validation (whether invariants hold under sustained operation, learning accumulation, and scenario switching) is the next empirical layer.

---

## 8. How to read the other docs

This overview connects to the rest of the documentation:

- **`docs/eva-framework-implementation.md`** — detailed framework surface: what each module in `eva/` implements, the current contract seams, and the Stage I memory layer landing
- **`docs/scenarios-SPEC.md`** — the cross-scenario contract: what a scenario must provide to integrate with the framework, and how runner activation works
- **`docs/implementation-tracking.md`** — which theory commitments are currently landed, partial, or deferred
- **`scenarios/linux_runtime/SPEC.md`** — concrete design of the primary reference runtime
- **`scenarios/crafter/SPEC.md`** — concrete design of the bounded validation runtime

For the theory behind these design choices, read the [eva-theory repository](https://github.com/slamslammo/eva-theory) — v0.5 for the core architecture and four engineering contributions, v0.6 for active persistence, rate sensing, memory layering, and inherited priors.

---

## 9. LLM advisory configuration

The working-memory layer can optionally invoke an LLM for bounded advisory generation. Advisory is **never required** for runtime forward progress — the kernel and L3 mediator continue to operate under default inhibition without it.

The framework speaks **OpenAI Chat Completions** to any compatible endpoint (DeepSeek, OpenAI, Moonshot, Qwen via DashScope, Together, Fireworks, Groq, OpenRouter, local Ollama / vLLM / LM Studio). No vendor-specific code path exists; "which vendor" is determined entirely by the configured base URL.

### Enabling live advisory

Pass these CLI flags and set four environment variables:

```bash
python -m runners.run_crafter \
  --working-memory-backend llm_assisted \
  --working-memory-model-client-mode live \
  ...
```

| Variable | Required | Purpose |
|---|---|---|
| `EVA_LLM_API_BASE_URL` | yes | Base URL including `/v1` segment (e.g. `https://api.deepseek.com/v1`) |
| `EVA_LLM_API_KEY` | yes | Bearer token sent as `Authorization: Bearer <key>` |
| `EVA_LLM_MODEL` | yes | Model name passed in request body |
| `EVA_LLM_EXTRA_PARAMS_JSON` | no | JSON object merged into request body; carries vendor-private fields (e.g. DeepSeek `thinking.disabled`) |

Missing or malformed values raise `RuntimeError` at startup; the runtime does not silently fall back, which would mask config errors in long-run scenarios.

### Reference configurations

```bash
# DeepSeek v4-flash, non-thinking mode (recommended for advisory)
export EVA_LLM_API_BASE_URL=https://api.deepseek.com/v1
export EVA_LLM_API_KEY=<your-deepseek-key>
export EVA_LLM_MODEL=deepseek-v4-flash
export EVA_LLM_EXTRA_PARAMS_JSON='{"thinking":{"type":"disabled"}}'

# OpenAI (gpt-4o-mini)
export EVA_LLM_API_BASE_URL=https://api.openai.com/v1
export EVA_LLM_API_KEY=<your-openai-key>
export EVA_LLM_MODEL=gpt-4o-mini

# Local Ollama
export EVA_LLM_API_BASE_URL=http://localhost:11434/v1
export EVA_LLM_API_KEY=ollama
export EVA_LLM_MODEL=qwen2.5:7b
```

### Resilience

The live client retries `HTTP 5xx` and `transport_unavailable` errors three times with exponential backoff (1s, 2s, 4s) before falling back to the bounded local heuristic. `4xx` errors and response-parsing failures fall back immediately. The fallback reason is appended to the advisory's `reasoning_trace` for audit visibility.

### Anthropic Messages API

**Not supported in this round.** Anthropic's native protocol differs (`x-api-key` auth, content block-list format) and would require a per-vendor code path that contradicts the vendor-neutral abstraction. To access Claude models, route through a relay that exposes OpenAI Chat Completions compatibility (OpenRouter, Helicone, Portkey, or similar).