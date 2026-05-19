# Round 1.B-3 — Semantic Memory → Drive Impact Overlay (W5) — Startup Instruction

**Recipient**: Claude Code
**Issued by**: Architect (current session)
**Status**: Round 1.B-3 — W5 capability landing; semantic memory begins shaping drive_impact_schema via bounded overlay

**Companion documents**:
- `.claude/plans/federated-snacking-engelbart.md` — Round 1 plan
- `maintainer/development/round-1b-2-progress.md` — Round 1.B-2 closeout (exploration drive landed; provides the second drive overlay channel that this slice will work alongside)
- `eva/l3_deliberation/reasoning/value_judgment.py:108-130` — current `_effective_drive_impact_schema` blend logic (to be extended)
- `eva/l3_deliberation/peer_circuit/rpe.py:182-227` — reference implementation of `build_learned_impact_overlay` (the pattern to mirror)
- `eva/l3_deliberation/reasoning/value_judgment.py:246-270` — current `_semantic_pattern_bias` (which already touches semantic memory at the learning_bias level; we extend the SAME data source to also feed the impact overlay)
- `docs/architecture-implementation-blueprint-v0.6.md` §6.8 / §7.3.3 — semantic memory's role and safe-path constraint

---

## 1. What this work is and is not

**Core idea**: semantic memory already contributes to candidate scoring through `_semantic_pattern_bias` (a flat addition to the assessment score). W5 extends that contribution INTO the drive_impact_schema — when semantic memory has high-confidence guidance about a candidate profile, the candidate's per-drive impact is lightly amplified along positive directions. The semantic learning thus shapes WHICH drives the candidate is expected to satisfy, not just whether to pick it.

**What W5 is**:
- Add `build_semantic_drive_impact_overlay` in `value_judgment.py` (parallel to `build_learned_impact_overlay` in `rpe.py`)
- Extend `_effective_drive_impact_schema` to apply the semantic overlay AFTER the existing learned (RPE/habit) overlay
- Bounded: `MAX_SEMANTIC_OVERLAY_BLEND = 0.15` (smaller than `MAX_LEARNED_IMPACT_BLEND` — semantic is weaker evidence than habit)
- Confidence threshold: only patterns with `confidence >= MIN_SEMANTIC_OVERLAY_CONFIDENCE (0.7)` participate
- Reason tag: `"semantic_impact_overlay"` added to reasons when applied

**What W5 is NOT**:
- Not modifying drive levels (preserves the drive read-only boundary that v0.6.1 mandates)
- Not modifying `SemanticMemoryRecord` schema (uses existing `preferred_candidate_profiles` + `confidence` fields)
- Not modifying semantic memory write path (`semantic.py` untouched)
- Not modifying the existing `_semantic_pattern_bias` — that path stays as a learning-bias contribution; W5 is a SEPARATE drive-impact contribution sourced from the SAME data
- Not modifying Linux scenario or Crafter scenario code — this is framework-level only

---

## 2. Exit criterion

### Behavioral
- When semantic_patterns matching `candidate_profile` are present with `confidence ≥ 0.7`, the candidate's `drive_impact_schema` is amplified along positive entries via the new overlay path.
- When semantic_patterns are absent or confidence < 0.7, no change to drive_impact_schema (the overlay path is a no-op).
- Semantic overlay's effect is smaller than the existing learned overlay's effect at equivalent confidence (because `MAX_SEMANTIC_OVERLAY_BLEND < MAX_LEARNED_IMPACT_BLEND`).
- Linux behavior bit-equivalent in scenarios that don't carry semantic patterns (the new path is a no-op when working_memory_context lacks semantic patterns or none match).

### Engineering
- Full regression passes (target: 350 + ~5 new tests = ~355).
- `git diff main -- 'scenarios/'` shows zero modifications.
- `eva/l2_drive/`, `eva/anchor/`, `eva/scenario_bundle.py` untouched.
- `_semantic_pattern_bias` untouched (preserves existing learning_bias contribution).

### Documentation
- `maintainer/development/round-1b-3-progress.md` written.
- `docs/implementation-tracking.md` flips "Semantic memory → L2 drive-weight semantics" from deferred → production for the safe-path.
- `docs/implementation-tracking-zh.md` mirror.
- `docs/blueprint-to-tracking-map.md` exploration row updated.

---

## 3. Scope target state

### Files to modify
- `eva/l3_deliberation/reasoning/value_judgment.py` — add `build_semantic_drive_impact_overlay`; extend `_effective_drive_impact_schema` to call it

### Files NOT to modify
- `scenarios/` — entire scenario tree
- `eva/l2_drive/`, `eva/anchor/`, `eva/scenario_bundle.py`
- `eva/l3_deliberation/peer_circuit/rpe.py` — preserve as the reference learned overlay path
- `eva/l3_deliberation/memory/semantic.py` — semantic write/read path
- `eva/l3_deliberation/contracts.py` — no schema change
- `_semantic_pattern_bias` in `value_judgment.py` — existing learning_bias path stays

### Tests to add
- New: `tests/l3_deliberation/reasoning/test_semantic_drive_overlay.py`
  1. `test_high_confidence_semantic_pattern_amplifies_drive_impact` — positive case
  2. `test_low_confidence_semantic_pattern_does_nothing` — below threshold no-op
  3. `test_no_semantic_patterns_is_no_op` — absent input no-op
  4. `test_semantic_overlay_smaller_than_learned_overlay` — bounded check
  5. `test_semantic_overlay_does_not_modify_drive_levels` — boundary check
  6. `test_semantic_overlay_reason_recorded_in_assessment_reasons` — provenance

---

## 4. Implementation slices

### 1.B-3-a: Failing tests pinning target behavior
Add the 6 tests outlined above. They should fail on current main.

### 1.B-3-b: `build_semantic_drive_impact_overlay` implementation

Add the function to `value_judgment.py`:

```python
MIN_SEMANTIC_OVERLAY_CONFIDENCE = 0.7
MAX_SEMANTIC_OVERLAY_BLEND = 0.15


def build_semantic_drive_impact_overlay(
    working_memory_context: dict[str, Any] | None,
    *,
    candidate_profile: str,
    drive_impact_schema: dict[str, float],
) -> tuple[dict[str, float], float]:
    """Round 1.B-3 (W5): return a bounded amplification overlay derived from
    semantic memory patterns matching the current candidate profile.

    Semantic memory's contribution is intentionally weaker than the RPE /
    habit-driven learned overlay because semantic patterns are inferential
    summaries of episodic history, not direct outcome reinforcement. The
    overlay only amplifies positive drive impacts — it never flips signs and
    never weakens negative impacts (those represent safety / cost concerns
    that must persist regardless of semantic guidance).

    Returns ({}, 0.0) when no qualifying pattern exists.
    """

    if not isinstance(working_memory_context, dict):
        return {}, 0.0
    semantic_patterns = working_memory_context.get("semantic_patterns")
    if not isinstance(semantic_patterns, list) or not semantic_patterns:
        return {}, 0.0
    matched_confidences: list[float] = []
    for pattern in semantic_patterns:
        if not isinstance(pattern, dict):
            continue
        preferred = pattern.get("preferred_candidate_profiles")
        if not isinstance(preferred, list) or candidate_profile not in preferred:
            continue
        confidence = float(pattern.get("confidence", 0.0))
        if confidence < MIN_SEMANTIC_OVERLAY_CONFIDENCE:
            continue
        matched_confidences.append(confidence)
    if not matched_confidences:
        return {}, 0.0

    # Aggregate confidence and translate into a small amplification.
    avg_confidence = sum(matched_confidences) / len(matched_confidences)
    amplification_factor = avg_confidence  # 0.7..1.0 — pre-blend signal magnitude

    overlay: dict[str, float] = {}
    for drive_name, impact in drive_impact_schema.items():
        if impact > 0:
            overlay[drive_name] = float(impact) * (1.0 + amplification_factor)
        # Negative or zero impacts stay unchanged — semantic memory must not
        # weaken safety / cost signals.

    if not overlay:
        return {}, 0.0

    # Blend factor scales with how many patterns aligned with this profile
    # (more independent confirmations -> slightly higher blend), but capped.
    raw_blend = 0.05 * len(matched_confidences) * avg_confidence
    blend_factor = round(min(MAX_SEMANTIC_OVERLAY_BLEND, raw_blend), 3)
    if blend_factor <= 0.0:
        return {}, 0.0
    return overlay, blend_factor
```

### 1.B-3-c: Wire overlay into `_effective_drive_impact_schema`

Extend the existing function:

```python
def _effective_drive_impact_schema(
    deliberation_input: DeliberationInput,
    *,
    candidate_profile: str,
    top_drive: str,
    drive_impact_schema: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    """Return the effective impact schema after any bounded learned overlay."""

    effective_schema = dict(drive_impact_schema)
    applied_reasons: list[str] = []

    # Existing learned overlay (RPE/habit-driven) - unchanged.
    learned_overlay, learned_blend = build_learned_impact_overlay(
        deliberation_input.working_memory_context,
        candidate_profile=candidate_profile,
        top_drive=top_drive,
    )
    if learned_overlay and learned_blend > 0.0:
        for drive_name, learned_signal in learned_overlay.items():
            baseline = float(effective_schema.get(drive_name, 0.0))
            effective_schema[drive_name] = _bounded_drive_impact_value(
                ((1.0 - learned_blend) * baseline) + (learned_blend * float(learned_signal))
            )
        applied_reasons.append("learned_impact_overlay")

    # Round 1.B-3 (W5): semantic memory drive-impact overlay.
    semantic_overlay, semantic_blend = build_semantic_drive_impact_overlay(
        deliberation_input.working_memory_context,
        candidate_profile=candidate_profile,
        drive_impact_schema=effective_schema,
    )
    if semantic_overlay and semantic_blend > 0.0:
        for drive_name, semantic_signal in semantic_overlay.items():
            baseline = float(effective_schema.get(drive_name, 0.0))
            effective_schema[drive_name] = _bounded_drive_impact_value(
                ((1.0 - semantic_blend) * baseline) + (semantic_blend * float(semantic_signal))
            )
        applied_reasons.append("semantic_impact_overlay")

    return effective_schema, applied_reasons
```

### 1.B-3-d: Docs sync + closeout

- `docs/implementation-tracking.md` — "Semantic memory → L2 drive-weight semantics" row: deferred → production (safe-path landed)
- `docs/implementation-tracking-zh.md` — mirror
- `docs/blueprint-to-tracking-map.md` — same row
- `maintainer/development/stage-i-followups.md` — append note that followup #2 is resolved by Round 1.B-3
- `maintainer/development/round-1b-3-progress.md` — slice-by-slice record
- `maintainer/development/current-intake.md` — closeout

---

## 5. Boundary / invariants

- Drive read-only broadcast — preserved (overlay touches impact_schema, not drive levels)
- Existing `_semantic_pattern_bias` path — preserved
- Existing `build_learned_impact_overlay` path — preserved
- Negative drive impacts — NEVER weakened by semantic overlay (preserves safety/cost signals)
- Confidence threshold (0.7) — patterns below threshold ignored
- Blend cap (0.15) — semantic overlay's max effect is smaller than learned overlay's typical effect
- No scenario changes
- No L2 drive layer changes

---

## 6. Architect gates

- **G1-3B** (pre-implementation): intake written; architect confirms scope
- **G2-3B** (post-1.B-3-c): regression green; architect confirms ready for docs sync
- **G3-3B** (closeout): full regression + progress doc; architect approves moving to Round 1.C

---

## 7. Recommended starting flow

1. Re-read `value_judgment.py` lines 108-130 and 246-270 to confirm signature compatibility
2. Re-read `rpe.py` `build_learned_impact_overlay` for the pattern to mirror
3. Write intake; sub-slice A → B → C → D
4. After each sub-slice run full regression
