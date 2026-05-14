"""Rule-based bounded compatibility bridge owned by the L3 tool-edge namespace."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ...kernel import RuntimeState, StateStore
from ...scenario_bundle import get_active_runtime_scenario
from ..contracts import ReleaseToken
from .executors import ConservativeRuntime, execute_integrity_selection
from .history import append_response_history, build_response_summary
from .tool_registry import (
    ResponseCandidate,
    ResponseFilterDecision,
    ResponseSelection,
    build_integrity_response_candidates,
    filter_response_candidates,
    get_action_constants,
    response_mode_from_release_context,
    select_integrity_response,
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
    "get_default_response_mode",
    "select_integrity_response",
    "select_response_action",
    "execute_integrity_selection",
    "respond_to_integrity_pressure",
    "maybe_respond_after_patrol",
]


def get_default_response_mode() -> str:
    """Return the current scenario default response mode."""

    return get_action_constants().default_response_mode


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
    release_token: ReleaseToken | None = None,
    selected_candidate_id: str | None = None,
) -> dict[str, object]:
    """Run the compatibility-only response closure for one integrity pressure."""

    normalized_release_context = None if release_context is None else dict(release_context)
    selection = select_integrity_response(
        pressure,
        runtime_state,
        release_context=normalized_release_context,
    )
    execution_result = execute_integrity_selection(
        store,
        pressure,
        runtime_state,
        selection,
        runtime=runtime,
        allow_repair_side_effects=allow_repair_side_effects,
        release_context=normalized_release_context,
        release_token=release_token,
        selected_candidate_id=selected_candidate_id,
    )
    response_mode = response_mode_from_release_context(normalized_release_context)
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
    return build_response_summary(
        pressure,
        selection,
        execution_result,
        drive_context=drive_context_payload,
        response_mode=response_mode,
    )


def maybe_respond_after_patrol(
    store: StateStore,
    runtime_state: RuntimeState,
    now: datetime,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
    drive_context: DriveBroadcast | dict[str, object] | None = None,
    release_context: dict[str, object] | None = None,
    release_token: ReleaseToken | None = None,
    selected_candidate_id: str | None = None,
) -> dict[str, object] | None:
    """Run the compatibility-only post-patrol response when a compatible pressure exists."""

    pressure = _pressure_for_active_scenario(store)
    if pressure is None:
        return None
    return respond_to_integrity_pressure(
        store,
        pressure,
        runtime_state,
        now,
        runtime=runtime,
        allow_repair_side_effects=allow_repair_side_effects,
        drive_context=drive_context,
        release_context=release_context,
        release_token=release_token,
        selected_candidate_id=selected_candidate_id,
    )


def _pressure_for_active_scenario(store: StateStore) -> ActivePressure | None:
    """Return the active pressure currently eligible for the bounded compatibility path."""

    pressure_table = store.read_active_pressures()
    scenario_name = get_active_runtime_scenario().name
    if scenario_name == "crafter":
        return pressure_table.pressures[0] if pressure_table.pressures else None
    for pressure in pressure_table.pressures:
        if pressure.type == "integrity":
            return pressure
    return None
