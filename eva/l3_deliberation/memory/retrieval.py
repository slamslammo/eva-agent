"""Read-side retrieval helpers for working-memory context assembly."""

from __future__ import annotations

from typing import Any

from ..contracts import DeliberationInput
from .skill_library import _situation_key_from_learning_outcome, build_situation_key_from_values

MIN_SIMILAR_DRIVE_MATCH = 0.5


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
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    drive_levels: dict[str, Any] | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Return bounded recent learning outcomes ranked by situation relevance."""

    ranked: list[tuple[float, float, str, dict[str, Any]]] = []
    for record in learning_outcomes:
        match_score = _learning_outcome_match_score(
            record,
            situation_key=situation_key,
            top_drive=top_drive,
            life_state=life_state,
            pressure_reason=pressure_reason,
            drive_levels=drive_levels,
        )
        if match_score <= 0.0:
            continue
        ranked.append(
            (
                match_score,
                float(record.get("confidence", 0.0)),
                str(record.get("recorded_at") or ""),
                record,
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [recent_outcome_trace(record) for _, _, _, record in ranked[:limit]]


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
        "top_drive": content.get("top_drive"),
        "life_state": content.get("life_state"),
        "pressure_reason": record.get("pressure_reason") or content.get("pressure_reason"),
        "situation_key": _situation_key_from_learning_outcome(record),
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
    drive_levels: dict[str, Any] | None = None,
    limit: int,
) -> list[dict[str, Any]]:
    """Return compact recent response history entries when episodic traces do not yet exist."""

    ranked: list[tuple[float, str, dict[str, Any]]] = []
    for entry in response_history:
        drive_context = entry.get("drive_context") or {}
        match_score = _response_history_match_score(
            entry,
            top_drive=top_drive,
            life_state=life_state,
            pressure_reason=pressure_reason,
            drive_levels=drive_levels,
        )
        if match_score <= 0.0:
            continue
        ranked.append(
            (
                match_score,
                str(entry.get("recorded_at") or ""),
                {
                    "recorded_at": entry.get("recorded_at"),
                    "selected_action": entry.get("selected_action"),
                    "pressure_outcome": entry.get("pressure_outcome"),
                    "execution_status": entry.get("execution_status"),
                    "followup_needed": entry.get("followup_needed"),
                    "top_drive": drive_context.get("top_drive") or top_drive,
                    "life_state": entry.get("life_state") or "unknown",
                    "pressure_reason": entry.get("pressure_reason") or "none",
                    "situation_key": build_situation_key_from_values(
                        top_drive=str(drive_context.get("top_drive") or top_drive),
                        life_state=str(entry.get("life_state") or "unknown"),
                        pressure_reason=str(entry.get("pressure_reason") or "none"),
                    ),
                },
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [trace for _, _, trace in ranked[:limit]]


def recent_cognitive_memory_stub_traces(
    memory_stubs: list[dict[str, Any]],
    *,
    situation_key: str,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    drive_levels: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    """Return bounded episodic traces ranked by situation, drive alignment, and salience."""

    ranked: list[tuple[float, float, str, dict[str, Any]]] = []
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
        salience = _coerced_salience(stub.get("salience"))
        stub_pressure_reason = _memory_stub_pressure_reason(content)
        stub_life_state = _memory_stub_life_state(content)
        stub_situation_key = _memory_stub_situation_key(content)
        match_score = _memory_stub_match_score(
            situation_key=situation_key,
            top_drive=top_drive,
            life_state=life_state,
            pressure_reason=pressure_reason,
            drive_levels=drive_levels,
            drive_state_at_encoding=drive_state_at_encoding,
            encoded_top_drive=encoded_top_drive,
            stub_pressure_reason=stub_pressure_reason,
            stub_life_state=stub_life_state,
            stub_situation_key=stub_situation_key,
            salience=salience,
        )
        if match_score <= 0.0:
            continue
        habitual_trace = "habitual_neutral"
        habitual_trace_reasons: list[str] = []
        memory_type = str(stub.get("memory_type") or "unknown")
        if memory_type == "threat_trace":
            habitual_trace = "habitual_suppression"
            habitual_trace_reasons.append("threat_trace")
        elif memory_type == "release_trace":
            habitual_trace = "habitual_support"
            habitual_trace_reasons.append("release_trace")
        if salience >= 0.8:
            habitual_trace_reasons.append("high_salience")
        trace = {
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
        if stub_pressure_reason is not None:
            trace["pressure_reason"] = stub_pressure_reason
        if stub_situation_key is not None:
            trace["situation_key"] = stub_situation_key
        if stub_life_state is not None:
            trace["life_state"] = stub_life_state
        if encoded_top_drive:
            trace["top_drive"] = encoded_top_drive
        ranked.append((match_score, salience, str(stub.get("recorded_at") or ""), trace))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [trace for _, _, _, trace in ranked[:limit]]


def _learning_outcome_match_score(
    record: dict[str, Any],
    *,
    situation_key: str,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    drive_levels: dict[str, Any] | None = None,
) -> float:
    """Return a bounded relevance score for one prior learning outcome."""

    content = record.get("content") or {}
    score = 0.0
    has_bounded_match = False
    if _situation_key_from_learning_outcome(record) == situation_key:
        score += 4.0
        has_bounded_match = True
    record_pressure_reason = str(record.get("pressure_reason") or content.get("pressure_reason") or "none")
    record_top_drive = str(content.get("top_drive") or "unknown")
    record_life_state = str(content.get("life_state") or "unknown")
    if pressure_reason != "none" and record_pressure_reason == pressure_reason:
        score += 1.5
        has_bounded_match = True
    if record_life_state == life_state:
        score += 0.5
    drive_similarity = _drive_similarity_from_top_drive(
        top_drive=top_drive,
        drive_levels=drive_levels,
        encoded_top_drive=record_top_drive,
        encoded_drive_levels=content.get("drive_state_at_encoding"),
    )
    if drive_similarity >= MIN_SIMILAR_DRIVE_MATCH:
        has_bounded_match = True
    score += 1.5 * drive_similarity
    if not has_bounded_match:
        return 0.0
    return round(score, 6)


def recent_semantic_memory(
    semantic_entries: list[dict[str, Any]],
    *,
    scenario: str,
    situation_key: str,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Return bounded semantic-memory entries most relevant to the current situation."""

    ranked: list[tuple[float, float, str, dict[str, Any]]] = []
    for entry in semantic_entries:
        scope = entry.get("scope") or {}
        if not isinstance(scope, dict):
            continue
        if str(scope.get("scenario") or "") != scenario:
            continue
        score = 0.0
        has_bounded_match = False
        if str(scope.get("situation_key") or "") == situation_key:
            score += 4.0
            has_bounded_match = True
        if pressure_reason != "none" and str(scope.get("pressure_reason") or "") == pressure_reason:
            score += 1.5
            has_bounded_match = True
        if str(scope.get("life_state") or "") == life_state:
            score += 0.5
        if str(scope.get("top_drive") or "") == top_drive:
            score += 1.5
            has_bounded_match = True
        if not has_bounded_match:
            continue
        confidence = float(entry.get("confidence", 0.0))
        ranked.append((round(score, 6), confidence, str(entry.get("recorded_at") or ""), _semantic_trace(entry)))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [trace for _, _, _, trace in ranked[:limit]]



def _semantic_trace(entry: dict[str, Any]) -> dict[str, Any]:
    """Return one compact semantic-memory trace for working-memory assembly."""

    scope = entry.get("scope") or {}
    provenance = entry.get("provenance") or {}
    trace = {
        "recorded_at": entry.get("recorded_at"),
        "pattern_summary": str(entry.get("pattern_summary") or ""),
        "confidence": float(entry.get("confidence", 0.0)),
        "scope": dict(scope) if isinstance(scope, dict) else {},
        "preferred_candidate_profiles": [
            str(profile)
            for profile in entry.get("preferred_candidate_profiles", [])
            if profile is not None
        ],
        "provenance": dict(provenance) if isinstance(provenance, dict) else {},
    }
    if isinstance(scope, dict):
        for field_name in ("situation_key", "top_drive", "life_state", "pressure_reason", "topic", "scenario"):
            if field_name in scope:
                trace[field_name] = scope.get(field_name)
    return trace



def _memory_stub_match_score(
    *,
    situation_key: str,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    drive_levels: dict[str, Any],
    drive_state_at_encoding: Any,
    encoded_top_drive: str,
    stub_pressure_reason: str | None,
    stub_life_state: str | None,
    stub_situation_key: str | None,
    salience: float,
) -> float:
    """Return a bounded retrieval score for one episodic memory stub."""

    score = 0.0
    has_bounded_match = False
    if stub_situation_key is not None and stub_situation_key == situation_key:
        score += 4.0
        has_bounded_match = True
    if pressure_reason != "none" and stub_pressure_reason is not None and stub_pressure_reason == pressure_reason:
        score += 1.5
        has_bounded_match = True
    drive_similarity = _drive_similarity_from_top_drive(
        top_drive=top_drive,
        drive_levels=drive_levels,
        encoded_top_drive=encoded_top_drive,
        encoded_drive_levels=drive_state_at_encoding,
    )
    if drive_similarity >= MIN_SIMILAR_DRIVE_MATCH:
        has_bounded_match = True
    score += 1.5 * drive_similarity
    if stub_life_state is not None and stub_life_state == life_state:
        score += 0.5
    if not has_bounded_match:
        return 0.0
    score += 0.5 * salience
    return round(score, 6)


def _response_history_match_score(
    entry: dict[str, Any],
    *,
    top_drive: str,
    life_state: str,
    pressure_reason: str,
    drive_levels: dict[str, Any] | None = None,
) -> float:
    """Return a bounded retrieval score for one response-history entry."""

    drive_context = entry.get("drive_context") or {}
    record_top_drive = str(drive_context.get("top_drive") or "unknown")
    record_life_state = str(entry.get("life_state") or "unknown")
    record_pressure_reason = str(entry.get("pressure_reason") or "none")
    score = 0.0
    has_bounded_match = False
    if pressure_reason != "none" and record_pressure_reason == pressure_reason:
        score += 1.5
        has_bounded_match = True
    if record_life_state == life_state:
        score += 0.5
    drive_similarity = _drive_similarity_from_top_drive(
        top_drive=top_drive,
        drive_levels=drive_levels,
        encoded_top_drive=record_top_drive,
        encoded_drive_levels=drive_context.get("drive_levels"),
    )
    if drive_similarity >= MIN_SIMILAR_DRIVE_MATCH:
        has_bounded_match = True
    score += 1.5 * drive_similarity
    if not has_bounded_match:
        return 0.0
    return round(score, 6)


def _drive_similarity_from_top_drive(
    *,
    top_drive: str,
    drive_levels: dict[str, Any] | None,
    encoded_top_drive: str,
    encoded_drive_levels: Any,
) -> float:
    """Return a bounded drive similarity without requiring exact top-drive equality."""

    if top_drive == encoded_top_drive:
        return 1.0
    normalized_levels = drive_levels if isinstance(drive_levels, dict) else {}
    top_level = _coerced_salience(normalized_levels.get(top_drive, 0.0))
    encoded_level = _coerced_salience(normalized_levels.get(encoded_top_drive, 0.0))
    if top_level > 0.0 and encoded_level > 0.0:
        return round(min(top_level, encoded_level), 3)
    return _drive_state_alignment(
        top_drive=top_drive,
        drive_levels=normalized_levels,
        drive_state_at_encoding=encoded_drive_levels,
    )


def _drive_state_alignment(
    *,
    top_drive: str,
    drive_levels: dict[str, Any] | None,
    drive_state_at_encoding: Any,
) -> float:
    """Return how closely one encoded drive snapshot matches the current top-drive level."""

    normalized_levels = drive_levels if isinstance(drive_levels, dict) else {}
    if not isinstance(drive_state_at_encoding, dict):
        return 0.0
    encoded_levels = drive_state_at_encoding.get("drive_levels") or {}
    if not isinstance(encoded_levels, dict):
        return 0.0
    current_level = _coerced_salience(normalized_levels.get(top_drive, 0.0))
    encoded_level = _coerced_salience(encoded_levels.get(top_drive, 0.0))
    if current_level == 0.0 and encoded_level == 0.0:
        return 0.0
    return round(max(0.0, 1.0 - abs(current_level - encoded_level)), 3)


def _memory_stub_pressure_reason(content: dict[str, Any]) -> str | None:
    """Return the stored pressure reason for one memory stub when present."""

    if "pressure_reason" not in content:
        return None
    return str(content.get("pressure_reason") or "none")


def _memory_stub_life_state(content: dict[str, Any]) -> str | None:
    """Return the stored life-state context for one memory stub when present."""

    runtime_gate_context = content.get("runtime_gate_context") or {}
    if not isinstance(runtime_gate_context, dict) or "life_state" not in runtime_gate_context:
        return None
    return str(runtime_gate_context.get("life_state") or "unknown")


def _memory_stub_situation_key(content: dict[str, Any]) -> str | None:
    """Return the stored or derivable situation key for one memory stub when available."""

    stored = content.get("situation_key")
    if stored:
        return str(stored)
    pressure_reason = _memory_stub_pressure_reason(content)
    life_state = _memory_stub_life_state(content)
    drive_state_at_encoding = content.get("drive_state_at_encoding") or {}
    encoded_top_drive = str(drive_state_at_encoding.get("top_drive") or content.get("top_drive") or "")
    if pressure_reason is None or life_state is None or not encoded_top_drive:
        return None
    return build_situation_key_from_values(
        top_drive=encoded_top_drive,
        life_state=life_state,
        pressure_reason=pressure_reason,
    )


def _coerced_salience(value: Any) -> float:
    """Normalize persisted salience for retrieval ranking."""

    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return 0.0
