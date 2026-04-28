"""Rule-based working-memory adapter for the initial Phase C learning layer."""

from __future__ import annotations

from typing import Any

from ..kernel import StateStore
from .contracts import DeliberationInput, HabitBiasSummary, WorkingMemoryContext


def build_situation_key(deliberation_input: DeliberationInput) -> str:
    """Build the compact recurring-situation key for one deliberation input."""

    return build_situation_key_from_values(
        top_drive=str(deliberation_input.drive_broadcast.get("top_drive") or "unknown"),
        life_state=str(deliberation_input.runtime_gate_context.get("life_state") or "unknown"),
        pressure_reason=_pressure_reason_from_input(deliberation_input),
    )


def build_situation_key_from_values(*, top_drive: str, life_state: str, pressure_reason: str) -> str:
    """Build the compact recurring-situation key from normalized values."""

    return "|".join(
        (
            str(top_drive or "unknown"),
            str(life_state or "unknown"),
            str(pressure_reason or "none"),
        )
    )


def build_working_memory_context(
    deliberation_input: DeliberationInput,
    *,
    learning_outcomes: list[dict[str, Any]],
    habit_bias_entries: list[dict[str, Any]] | None = None,
    response_history: list[dict[str, Any]] | None = None,
    memory_stubs: list[dict[str, Any]] | None = None,
    max_bias_summaries: int = 2,
    max_recent_outcomes: int = 3,
) -> WorkingMemoryContext:
    """Build a compact working-memory context from local append-only artifacts."""

    del memory_stubs
    situation_key = build_situation_key(deliberation_input)
    matching_habit_bias = [
        dict(entry)
        for entry in (habit_bias_entries or [])
        if str(entry.get("situation_key") or "") == situation_key
    ]
    if matching_habit_bias:
        bias_summaries = matching_habit_bias[:max_bias_summaries]
    else:
        bias_summaries = [
            summary.to_dict()
            for summary in summarize_habit_bias(learning_outcomes, situation_key=situation_key)[:max_bias_summaries]
        ]
    recent_outcomes = _recent_learning_outcomes(learning_outcomes, situation_key=situation_key, limit=max_recent_outcomes)
    if not recent_outcomes:
        recent_outcomes = _recent_response_history(
            response_history or [],
            top_drive=str(deliberation_input.drive_broadcast.get("top_drive") or "unknown"),
            life_state=str(deliberation_input.runtime_gate_context.get("life_state") or "unknown"),
            pressure_reason=_pressure_reason_from_input(deliberation_input),
            limit=max_recent_outcomes,
        )
    confidence = min(1.0, 0.25 * len(bias_summaries) + 0.2 * len(recent_outcomes))
    return WorkingMemoryContext(
        situation_key=situation_key,
        bias_summaries=bias_summaries,
        recent_relevant_outcomes=recent_outcomes,
        confidence=round(confidence, 3),
        source_backend="local_rule_based",
    )


def build_working_memory_context_from_store(
    store: StateStore,
    deliberation_input: DeliberationInput,
    *,
    max_bias_summaries: int = 2,
    max_recent_outcomes: int = 3,
) -> WorkingMemoryContext:
    """Build working-memory context directly from the runtime store."""

    return build_working_memory_context(
        deliberation_input,
        learning_outcomes=store.read_learning_outcomes(),
        habit_bias_entries=store.read_habit_bias(),
        response_history=store.read_response_history(),
        memory_stubs=store.read_cognitive_memory_stub(),
        max_bias_summaries=max_bias_summaries,
        max_recent_outcomes=max_recent_outcomes,
    )


def summarize_habit_bias(learning_outcomes: list[dict[str, Any]], *, situation_key: str) -> list[HabitBiasSummary]:
    """Summarize recurring positive/negative outcomes into minimal habit-bias entries."""

    grouped: dict[str, dict[str, Any]] = {}
    for record in learning_outcomes:
        if _situation_key_from_learning_outcome(record) != situation_key:
            continue
        candidate_profile = str(record.get("candidate_profile") or "unknown")
        entry = grouped.setdefault(
            candidate_profile,
            {
                "recorded_at": str(record.get("recorded_at") or ""),
                "preferred_action": None,
                "avoid_action": None,
                "support_count": 0,
                "failure_count": 0,
                "last_outcome_delta": 0.0,
            },
        )
        delta = float(record.get("outcome_delta", 0.0))
        action = record.get("selected_action")
        entry["recorded_at"] = str(record.get("recorded_at") or entry["recorded_at"])
        entry["last_outcome_delta"] = delta
        if delta > 0:
            entry["support_count"] += 1
            if action is not None:
                entry["preferred_action"] = str(action)
        elif delta < 0:
            entry["failure_count"] += 1
            if action is not None:
                entry["avoid_action"] = str(action)
    summaries: list[HabitBiasSummary] = []
    for candidate_profile, entry in grouped.items():
        evidence_count = entry["support_count"] + entry["failure_count"]
        bias_strength = 0.0 if evidence_count == 0 else (entry["support_count"] - entry["failure_count"]) / evidence_count
        summaries.append(
            HabitBiasSummary(
                recorded_at=entry["recorded_at"],
                situation_key=situation_key,
                candidate_profile=candidate_profile,
                preferred_action=entry["preferred_action"],
                avoid_action=entry["avoid_action"],
                support_count=int(entry["support_count"]),
                failure_count=int(entry["failure_count"]),
                last_outcome_delta=float(entry["last_outcome_delta"]),
                bias_strength=round(bias_strength, 3),
            )
        )
    return sorted(
        summaries,
        key=lambda summary: (
            -abs(summary.bias_strength),
            -summary.support_count,
            summary.candidate_profile,
        ),
    )


def _pressure_reason_from_input(deliberation_input: DeliberationInput) -> str:
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


def _situation_key_from_learning_outcome(record: dict[str, Any]) -> str:
    """Return the normalized situation key recorded with one learning outcome."""

    content = record.get("content") or {}
    stored = content.get("situation_key")
    if stored:
        return str(stored)
    return build_situation_key_from_values(
        top_drive=str(content.get("top_drive") or "unknown"),
        life_state=str(content.get("life_state") or "unknown"),
        pressure_reason=str(record.get("pressure_reason") or content.get("pressure_reason") or "none"),
    )


def _recent_learning_outcomes(learning_outcomes: list[dict[str, Any]], *, situation_key: str, limit: int) -> list[dict[str, Any]]:
    """Return compact recent learning outcomes for one matching situation."""

    matching = [record for record in learning_outcomes if _situation_key_from_learning_outcome(record) == situation_key]
    recent = matching[-limit:]
    return [
        {
            "recorded_at": record.get("recorded_at"),
            "candidate_profile": record.get("candidate_profile"),
            "selected_action": record.get("selected_action"),
            "observed_outcome": record.get("observed_outcome"),
            "evaluation_label": record.get("evaluation_label"),
            "outcome_delta": record.get("outcome_delta"),
        }
        for record in recent
    ]


def _recent_response_history(
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
