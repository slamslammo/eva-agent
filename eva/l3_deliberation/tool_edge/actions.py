"""Bounded compatibility action registry for the L3 tool-edge bridge."""

from __future__ import annotations

__all__ = [
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "ESCALATE_ACTION",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_LIFE_STATES",
    "ACTION_TO_ALLOWED_STATES",
]

RECHECK_ACTION = "recheck_runtime_integrity"
REPAIR_ACTION = "shrink_to_conservative_mode"
ESCALATE_ACTION = "escalate_integrity_risk"

ACTION_TO_POSTURE = {
    RECHECK_ACTION: "recheck_or_observe",
    REPAIR_ACTION: "attempt_minimal_repair",
    ESCALATE_ACTION: "defer_or_request_help",
}

ACTION_TO_STATE_MODE = {
    RECHECK_ACTION: "normal",
    REPAIR_ACTION: "conservative",
    ESCALATE_ACTION: "escalation_only",
}

ALL_LIFE_STATES = ("RECOVERING", "STABLE", "DEGRADED", "CRITICAL")
ACTION_TO_ALLOWED_STATES = {
    RECHECK_ACTION: ALL_LIFE_STATES,
    REPAIR_ACTION: ("STABLE",),
    ESCALATE_ACTION: ALL_LIFE_STATES,
}
