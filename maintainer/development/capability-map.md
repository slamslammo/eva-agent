# Capability Map

This file bridges the **public capability-based status view** and the **local phase-based development materials**.

Use it to keep the following layers aligned:
1. `docs/eva-agent-full-implementation.md` — target architecture
2. `docs/current-status.md` — public capability/status view
3. `maintainer/development/roadmap.md` — local sequencing and gates
4. `maintainer/development/phase-*-progress.md` — local evidence and implementation facts

## Mapping table

| Public area | Capability | Public status anchor | Local evidence | Primary phase owner | Current internal reading |
| --- | --- | --- | --- | --- | --- |
| Infrastructure / Kernel | heartbeat-first lifecycle | `docs/current-status.md` Infrastructure / Kernel | `phase-a-progress.md` | Phase A | Baseline established; keep as hard runtime boundary |
| Infrastructure / Kernel | instance validity | `docs/current-status.md` Infrastructure / Kernel | `phase-a-progress.md` | Phase A | Established and preserved as kernel authority |
| Infrastructure / Kernel | persistence split | `docs/current-status.md` Infrastructure / Kernel | `phase-a-progress.md`, `phase-b-progress.md`, `phase-c-progress.md` | Phase A → B → C | Established and extended across later artifacts |
| Infrastructure / Kernel | runtime gate context | `docs/current-status.md` Infrastructure / Kernel | `phase-a-progress.md`, `phase-b-progress.md` | B0 / Phase B | Frozen as stable upstream contract |
| L1 Homeostatic Sensing | state sensing | `docs/current-status.md` L1 Homeostatic Sensing | `phase-a-progress.md`, `roadmap.md` | Phase A | Baseline established |
| L1 Homeostatic Sensing | rate sensing | `docs/current-status.md` L1 Homeostatic Sensing | `phase-a-progress.md` | Phase A | Baseline established; temporal semantics still thin |
| L1 Homeostatic Sensing | judgment rule baseline | `docs/current-status.md` L1 Homeostatic Sensing | `phase-a-progress.md` | Phase A | Rule baseline established |
| L1 Homeostatic Sensing | signal publication contract | `docs/current-status.md` L1 Homeostatic Sensing | `phase-a-progress.md`, `roadmap.md` | Phase A | Baseline established and should stay frozen |
| L1 Homeostatic Sensing | signal classification | `docs/current-status.md` L1 Homeostatic Sensing | `phase-a-progress.md`, `roadmap.md` | Phase A | Baseline established; downstream routing still weak |
| L1 Homeostatic Sensing | routing / urgency / sensor registry | `docs/current-status.md` L1 Homeostatic Sensing | `roadmap.md` | Future post-alignment work | Still missing; public status correctly shows as gap |
| L2 Drive Layer | continuous drive state | `docs/current-status.md` L2 Drive Layer | `phase-a-progress.md` | Phase A | Baseline established |
| L2 Drive Layer | drive update mechanics | `docs/current-status.md` L2 Drive Layer | `phase-a-progress.md`, `roadmap.md` | Phase A | Baseline established; still patrol-heavy |
| L2 Drive Layer | drive broadcast | `docs/current-status.md` L2 Drive Layer | `phase-a-progress.md`, `phase-b-progress.md` | Phase A / B0 | Frozen as canonical read surface |
| L2 Drive Layer | drive-native downstream shaping | `docs/current-status.md` L2 Drive Layer | `phase-b-progress.md`, `roadmap.md` | Phase B and later | Still incomplete; pressure-led compatibility path remains transitional |
| L2 Drive Layer | reflex path | `docs/current-status.md` L2 Drive Layer | `roadmap.md` | Future post-alignment work | Not yet explicitly established |
| Transitional compatibility / execution layer | pressure/history projection | `docs/current-status.md` Transitional compatibility / execution layer | `phase-a-progress.md`, `phase-b-progress.md`, `phase-c-progress.md` | Transitional across A/B/C | Intentionally retained as compatibility layer |
| Transitional compatibility / execution layer | current execution bridge | `docs/current-status.md` Transitional compatibility / execution layer | `phase-b-progress.md`, `phase-c-progress.md` | Phase B / C | Still the active execution bridge; not future long-term owner |
| L3 Deliberation, memory, and learning | deliberation package boundary | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-b-progress.md` | Phase B | Minimal structural skeleton established |
| L3 Deliberation, memory, and learning | deliberation input contract | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-b-progress.md`, `phase-c-plan.md` | B0 / Phase B / C | Stable required upstream contract preserved |
| L3 Deliberation, memory, and learning | candidate generation / anchors / value judgment / mediator | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-b-progress.md` | Phase B | Minimal baseline established |
| L3 Deliberation, memory, and learning | audit vs memory split | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-b-progress.md` | Phase B | Split established, memory still stub-level |
| L3 Deliberation, memory, and learning | outcome evaluation | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-c-progress.md` | Phase C | Established post-hoc learning loop |
| L3 Deliberation, memory, and learning | bounded learning bias | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-c-progress.md`, `phase-c-plan.md` | Phase C | Established with evidence / recency / stability / confidence gating |
| L3 Deliberation, memory, and learning | habit crystallization | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-c-progress.md`, `phase-c-plan.md` | Phase C | Established in bounded form; still needs broader usage |
| L3 Deliberation, memory, and learning | working-memory interface / advisory model seam | `docs/current-status.md` L3 Deliberation, memory, and learning | `phase-c-progress.md`, `phase-c-plan.md` | Phase C | Baseline established; still advisory-only |
| L3 Deliberation, memory, and learning | tool edge / broader action surface / full retrieval | `docs/current-status.md` L3 Deliberation, memory, and learning | `roadmap.md`, `phase-b-progress.md`, `phase-c-progress.md` | Future post-alignment work | Still incomplete or absent |
| Higher layers | L4 Self-Model | `docs/current-status.md` Higher layers | `roadmap.md` | Deferred | Intentionally reserved |
| Higher layers | L5 Social / External Coordination | `docs/current-status.md` Higher layers | `roadmap.md` | Deferred | Intentionally reserved |

## Maintenance rule

When public status wording changes, update this file if the change affects:
- which local document serves as the main evidence source
- which phase owns the capability
- whether a capability is already implemented, only partially present, or still absent

When a phase progress document changes materially, check whether the related row here and the public wording in `docs/current-status.md` still match.
