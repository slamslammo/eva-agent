# EVA-Agent

**EVA v0.5-aligned, existence-centered agent architecture experiment.**

Instead of starting from a task-first agent and adding more orchestration, EVA-agent starts from structural questions: how an agent remains the same running subject, how drive shapes behavior as context, how candidate generation is constrained before release, and how memory and learning stay inside explicit boundaries.

The architecture is grounded in [EVA theory v0.5](https://github.com/slamslammo/eva-theory) and its v0.6 extension. Read the theory for the full motivation and derivations. Read this repository for what is currently implemented and how.

## Current status

The repository presents a framework-separated EVA runtime with one primary reference runtime and one bounded validation runtime.

- **Linux runtime** — primary shipped reference runtime
- **Crafter** — bounded end-to-end second scenario used to validate the cross-scenario framework seam
- **Recent milestone**: Stage I engineering closeout associated with EVA v0.6 unified release. Framework/scenario split is now stable.

The current priority is deepening memory composition and broadening mediated action vocabulary without weakening the advisory-only and mediator-owned release boundaries.

## Where to start

Start here based on what you need to understand:

**If you want the target architecture to build from scratch**
→ [`docs/architecture-implementation-blueprint-v0.6.md`](docs/architecture-implementation-blueprint-v0.6.md)

**If you want the overall architecture at a glance**
→ [`docs/architecture-overview.md`](docs/architecture-overview.md)

**If you want to understand what the framework implements**
→ [`docs/eva-framework-implementation.md`](docs/eva-framework-implementation.md)

**If you want to understand how scenarios connect to the framework**
→ [`docs/scenarios-SPEC.md`](docs/scenarios-SPEC.md)
→ Specific scenario docs: [`scenarios/linux_runtime/SPEC.md`](scenarios/linux_runtime/SPEC.md), [`scenarios/crafter/SPEC.md`](scenarios/crafter/SPEC.md)

**If you want to check which commitments are landed and which are not**
→ [`docs/implementation-tracking.md`](docs/implementation-tracking.md)

**If you want to read the theory**
→ [eva-theory repository](https://github.com/slamslammo/eva-theory)

**Chinese version / 中文版**
→ [`README-zh.md`](README-zh.md)

## Repository structure

```
eva-agent/
├── README.md                   ← this file: public entry point, English
├── README-zh.md                ← 中文入口
│
├── docs/                       ← public English documentation
│   ├── architecture-overview.md          ← architecture bird's-eye view
│   ├── eva-framework-implementation.md   ← what the framework implements
│   ├── scenarios-SPEC.md               ← cross-scenario contract
│   ├── implementation-tracking.md       ← theory → implementation status
│   └── archive/                        ← historical reference material
│
├── eva/                       ← Python framework implementation
├── scenarios/                  ← scenario packages (each with its own SPEC.md)
│   ├── linux_runtime/
│   └── crafter/
├── runners/                    ← explicit startup paths per scenario
├── tests/
├── stability_metrics/           ← architecture-neutral stability measurement
├── inheritance_distillation/    ← same-scenario prior distillation pipeline
└── maintainer/                 ← internal engineering records (not public)
```

## Core architectural commitments

These are the structural properties that EVA-agent implements, not recommendations:

- continuous existence as a first-order constraint
- heartbeat-first runtime structure, with bounded `tick` / `turn` separation
- drive as contextual broadcast, not command
- anchors as pre-generative structural constraints (`G(s) → A'(s) ⊆ A(s)`)
- reasoning structurally distinct from release; mediator owns action release
- default inhibition: the resting state is inaction
- separated audit, memory, and learning tracks
- framework/scenario boundary: the framework owns runtime authority and structural invariants; scenarios own world-specific content

## Related projects

- **[eva-theory](https://github.com/slamslammo/eva-theory)**: canonical theory, terminology, and design documentation. Public English.

## License

CC BY 4.0
