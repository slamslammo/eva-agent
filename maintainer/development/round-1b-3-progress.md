# Round 1.B-3 Progress — Semantic Memory → Drive Impact Overlay (W5)

## Status

- **Implementation**: complete — sub-slices A → B+C → D landed
- **Regression**: 357 / 357 tests pass
- **Stage I follow-up #2**: resolved
- **G3-3B gate**: pending architect review

## Goal recap

Round 1.B-3 closed Stage I follow-up #2 — the deferred "semantic memory → L2 drive-weight semantics" path — by adding a bounded safe-path overlay that lets semantic memory shape `drive_impact_schema` without violating the drive read-only broadcast boundary.

The overlay only amplifies positive entries in the impact schema; negative impacts (representing safety / cost signals) are never weakened. Semantic memory's overall contribution is intentionally smaller than the RPE/habit-driven learned overlay because semantic patterns are inferential summaries rather than direct outcome reinforcement.

## Sub-slice record

### 1.B-3-a: Failing tests pinning behavior

- **File**: `tests/l3_deliberation/reasoning/test_semantic_drive_overlay.py` (new, 7 tests)
- **Coverage**:
  - Unit tests on `build_semantic_drive_impact_overlay`:
    - high-confidence pattern amplifies positive impacts; negatives preserved
    - below-threshold confidence → no-op
    - empty / missing / None semantic_patterns → no-op
    - pattern for different profile → no-op
  - Integration tests through `assess_candidates`:
    - `semantic_impact_overlay` reason recorded when overlay applies
    - reason absent when no matching pattern
    - `MAX_SEMANTIC_OVERLAY_BLEND < MAX_LEARNED_IMPACT_BLEND` (bounded check)
- **State on main**: ImportError on the new constants — confirmed failing.

### 1.B-3-b + 1.B-3-c: Implementation (combined commit)

Combined into one commit because the new function (`build_semantic_drive_impact_overlay`) and its wiring (`_effective_drive_impact_schema` extension) are mechanically inseparable — neither makes sense without the other.

- **File**: `eva/l3_deliberation/reasoning/value_judgment.py`
- **Additions**:
  - Module constants: `MIN_SEMANTIC_OVERLAY_CONFIDENCE = 0.7`, `MAX_SEMANTIC_OVERLAY_BLEND = 0.15`
  - New function `build_semantic_drive_impact_overlay(working_memory_context, *, candidate_profile, drive_impact_schema) → (overlay, blend_factor)`
  - Extension of `_effective_drive_impact_schema`: after the existing learned overlay step, applies semantic overlay with its own blend factor, accumulates reasons (`"learned_impact_overlay"`, `"semantic_impact_overlay"`)
- **Import added**: `from typing import Any` (needed for the type annotation on `working_memory_context: dict[str, Any] | None`)
- **Linux equivalence**: when `working_memory_context.semantic_patterns` is empty or absent (the typical case in existing Linux tests), the new path is a strict no-op. Verified by full regression passing without any Linux test modification.

### Algorithm summary

```
For each semantic pattern in working_memory_context["semantic_patterns"]:
    If candidate_profile in pattern["preferred_candidate_profiles"]
       and pattern["confidence"] >= 0.7:
        Record the confidence.

If no qualifying pattern: return ({}, 0.0).

avg_confidence = mean of recorded confidences.
For each (drive_name, impact) in drive_impact_schema:
    If impact > 0:
        overlay[drive_name] = impact * (1 + avg_confidence)
    # Negative or zero impacts stay out of the overlay.

blend_factor = min(0.15, 0.05 * count_of_matched_patterns * avg_confidence)
return (overlay, blend_factor)
```

The pre-blend signal in `overlay` is later combined with the existing
schema via the standard linear blend: `(1-blend) * baseline + blend * signal`.
This makes the actual effective change much smaller than the raw signal —
e.g., a single 0.85-confidence pattern produces blend = 0.0425, so a drive
impact of 0.5 becomes (1-0.0425) * 0.5 + 0.0425 * 0.5*(1+0.85) ≈ 0.515.
About 3% amplification — small, principled, scaled.

### 1.B-3-d: Docs sync

- `docs/implementation-tracking.md` — "Semantic memory → L2 drive-weight semantics" row flipped from deferred → production with implementation reference + safety-bound annotations. The "Four-layer memory surface" row's note updated to point W4 (semantic indexing) at Round 1.C and W5 at Round 1.B-3. The follow-up #2 row marked resolved.
- `docs/implementation-tracking-zh.md` — same updates mirrored.
- `docs/blueprint-to-tracking-map.md` — "Semantic memory → L2 safe path" row flipped to production with reference.
- `maintainer/development/stage-i-followups.md` — follow-up #2 marked resolved with implementation pointer.
- `maintainer/development/round-1b-3-progress.md` — this file.
- `maintainer/development/current-intake.md` — closeout.

## Files changed

### Modified (framework, 1 file)
- `eva/l3_deliberation/reasoning/value_judgment.py` — added function + extended existing function; new module-level constants

### Modified (docs, 4 files)
- `docs/implementation-tracking.md`
- `docs/implementation-tracking-zh.md`
- `docs/blueprint-to-tracking-map.md`
- `maintainer/development/stage-i-followups.md`

### Added (test, 1 file)
- `tests/l3_deliberation/reasoning/test_semantic_drive_overlay.py` (7 tests)

### Maintainer docs (added)
- `maintainer/development/round-1b-3-semantic-drive-impact-overlay-startup-instruction.md`
- `maintainer/development/round-1b-3-progress.md` (this file)

### Not modified
- `scenarios/` — zero changes
- `eva/l2_drive/`, `eva/anchor/`, `eva/scenario_bundle.py`, `eva/kernel/`, `eva/l1_sensing/` — unchanged
- `eva/l3_deliberation/peer_circuit/rpe.py` — preserved as the canonical learned overlay reference
- `eva/l3_deliberation/memory/semantic.py` — semantic write/read path unchanged
- `_semantic_pattern_bias` in `value_judgment.py` — existing learning_bias contribution preserved

## Verification log

| Step | Result |
|---|---|
| 1.B-3-a failing tests added | ImportError on missing constants — confirmed |
| 1.B-3-b + c (combined) — function + wiring + Any import | 7 new tests pass; full regression 357 / 357 OK |
| 1.B-3-d docs sync | regression remains 357 / 357 OK |
| Final regression | **357 / 357 OK** |
| `git diff main -- 'scenarios/'` for Round 1.B-3 only | empty (Crafter changes shown in diff are from Round 1.A / 1.B-2) |

## Round 1.B-3 exit criteria status

| Criterion | Status |
|---|---|
| High-confidence semantic pattern amplifies positive drive impact | ✅ |
| Below-threshold patterns are no-op | ✅ |
| No semantic patterns is no-op | ✅ |
| Linux behavior bit-equivalent when no semantic patterns present | ✅ verified by full regression with no Linux test modifications |
| Negative drive impacts never weakened by overlay | ✅ pinned by unit test |
| Reason tag `semantic_impact_overlay` recorded in assessments | ✅ |
| `MAX_SEMANTIC_OVERLAY_BLEND < MAX_LEARNED_IMPACT_BLEND` | ✅ pinned by integration test |
| Stage I follow-up #2 closed | ✅ marked resolved in stage-i-followups.md |

## Surfaced for Round 1.D long-run validation

These are not regressions; they are tunings to revisit when long-run validation has data:

1. **`MAX_SEMANTIC_OVERLAY_BLEND = 0.15`** is a conservative starting cap. If long-run shows semantic memory accumulating high-confidence patterns that should have more weight, tune upward (toward but not above the learned overlay cap).

2. **Amplification factor (1 + avg_confidence)** is a simple multiplicative form. More sophisticated forms (e.g., exponential, sigmoid) could be evaluated in 1.D if the current linear amplification proves too coarse.

3. **Negative impacts are never amplified.** This is the right safe-path default but may become a future deepening item — semantic memory could in principle suggest that certain candidates are MORE risky than the baseline impact_schema represents (e.g., "I learned that this action increases safety risk above the static prediction"). Out of Round 1 scope; record for v0.7 consideration.

## Round 1.B is now complete

Round 1.B-1 (de-Linuxification), Round 1.B-2 (exploration drive), Round 1.B-3 (semantic drive overlay) are all landed. The framework + Crafter stack is structurally ready for Round 1.C (perf + interface review) and Round 1.D (long-run validation).
