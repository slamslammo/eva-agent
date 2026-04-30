# Maintainer Workspace

This directory contains maintainer-facing materials for ongoing development and documentation work.

It is versioned with the repository so that roadmap, phase history, and source materials remain traceable across development cycles, but it is **not** part of the public reading path.

## Role of this directory

`maintainer/` exists to support internal authoring, development sequencing, and historical traceability.

It should be used for:
- local development roadmap and phase progress tracking
- Chinese source materials and merged local reading drafts
- archived documentation that is no longer part of the public mainline
- capability-to-phase mapping used to keep public and local docs aligned

It should not be treated as the public documentation surface.

## Structure

- `development/` — roadmap, plans, progress, and capability mapping
- `full-implementation/` — Chinese source sections and merged local reference draft
- `archive/` — superseded documents kept for historical reference

## Public reading path

External readers should primarily use:
- `README.md`
- `docs/eva-agent-full-implementation.md`
- `docs/current-status.md`

## Maintainer reading path

For local development work, use:
1. `development/roadmap.md`
2. `development/capability-map.md`
3. the active phase plan and progress documents
4. `full-implementation/` source materials when refining architecture text
