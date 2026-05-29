"""Framework action-policy seam and compatibility wrappers for the L3 tool-edge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...kernel import ActivePressure, RuntimeState
from ...scenario_bundle import get_active_runtime_scenario

__all__ = [
    "ActionConstants",
    "ResponseCandidate",
    "ResponseFilterDecision",
    "ResponseSelection",
    "bridge_policy_from_release_context",
    "get_action_constants",
    "response_mode_from_release_context",
    "build_integrity_response_candidates",
    "filter_response_candidates",
    "select_integrity_response",
    "select_response_action",
]


@dataclass(frozen=True)
class ActionConstants:
    """Read-only view of current scenario action vocabulary and metadata."""

    recheck_action: str
    repair_action: str
    escalate_action: str
    default_response_mode: str
    action_to_posture: dict[str, str]
    action_to_state_mode: dict[str, str]
    all_life_states: tuple[str, ...]
    action_to_allowed_states: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ResponseCandidate:
    """One candidate Step 2 action before anchor and state filtering."""

    action: str
    posture: str
    allowed_in_states: tuple[str, ...]


@dataclass(frozen=True)
class ResponseFilterDecision:
    """Filter result for one response candidate."""

    action: str
    result: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResponseSelection:
    """Final response choice after filtering and minimal comparison.

    PR-S1 §3.2: ``is_deferred`` + ``deferred_reason`` let the bridge signal
    "do not advance scenario time" instead of forcing a noop env.step. The
    kernel reads ``is_deferred`` together with the active scenario's
    ``clock_source`` to decide whether to call ``env.step`` (clock_source=
    ``wall_clock`` always steps; clock_source=``step`` skips when deferred).
    Defaults ``False`` / ``None`` preserve Linux byte-equivalence.
    """

    pressure_id: str
    selected_action: str
    selected_posture: str
    selected_action_reason: str
    filter_result: str
    candidate_actions: tuple[str, ...]
    denied_actions: tuple[str, ...]
    discouraged_actions: tuple[str, ...]
    filter_reasons: tuple[str, ...]
    state_mode: str
    # PR-S1: bridge-side defer signaling (default-False preserves Linux).
    is_deferred: bool = False
    deferred_reason: str | None = None


def get_action_constants() -> ActionConstants:
    """Return the current scenario-owned action vocabulary at point of use."""

    actions = get_active_runtime_scenario().actions
    return ActionConstants(
        recheck_action=actions.recheck_action,
        repair_action=actions.repair_action,
        escalate_action=actions.escalate_action,
        default_response_mode=actions.default_response_mode,
        action_to_posture=dict(actions.action_to_posture),
        action_to_state_mode=dict(actions.action_to_state_mode),
        all_life_states=tuple(actions.all_life_states),
        action_to_allowed_states=dict(actions.action_to_allowed_states),
    )


def bridge_policy_from_release_context(release_context: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the bridge-policy payload when one is present in release context."""

    if not isinstance(release_context, dict):
        return None
    bridge_policy = release_context.get("bridge_policy")
    if not isinstance(bridge_policy, dict):
        return None
    return dict(bridge_policy)


def response_mode_from_release_context(release_context: dict[str, Any] | None) -> str:
    """Return the bounded response mode carried by release context."""

    default_response_mode = get_action_constants().default_response_mode
    if not isinstance(release_context, dict):
        return default_response_mode
    return str(release_context.get("response_mode") or default_response_mode)


def build_integrity_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
) -> list[ResponseCandidate]:
    """Build the current scenario-owned candidate set for one integrity pressure."""

    return get_active_runtime_scenario().actions.build_integrity_response_candidates(pressure, runtime_state)


def filter_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
) -> list[ResponseFilterDecision]:
    """Filter candidates using the current scenario-owned response policy."""

    return get_active_runtime_scenario().actions.filter_response_candidates(pressure, runtime_state, candidates)


def select_integrity_response(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    *,
    release_context: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Return the mediated selection under the current scenario-owned response policy."""

    return get_active_runtime_scenario().actions.select_integrity_response(
        pressure,
        runtime_state,
        release_context=release_context,
    )


def select_response_action(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
    decisions: list[ResponseFilterDecision],
    *,
    bridge_policy: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Select the final Step 2 action under the current scenario-owned response policy."""

    return get_active_runtime_scenario().actions.select_response_action(
        pressure,
        runtime_state,
        candidates,
        decisions,
        bridge_policy=bridge_policy,
    )
