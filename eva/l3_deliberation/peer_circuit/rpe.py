"""Canonical peer-circuit prediction/comparison/update helpers for learning outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..contracts import DeliberationAuditRecord

__all__ = [
    "LearningOutcomeRecord",
    "build_learning_outcome_record",
    "evaluate_response_outcome",
    "build_learned_impact_overlay",
]

MIN_LEARNED_IMPACT_EVIDENCE = 10
MIN_LEARNED_IMPACT_CONFIDENCE = 0.6
MIN_LEARNED_IMPACT_STABILITY = 0.6
MAX_LEARNED_IMPACT_BLEND = 0.35
LEARNED_IMPACT_BLEND_STEP = 0.05


@dataclass(frozen=True)
class LearningOutcomeRecord:
    """Append-only Phase C learning record linking release intent to actual outcome."""

    recorded_at: str
    source: str
    linked_audit_recorded_at: str
    linked_response_id: str | None = None
    selected_action: str | None = None
    candidate_profile: str | None = None
    response_mode: str | None = None
    pressure_id: str | None = None
    pressure_type: str | None = None
    pressure_reason: str | None = None
    expected_outcome: str = "unknown"
    observed_outcome: str = "unknown"
    outcome_delta: float = 0.0
    rpe_like_score: float = 0.0
    evaluation_label: str = "uncertain"
    confidence: float = 0.0
    content: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the learning outcome payload."""

        payload = {
            "recorded_at": self.recorded_at,
            "source": self.source,
            "linked_audit_recorded_at": self.linked_audit_recorded_at,
            "expected_outcome": self.expected_outcome,
            "observed_outcome": self.observed_outcome,
            "outcome_delta": self.outcome_delta,
            "rpe_like_score": self.rpe_like_score,
            "evaluation_label": self.evaluation_label,
            "confidence": self.confidence,
            "content": dict(self.content),
        }
        if self.linked_response_id is not None:
            payload["linked_response_id"] = self.linked_response_id
        if self.selected_action is not None:
            payload["selected_action"] = self.selected_action
        if self.candidate_profile is not None:
            payload["candidate_profile"] = self.candidate_profile
        if self.response_mode is not None:
            payload["response_mode"] = self.response_mode
        if self.pressure_id is not None:
            payload["pressure_id"] = self.pressure_id
        if self.pressure_type is not None:
            payload["pressure_type"] = self.pressure_type
        if self.pressure_reason is not None:
            payload["pressure_reason"] = self.pressure_reason
        return payload



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
    from ..memory.skill_library import build_situation_key_from_values

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
        "habit_skill_match": candidate_profile in {"observe_first", "stabilize_first", "escalate_first"},
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


def build_learned_impact_overlay(
    working_memory_context: dict[str, Any] | None,
    *,
    candidate_profile: str,
    top_drive: str,
) -> tuple[dict[str, float], float]:
    """Return a bounded learned impact overlay plus blend factor for one candidate profile."""

    if not isinstance(working_memory_context, dict):
        return {}, 0.0
    bias_summaries = working_memory_context.get("bias_summaries")
    if not isinstance(bias_summaries, list):
        return {}, 0.0
    summary = next(
        (
            item
            for item in bias_summaries
            if isinstance(item, dict) and str(item.get("candidate_profile") or "") == candidate_profile
        ),
        None,
    )
    if summary is None:
        return {}, 0.0
    evidence_count = int(summary.get("evidence_count", 0))
    confidence = float(summary.get("confidence", 0.0))
    stability_score = float(summary.get("stability_score", 0.0))
    if evidence_count < MIN_LEARNED_IMPACT_EVIDENCE:
        return {}, 0.0
    if confidence < MIN_LEARNED_IMPACT_CONFIDENCE or stability_score < MIN_LEARNED_IMPACT_STABILITY:
        return {}, 0.0
    bias_strength = _clamp_signal(float(summary.get("bias_strength", 0.0)))
    last_outcome_delta = _clamp_signal(float(summary.get("last_outcome_delta", 0.0)))
    learned_signal = _clamp_signal((0.6 * bias_strength) + (0.4 * last_outcome_delta))
    recent_signal = _recent_outcome_signal(
        working_memory_context.get("recent_relevant_outcomes"),
        candidate_profile=candidate_profile,
    )
    if recent_signal is not None:
        learned_signal = _clamp_signal((0.75 * learned_signal) + (0.25 * recent_signal))
    blend_factor = min(
        MAX_LEARNED_IMPACT_BLEND,
        max(0.0, (evidence_count - MIN_LEARNED_IMPACT_EVIDENCE + 1) * LEARNED_IMPACT_BLEND_STEP),
    )
    if blend_factor <= 0.0:
        return {}, 0.0
    return {top_drive: learned_signal}, round(blend_factor, 3)



def _expected_outcome(release_decision: dict[str, Any], candidate_profile: str | None) -> str:
    """Return the compact expected-outcome label implied by one release decision."""

    outcome = str(release_decision.get("outcome") or "withhold")
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


def _recent_outcome_signal(
    recent_relevant_outcomes: Any,
    *,
    candidate_profile: str,
) -> float | None:
    """Return one bounded recent-outcome signal for matching candidate profile."""

    if not isinstance(recent_relevant_outcomes, list):
        return None
    for outcome in reversed(recent_relevant_outcomes):
        if not isinstance(outcome, dict):
            continue
        if str(outcome.get("candidate_profile") or "") != candidate_profile:
            continue
        if float(outcome.get("confidence", 0.0)) < 0.75:
            continue
        return _clamp_signal(float(outcome.get("outcome_delta", 0.0)))
    return None


def _clamp_signal(value: float) -> float:
    """Clamp one learned signal so it stays bounded."""

    return max(-1.0, min(1.0, value))
