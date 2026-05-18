# Current Status

`eva-agent` currently presents a framework-separated EVA runtime with one primary Linux runtime and one bounded Crafter validation runtime.

The current public architecture entry points are:

- [Documentation entry point](README.md)
- [Framework implementation](eva-framework-implementation.md)
- [Scenario contract](scenarios-SPEC.md)
- [Theory → implementation landing](theory-implementation-landing.md)
- [Capability inventory](capability-inventory.md)
- [Development trajectory](development-trajectory.md)
- [Linux runtime scenario](../scenarios/linux_runtime/SPEC.md)
- [Crafter scenario](../scenarios/crafter/SPEC.md)

## Reference deployments

- **Linux runtime** — the primary shipped reference runtime
- **Crafter** — a bounded second scenario used to validate the cross-scenario framework seam end to end

Both runtimes use explicit scenario activation, scenario-owned persistence registration, and runner-owned startup assembly.

## Recent milestone

The current repository state reflects the closeout of the Stage I engineering landing associated with the EVA v0.6 unified release.

At the public architecture level, that means:

- the `eva/` package now serves as the framework-owned runtime spine
- `scenarios/linux_runtime/` and `scenarios/crafter/` own field-specific content
- `runners/run_linux.py` and `runners/run_crafter.py` are explicit startup paths
- the same bounded framework loop now carries more than one scenario shape without widening release authority

## Stable architectural posture

The following architectural posture is now stable enough to read as the current public baseline:

- framework ownership and scenario ownership are explicitly separated
- runtime authority stays with the kernel, mediator, append-only artifacts, and persistence boundaries
- scenario content supplies drives, sensors, actions, anchors, outcome interpretation, and prior-skill policy
- runner assembly is explicit rather than hidden behind generic auto-loading
- Crafter is real and end-to-end, but still intentionally bounded in scope

## Where to look next

- For framework ownership and seams, read [eva-framework-implementation.md](eva-framework-implementation.md)
- For the cross-scenario contract, read [scenarios-SPEC.md](scenarios-SPEC.md)
- For theory-to-code mapping, read [theory-implementation-landing.md](theory-implementation-landing.md)
- For capability completeness and gaps, read [capability-inventory.md](capability-inventory.md)
- For next-step sequencing, read [development-trajectory.md](development-trajectory.md)

## What this page is not

This page is a status snapshot. It is not:

- a capability inventory
- a development roadmap
- a scenario specification
- a theory document

Those roles now live in the more specific documents above.