"""Tool-edge package for bounded compatibility execution within L3."""

from .compatibility import (
    ResponseCandidate,
    ResponseFilterDecision,
    ResponseSelection,
    DEFAULT_RESPONSE_MODE,
    build_integrity_response_candidates,
    filter_response_candidates,
    maybe_respond_after_patrol,
    respond_to_integrity_pressure,
    select_integrity_response,
    select_response_action,
)
from .executors import ConservativeRuntime, execute_integrity_selection, execute_response_action
from .history import append_response_history, build_response_selected_event_details, build_response_summary
from .tool_registry import (
    ACTION_TO_ALLOWED_STATES,
    ACTION_TO_POSTURE,
    ACTION_TO_STATE_MODE,
    ALL_LIFE_STATES,
    ESCALATE_ACTION,
    RECHECK_ACTION,
    REPAIR_ACTION,
    bridge_policy_from_release_context,
    response_mode_from_release_context,
)

__all__ = [
    "ACTION_TO_ALLOWED_STATES",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_LIFE_STATES",
    "ESCALATE_ACTION",
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "DEFAULT_RESPONSE_MODE",
    "ConservativeRuntime",
    "ResponseCandidate",
    "ResponseFilterDecision",
    "ResponseSelection",
    "bridge_policy_from_release_context",
    "response_mode_from_release_context",
    "build_integrity_response_candidates",
    "execute_integrity_selection",
    "execute_response_action",
    "filter_response_candidates",
    "maybe_respond_after_patrol",
    "respond_to_integrity_pressure",
    "select_integrity_response",
    "select_response_action",
    "append_response_history",
    "build_response_selected_event_details",
    "build_response_summary",
]
