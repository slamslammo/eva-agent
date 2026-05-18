# Development Trajectory

This document describes the planned sequence of work after the current Stage I closeout. It is not a dated roadmap. It is a sequencing document: what comes before what, and why.

For the current implemented capability surface, see [capability-inventory.md](capability-inventory.md). For internal stage records, see `maintainer/development/`.

## Sequencing principles

Three principles currently govern the order of work:

1. **Theory before extension.** Capabilities already committed in EVA v0.5 and v0.6 come before any broader expansion that would need new theory.
2. **Framework before multiplication.** If a capability should hold across scenarios, its framework boundary should be clean before more field-specific growth is added.
3. **Validation before widening.** The repo should keep validating the already-landed structure before widening into new high-level behavioral surfaces.

## Near-term sequence

### 1. Public docs reorganization

Current work:

- establish `docs/README.md` as the public entry point
- add a theory-to-implementation landing map
- add a flat capability inventory with explicit tiers
- separate status snapshot from capability state and future sequence

Why first:

- the current codebase has already crossed the one-document stage
- Stage I closed with a real framework/scenario split, and the public docs need to reflect that cleanly before the next engineering cycle

### 2. Maintainer docs reorganization

Next after the public `docs/` cleanup:

- reorganize `maintainer/` around workflow efficiency rather than public readability
- retarget maintainer cross-references to the new public docs structure
- preserve stage history while reducing navigation friction for future implementation cycles

Why second:

- internal working docs should point into the settled public docs structure, not the other way around

### 3. Post-Stage-I follow-ups

Current carry-forward follow-ups already identified in maintainer records:

- semantic-memory store-side windowing / indexing
- review of the working-memory interface signature as more inputs accumulate
- eventual evaluation of a minimal safe path from semantic memory into L2 drive-weight semantics

Why before broader expansion:

- these are direct quality follow-ups on already-landed Stage I surfaces
- they improve runtime quality without requiring a new theory cycle

### 4. Baseline and comparative validation work

The next empirical layer after documentation and Stage I follow-ups is expected to include:

- stronger Codex / baseline experiment preparation
- comparative stability evaluation against non-EVA baselines
- validation work around the theory-side Comparative Stability Hypothesis

Why here:

- the repository now has a second scenario and an architecture-neutral `stability_metrics/` surface
- the remaining need is comparative experimental work, not another theory document pretending the experiments already exist

## Medium-term sequence

### Exploration as growth driver

Theory-side exploration commitments are already present in EVA v0.6 §1.4, but the runtime does not yet implement an exploration-growth mechanism.

This is a natural medium-term item because:

- it is already theory-committed
- it depends on the lower sensing / outcome / memory surfaces now being explicit
- it should be added only after the current bounded runtime surfaces and their follow-ups are stable

### Cross-scenario inherited priors

Same-scenario inherited-prior reuse is landed. Cross-scenario reuse is not.

This remains later than same-scenario reuse because:

- the current theory explicitly distinguishes what can and cannot be distilled at L3
- cross-scenario transfer is more likely to create scope drift if introduced prematurely
- the current repo still treats Crafter primarily as a bounded validation scenario rather than a broad second deployment surface

### Higher persistence levels and L4 / L5 work

The current repo exposes lower persistence-level runtime structure and leaves Levels 5–7, L4 self-model deepening, and L5 social-layer deepening for later work.

These belong later because:

- v0.6 already marks the higher persistence levels as future-facing placeholders
- they should follow lower-layer validation rather than precede it

## Open trajectories

The following trajectories are real but not currently sequenced into the immediate next slice:

- semantic memory participation in L2 drive-weight semantics
- broader Crafter widening beyond its current validation role
- generic scenario loader / validator work
- any future v0.7 theory-linked items such as L4/L5 deepening, higher persistence levels, or broader transmission mechanisms

## Process expectation

When one of the items above becomes the next implementation slice, the expected process remains:

1. maintainer intake / startup instruction
2. bounded implementation against current structural constraints
3. review and closeout
4. public doc sync where capability state changes
5. selection of the next slice from this sequence

The key rule is that `development-trajectory.md` tracks sequence, while `maintainer/development/` tracks the working record.