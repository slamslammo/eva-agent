"""Canonical habit-path candidate-shaping helpers for the peer-circuit."""

from __future__ import annotations

from typing import Any

from ..contracts import Candidate, DeliberationInput

OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"
MIN_HABIT_NARROWING_EVIDENCE = 4
MIN_HABIT_NARROWING_STABILITY = 0.75
MIN_HABIT_NARROWING_CONFIDENCE = 0.8

__all__ = [
    "crystallized_habit_skill_hints",
    "habitual_candidate_explanations",
    "shape_candidates_with_habit_track",
]


def shape_candidates_with_habit_track(
    candidates: list[Candidate],
    deliberation_input: DeliberationInput,
) -> list[Candidate]:
    """Apply habit-path candidate shaping from already-assembled working memory."""

    habit_skill_hints = crystallized_habit_skill_hints(deliberation_input)
    habitual_explanations = habitual_candidate_explanations(deliberation_input)
    enriched_candidates = [
        _enrich_candidate_with_habit_context(
            candidate,
            habit_skill_hint=habit_skill_hints.get(str(candidate.parameter_domain.get("candidate_profile") or "")),
            habitual_explanation=habitual_explanations.get(str(candidate.parameter_domain.get("candidate_profile") or "")),
        )
        for candidate in candidates
    ]
    narrowed = _narrow_candidates_from_habit_skill(enriched_candidates, habit_skill_hints=habit_skill_hints)
    if narrowed is not None:
        return narrowed
    base_order = {
        OBSERVE_FIRST_PROFILE: 0,
        STABILIZE_FIRST_PROFILE: 1,
    }
    return sorted(
        enriched_candidates,
        key=lambda candidate: _candidate_priority_key(
            candidate,
            habit_skill_hints=habit_skill_hints,
            base_order=base_order,
        ),
    )


def crystallized_habit_skill_hints(deliberation_input: DeliberationInput) -> dict[str, dict[str, Any]]:
    """Return crystallized habit-skill hints keyed by candidate profile."""

    working_memory_context = deliberation_input.working_memory_context or {}
    habit_skills = working_memory_context.get("habit_skills")
    if not isinstance(habit_skills, list):
        return {}
    hints: dict[str, dict[str, Any]] = {}
    for skill in habit_skills:
        if not isinstance(skill, dict) or not bool(skill.get("crystallized", False)):
            continue
        candidate_profile = str(skill.get("candidate_profile") or "")
        if candidate_profile not in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE}:
            continue
        current = hints.get(candidate_profile)
        candidate_hint = {
            "preferred_action": skill.get("preferred_action"),
            "confidence": float(skill.get("confidence", 0.0)),
            "stability_score": float(skill.get("stability_score", 0.0)),
            "evidence_count": int(skill.get("evidence_count", 0)),
        }
        if current is None or _hint_rank(candidate_hint) < _hint_rank(current):
            hints[candidate_profile] = candidate_hint
    return hints


def habitual_candidate_explanations(deliberation_input: DeliberationInput) -> dict[str, dict[str, Any]]:
    """Return compact candidate-level habitual explanations keyed by profile."""

    working_memory_context = deliberation_input.working_memory_context or {}
    explanations: dict[str, dict[str, Any]] = {}

    bias_summaries = working_memory_context.get("bias_summaries")
    if isinstance(bias_summaries, list):
        for summary in bias_summaries:
            if not isinstance(summary, dict):
                continue
            candidate_profile = str(summary.get("candidate_profile") or "")
            if candidate_profile not in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE}:
                continue
            explanations[candidate_profile] = {
                "habit_eligible": bool(summary.get("habit_eligible", False)),
                "habit_eligibility_reasons": list(summary.get("habit_eligibility_reasons") or []),
                "habitual_trace": _habitual_trace_from_summary(summary),
                "habitual_trace_reasons": _habitual_trace_reasons_from_summary(summary),
            }

    recent_relevant_outcomes = working_memory_context.get("recent_relevant_outcomes")
    if isinstance(recent_relevant_outcomes, list):
        for outcome in reversed(recent_relevant_outcomes):
            if not isinstance(outcome, dict):
                continue
            candidate_profile = str(outcome.get("candidate_profile") or "")
            if candidate_profile not in {OBSERVE_FIRST_PROFILE, STABILIZE_FIRST_PROFILE}:
                continue
            entry = explanations.setdefault(candidate_profile, {})
            inferred_trace = _habitual_trace_from_outcome(outcome)
            inferred_reasons = _habitual_trace_reasons_from_outcome(outcome)
            if inferred_trace is not None:
                entry["habitual_trace"] = inferred_trace
            if inferred_reasons:
                entry["habitual_trace_reasons"] = inferred_reasons

    return explanations


def _enrich_candidate_with_habit_context(
    candidate: Candidate,
    *,
    habit_skill_hint: dict[str, Any] | None,
    habitual_explanation: dict[str, Any] | None,
) -> Candidate:
    """Return one candidate with habit-path fields populated."""

    parameter_domain = dict(candidate.parameter_domain)
    justification = list(candidate.justification)
    parameter_domain["habitual_trace"] = "habitual_neutral"
    parameter_domain["habitual_trace_reasons"] = []
    parameter_domain["habit_eligible"] = False
    parameter_domain["habit_eligibility_reasons"] = []
    if habit_skill_hint:
        parameter_domain["habit_skill_match"] = True
        parameter_domain["habit_eligible"] = True
        parameter_domain["habit_skill_confidence"] = float(habit_skill_hint.get("confidence", 0.0))
        parameter_domain["habit_skill_evidence_count"] = int(habit_skill_hint.get("evidence_count", 0))
        if habit_skill_hint.get("preferred_action") is not None:
            parameter_domain["habit_preferred_action"] = str(habit_skill_hint.get("preferred_action"))
            justification.append(f"habit_preferred_action={habit_skill_hint.get('preferred_action')}")
        justification.append("habit_skill_match")
    if habitual_explanation:
        if "habitual_trace" in habitual_explanation:
            parameter_domain["habitual_trace"] = str(habitual_explanation.get("habitual_trace") or "habitual_neutral")
        if "habitual_trace_reasons" in habitual_explanation:
            parameter_domain["habitual_trace_reasons"] = list(habitual_explanation.get("habitual_trace_reasons") or [])
        if "habit_eligible" in habitual_explanation:
            parameter_domain["habit_eligible"] = bool(habitual_explanation.get("habit_eligible", False))
        if "habit_eligibility_reasons" in habitual_explanation:
            parameter_domain["habit_eligibility_reasons"] = list(habitual_explanation.get("habit_eligibility_reasons") or [])
        if parameter_domain["habitual_trace"] == "habitual_suppression":
            justification.append("habitual_suppression_trace")
        elif parameter_domain["habitual_trace"] == "habitual_support":
            justification.append("habitual_support_trace")
    return Candidate(
        candidate_id=candidate.candidate_id,
        capability=candidate.capability,
        action=candidate.action,
        parameter_domain=parameter_domain,
        justification=tuple(justification),
    )


def _habitual_trace_from_outcome(outcome: dict[str, Any]) -> str | None:
    """Infer a habitual trace from one recent outcome entry."""

    explicit_trace = outcome.get("habitual_trace")
    if explicit_trace is not None:
        return str(explicit_trace or "habitual_neutral")
    outcome_delta = float(outcome.get("outcome_delta", 0.0))
    evaluation_label = str(outcome.get("evaluation_label") or "unknown")
    if outcome_delta < 0.0 or evaluation_label == "negative":
        return "habitual_suppression"
    if outcome_delta > 0.0 or evaluation_label == "positive":
        return "habitual_support"
    return None


def _habitual_trace_reasons_from_outcome(outcome: dict[str, Any]) -> list[str]:
    """Infer habitual trace reasons from one recent outcome entry."""

    explicit_reasons = outcome.get("habitual_trace_reasons")
    if isinstance(explicit_reasons, list):
        return [reason for reason in explicit_reasons if isinstance(reason, str) and reason]
    reasons: list[str] = []
    if bool(outcome.get("habit_skill_match", False)):
        reasons.append("habit_skill_match")
    if bool(outcome.get("habit_narrowed", False)):
        reasons.append("habit_narrowed")
    outcome_delta = float(outcome.get("outcome_delta", 0.0))
    evaluation_label = str(outcome.get("evaluation_label") or "unknown")
    if outcome_delta < 0.0 or evaluation_label == "negative":
        reasons.append("recent_negative_feedback")
    elif outcome_delta > 0.0 or evaluation_label == "positive":
        reasons.append("recent_positive_feedback")
    return reasons


def _habitual_trace_from_summary(summary: dict[str, Any]) -> str:
    """Infer a compact habitual trace from one bias summary when no recent trace is present."""

    recent_negative_count = int(summary.get("recent_negative_count", 0))
    last_outcome_delta = float(summary.get("last_outcome_delta", 0.0))
    if recent_negative_count > 0 or last_outcome_delta < 0.0:
        return "habitual_suppression"
    return "habitual_neutral"


def _habitual_trace_reasons_from_summary(summary: dict[str, Any]) -> list[str]:
    """Infer compact habitual trace reasons from one bias summary."""

    reasons: list[str] = []
    if int(summary.get("recent_negative_count", 0)) > 0 or float(summary.get("last_outcome_delta", 0.0)) < 0.0:
        reasons.append("recent_negative_feedback")
    return reasons


def _candidate_priority_key(
    candidate: Candidate,
    *,
    habit_skill_hints: dict[str, dict[str, Any]],
    base_order: dict[str, int],
) -> tuple[float | int | str, ...]:
    """Return a deterministic candidate ordering that prefers crystallized habit hints."""

    candidate_profile = str(candidate.parameter_domain.get("candidate_profile") or "")
    hint = habit_skill_hints.get(candidate_profile, {})
    return (
        0 if hint else 1,
        -float(hint.get("confidence", 0.0)),
        -float(hint.get("stability_score", 0.0)),
        -int(hint.get("evidence_count", 0)),
        base_order.get(candidate_profile, 99),
        candidate.candidate_id,
    )


def _narrow_candidates_from_habit_skill(
    candidates: list[Candidate],
    *,
    habit_skill_hints: dict[str, dict[str, Any]],
) -> list[Candidate] | None:
    """Return a narrowed candidate set only for one strong, unambiguous habit skill."""

    strong_profiles = [
        candidate_profile
        for candidate_profile, hint in habit_skill_hints.items()
        if _eligible_for_candidate_narrowing(hint)
    ]
    if len(strong_profiles) != 1:
        return None
    narrowed_profile = strong_profiles[0]
    narrowed = [candidate for candidate in candidates if str(candidate.parameter_domain.get("candidate_profile") or "") == narrowed_profile]
    if len(narrowed) != 1:
        return None
    candidate = narrowed[0]
    narrowed_domain = dict(candidate.parameter_domain)
    narrowed_domain["habit_narrowed"] = True
    narrowed_domain["habit_narrowed_from"] = len(candidates)
    return [
        Candidate(
            candidate_id=candidate.candidate_id,
            capability=candidate.capability,
            action=candidate.action,
            parameter_domain=narrowed_domain,
            justification=(*candidate.justification, "habit_candidate_narrowing"),
        )
    ]


def _eligible_for_candidate_narrowing(hint: dict[str, Any]) -> bool:
    """Return whether one crystallized habit skill is strong enough to narrow candidates."""

    return bool(
        float(hint.get("confidence", 0.0)) >= MIN_HABIT_NARROWING_CONFIDENCE
        and float(hint.get("stability_score", 0.0)) >= MIN_HABIT_NARROWING_STABILITY
        and int(hint.get("evidence_count", 0)) >= MIN_HABIT_NARROWING_EVIDENCE
    )


def _hint_rank(hint: dict[str, Any]) -> tuple[float, float, int]:
    """Return a comparable rank for one habit-skill hint."""

    return (
        -float(hint.get("confidence", 0.0)),
        -float(hint.get("stability_score", 0.0)),
        -int(hint.get("evidence_count", 0)),
    )
