# eva-agent Documentation

This directory contains the public-facing implementation documents for `eva-agent`.

- Theory lives in the sibling `eva-theory` repository.
- Internal engineering planning lives under `maintainer/`.
- Scenario-specific concrete behavior lives in each scenario's own `SPEC.md` file.

## Reading order

1. **[Current status](current-status.md)** — the shortest snapshot of what currently runs and what the stable architectural posture is.
2. **[Framework implementation](eva-framework-implementation.md)** — what the `eva/` framework owns across scenarios.
3. **[Scenario contract](scenarios-SPEC.md)** — the cross-scenario contract the framework expects.
4. **[Theory → implementation landing](theory-implementation-landing.md)** — where major EVA v0.5 and v0.6 commitments land in code.
5. **[Capability inventory](capability-inventory.md)** — a flat capability list with explicit completeness tiers.
6. **[Development trajectory](development-trajectory.md)** — the sequence of follow-on work after the current landing.

## Scenario specifications

Concrete shipped scenarios are documented beside their code, not duplicated in `docs/`:

- [`../scenarios/linux_runtime/SPEC.md`](../scenarios/linux_runtime/SPEC.md)
- [`../scenarios/crafter/SPEC.md`](../scenarios/crafter/SPEC.md)

## Architecture diagrams

Architecture diagrams referenced by the public docs live under `assets/architecture/`.

## Archived documents

`archive/` contains historical reference material that is no longer canonical. The most important archived file is:

- [`archive/eva-agent-full-implementation-v0.5.md`](archive/eva-agent-full-implementation-v0.5.md)

That document remains useful for historical comparison, but it is not the canonical description of the current framework/scenario split.

## What is not in this directory

- `maintainer/` — internal planning, stage records, follow-ups, and maintainer workflow documents
- `eva-theory` — canonical theory, terminology, and theory-side articles

Read `docs/` for implementation-facing public documentation. Read `maintainer/` only when you need the internal engineering record.