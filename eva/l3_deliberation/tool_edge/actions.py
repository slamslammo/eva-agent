"""Compatibility re-export surface for the bounded tool-edge action registry."""

from __future__ import annotations

from .tool_registry import (
    ACTION_TO_ALLOWED_STATES,
    ACTION_TO_POSTURE,
    ACTION_TO_STATE_MODE,
    ALL_LIFE_STATES,
    ESCALATE_ACTION,
    RECHECK_ACTION,
    REPAIR_ACTION,
)

__all__ = [
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "ESCALATE_ACTION",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_LIFE_STATES",
    "ACTION_TO_ALLOWED_STATES",
]
