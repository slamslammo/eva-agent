"""Rule-based bounded compatibility bridge owned by the L3 tool-edge namespace."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ...kernel import RuntimeState, StateStore
from .executors import ConservativeRuntime, _allow_repair_side_effects, execute_response_action
from .history import append_response_history
from .tool_registry import (
    ResponseCandidate,
    ResponseFilterDecision,
    ResponseSelection,
    build_integrity_response_candidates,
    filter_response_candidates,
    select_response_action,
)

if TYPE_CHECKING:
    from ...kernel import ActivePressure
    from ...l2_drive.broadcast import DriveBroadcast

__all__ = [
    "ResponseCandidate",
    "ResponseFilterDecision",
    "ResponseSelection",
    "ConservativeRuntime",
    "build_integrity_response_candidates",
    "filter_response_candidates",
    "select_response_action",
    "execute_response_action",
    "respond_to_integrity_pressure",
    "maybe_respond_after_patrol",
]


def respond_to_integrity_pressure(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    now: datetime,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
    drive_context: DriveBroadcast | dict[str, object] | None = None,
    release_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run the compatibility-only response closure for one integrity pressure."""

    candidates = build_integrity_response_candidates(pressure, runtime_state)
    decisions = filter_response_candidates(pressure, runtime_state, candidates)
    selection = select_response_action(
        pressure,
        runtime_state,
        candidates,
        decisions,
        bridge_policy=((release_context or {}).get("bridge_policy") if isinstance((release_context or {}).get("bridge_policy"), dict) else None),
    )
    normalized_release_context = None if release_context is None else dict(release_context)
    effective_allow_repair_side_effects = _allow_repair_side_effects(
        bridge_policy=((normalized_release_context or {}).get("bridge_policy") if isinstance((normalized_release_context or {}).get("bridge_policy"), dict) else None),
        default=allow_repair_side_effects,
    )
    execution_result = execute_response_action(
        store,
        pressure,
        runtime_state,
        selection,
        runtime=runtime,
        allow_repair_side_effects=effective_allow_repair_side_effects,
    )
    response_mode = str((normalized_release_context or {}).get("response_mode") or "pressure_led_compatibility")
    drive_context_payload = None if drive_context is None else (drive_context.to_dict() if hasattr(drive_context, "to_dict") else dict(drive_context))
    append_response_history(
        store,
        pressure,
        runtime_state,
        selection,
        execution_result,
        now,
        drive_context=drive_context_payload,
        release_context=normalized_release_context,
        response_mode=response_mode,
    )
    return {
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "selected_action": selection.selected_action,
        "selected_posture": selection.selected_posture,
        "execution_status": execution_result["execution_status"],
        "pressure_outcome": execution_result["pressure_outcome"],
        "followup_needed": execution_result["followup_needed"],
        "drive_context": drive_context_payload,
        "response_mode": response_mode,
    }


def maybe_respond_after_patrol(
    store: StateStore,
    runtime_state: RuntimeState,
    now: datetime,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
    drive_context: DriveBroadcast | dict[str, object] | None = None,
    release_context: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Run the compatibility-only post-patrol response when an integrity pressure exists."""

    pressure_table = store.read_active_pressures()
    for pressure in pressure_table.pressures:
        if pressure.type == "integrity":
            return respond_to_integrity_pressure(
                store,
                pressure,
                runtime_state,
                now,
                runtime=runtime,
                allow_repair_side_effects=allow_repair_side_effects,
                drive_context=drive_context,
                release_context=release_context,
            )
    return None
