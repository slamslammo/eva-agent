"""Rule-based value judgment for the minimal Phase B / early Phase C L3 skeleton."""

from __future__ import annotations

from .candidate_generation import current_anchor_profiles
from .conflict_detection import build_candidate_conflict_context
from ..contracts import Candidate, CandidateAssessment, DeliberationInput
from ..peer_circuit.rpe import build_learned_impact_overlay


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
                advisory_bonus, advisory_reasons = _llm_advisory_bonus_for_candidate_profile(
                    deliberation_input,
                    candidate_profile=candidate_profile,
                )
                if advisory_bonus != 0.0:
                    score += advisory_bonus
                    reasons.extend(reason for reason in advisory_reasons if reason not in reasons)
        else:
            disposition = conflict.disposition
            reasons.extend(reason for reason in conflict.reasons if reason not in reasons)
        assessments.append(
            CandidateAssessment(
                candidate_id=candidate.candidate_id,
                action=candidate.action,
                score=round(score, 6),
                disposition=disposition,
                reasons=tuple(reasons),
                learning_bias=round(learning_bias, 6),
                bias_reasons=tuple(bias_reasons),
            )
        )
    return assessments


def _effective_drive_impact_schema(
    deliberation_input: DeliberationInput,
    *,
    candidate_profile: str,
    top_drive: str,
    drive_impact_schema: dict[str, float],
) -> tuple[dict[str, float], list[str]]:
    """Return the effective impact schema after any bounded learned overlay."""

    effective_schema = dict(drive_impact_schema)
    learned_overlay, blend_factor = build_learned_impact_overlay(
        deliberation_input.working_memory_context,
        candidate_profile=candidate_profile,
        top_drive=top_drive,
    )
    if not learned_overlay or blend_factor <= 0.0:
        return effective_schema, []
    for drive_name, learned_signal in learned_overlay.items():
        baseline = float(effective_schema.get(drive_name, 0.0))
        effective_schema[drive_name] = _bounded_drive_impact_value(
            ((1.0 - blend_factor) * baseline) + (blend_factor * float(learned_signal))
        )
    return effective_schema, ["learned_impact_overlay"]


def _drive_weighted_score(
    drive_impact_schema: dict[str, float],
    drive_levels: dict[str, object],
) -> float:
    """Return the main candidate score from continuous drive levels and predicted impact."""

    if not drive_impact_schema:
        return 0.0
    score = 0.0
    for drive_name in ("survival", "integrity", "continuity", "curiosity"):
        score += float(drive_levels.get(drive_name, 0.0)) * float(drive_impact_schema.get(drive_name, 0.0))
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


def _habit_skill_priority_bonus(parameter_domain: dict[str, object]) -> float:
    """Return a tiny bounded bonus for a crystallized habit-skill candidate hint."""

    if not bool(parameter_domain.get("habit_skill_match", False)):
        return 0.0
    confidence = float(parameter_domain.get("habit_skill_confidence", 0.0))
    evidence_count = int(parameter_domain.get("habit_skill_evidence_count", 0))
    if confidence < 0.6 or evidence_count < 3:
        return 0.0
    return min(0.1, confidence * 0.1)



def _llm_advisory_bonus_for_candidate_profile(
    deliberation_input: DeliberationInput,
    *,
    candidate_profile: str,
) -> tuple[float, list[str]]:
    """Return a tiny bounded advisory bias for one admitted candidate profile."""

    working_memory_context = deliberation_input.working_memory_context or {}
    if str(working_memory_context.get("source_backend") or "") != "llm_assisted":
        return 0.0, []
    advisory_context = working_memory_context.get("advisory_context")
    if not isinstance(advisory_context, dict):
        return 0.0, []
    candidate_suggestions = advisory_context.get("candidate_suggestions")
    if not isinstance(candidate_suggestions, list) or candidate_profile not in candidate_suggestions:
        return 0.0, []
    advisory_confidence = float(advisory_context.get("confidence", 0.0))
    if advisory_confidence <= 0.0:
        return 0.0, []
    bounded_bonus = min(0.12, advisory_confidence * 0.12)
    return bounded_bonus, ["llm_advisory_candidate_preference"]



def _bounded_learning_bias(raw_bias: float) -> float:
    """Clamp learning bias so it stays advisory and bounded."""

    return max(-0.35, min(0.35, raw_bias))
