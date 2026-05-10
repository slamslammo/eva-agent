"""Canonical mediated external execution helpers for the L3 tool-edge."""

from __future__ import annotations

from typing import Any, Protocol

from ...kernel import ActivePressure, StateStore
from ...scenario_bundle import get_active_runtime_scenario
from ..contracts import ReleaseToken
from ..peer_circuit.mediator import validate_release_token
from .tool_registry import ResponseSelection, bridge_policy_from_release_context

__all__ = [
    "ConservativeRuntime",
    "execute_response_action",
    "execute_integrity_selection",
]


class ConservativeRuntime(Protocol):
    """Minimal runtime hook used by repair actions."""

    def activate_conservative_until_next_patrol(self) -> None: ...


def execute_integrity_selection(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: Any,
    selection: ResponseSelection,
    *,
    runtime: ConservativeRuntime | None = None,
    allow_repair_side_effects: bool = True,
    release_context: dict[str, Any] | None = None,
    release_token: ReleaseToken | None = None,
    selected_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Execute one mediated integrity selection under the current bridge policy."""

    return execute_response_action(
        store,
        pressure,
        runtime_state,
        selection,
        runtime=runtime,
        allow_repair_side_effects=_allow_repair_side_effects(
            bridge_policy=bridge_policy_from_release_context(release_context),
            default=allow_repair_side_effects,
        ),
        release_token=release_token,
        selected_candidate_id=selected_candidate_id,
    )


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
    return get_active_runtime_scenario().actions.execute_response_action(
        store,
        pressure,
        selection,
        runtime=runtime,
        allow_repair_side_effects=allow_repair_side_effects,
    )


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
