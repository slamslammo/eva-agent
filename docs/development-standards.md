# Development Standards

## Purpose
This document defines the ongoing development standards for `eva-agent`.

It is intended to keep future iterations readable, consistent, maintainable, and aligned with the project's existing engineering style.

## Scope
These standards apply to:
- Python source code under `eva/`
- tests under `tests/`
- related technical documentation when behavior, persistence, or interfaces change

## Core Principles

### 1. Readability first
- Prefer code that is easy to read and explain
- Avoid clever but opaque implementations
- Make control flow and state transitions easy to follow

### 2. Consistency over personal style
- Follow the existing project style unless there is a strong reason to change it
- Keep naming, typing style, data modeling, and module structure consistent across files

### 3. Explicitness over hidden magic
- Prefer explicit data flow and explicit state transitions
- Avoid unnecessary indirection, implicit side effects, and over-abstracted helper layers

### 4. Small, focused units
- Functions should do one clear thing
- Modules should have clear boundaries
- Keep related logic close to the stage or capability it belongs to

### 5. Minimal sufficient abstraction
- Do not introduce abstractions for hypothetical future reuse
- Prefer the simplest structure that cleanly solves the current problem
- Refactor only when duplication or complexity becomes real

## Python Code Standards

### Typing
- Use type hints consistently for public functions, methods, and important internal boundaries
- Keep type annotations readable and practical
- Do not introduce overly complex type machinery unless clearly necessary

### Data modeling
- Prefer `dataclass` for structured state and records
- Keep persisted structures explicit and stable
- Avoid hiding important schema changes behind loose dictionaries when a clear model is better

### Naming
- Use `snake_case` for functions, variables, and module-level helpers
- Use clear, capability-oriented names
- Prefer names that describe intent, not mechanism jargon

### Function and module design
- Keep functions short and purpose-driven
- Keep module responsibilities narrow and understandable
- Avoid mixing unrelated concerns in the same function or file

## Comments and Docstrings

### Docstrings
- Add docstrings to modules, important classes, and non-trivial functions
- Keep docstrings concise and practical
- Describe intent, responsibility, and important boundaries

### Inline comments
- Use comments only for non-obvious control flow, invariants, or design constraints
- Do not comment code that is already self-explanatory
- Keep comments accurate and synchronized with the code

## Change Discipline

### Behavior changes
- If behavior changes, update tests
- If persistence shape or protocol changes, update the related docs
- If a change affects lifecycle or stage boundaries, update the relevant design docs first or together

### Refactoring
- Do not mix broad refactors into a focused feature change unless necessary
- Preserve existing behavior unless the task explicitly requires behavior change
- Prefer incremental cleanup over wide rewrites

### Testing
- New logic should be covered at the appropriate level
- Regression risk should be matched with regression tests
- Tests should remain readable and deterministic

## Review Checklist
Before finishing a change, check:

- Is the code easy to read?
- Is it consistent with the surrounding files?
- Are names clear?
- Is the abstraction level appropriate?
- Are docstrings/comments sufficient but not excessive?
- Are tests updated where needed?
- Are related docs updated if the change affects contracts or persistence?

## Project-Specific Notes for `eva-agent`
- Preserve heartbeat-first lifecycle priority
- Do not let normal turn work obscure lifecycle safety boundaries
- Keep Step 0 / Step 1 / later-stage concerns clearly separated
- Prefer deterministic, rule-based behavior unless a later stage explicitly introduces more open-ended reasoning
