# Current Status

## Overview

`eva-agent` already has a meaningful lower-layer backbone, but it is still a partial EVA v0.5 implementation rather than a complete system.

This page reports progress as a **layer-by-layer capability checklist**. It is meant to answer a practical question for external readers: **what is already implemented, what is still missing, and what should come next?**

For the target architecture, see [Full implementation architecture](eva-agent-full-implementation.md).

This page is a public implementation-status view, not the local development roadmap. It shows the current structural state of the repository in externally readable terms.

## How to read this page

- **Current implementation**: what already exists in this repository
- **Target EVA v0.5 state**: what the capability should become in the target architecture
- **Remaining gap**: the main limitation still left in the current repo
- **Gap type**:
  - **Stable baseline**: the basic boundary exists and should be preserved
  - **Tighten**: the capability exists, but its structure or semantics still need to be tightened
  - **Missing piece**: a necessary capability is still largely absent
  - **Misaligned**: a transitional path still carries too much responsibility compared with the target architecture
  - **Deferred**: intentionally reserved for later layers

## Infrastructure / Kernel

| Capability | Current implementation | Target EVA v0.5 state | Remaining gap | Gap type | Next recommended step |
| --- | --- | --- | --- | --- | --- |
| Heartbeat-first lifecycle | Implemented. `tick` and `turn` are separated, and heartbeat deadlines remain ahead of ordinary work. | Must remain the primary runtime rhythm source. | Kernel-critical events are not yet projected into a richer normalized signal surface. | Tighten | Publish kernel-critical events into the L1 signal path without giving L1 control over kernel authority. |
| Instance validity | Implemented. Lock / generation / lease semantics already gate whether the current instance may continue ordinary turns. | Must remain a hard legitimacy boundary for continuous existence. | Validity transitions are not yet exposed as a richer cross-layer observability surface. | Tighten | Make validity transitions easier to inspect in audit and runtime traces. |
| Persistence split | Implemented. Atomic current-state files and append-only history tracks are already separated. | Must remain the standard persistence boundary across the architecture. | More L3 artifacts still need the same level of typed separation and long-horizon traceability. | Tighten | Continue the same split for audit, memory, learning, and future retrieval artifacts. |
| Runtime gate context | Implemented. A minimal `runtime_gate_context` already flows downstream. | Should remain the stable kernel-to-deliberation runtime contract. | The contract is still minimal and not yet a fully articulated gate surface. | Stable baseline | Keep the contract narrow and only refine semantics where downstream structure clearly needs it. |

## L1 Homeostatic Sensing

| Capability | Current implementation | Target EVA v0.5 state | Remaining gap | Gap type | Next recommended step |
| --- | --- | --- | --- | --- | --- |
| State sensing | Implemented. The runtime can already read internal state such as runtime, instance, disk, and recent-event context. | Should remain the extensible L1 sensing input surface. | The current sensing path is still concentrated in centralized sampling logic rather than an explicit sensor system. | Tighten | Introduce a formal **Sensor Registry** with independently registered sensors and standardized outputs. |
| Rate sensing | Implemented at baseline. Delta, direction, and rate-of-change information already influence judgment. | Should support stronger temporal semantics than adjacent-snapshot comparison alone. | Temporal semantics are still thin: little smoothing, windowing, hysteresis, or confidence structure. | Tighten | Add a temporal-evidence structure with window, samples, confidence, and hysteresis semantics. |
| Judgment rule baseline | Implemented. Deterministic rule-based judgment already reads rate context. | Should remain a rule-grounded L1 judgment sublayer. | Judgment exists, but the interface from judgment to routing is still not explicit enough. | Tighten | Keep the rule baseline, but formalize the judgment-to-routing contract. |
| Signal publication contract | Implemented. A normalized envelope already exists around source, class, payload, timestamp, and rate context. | Should remain the standard signal envelope for L1 outputs. | The repository has a publication contract, but not yet a fuller signal bus with stronger downstream routing semantics. | Tighten | Freeze the schema and require all L1 outputs to pass through the same signal envelope. |
| Signal classification | Implemented. Threat / status / background classes already exist. | Should actively drive downstream routing semantics. | Classification is present, but downstream paths do not yet depend on it strongly enough. | Tighten | Make later processing paths explicitly branch on signal class rather than only recording summaries. |
| Routing | Largely absent. Patrol produces a signal batch, but there is not yet a clear fast-path / slow-path routing layer. | Should provide explicit routing semantics for reflex vs deliberative handling. | The system has signals, but not yet a proper routing layer. | Missing piece | Add a minimal routing layer so threat-class signals can trigger reflex handling while lower-urgency signals feed drive update and deliberation. |
| Urgency / preemption semantics | Still mostly implicit in lifecycle and kernel boundaries, not in the signal contract itself. | Should be explicit without breaking heartbeat-first runtime rules. | Urgency is not yet carried as a first-class field in the signal contract. | Missing piece | Add bounded internal fields such as `urgency` or `dispatch_hint` before exposing richer routing behavior. |
| Sensor registry | Not yet implemented. | Should become the extensible registration surface for L1 sensing. | Sensing still depends on centralized logic rather than a composable sensor layer. | Missing piece | Define `SensorSpec`, `SensorOutput`, and a registry mechanism. |
| Kernel ↔ L1 boundary | Mostly correct. Heartbeat, distress, and yield remain kernel-owned, while L1 does not take over those authority boundaries. | Kernel should keep authority while projecting only necessary state into L1. | Kernel-critical events are not yet systematically projected into the L1 signal layer. | Tighten | Normalize kernel-critical events as high-priority L1 signals without letting L1 rewrite kernel life-boundary decisions. |

## L2 Drive Layer

| Capability | Current implementation | Target EVA v0.5 state | Remaining gap | Gap type | Next recommended step |
| --- | --- | --- | --- | --- | --- |
| Continuous drive state | Implemented. Continuous values already exist for survival, integrity, continuity, and curiosity. | This is the correct long-term direction and should remain. | No major architectural problem at the baseline level. | Stable baseline | Preserve the structure and continue semantic refinement rather than redesigning it. |
| Drive update mechanics | Implemented as a rule-based accumulation / decay path, mostly driven by patrol cadence. | Should become signal-driven with patrol-based reconciliation, not patrol-driven alone. | Update timing is still too coarse. | Tighten | Let events and signal arrivals trigger lightweight updates while patrol handles periodic reconciliation. |
| Drive contribution semantics | Partially implemented. Judged dimensions and threat presence already influence drive changes. | Should support clearer per-drive contributors, suppression, recovery, and escalation logic. | Drive semantics are still fairly coarse. | Tighten | Add per-drive contributor policies with clearer baseline, decay, recovery, suppression, and escalation semantics. |
| Drive broadcast | Implemented. A read-only broadcast surface already exists, and downstream layers cannot write drive state directly. | Must remain the standard downstream drive-reading surface. | Downstream still does not treat it as the dominant behavioral context strongly enough. | Tighten | Require downstream reasoning to read through `DriveBroadcast` rather than treating pressure views as the primary context. |
| Drive as context, not command | Structurally true: the broadcast is contextual rather than imperative. | Should become a real shaping force on candidate generation and evaluation. | The downstream path is not yet shaped deeply enough by drive state. | Misaligned | Push drive further into candidate shaping instead of leaving it mostly as background context and logging. |
| Reflex path | Not yet explicit in L2. Fast reaction is still largely carried by lifecycle and compatibility-response paths. | Should include a small, tightly bounded L2 reflex arc. | A core fast-response structure is still missing. | Missing piece | Add an `L2 Reflex Controller` for a very small set of low-complexity protective responses. |
| Downstream consumption | Still transitional. The current execution path remains largely pressure-led, and drive context is still secondary in practice. | Downstream behavior should become drive-native, with pressure retained only as a projection or compatibility view. | The main control meaning still sits too much in pressure rather than drive. | Misaligned | Shift candidate shaping and response selection toward drive-native semantics. |
| Pressure role | Already downgraded conceptually into a compatibility projection, which is the correct direction. | Should remain a projection layer rather than the internal core model. | Code paths still often treat pressure as the main trigger surface. | Misaligned | Continue moving `active_pressures` toward a readable risk view rather than a primary decision owner. |
| Persistence boundary | Implemented. `drive_state.json` is already separate from `runtime_state.json`. | This separation should remain. | No major architectural problem at the baseline level. | Stable baseline | Keep state separation; add history and decay traces only when they materially help reasoning or learning. |
| L2 ↔ L3 boundary | Implemented at the hard-boundary level: L3 and response paths cannot write drive state. | Must remain a hard invariant. | The boundary is present, but L3 is still not yet fully drive-native in its practical behavior. | Tighten | Keep L3 as a consumer of `DriveBroadcast` only, and strengthen drive-native candidate shaping on top of that boundary. |

## Transitional compatibility / execution layer

| Capability | Current implementation | Target EVA v0.5 state | Remaining gap | Gap type | Next recommended step |
| --- | --- | --- | --- | --- | --- |
| Pressure / history projection | Implemented. Pressure and response-history views still exist and are usable. | Should remain available only as compatibility or projection surfaces. | These views still carry too much behavioral weight in some paths. | Misaligned | Keep them readable, but continue shrinking their role as primary decision inputs. |
| Current execution bridge | Implemented. A narrow compatibility bridge still carries actual response execution. | Should remain only a bounded bridge while broader mediated action ownership moves into L3. | The execution surface is still narrower and more transitional than the target architecture. | Missing piece | Build broader mediated action ownership in L3 instead of continuing to grow the compatibility bridge. |

## L3 Deliberation, memory, and learning

| Capability | Current implementation | Target EVA v0.5 state | Remaining gap | Gap type | Next recommended step |
| --- | --- | --- | --- | --- | --- |
| Deliberation package boundary | Implemented. A distinct L3 package and minimal contract set already exist. | Should remain the formal home of deliberation, release, memory, and learning coordination. | The structure exists, but it is still a minimal skeleton rather than a mature cognitive layer. | Stable baseline | Extend capabilities by deepening this package boundary, not by bypassing it. |
| Deliberation input contract | Implemented. `drive_broadcast`, `signal_batch`, and `runtime_gate_context` already form the required upstream contract; working memory is optional. | These should remain the core required upstream surfaces. | Optional enrichment inputs are still narrow. | Stable baseline | Preserve the narrow required contract and keep optional inputs advisory rather than authoritative. |
| Candidate generation | Implemented at a minimal level. The system can generate internal compatibility candidates. | Should produce a broader candidate space shaped by drive, anchor, memory, and learned skill. | The current candidate set is still narrow and compatibility-oriented. | Missing piece | Broaden candidate semantics inside L3 before widening the external action surface. |
| Anchor restriction | Implemented at baseline. Runtime validity and life-boundary constraints already shape the candidate parameter domain. | Should become a fuller pre-generative anchor system. | Current anchors cover only a minimal subset of the full target anchor space. | Tighten | Expand anchor sources and semantics without turning anchors into post-hoc filtering. |
| Value judgment | Implemented at baseline. Drive, signal pressure, and bounded learning already affect scoring and disposition. | Should become a richer but still interpretable judgment layer. | Scoring semantics are still narrow. | Tighten | Improve explicit weighting and conflict handling rather than hiding behavior in opaque heuristics. |
| Mediator / default inhibition | Implemented. Release is withheld by default, and only limited compatibility release is currently allowed. | Must remain an independent release authority with default inhibition. | The release vocabulary and action surface are still narrow. | Stable baseline | Preserve mediator authority while expanding the candidate and release vocabulary around it. |
| Audit vs memory split | Implemented at skeleton level. Deliberation audit and cognitive-memory-stub tracks are already separated. | Should become a fuller separation among audit, episodic memory, semantic memory, and skill tracks. | Cognitive memory is still at stub level. | Missing piece | Add richer retrieval and writing behavior without collapsing audit and memory into one track. |
| Outcome evaluation | Implemented. Expected outcome, observed outcome, delta, and an RPE-like score are already recorded after execution. | Should remain a post-hoc evaluation loop rather than becoming pre-release authority. | The current loop is still tied to a narrow execution bridge. | Stable baseline | Keep evaluation post-hoc and extend it carefully as the action surface broadens. |
| Bounded learning bias | Implemented. Evidence, recency, stability, and confidence gating already bound how learning feeds back into later judgment. | Should remain bounded and never override runtime gates, anchors, or mediator authority. | Current shaping is still tuned around narrow compatibility profiles. | Tighten | Extend read-side learning effects carefully while preserving hard structural gates. |
| Habit crystallization | Implemented at an initial level. Recurrent bias can produce bounded habit skills and limited candidate narrowing under strong evidence. | Should reduce deliberative load without becoming autonomous execution. | Current habit usage is still narrow and context-limited. | Tighten | Broaden skill derivation and observability before considering stronger automatic use. |
| Working-memory interface | Implemented. Local rule-based backends, protocol objects, placeholders, and client-backed shells already exist. | Should remain an optional advisory context layer. | Retrieval and context composition are still limited, and the model-backed path is intentionally not an execution owner. | Stable baseline | Improve advisory retrieval and context composition before considering richer model assistance. |
| Model-assisted advisory path | Implemented only as a bounded advisory seam, not as release authority. | Should remain advisory even when expanded. | There is not yet a real model-backed reasoning path in production use. | Stable baseline | Preserve the advisory-only boundary and only deepen the seam after the rest of the structure is clearer. |
| Tool edge / action surface | Still minimal. Practical execution is still routed through the narrow compatibility path rather than a broader mediated tool edge. | Should become a wider but still mediator-owned external action surface. | The tool edge is still underdeveloped. | Missing piece | Grow a mediated action surface inside L3 instead of enlarging the compatibility path. |
| Full cognitive retrieval | Not yet implemented. | Should provide salience-weighted episodic retrieval and richer cognitive memory use. | The retrieval layer is still missing. | Missing piece | Build retrieval before attempting higher-order self-model or social-layer expansion. |

## Higher layers

| Capability | Current implementation | Target EVA v0.5 state | Remaining gap | Gap type | Next recommended step |
| --- | --- | --- | --- | --- | --- |
| L4 Self-Model | Reserved only. | Should provide higher-order self-model interfaces grounded in stable lower-layer history. | The layer is intentionally not implemented yet. | Deferred | Do not expand L4 until lower-layer behavior, memory, and release history are more stable. |
| L5 Social / External Coordination | Reserved only. | Should provide social and coordination interfaces on top of a stable lower architecture. | The layer is intentionally not implemented yet. | Deferred | Keep L5 deferred until the lower layers are behaviorally and architecturally steadier. |

## Current public development posture

The repository is currently in a consolidation step rather than a feature-race step.

The practical near-term priority is:

1. keep the public target-architecture document and this public status page consistent,
2. preserve the lower-layer structural backbone that already exists,
3. close the missing L1 / L2 / L3 structural pieces before expanding higher-order layers,
4. avoid turning transitional compatibility paths into long-term architecture owners.

In short: the repository already contains a real structural prototype, but the next visible progress should come from tightening the lower-layer architecture and broadening missing core capabilities — not from prematurely expanding L4, L5, or unconstrained model-driven behavior.
