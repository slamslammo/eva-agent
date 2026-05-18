# eva-agent

<p align="center">
  <a >
    <img src="eva_theory.png" alt="EVA Theory identifier" width="280" />
  </a>
</p>

`eva-agent` is an EVA v0.5-aligned, existence-centered agent architecture experiment.

Instead of starting from a task-first agent and adding more orchestration, the project starts from structural questions: how an agent remains the same running subject, how drive shapes behavior as context, how candidate generation is constrained before release, and how memory and learning stay inside explicit boundaries.

## Public documentation

- [Documentation entry point](docs/README.md)
- [Current implementation status](docs/current-status.md) — public snapshot of the current runtime posture
- [Capability inventory](docs/capability-inventory.md) — capability tiers, gaps, and deferred items

## Repository structure

- `docs/` — public English documentation
- `docs/assets/architecture/` — architecture diagrams used by the docs
- `eva/` — current Python implementation
- `tests/` — regression and validation coverage

## Current project posture

The repository is still an early reference implementation, not a complete EVA system.

It already contains:

- a stable kernel baseline
- an L1 / L2 baseline
- a bounded L3 deliberation skeleton with learning and habit shaping
- a real but advisory-only Anthropic-backed working-memory path with automatic local fallback
- separated append-only audit, episodic, learning, habit, and LLM-advisory tracks

The current priority is to deepen retrieval/context composition and broaden mediated action vocabulary without weakening the advisory-only and mediator-owned release boundaries.

## Core architectural commitments

- continuous existence as a first-order constraint
- heartbeat-first runtime structure
- separation of `tick` and `turn`
- drive as contextual broadcast, not command
- anchors as pre-generative structural constraints
- reasoning structurally distinct from release
- separated audit, memory, and learning tracks
