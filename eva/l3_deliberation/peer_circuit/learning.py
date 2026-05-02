"""Rule-based Phase C outcome evaluation built on the compatibility response path."""

from __future__ import annotations

from typing import Any

from ..contracts import DeliberationAuditRecord, LearningOutcomeRecord
from ..reasoning import build_situation_key_from_values

__all__ = ["build_learning_outcome_record", "evaluate_response_outcome"]


def build_learning_outcome_record(
    recorded_at: str,
    deliberation_audit: DeliberationAuditRecord | dict[str, Any],
    response_summary: dict[str, Any],
    response_history_entry: dict[str, Any] | None = None,
    *,
    source: str = "l3_learning",
) -> LearningOutcomeRecord:
    """Build one Phase C learning record from release intent plus actual response outcome."""

    audit_payload = deliberation_audit.to_dict() if isinstance(deliberation_audit, DeliberationAuditRecord) else dict(deliberation_audit)
    release_decision = dict(audit_payload.get("release_decision") or {})
    release_context = dict(release_decision.get("release_context") or {})
    history = {} if response_history_entry is None else dict(response_history_entry)
    selected_action = str(
        response_summary.get("selected_action")
        or history.get("selected_action")
        or release_decision.get("selected_action")
        or ""
    ) or None
    candidate_profile = str(release_context.get("candidate_profile") or "") or None
    expected_outcome = _expected_outcome(release_decision, candidate_profile)
    observed_outcome, outcome_delta, evaluation_label, confidence = evaluate_response_outcome(response_summary, history)
    drive_context = dict(history.get("drive_context") or response_summary.get("drive_context") or {})
    top_drive = str(drive_context.get("top_drive") or "unknown")
    life_state = str(history.get("life_state") or "unknown")
    pressure_reason = str(history.get("pressure_reason") or "unknown")
    situation_key = build_situation_key_from_values(
        top_drive=top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
    )
    learning_context = dict(release_decision.get("learning_context") or {})
    content = {
        "execution_status": history.get("execution_status") or response_summary.get("execution_status"),
        "pressure_outcome": history.get("pressure_outcome") or response_summary.get("pressure_outcome"),
        "followup_needed": bool(
            history.get("followup_needed")
            if "followup_needed" in history
            else response_summary.get("followup_needed")
        ),
        "uncertainty_after_action": history.get("uncertainty_after_action"),
        "top_drive": top_drive,
        "life_state": life_state,
        "pressure_reason": pressure_reason,
        "situation_key": situation_key,
        "habit_skill_match": candidate_profile in {"observe_first", "stabilize_first"},
        "habit_narrowed": bool(learning_context.get("habit_narrowed", False)),
    }
    return LearningOutcomeRecord(
        recorded_at=recorded_at,
        source=source,
        linked_audit_recorded_at=str(audit_payload.get("recorded_at") or recorded_at),
        linked_response_id=(str(history.get("response_id")) if history.get("response_id") is not None else None),
        selected_action=selected_action,
        candidate_profile=candidate_profile,
        response_mode=str(response_summary.get("response_mode") or history.get("response_mode") or release_context.get("response_mode") or "") or None,
        pressure_id=(str(response_summary.get("pressure_id")) if response_summary.get("pressure_id") is not None else (str(history.get("pressure_id")) if history.get("pressure_id") is not None else None)),
        pressure_type=(str(response_summary.get("pressure_type")) if response_summary.get("pressure_type") is not None else (str(history.get("pressure_type")) if history.get("pressure_type") is not None else None)),
        pressure_reason=pressure_reason,
        expected_outcome=expected_outcome,
        observed_outcome=observed_outcome,
        outcome_delta=outcome_delta,
        rpe_like_score=outcome_delta,
        evaluation_label=evaluation_label,
        confidence=confidence,
        content=content,
    )


def evaluate_response_outcome(
    response_summary: dict[str, Any],
    response_history_entry: dict[str, Any] | None = None,
) -> tuple[str, float, str, float]:
    """Map the compatibility response result into a minimal outcome-delta signal."""

    history = {} if response_history_entry is None else dict(response_history_entry)
    execution_status = str(history.get("execution_status") or response_summary.get("execution_status") or "unknown")
    pressure_outcome = str(history.get("pressure_outcome") or response_summary.get("pressure_outcome") or "unknown")
    followup_needed = bool(history.get("followup_needed") if "followup_needed" in history else response_summary.get("followup_needed"))
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


def _expected_outcome(release_decision: dict[str, Any], candidate_profile: str | None) -> str:
    """Return the compact expected-outcome label implied by one release decision."""

    outcome = str(release_decision.get("outcome") or "withhold")
    if outcome == "compatibility_release":
        if candidate_profile == "observe_first":
            return "improve_information_under_pressure"
        if candidate_profile == "stabilize_first":
            return "stabilize_or_relieve_pressure"
        return "bounded_pressure_response"
    if outcome == "defer":
        return "wait_for_safer_boundary"
    return "no_external_change"
