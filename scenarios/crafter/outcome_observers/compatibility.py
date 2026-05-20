"""Crafter outcome observers for Stage H H-2."""

from __future__ import annotations

from typing import Any

from eva.l3_deliberation.contracts import OutcomeVector

from ..prior_skills import habit_skill_match_for_candidate_profile

OUTCOME_DELTA_WEIGHTS = {
    "viability": 1.0,
    "resource": 0.2,
    "capability": 0.3,
    "risk": -1.0,
}


def _confidence_from_uncertainty(uncertainty: float) -> float:
    """Map observed uncertainty onto a bounded compatibility confidence."""

    return round(max(0.0, min(1.0, 1.0 - (uncertainty * 0.5))), 2)


def expected_outcome_for_release(outcome: str, candidate_profile: str | None) -> str:
    if outcome == "compatibility_release":
        if candidate_profile == "observe_first":
            return "gather_safe_information"
        if candidate_profile == "stabilize_first":
            return "stabilize_avatar_state"
        if candidate_profile == "escalate_first":
            return "high_risk_interaction"
        return "bounded_crafter_action"
    if outcome == "defer":
        return "wait_for_safer_state"
    return "no_external_change"


def evaluate_response_outcome(
    response_summary: dict[str, Any],
    response_history_entry: dict[str, Any] | None = None,
) -> tuple[str, float, str, float, OutcomeVector]:
    history = {} if response_history_entry is None else dict(response_history_entry)
    selected_action = str(history.get("selected_action") or response_summary.get("selected_action") or "noop")
    achievement_delta = float(history.get("achievement_delta") or response_summary.get("achievement_delta") or 0.0)
    inventory_delta = dict(history.get("inventory_delta") or response_summary.get("inventory_delta") or {})
    life_delta = dict(history.get("life_delta") or response_summary.get("life_delta") or {})
    threat_count = int(history.get("visible_threat_count") or response_summary.get("visible_threat_count") or 0)
    followup_needed = bool(history.get("followup_needed") if "followup_needed" in history else response_summary.get("followup_needed"))

    # Fix-A: only real measured life change earns viability; the old idle-sleep +0.2 default rewarded inaction and habit-learning locked the agent into passive sleep.
    viability_score = sum(float(value) for value in life_delta.values()) if life_delta else 0.0
    resource_score = sum(float(value) for value in inventory_delta.values()) if inventory_delta else 0.0
    capability_score = 1.0 if selected_action.startswith("make_") or selected_action.startswith("place_") else 0.0
    task_progress = achievement_delta if achievement_delta != 0.0 else None
    # Fix-A: under a visible threat, sleeping is the most dangerous (vulnerable) and engaging via `do` is the appropriate, only mildly risky response; the old mapping perversely rewarded sleeping through danger and punished engaging.
    if threat_count > 0:
        risk_delta = 0.5 if selected_action == "sleep" else 0.2 if selected_action == "do" else 0.3
    else:
        risk_delta = 0.0
    reversibility = 1.0 if selected_action.startswith("move_") or selected_action == "noop" else 0.5 if selected_action in {"do", "sleep"} else 0.1
    uncertainty = 0.8 if followup_needed else 0.4
    confidence = _confidence_from_uncertainty(uncertainty)
    outcome_delta = round(
        (OUTCOME_DELTA_WEIGHTS["viability"] * viability_score)
        + (OUTCOME_DELTA_WEIGHTS["resource"] * resource_score)
        + (OUTCOME_DELTA_WEIGHTS["capability"] * capability_score)
        + (OUTCOME_DELTA_WEIGHTS["risk"] * risk_delta),
        3,
    )
    if outcome_delta > 0.0:
        label = "positive"
        observed = "improved"
    elif outcome_delta < 0.0:
        label = "negative"
        observed = "degraded"
    else:
        label = "uncertain"
        observed = "unchanged"
    return (
        observed,
        outcome_delta,
        label,
        confidence,
        OutcomeVector(
            task_progress=task_progress,
            viability_delta=life_delta or None,
            resource_delta=inventory_delta or None,
            capability_delta={"craft_or_place": capability_score} if capability_score else None,
            risk_delta=risk_delta,
            reversibility=reversibility,
            cost={"action_count": 1.0},
            uncertainty=uncertainty,
        ),
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
    return {
        "scenario": "crafter",
        "execution_status": execution_status,
        "pressure_outcome": pressure_outcome,
        "followup_needed": followup_needed,
        "uncertainty_after_action": uncertainty_after_action,
        "top_drive": top_drive,
        "life_state": life_state,
        "pressure_reason": pressure_reason,
        "situation_key": situation_key,
        "candidate_profile": candidate_profile,
        "habit_narrowed": bool(learning_context.get("habit_narrowed", False)),
        "habit_skill_match": habit_skill_match_for_candidate_profile(candidate_profile),
    }


__all__ = [
    "OUTCOME_DELTA_WEIGHTS",
    "build_learning_outcome_content",
    "evaluate_response_outcome",
    "expected_outcome_for_release",
]
