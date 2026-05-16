"""Linux runtime outcome observation policy for Phase A."""

from __future__ import annotations

from typing import Any

from eva.l3_deliberation.contracts import OutcomeVector

from ..prior_skills import habit_skill_match_for_candidate_profile


def expected_outcome_for_release(outcome: str, candidate_profile: str | None) -> str:
    """Return the Linux runtime expected-outcome label for one mediator outcome."""

    if outcome == "compatibility_release":
        if candidate_profile == "observe_first":
            return "improve_information_under_pressure"
        if candidate_profile == "stabilize_first":
            return "stabilize_or_relieve_pressure"
        if candidate_profile == "escalate_first":
            return "escalate_for_safety_under_pressure"
        return "bounded_pressure_response"
    if outcome == "defer":
        return "wait_for_safer_boundary"
    return "no_external_change"


def evaluate_response_outcome(
    response_summary: dict[str, Any],
    response_history_entry: dict[str, Any] | None = None,
) -> tuple[str, float, str, float, OutcomeVector]:
    """Map the current Linux compatibility response result into a minimal outcome-delta signal."""

    history = {} if response_history_entry is None else dict(response_history_entry)
    execution_status = str(history.get("execution_status") or response_summary.get("execution_status") or "unknown")
    pressure_outcome = str(history.get("pressure_outcome") or response_summary.get("pressure_outcome") or "unknown")
    followup_needed = bool(
        history.get("followup_needed") if "followup_needed" in history else response_summary.get("followup_needed")
    )
    uncertainty_after_action = str(history.get("uncertainty_after_action") or "unknown")

    if execution_status == "failed":
        outcome_delta = -1.0
        return (
            "failed",
            outcome_delta,
            "negative",
            0.95,
            OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=1.0, risk_delta=1.0),
        )
    if execution_status == "escalated":
        outcome_delta = -0.75
        return (
            "escalated",
            outcome_delta,
            "negative",
            0.9,
            OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=0.9, risk_delta=0.75),
        )
    if execution_status == "completed" and pressure_outcome == "relieved" and not followup_needed:
        outcome_delta = 1.0
        confidence = 0.9 if uncertainty_after_action != "cannot_determine_safely" else 0.7
        return (
            "relieved",
            outcome_delta,
            "positive",
            confidence,
            OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=0.2 if confidence >= 0.9 else 0.4, risk_delta=-1.0),
        )
    if execution_status == "completed" and pressure_outcome == "relieved":
        outcome_delta = 0.5
        confidence = 0.75 if uncertainty_after_action != "cannot_determine_safely" else 0.55
        return (
            "partial_relief",
            outcome_delta,
            "positive",
            confidence,
            OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=0.35 if confidence >= 0.75 else 0.55, risk_delta=-0.5),
        )
    if execution_status == "completed" and pressure_outcome == "unchanged":
        outcome_delta = -0.25 if followup_needed else 0.0
        evaluation_label = "negative" if followup_needed else "neutral"
        return (
            "unchanged",
            outcome_delta,
            evaluation_label,
            0.75,
            OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=0.5, risk_delta=0.25 if followup_needed else 0.0),
        )
    if execution_status == "completed" and pressure_outcome == "unknown":
        outcome_delta = 0.0
        return (
            "unknown",
            outcome_delta,
            "uncertain",
            0.4,
            OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=1.0),
        )
    outcome_delta = 0.0
    return (
        "uncertain",
        outcome_delta,
        "uncertain",
        0.3,
        OutcomeVector(viability_delta={"level_1": outcome_delta}, uncertainty=1.0),
    )


def build_learning_outcome_content(
    *,
    candidate_profile: str | None,
    learning_context: dict[str, Any],
    execution_status: Any,
    pressure_outcome: Any,
    followup_needed: bool,
    uncertainty_after_action: Any,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    situation_key: str,
) -> dict[str, Any]:
    """Build the Linux runtime learning-content payload attached to one learning record."""

    return {
        "scenario": "linux_runtime",
        "execution_status": execution_status,
        "pressure_outcome": pressure_outcome,
        "followup_needed": followup_needed,
        "uncertainty_after_action": uncertainty_after_action,
        "top_drive": top_drive,
        "life_state": life_state,
        "pressure_reason": pressure_reason,
        "situation_key": situation_key,
        "habit_skill_match": habit_skill_match_for_candidate_profile(candidate_profile),
        "habit_narrowed": bool(learning_context.get("habit_narrowed", False)),
    }


__all__ = [
    "build_learning_outcome_content",
    "evaluate_response_outcome",
    "expected_outcome_for_release",
]
