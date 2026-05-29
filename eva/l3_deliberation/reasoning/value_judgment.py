"""Rule-based value judgment for the minimal Phase B / early Phase C L3 skeleton."""

from __future__ import annotations

import math
from typing import Any

from .candidate_generation import current_anchor_profiles
from .conflict_detection import build_candidate_conflict_context
from ..contracts import Candidate, CandidateAssessment, DeliberationInput, ScoreDecomposition
from ..peer_circuit.rpe import build_learned_impact_overlay
from ...observability import current_trace_sink, current_trace_turn_index


def assess_candidates(candidates: list[Candidate], deliberation_input: DeliberationInput) -> list[CandidateAssessment]:
    """Assess candidates using drive-weighted scoring with bounded projection fallback."""

    anchor_profiles = current_anchor_profiles()
    signal_summary = deliberation_input.signal_batch.get("summary", {})
    threat_count = int(signal_summary.get("threat_signal_count", 0))
    drive_broadcast = deliberation_input.drive_broadcast
    top_drive = str(drive_broadcast.get("top_drive") or "unknown")
    drive_levels = drive_broadcast.get("drive_levels")
    normalized_drive_levels = dict(drive_levels) if isinstance(drive_levels, dict) else {}

    assessments: list[CandidateAssessment] = []
    for candidate in candidates:
        reasons: list[str] = [f"top_drive={top_drive}"]
        if "habit_candidate_narrowing" in candidate.justification:
            reasons.append("habit_candidate_narrowing")
        score = 0.0
        learning_bias = 0.0
        bias_reasons: list[str] = []
        # Round 1.H H-3b: score-decomposition components for the candidate_scoring
        # snapshot (owner-hook #2). Initialized here so the read-only emit below always
        # has them; the allow branch reassigns the live values. Purely additive — the
        # returned CandidateAssessment is unaffected (byte-equivalent).
        drive_score = 0.0
        projection_score = 0.0
        habit_priority_bonus = 0.0
        conflict = build_candidate_conflict_context(
            candidate,
            top_drive=top_drive,
            threat_count=threat_count,
            drive_levels=normalized_drive_levels,
        )
        if candidate.action == "compatibility_release":
            candidate_profile = conflict.candidate_profile
            if candidate_profile in {
                anchor_profiles.observe_first_profile,
                anchor_profiles.stabilize_first_profile,
                anchor_profiles.escalate_first_profile,
            }:
                habitual_trace = str(candidate.parameter_domain.get("habitual_trace") or "habitual_neutral")
                if habitual_trace == "habitual_suppression":
                    reasons.append("habitual_suppression_trace")
                elif habitual_trace == "habitual_support":
                    reasons.append("habitual_support_trace")
                if not bool(candidate.parameter_domain.get("habit_eligible", False)):
                    habit_eligibility_reasons = candidate.parameter_domain.get("habit_eligibility_reasons") or []
                    if isinstance(habit_eligibility_reasons, list):
                        reasons.extend(
                            f"habit_ineligible:{reason}"
                            for reason in habit_eligibility_reasons
                            if isinstance(reason, str) and reason
                        )
            disposition = conflict.disposition
            reasons.extend(reason for reason in conflict.reasons if reason not in reasons)
            if disposition == "allow":
                effective_drive_impact_schema, impact_reasons = _effective_drive_impact_schema(
                    deliberation_input,
                    candidate_profile=candidate_profile,
                    top_drive=top_drive,
                    drive_impact_schema=candidate.drive_impact_schema,
                )
                reasons.extend(reason for reason in impact_reasons if reason not in reasons)
                drive_score = _drive_weighted_score(effective_drive_impact_schema, normalized_drive_levels)
                score = drive_score
                projection_score = _projection_fallback_score(
                    conflict.score_delta,
                    drive_score=drive_score,
                )
                if projection_score != 0.0:
                    score += projection_score
                    reasons.append("projection_fallback")
                learning_bias, bias_reasons = _learning_bias_for_candidate_profile(
                    deliberation_input,
                    candidate_profile=candidate_profile,
                )
                score += learning_bias
                habit_priority_bonus = _habit_skill_priority_bonus(candidate.parameter_domain)
                if habit_priority_bonus != 0.0:
                    score += habit_priority_bonus
                    reasons.append("crystallized_habit_skill_hint")
                # Round 1.G: the ≤0.12 LLM advisory bonus is retired (drift; round-1f
                # showed it had no doctrinal basis and, under live LLM, harmfully biased
                # selection toward passivity). OFC scoring stays drive-weighted only;
                # the model's contribution moves to dlPFC candidate production (phase 2).
        elif "raw_action_candidate" in conflict.reasons:
            candidate_profile = conflict.candidate_profile
            disposition = conflict.disposition
            reasons.extend(reason for reason in conflict.reasons if reason not in reasons)
            if disposition == "allow":
                effective_drive_impact_schema, impact_reasons = _effective_drive_impact_schema(
                    deliberation_input,
                    candidate_profile=candidate_profile,
                    top_drive=top_drive,
                    drive_impact_schema=candidate.drive_impact_schema,
                )
                reasons.extend(reason for reason in impact_reasons if reason not in reasons)
                drive_score = _drive_weighted_score(effective_drive_impact_schema, normalized_drive_levels)
                score = drive_score
                projection_score = _projection_fallback_score(
                    conflict.score_delta,
                    drive_score=drive_score,
                )
                if projection_score != 0.0:
                    score += projection_score
                    reasons.append("projection_fallback")
                learning_bias, bias_reasons = _learning_bias_for_candidate_profile(
                    deliberation_input,
                    candidate_profile=candidate_profile,
                )
                score += learning_bias
                habit_priority_bonus = _habit_skill_priority_bonus(candidate.parameter_domain)
                if habit_priority_bonus != 0.0:
                    score += habit_priority_bonus
                    reasons.append("crystallized_habit_skill_hint")
        else:
            disposition = conflict.disposition
            reasons.extend(reason for reason in conflict.reasons if reason not in reasons)
        # PR-Γ §6.1: explicit ScoreDecomposition for OFC_classical observability.
        # ``semantic_overlay_blend`` is currently 0.0 (the semantic overlay blend
        # is applied to drive_impact_schema upstream of scoring rather than as a
        # separate scalar term); reserved here so future single-source drive
        # metadata can fill it.
        score_decomposition = ScoreDecomposition(
            drive_weighted=round(drive_score, 6),
            projection_fallback=round(projection_score, 6),
            learning_bias=round(learning_bias, 6),
            habit_priority_bonus=round(habit_priority_bonus, 6),
            semantic_overlay_blend=0.0,
            advisory=0.0,  # retired in Round 1.G
            final_score=round(score, 6),
            reasons=tuple(reasons),
        )
        assessments.append(
            CandidateAssessment(
                candidate_id=candidate.candidate_id,
                action=candidate.action,
                score=round(score, 6),
                disposition=disposition,
                reasons=tuple(reasons),
                learning_bias=round(learning_bias, 6),
                bias_reasons=tuple(bias_reasons),
                score_decomposition=score_decomposition,
            )
        )
        # Round 1.H H-3b: flag-gated read-only owner-hook (A-approved exception #2).
        # The per-candidate score decomposition (drive_weighted / projection / habit /
        # advisory) is local here and invisible at any seam — only ``score`` +
        # ``learning_bias`` survive on CandidateAssessment. Gated on the process-current
        # trace sink (NullTraceSink off → no-op → byte-equivalent); never reads back.
        _trace = current_trace_sink()
        if _trace.enabled:
            _trace.emit_snapshot(
                snapshot_type="candidate_scoring",
                turn_index=current_trace_turn_index(),
                values={
                    "candidate_id": candidate.candidate_id,
                    "drive_weighted": round(drive_score, 6),
                    "projection": round(projection_score, 6),
                    "learning_bias": round(learning_bias, 6),
                    "habit": round(habit_priority_bonus, 6),
                    "advisory": 0.0,  # retired in Round 1.G (drift)
                    "final_score": round(score, 6),
                },
            )
    return assessments


# Round 1.B-3 (W5): bounded semantic-memory contribution to drive_impact_schema.
# Smaller than ``MAX_LEARNED_IMPACT_BLEND`` (see rpe.py) because semantic
# patterns are inferential summaries of episodic history rather than direct
# outcome reinforcement. Threshold of 0.7 confidence keeps low-evidence
# patterns from leaking into the impact schema.
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

    Semantic memory's contribution to drive_impact_schema is intentionally
    weaker than RPE/habit-driven learning because semantic patterns are
    inferential summaries of episodic history, not direct outcome
    reinforcement. The overlay only amplifies positive drive impacts — it
    never flips signs and never weakens negative impacts (those represent
    safety / cost concerns that must persist regardless of semantic
    guidance).

    Returns ``({}, 0.0)`` when no qualifying pattern exists.
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

    avg_confidence = sum(matched_confidences) / len(matched_confidences)

    # Amplify only positive impacts; preserve negative impacts unchanged so
    # safety / cost signals are never weakened by semantic guidance.
    overlay: dict[str, float] = {}
    for drive_name, impact in drive_impact_schema.items():
        impact_value = float(impact)
        if impact_value > 0.0:
            overlay[drive_name] = impact_value * (1.0 + avg_confidence)

    if not overlay:
        return {}, 0.0

    # Blend factor grows mildly with the number of independent confirming
    # patterns, capped by ``MAX_SEMANTIC_OVERLAY_BLEND``.
    raw_blend = 0.05 * len(matched_confidences) * avg_confidence
    blend_factor = round(min(MAX_SEMANTIC_OVERLAY_BLEND, raw_blend), 3)
    if blend_factor <= 0.0:
        return {}, 0.0
    return overlay, blend_factor


def _effective_drive_impact_schema(
    deliberation_input: DeliberationInput,
    *,
    candidate_profile: str,
    top_drive: str,
    drive_impact_schema: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    """Return the effective impact schema after any bounded learned overlay
    and semantic-memory overlay (Round 1.B-3)."""

    effective_schema = dict(drive_impact_schema)
    applied_reasons: list[str] = []

    learned_overlay, blend_factor = build_learned_impact_overlay(
        deliberation_input.working_memory_context,
        candidate_profile=candidate_profile,
        top_drive=top_drive,
    )
    if learned_overlay and blend_factor > 0.0:
        for drive_name, learned_signal in learned_overlay.items():
            baseline = float(effective_schema.get(drive_name, 0.0))
            effective_schema[drive_name] = _bounded_drive_impact_value(
                ((1.0 - blend_factor) * baseline) + (blend_factor * float(learned_signal))
            )
        applied_reasons.append("learned_impact_overlay")

    # Round 1.B-3 (W5): semantic-memory contribution layered on top of the
    # learned overlay. Same blend math, smaller cap, restricted to amplifying
    # already-positive impacts.
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


def _drive_weighted_score(
    drive_impact_schema: dict[str, float],
    drive_levels: dict[str, object],
) -> float:
    """Return the main candidate score from continuous drive levels and predicted impact.

    Round 1.B-1-a: iteration is scenario-neutral — it walks the drives that
    the candidate has actually declared an impact for. The previous
    implementation hardcoded the Linux drive vocabulary
    (``"survival", "integrity", "continuity", "curiosity"``), which silently
    zeroed-out scoring for any scenario (e.g., Crafter) whose drives have
    different names. The new form is bit-equivalent for Linux because every
    Linux drive that contributed under the old loop is present in
    ``drive_impact_schema.items()``, and any drive absent from
    ``drive_impact_schema`` would have contributed ``0`` anyway via the
    ``drive_impact_schema.get(_, 0.0)`` fallback in the old form.
    """

    if not drive_impact_schema:
        return 0.0
    score = 0.0
    for drive_name, impact in drive_impact_schema.items():
        score += float(drive_levels.get(drive_name, 0.0)) * float(impact)
    return score


def _projection_fallback_score(score_delta: float, *, drive_score: float) -> float:
    """Return a small projection-only fallback when drive scoring does not separate candidates."""

    if score_delta == 0.0 or drive_score != 0.0:
        return 0.0
    return min(0.15, score_delta * 0.02)


def _bounded_drive_impact_value(raw_value: float) -> float:
    """Clamp one effective drive-impact value so learned overlay stays bounded."""

    return max(-1.0, min(1.0, raw_value))


def _learning_bias_for_candidate_profile(
    deliberation_input: DeliberationInput,
    *,
    candidate_profile: str,
) -> tuple[float, list[str]]:
    """Return the bounded learning bias for one candidate profile."""

    working_memory_context = deliberation_input.working_memory_context or {}
    total_bias = 0.0
    reasons: list[str] = []

    bias_summaries = working_memory_context.get("bias_summaries")
    if isinstance(bias_summaries, list):
        for summary in bias_summaries:
            if str(summary.get("candidate_profile") or "") != candidate_profile:
                continue
            evidence_count = int(summary.get("evidence_count", 0))
            confidence = float(summary.get("confidence", 0.0))
            stability_score = float(summary.get("stability_score", 0.0))
            if evidence_count >= 2 and confidence >= 0.5 and stability_score >= 0.5:
                summary_bias = _bounded_learning_bias(float(summary.get("bias_strength", 0.0)) * 0.25)
                if summary_bias != 0.0:
                    total_bias += summary_bias
                    reasons.append("positive_habit_bias" if summary_bias > 0 else "negative_habit_bias")
            break

    recent_relevant_outcomes = working_memory_context.get("recent_relevant_outcomes")
    if isinstance(recent_relevant_outcomes, list):
        recent_outcome_bias = _recent_negative_outcome_bias(
            recent_relevant_outcomes,
            candidate_profile=candidate_profile,
        )
        if recent_outcome_bias != 0.0:
            total_bias += recent_outcome_bias
            reasons.append("recent_negative_outcome_bias")

    semantic_patterns = working_memory_context.get("semantic_patterns")
    if isinstance(semantic_patterns, list):
        semantic_bias = _semantic_pattern_bias(
            semantic_patterns,
            candidate_profile=candidate_profile,
        )
        if semantic_bias != 0.0:
            total_bias += semantic_bias
            reasons.append("semantic_pattern_bias")

    inherited_priors = working_memory_context.get("inherited_priors")
    if isinstance(inherited_priors, list):
        inherited_bias = _inherited_prior_bias(
            inherited_priors,
            candidate_profile=candidate_profile,
        )
        if inherited_bias != 0.0:
            total_bias += inherited_bias
            reasons.append("inherited_prior_bias")

    bounded_bias = _bounded_learning_bias(total_bias)
    if bounded_bias == 0.0:
        return 0.0, []
    return bounded_bias, reasons


def _recent_negative_outcome_bias(
    recent_relevant_outcomes: list[dict[str, object]],
    *,
    candidate_profile: str,
) -> float:
    """Return a small negative bias from a recent, confident matching negative outcome."""

    for outcome in reversed(recent_relevant_outcomes):
        if str(outcome.get("candidate_profile") or "") != candidate_profile:
            continue
        confidence = float(outcome.get("confidence", 0.0))
        if confidence < 0.75:
            return 0.0
        outcome_delta = float(outcome.get("outcome_delta", 0.0))
        evaluation_label = str(outcome.get("evaluation_label") or "unknown")
        if outcome_delta < 0.0:
            return _bounded_learning_bias(max(-0.2, outcome_delta * 0.15))
        if evaluation_label == "negative":
            return -0.1
        return 0.0
    return 0.0


def _semantic_pattern_bias(
    semantic_patterns: list[dict[str, object]],
    *,
    candidate_profile: str,
) -> float:
    """Return a tiny bounded bias from matching semantic-memory guidance."""

    for pattern in semantic_patterns:
        preferred_profiles = pattern.get("preferred_candidate_profiles")
        if not isinstance(preferred_profiles, list) or candidate_profile not in preferred_profiles:
            continue
        confidence = float(pattern.get("confidence", 0.0))
        if confidence <= 0.0:
            return 0.0
        return min(0.08, confidence * 0.08)
    return 0.0



def _inherited_prior_bias(
    inherited_priors: list[dict[str, object]],
    *,
    candidate_profile: str,
) -> float:
    """Return a tiny bounded bias from same-scenario inherited priors."""

    for prior in inherited_priors:
        if str(prior.get("candidate_profile") or "") != candidate_profile:
            continue
        confidence = float(prior.get("confidence", 0.0))
        stability_score = float(prior.get("stability_score", 0.0))
        evidence_count = int(prior.get("evidence_count", 0))
        if confidence < 0.5 or stability_score < 0.5 or evidence_count < 2:
            return 0.0
        bias_strength = float(prior.get("bias_strength", 0.0))
        if bias_strength == 0.0:
            return 0.0
        return _bounded_learning_bias(max(-0.06, min(0.06, bias_strength * 0.06)))
    return 0.0



def _habit_skill_priority_bonus(parameter_domain: dict[str, object]) -> float:
    """Return a tiny bounded bonus for a crystallized habit-skill candidate hint."""

    if not bool(parameter_domain.get("habit_skill_match", False)):
        return 0.0
    confidence = float(parameter_domain.get("habit_skill_confidence", 0.0))
    evidence_count = int(parameter_domain.get("habit_skill_evidence_count", 0))
    if confidence < 0.6 or evidence_count < 3:
        return 0.0
    return min(0.1, confidence * 0.1)



def _bounded_learning_bias(raw_bias: float) -> float:
    """Clamp learning bias so it stays advisory and bounded."""

    return max(-0.35, min(0.35, raw_bias))


# ── PR-O1: robust-scoring primitives (ofc-robust-scoring plan §3 / A G1 Q1,Q3) ──
# Pure helpers; not wired into assess_candidates yet (a later slice does the
# aggregation rewrite with Linux A/B equivalence). Kept standalone + unit-tested
# so the math is verified before it touches the shared (Linux+Crafter) scorer.

def robust_normalize(value: float, *, scale: float) -> float:
    """Normalize a signed factor via tanh — sign-preserving + saturating.

    ``tanh(value / scale)`` maps R → (-1, 1): it keeps the sign (a negative factor
    stays a penalty — A G1 Q1: NOT clipped to [0, 1], which would drop the
    anti-drive veto signal) and saturates extremes (raw 0.99 vs 0.90 do not blow
    apart). ``scale`` is the per-factor calibration constant (the calibrated
    absolute range, NOT candidate-set min-max). A zero scale = "no signal" → 0.0
    (avoids divide-by-zero).
    """

    if scale == 0.0:
        return 0.0
    return math.tanh(value / scale)


def cap_group_contribution(value: float, *, cap: float) -> float:
    """Cap the SUMMED contribution of the experience factor group (A G1 Q3).

    Clips the experience group's combined weighted contribution to [-cap, +cap]
    so the experience factors (learning_bias / habit / semantic) cannot collude
    (plan §1.3) to overturn the drive + dlpfc main judgment. Caps the sum — not
    each factor individually.
    """

    return max(-cap, min(cap, value))
