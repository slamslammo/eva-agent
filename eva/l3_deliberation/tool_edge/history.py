"""History payload helpers for the bounded L3 tool-edge bridge."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING

from ...kernel import ActivePressure, RuntimeState, StateStore, to_iso8601

if TYPE_CHECKING:
    from .tool_registry import ResponseSelection

from .tool_registry import get_action_constants

OPTIONAL_EXECUTION_FIELDS = (
    "achievement_delta",
    "inventory_delta",
    "life_delta",
    "visible_threat_count",
)


def _optional_execution_fields(execution_result: dict[str, Any]) -> dict[str, Any]:
    return {
        field_name: execution_result[field_name]
        for field_name in OPTIONAL_EXECUTION_FIELDS
        if field_name in execution_result
    }

__all__ = ["append_response_history", "build_response_selected_event_details", "build_response_summary"]


def append_response_history(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    selection: ResponseSelection,
    execution_result: dict[str, Any],
    now: datetime,
    drive_context: dict[str, Any] | None = None,
    release_context: dict[str, Any] | None = None,
    response_mode: str | None = None,
) -> dict[str, Any]:
    """Append one complete Step 2 response record and return it."""

    payload = {
        "response_id": f"resp-{selection.pressure_id}-{int(now.timestamp())}",
        "recorded_at": to_iso8601(now),
        "response_mode": response_mode or get_action_constants().default_response_mode,
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "pressure_severity": pressure.severity,
        "pressure_trend": pressure.trend,
        "pressure_reason": _pressure_reason(pressure),
        "life_state": runtime_state.life_state,
        "instance_valid": runtime_state.instance_valid,
        "state_mode": selection.state_mode,
        "candidate_actions": list(selection.candidate_actions),
        "selected_action": selection.selected_action,
        "selected_posture": selection.selected_posture,
        "selected_action_reason": selection.selected_action_reason,
        "filter_result": selection.filter_result,
        "denied_actions": list(selection.denied_actions),
        "discouraged_actions": list(selection.discouraged_actions),
        "filter_reasons": list(selection.filter_reasons),
        "execution_status": execution_result["execution_status"],
        "pressure_outcome": execution_result["pressure_outcome"],
        "side_effects": execution_result["side_effects"],
        "uncertainty_after_action": execution_result["uncertainty_after_action"],
        "integration_hint": execution_result["integration_hint"],
        "followup_needed": execution_result["followup_needed"],
        # PR-S1 §3.5 R12: scenario-time observability. ``env_step_invoked``
        # comes from the bridge payload (False on deferred / fallback paths,
        # True after a successful step_external_action). ``deferred_reason``
        # is None unless bridge marked the selection deferred.
        # Default True for back-compat: wall_clock scenarios (Linux) never set
        # this and always step; only PR-S1-updated bridges (Crafter) emit False
        # on the deferred path. Mirrors the lifecycle counter-update default.
        "env_step_invoked": bool(execution_result.get("env_step_invoked", True)),
        "deferred_reason": execution_result.get("deferred_reason"),
        "is_deferred": bool(selection.is_deferred),
    }
    if drive_context is not None:
        payload["drive_context"] = drive_context
    if release_context is not None:
        payload["release_context"] = dict(release_context)
    payload.update(_optional_execution_fields(execution_result))
    store.append_response_history(payload)
    return payload



def build_response_summary(
    pressure: ActivePressure,
    selection: ResponseSelection,
    execution_result: dict[str, Any],
    *,
    drive_context: dict[str, Any] | None = None,
    response_mode: str | None = None,
) -> dict[str, Any]:
    """Build the bounded response summary returned to lifecycle after execution."""

    payload = {
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "selected_action": selection.selected_action,
        "selected_posture": selection.selected_posture,
        # Round 1.I I-2: carry the selection reason in the summary too (the persisted
        # response_history record already has it) so bridge.resolve_action trace records
        # the action_hint causal reason instead of None. Inert for events (those read
        # only named keys), so flag-off stays byte-equivalent.
        "selected_action_reason": selection.selected_action_reason,
        "execution_status": execution_result["execution_status"],
        "pressure_outcome": execution_result["pressure_outcome"],
        "followup_needed": execution_result["followup_needed"],
        "response_mode": response_mode or get_action_constants().default_response_mode,
        # PR-S1 §3.5: scenario-time signal needed by lifecycle to update its
        # dual counters (attempt_index / scenario_step_index). Default False
        # so legacy execution_result dicts (no env_step_invoked key) are
        # treated as "no advance" — safer than guessing.
        # Default True for back-compat: wall_clock scenarios (Linux) never set
        # this and always step; only PR-S1-updated bridges (Crafter) emit False
        # on the deferred path. Mirrors the lifecycle counter-update default.
        "env_step_invoked": bool(execution_result.get("env_step_invoked", True)),
    }
    if drive_context is not None:
        payload["drive_context"] = drive_context
    payload.update(_optional_execution_fields(execution_result))
    return payload



def build_response_selected_event_details(
    response_summary: dict[str, Any],
    *,
    work_slice: str,
    work_kind: str,
    selected_candidate_id: str | None = None,
    habit_narrowed: bool = False,
    habit_narrowed_from: int | None = None,
) -> dict[str, Any]:
    """Build the minimal downstream response_selected event payload."""

    payload = {
        "work_slice": work_slice,
        "work_kind": work_kind,
        "pressure_id": response_summary["pressure_id"],
        "pressure_type": response_summary["pressure_type"],
        "selected_action": response_summary["selected_action"],
    }
    if selected_candidate_id is not None:
        payload["selected_candidate_id"] = selected_candidate_id
    if habit_narrowed:
        payload["habit_narrowed"] = True
    if habit_narrowed_from is not None:
        payload["habit_narrowed_from"] = int(habit_narrowed_from)
    return payload



def _pressure_reason(pressure: ActivePressure) -> str:
    """Return the normalized reason string for one active pressure."""

    return str(pressure.evidence.get("reason") or "unknown")
