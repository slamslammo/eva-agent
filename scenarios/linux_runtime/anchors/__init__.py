"""Linux runtime anchor policy for Phase A."""

from .compatibility import (
    COMPATIBILITY_RELEASE_IMPACT,
    ESCALATE_FIRST_ADMISSION_SEVERITIES,
    ESCALATE_FIRST_PROFILE,
    HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC,
    HIGH_RISK_ESCALATION_REASONS,
    OBSERVE_FIRST_PROFILE,
    STABILIZE_FIRST_PROFILE,
    admit_linux_runtime_candidates,
    restriction_reasons_for_linux_runtime_candidates,
)

__all__ = [
    "COMPATIBILITY_RELEASE_IMPACT",
    "ESCALATE_FIRST_ADMISSION_SEVERITIES",
    "ESCALATE_FIRST_PROFILE",
    "HEARTBEAT_SCHEMA_NARROWING_WINDOW_SEC",
    "HIGH_RISK_ESCALATION_REASONS",
    "OBSERVE_FIRST_PROFILE",
    "STABILIZE_FIRST_PROFILE",
    "admit_linux_runtime_candidates",
    "restriction_reasons_for_linux_runtime_candidates",
]
