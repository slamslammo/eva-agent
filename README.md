# eva-agent

<p align="center">
  <a >
    <img src="eva_theory.png" alt="EVA Theory identifier" width="280" />
  </a>
</p>

`eva-agent` is an EVA v0.5-aligned, existence-centered agent architecture experiment.

Instead of starting from a task-first agent and adding more orchestration, the project starts from structural questions: how an agent remains the same running subject, how drive shapes behavior as context, how candidate generation is constrained before release, and how memory and learning stay inside explicit boundaries.

## Public documentation

- [Full implementation architecture](docs/eva-agent-full-implementation.md)
- [Current implementation status](docs/current-status.md) — layer-by-layer capability checklist, remaining gaps, and next-step direction

## Repository structure

- `docs/` — public English documentation
- `docs/assets/architecture/` — architecture diagrams used by the docs
- `eva/` — current Python implementation
- `tests/` — regression and validation coverage

## Current project posture

The repository is an early reference implementation, not a complete EVA system.

It already contains:

- a stable kernel baseline
- an L1 / L2 baseline
- a minimal L3 deliberation skeleton
- a first bounded learning baseline around outcome evaluation, bounded bias, and habit shaping

The project is currently consolidating its public architecture and status documents before deciding the next implementation step.

## Core architectural commitments

- continuous existence as a first-order constraint
- heartbeat-first runtime structure
- separation of `tick` and `turn`
- drive as contextual broadcast, not command
- anchors as pre-generative structural constraints
- reasoning structurally distinct from release
- separated audit, memory, and learning tracks
