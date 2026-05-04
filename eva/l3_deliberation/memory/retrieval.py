"""Read-side retrieval helpers for working-memory context assembly."""

from __future__ import annotations

from typing import Any

from ..contracts import DeliberationInput
from .skill_library import _situation_key_from_learning_outcome


def pressure_reason_from_input(deliberation_input: DeliberationInput) -> str:
    """Return the most relevant pressure reason from the compatibility context."""

    pressure_table = deliberation_input.compatibility_pressure_table or {}
    pressures = pressure_table.get("pressures")
    if isinstance(pressures, list):
        for pressure in pressures:
            if str(pressure.get("type") or "") == "integrity":
                reason = str((pressure.get("evidence") or {}).get("reason") or pressure.get("pressure_reason") or pressure.get("reason") or "")
                if reason:
                    return reason
        if pressures:
            first = pressures[0]
            reason = str((first.get("evidence") or {}).get("reason") or first.get("pressure_reason") or first.get("reason") or "")
            if reason:
                return reason
    return "none"



def recent_learning_outcomes(
    learning_outcomes: list[dict[str, Any]],
    *,
    situation_key: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Return compact recent learning outcomes for one matching situation."""

    matching = [record for record in learning_outcomes if _situation_key_from_learning_outcome(record) == situation_key]
    recent = matching[-limit:]
    return [recent_outcome_trace(record) for record in recent]



def recent_outcome_trace(record: dict[str, Any]) -> dict[str, Any]:
    """Return one compact recent outcome plus habitual trace labels."""

    content = record.get("content") or {}
    habit_skill_match = bool(content.get("habit_skill_match", False))
    habit_narrowed = bool(content.get("habit_narrowed", False))
    outcome_delta = float(record.get("outcome_delta", 0.0))
    evaluation_label = str(record.get("evaluation_label") or "unknown")
    trace_reasons: list[str] = []
    if habit_skill_match:
        trace_reasons.append("habit_skill_match")
    if habit_narrowed:
        trace_reasons.append("habit_narrowed")
    if outcome_delta < 0.0 or evaluation_label == "negative":
        trace_reasons.append("recent_negative_feedback")
    elif outcome_delta > 0.0 or evaluation_label == "positive":
        trace_reasons.append("recent_positive_feedback")
    habitual_trace = "habitual_support"
    if "recent_negative_feedback" in trace_reasons:
        habitual_trace = "habitual_suppression"
    elif not trace_reasons:
        habitual_trace = "habitual_neutral"
    return {
        "recorded_at": record.get("recorded_at"),
        "candidate_profile": record.get("candidate_profile"),
        "selected_action": record.get("selected_action"),
        "observed_outcome": record.get("observed_outcome"),
        "evaluation_label": evaluation_label,
        "outcome_delta": record.get("outcome_delta"),
        "confidence": record.get("confidence", 0.0),
        "habit_skill_match": habit_skill_match,
        "habit_narrowed": habit_narrowed,
        "habitual_trace": habitual_trace,
        "habitual_trace_reasons": trace_reasons,
    }



def latest_habit_bias_summaries(
    habit_bias_entries: list[dict[str, Any]],
    *,
    max_bias_summaries: int,
) -> list[dict[str, Any]]:
    """Return the latest append-only habit-bias entry per candidate profile."""

    latest_by_profile: dict[str, dict[str, Any]] = {}
    for entry in habit_bias_entries:
        candidate_profile = str(entry.get("candidate_profile") or "unknown")
        latest_by_profile[candidate_profile] = dict(entry)
    latest = sorted(
        latest_by_profile.values(),
        key=lambda entry: (
            -float(entry.get("confidence", 0.0)),
            -float(entry.get("stability_score", 0.0)),
            -abs(float(entry.get("bias_strength", 0.0))),
            str(entry.get("candidate_profile") or "unknown"),
        ),
    )
    return latest[:max_bias_summaries]



def recent_response_history(
    response_history: list[dict[str, Any]],
    *,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Return compact recent response history entries when learning outcomes do not yet exist."""

    matching = []
    for entry in response_history:
        drive_context = entry.get("drive_context") or {}
        if str(drive_context.get("top_drive") or "unknown") != str(top_drive):
            continue
        if str(entry.get("life_state") or "unknown") != str(life_state):
            continue
        if str(entry.get("pressure_reason") or "none") != str(pressure_reason):
            continue
        matching.append(
            {
                "recorded_at": entry.get("recorded_at"),
                "selected_action": entry.get("selected_action"),
                "pressure_outcome": entry.get("pressure_outcome"),
                "execution_status": entry.get("execution_status"),
                "followup_needed": entry.get("followup_needed"),
            }
        )
    return matching[-limit:]



def recent_cognitive_memory_stub_traces(
    memory_stubs: list[dict[str, Any]],
    *,
    top_drive: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Return compact recent cognitive-memory stub traces when richer evidence is absent."""

    matching: list[dict[str, Any]] = []
    for stub in memory_stubs:
        if str(stub.get("source") or "") != "l3_deliberation":
            continue
        content = stub.get("content") or {}
        if not isinstance(content, dict):
            continue
        drive_state_at_encoding = content.get("drive_state_at_encoding") or {}
        encoded_top_drive = str(
            drive_state_at_encoding.get("top_drive")
            or content.get("top_drive")
            or "unknown"
        )
        if encoded_top_drive != str(top_drive):
            continue
        memory_type = str(stub.get("memory_type") or "unknown")
        salience = _coerced_salience(stub.get("salience"))
        habitual_trace = "habitual_neutral"
        habitual_trace_reasons: list[str] = []
        if memory_type == "threat_trace":
            habitual_trace = "habitual_suppression"
            habitual_trace_reasons.append("threat_trace")
        elif memory_type == "release_trace":
            habitual_trace = "habitual_support"
            habitual_trace_reasons.append("release_trace")
        if salience >= 0.8:
            habitual_trace_reasons.append("high_salience")
        matching.append(
            {
                "recorded_at": stub.get("recorded_at"),
                "candidate_profile": content.get("candidate_profile"),
                "selected_action": content.get("selected_action"),
                "source": stub.get("source"),
                "memory_type": memory_type,
                "write_reason": stub.get("write_reason"),
                "linked_audit_recorded_at": stub.get("linked_audit_recorded_at"),
                "salience": salience,
                "drive_state_at_encoding": dict(drive_state_at_encoding) if isinstance(drive_state_at_encoding, dict) else {},
                "habitual_trace": habitual_trace,
                "habitual_trace_reasons": habitual_trace_reasons,
            }
        )
    ranked = sorted(
        matching,
        key=lambda trace: (
            -float(trace.get("salience", 0.0)),
            str(trace.get("recorded_at") or ""),
        ),
    )
    return ranked[:limit]


def _coerced_salience(value: Any) -> float:
    """Normalize persisted salience for retrieval ranking."""

    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return 0.0
