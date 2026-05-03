"""Rule-based value judgment for the minimal Phase B / early Phase C L3 skeleton."""

from __future__ import annotations

from .candidate_generation import OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE
from .conflict_detection import build_candidate_conflict_context
from ..contracts import Candidate, CandidateAssessment, DeliberationInput


def assess_candidates(candidates: list[Candidate], deliberation_input: DeliberationInput) -> list[CandidateAssessment]:
    """Assess candidates using drive/signal pressure plus anchored runtime boundaries."""

    signal_summary = deliberation_input.signal_batch.get("summary", {})
    threat_count = int(signal_summary.get("threat_signal_count", 0))
    top_drive = str(deliberation_input.drive_broadcast.get("top_drive") or "unknown")

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
        )
        if candidate.action == "compatibility_release":
            candidate_profile = conflict.candidate_profile
            if candidate_profile in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE}:
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
                score = 1.0 + conflict.score_delta
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


def _bounded_learning_bias(raw_bias: float) -> float:
    """Clamp learning bias so it stays advisory and bounded."""

    return max(-0.35, min(0.35, raw_bias))
