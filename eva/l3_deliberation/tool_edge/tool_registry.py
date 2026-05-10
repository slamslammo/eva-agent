"""Framework action-policy seam and compatibility wrappers for the L3 tool-edge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...kernel import ActivePressure, RuntimeState
from scenarios.linux_runtime.actions import (
    ACTION_TO_ALLOWED_STATES as _ACTION_TO_ALLOWED_STATES,
    ACTION_TO_POSTURE as _ACTION_TO_POSTURE,
    ACTION_TO_STATE_MODE as _ACTION_TO_STATE_MODE,
    ALL_LIFE_STATES as _ALL_LIFE_STATES,
    DEFAULT_RESPONSE_MODE as _DEFAULT_RESPONSE_MODE,
    ESCALATE_ACTION as _ESCALATE_ACTION,
    RECHECK_ACTION as _RECHECK_ACTION,
    REPAIR_ACTION as _REPAIR_ACTION,
    build_integrity_response_candidates as _build_integrity_response_candidates,
    filter_response_candidates as _filter_response_candidates,
    select_integrity_response as _select_integrity_response,
    select_response_action as _select_response_action,
)

__all__ = [
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "ESCALATE_ACTION",
    "DEFAULT_RESPONSE_MODE",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_LIFE_STATES",
    "ACTION_TO_ALLOWED_STATES",
    "ResponseCandidate",
    "ResponseFilterDecision",
    "ResponseSelection",
    "bridge_policy_from_release_context",
    "response_mode_from_release_context",
    "build_integrity_response_candidates",
    "filter_response_candidates",
    "select_integrity_response",
    "select_response_action",
]

RECHECK_ACTION = _RECHECK_ACTION
REPAIR_ACTION = _REPAIR_ACTION
ESCALATE_ACTION = _ESCALATE_ACTION
DEFAULT_RESPONSE_MODE = _DEFAULT_RESPONSE_MODE
ACTION_TO_POSTURE = _ACTION_TO_POSTURE
ACTION_TO_STATE_MODE = _ACTION_TO_STATE_MODE
ALL_LIFE_STATES = _ALL_LIFE_STATES
ACTION_TO_ALLOWED_STATES = _ACTION_TO_ALLOWED_STATES


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
    """Final response choice after filtering and minimal comparison."""

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

    if not isinstance(release_context, dict):
        return DEFAULT_RESPONSE_MODE
    return str(release_context.get("response_mode") or DEFAULT_RESPONSE_MODE)


def build_integrity_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
) -> list[ResponseCandidate]:
    """Build the current scenario-owned candidate set for one integrity pressure."""

    return _build_integrity_response_candidates(pressure, runtime_state)


def filter_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
) -> list[ResponseFilterDecision]:
    """Filter candidates using the current scenario-owned response policy."""

    return _filter_response_candidates(pressure, runtime_state, candidates)


def select_integrity_response(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    *,
    release_context: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Return the mediated selection under the current scenario-owned response policy."""

    return _select_integrity_response(pressure, runtime_state, release_context=release_context)


def select_response_action(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
    decisions: list[ResponseFilterDecision],
    *,
    bridge_policy: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Select the final Step 2 action under the current scenario-owned response policy."""

    return _select_response_action(
        pressure,
        runtime_state,
        candidates,
        decisions,
        bridge_policy=bridge_policy,
    )
