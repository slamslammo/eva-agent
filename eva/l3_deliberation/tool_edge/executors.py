"""Canonical mediated external execution helpers for the L3 tool-edge."""

from __future__ import annotations

from typing import Any, Protocol

from ...kernel import ActivePressure, StateStore
from ..contracts import ReleaseToken
from ..peer_circuit.mediator import validate_release_token
from .tool_registry import ESCALATE_ACTION, RECHECK_ACTION, REPAIR_ACTION, ResponseSelection, _pressure_reason

__all__ = [
    "ConservativeRuntime",
    "execute_response_action",
]


class ConservativeRuntime(Protocol):
    """Minimal runtime hook used by repair actions."""

    def activate_conservative_until_next_patrol(self) -> None: ...



def execute_response_action(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: Any,
    selection: ResponseSelection,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
    release_token: ReleaseToken | None = None,
    selected_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Execute the selected v1 action and return a structured result."""

    validate_release_token(
        release_token,
        selected_candidate_id=selected_candidate_id,
        expected_outcome="compatibility_release",
    )
    if selection.selected_action == RECHECK_ACTION:
        return _execute_recheck_action(store, pressure)
    if selection.selected_action == REPAIR_ACTION:
        if runtime is not None and allow_repair_side_effects:
            runtime.activate_conservative_until_next_patrol()
        return {
            "execution_status": "completed",
            "pressure_outcome": "unknown",
            "side_effects": ["temporary_conservative_until_next_patrol"] if runtime is not None and allow_repair_side_effects else [],
            "uncertainty_after_action": "still_needs_confirmation",
            "followup_needed": True,
            "integration_hint": "worth_review",
        }
    return {
        "execution_status": "escalated",
        "pressure_outcome": "unchanged",
        "side_effects": [],
        "uncertainty_after_action": "cannot_determine_safely",
        "followup_needed": True,
        "integration_hint": "needs_human_review",
    }



def _execute_recheck_action(store: StateStore, pressure: ActivePressure) -> dict[str, Any]:
    """Re-read current runtime artifacts and compare them with the active pressure."""

    artifacts_ok = all(
        path.exists()
        for path in (
            store.paths.active_instance_file,
            store.paths.runtime_state_file,
            store.paths.active_pressures_file,
            store.paths.events_file,
        )
    )
    if not artifacts_ok:
        return {
            "execution_status": "failed",
            "pressure_outcome": "unknown",
            "side_effects": [],
            "uncertainty_after_action": "cannot_determine_safely",
            "followup_needed": True,
            "integration_hint": "needs_human_review",
        }

    active_pressures = store.read_active_pressures()
    matching = [item for item in active_pressures.pressures if item.pressure_id == pressure.pressure_id]
    if not matching:
        return {
            "execution_status": "completed",
            "pressure_outcome": "relieved",
            "side_effects": [],
            "uncertainty_after_action": "resolved_enough",
            "followup_needed": False,
            "integration_hint": "none",
        }

    current_reason = _pressure_reason(matching[0])
    if current_reason == _pressure_reason(pressure):
        return {
            "execution_status": "completed",
            "pressure_outcome": "unchanged",
            "side_effects": [],
            "uncertainty_after_action": "still_needs_confirmation",
            "followup_needed": True,
            "integration_hint": "worth_review",
        }
    return {
        "execution_status": "completed",
        "pressure_outcome": "unknown",
        "side_effects": [],
        "uncertainty_after_action": "cannot_determine_safely",
        "followup_needed": True,
        "integration_hint": "worth_review",
    }



def _allow_repair_side_effects(*, bridge_policy: dict[str, Any] | None, default: bool) -> bool:
    """Return whether repair side effects are permitted under the current bridge policy."""

    if not isinstance(bridge_policy, dict):
        return default
    execution = bridge_policy.get("execution")
    if not isinstance(execution, dict):
        return default
    configured = execution.get("allow_repair_side_effects")
    if isinstance(configured, bool):
        return configured
    return default
