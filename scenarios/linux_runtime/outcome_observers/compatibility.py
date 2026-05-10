"""Linux runtime outcome observation policy for Phase A."""

from __future__ import annotations

from typing import Any

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
) -> tuple[str, float, str, float]:
    """Map the current Linux compatibility response result into a minimal outcome-delta signal."""

    history = {} if response_history_entry is None else dict(response_history_entry)
    execution_status = str(history.get("execution_status") or response_summary.get("execution_status") or "unknown")
    pressure_outcome = str(history.get("pressure_outcome") or response_summary.get("pressure_outcome") or "unknown")
    followup_needed = bool(
        history.get("followup_needed") if "followup_needed" in history else response_summary.get("followup_needed")
    )
    uncertainty_after_action = str(history.get("uncertainty_after_action") or "unknown")

    if execution_status == "failed":
        return ("failed", -1.0, "negative", 0.95)
    if execution_status == "escalated":
        return ("escalated", -0.75, "negative", 0.9)
    if execution_status == "completed" and pressure_outcome == "relieved" and not followup_needed:
        confidence = 0.9 if uncertainty_after_action != "cannot_determine_safely" else 0.7
        return ("relieved", 1.0, "positive", confidence)
    if execution_status == "completed" and pressure_outcome == "relieved":
        confidence = 0.75 if uncertainty_after_action != "cannot_determine_safely" else 0.55
        return ("partial_relief", 0.5, "positive", confidence)
    if execution_status == "completed" and pressure_outcome == "unchanged":
        return ("unchanged", -0.25 if followup_needed else 0.0, "negative" if followup_needed else "neutral", 0.75)
    if execution_status == "completed" and pressure_outcome == "unknown":
        return ("unknown", 0.0, "uncertain", 0.4)
    return ("uncertain", 0.0, "uncertain", 0.3)


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
