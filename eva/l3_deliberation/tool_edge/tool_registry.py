"""Canonical bounded tool/action registry and selection helpers for the L3 tool-edge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ...kernel import ActivePressure, RuntimeState

__all__ = [
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "ESCALATE_ACTION",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_LIFE_STATES",
    "ACTION_TO_ALLOWED_STATES",
    "ResponseCandidate",
    "ResponseFilterDecision",
    "ResponseSelection",
    "build_integrity_response_candidates",
    "filter_response_candidates",
    "select_response_action",
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


def build_integrity_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
) -> list[ResponseCandidate]:
    """Build the first-pass candidate set for one integrity pressure."""

    if pressure.type != "integrity":
        return []
    reason = _pressure_reason(pressure)
    actions: list[str]
    if reason in {"runtime_files_missing", "runtime_not_writable"}:
        actions = [RECHECK_ACTION, ESCALATE_ACTION]
    elif reason == "recent_distress_detected":
        actions = [ESCALATE_ACTION]
    elif reason == "instance_invalid":
        actions = [RECHECK_ACTION, ESCALATE_ACTION]
    elif reason == "recent_yield_detected":
        actions = [RECHECK_ACTION, ESCALATE_ACTION]
        if runtime_state.life_state == "STABLE":
            actions.insert(1, REPAIR_ACTION)
    else:
        actions = [RECHECK_ACTION, ESCALATE_ACTION]
    return [_make_candidate(action) for action in actions]


def filter_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
) -> list[ResponseFilterDecision]:
    """Filter candidates using the v1 anchor and life-state rules."""

    decisions: list[ResponseFilterDecision] = []
    for candidate in candidates:
        if candidate.action == RECHECK_ACTION:
            decisions.append(_filter_recheck_candidate(pressure))
        elif candidate.action == REPAIR_ACTION:
            decisions.append(_filter_repair_candidate(pressure, runtime_state))
        elif candidate.action == ESCALATE_ACTION:
            decisions.append(ResponseFilterDecision(action=candidate.action, result="allow"))
        else:
            decisions.append(
                ResponseFilterDecision(
                    action=candidate.action,
                    result="deny",
                    reasons=("too_complex_for_v1",),
                )
            )
    return decisions


def select_response_action(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
    decisions: list[ResponseFilterDecision],
    *,
    bridge_policy: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Select the final Step 2 action after filtering."""

    candidate_actions = tuple(candidate.action for candidate in candidates)
    decisions_by_action = {decision.action: decision for decision in decisions}
    allowed = [candidate.action for candidate in candidates if decisions_by_action[candidate.action].result == "allow"]
    discouraged = [candidate.action for candidate in candidates if decisions_by_action[candidate.action].result == "discourage"]
    denied = tuple(candidate.action for candidate in candidates if decisions_by_action[candidate.action].result == "deny")
    preferred_action = _preferred_action_for_reason(pressure, runtime_state)
    bridge_policy_applies = _bridge_policy_applies(pressure, runtime_state, bridge_policy)
    bridge_preferred_action = _bridge_policy_action(bridge_policy, "preferred_action") if bridge_policy_applies else None
    bridge_fallback_action = _bridge_policy_action(bridge_policy, "fallback_action") if bridge_policy_applies else None
    bridge_default_path = _bridge_policy_default_path(bridge_policy) if bridge_policy_applies else None

    if bridge_preferred_action in allowed:
        selected_action = bridge_preferred_action
    elif bridge_fallback_action in allowed:
        selected_action = bridge_fallback_action
    elif preferred_action in allowed and (not bridge_policy_applies or bridge_default_path == "pressure_default"):
        selected_action = preferred_action
    elif allowed:
        selected_action = allowed[0]
    elif bridge_preferred_action in discouraged:
        selected_action = bridge_preferred_action
    elif bridge_fallback_action in discouraged:
        selected_action = bridge_fallback_action
    elif preferred_action in discouraged and (not bridge_policy_applies or bridge_default_path == "pressure_default"):
        selected_action = preferred_action
    elif discouraged:
        selected_action = discouraged[0]
    else:
        selected_action = ESCALATE_ACTION
        decisions_by_action.setdefault(
            ESCALATE_ACTION,
            ResponseFilterDecision(action=ESCALATE_ACTION, result="allow"),
        )

    selected_decision = decisions_by_action[selected_action]
    selected_reason = _selection_reason(selected_action, preferred_action, bridge_preferred_action, bridge_fallback_action)
    return ResponseSelection(
        pressure_id=pressure.pressure_id,
        selected_action=selected_action,
        selected_posture=ACTION_TO_POSTURE[selected_action],
        selected_action_reason=selected_reason,
        filter_result=selected_decision.result,
        candidate_actions=candidate_actions,
        denied_actions=denied,
        discouraged_actions=tuple(discouraged),
        filter_reasons=_collect_filter_reasons(decisions),
        state_mode=ACTION_TO_STATE_MODE[selected_action],
    )


def _pressure_reason(pressure: ActivePressure) -> str:
    """Return the normalized reason string for one active pressure."""

    return str(pressure.evidence.get("reason") or "unknown")


def _make_candidate(action: str) -> ResponseCandidate:
    """Build one response candidate from the action registry."""

    return ResponseCandidate(
        action=action,
        posture=ACTION_TO_POSTURE[action],
        allowed_in_states=ACTION_TO_ALLOWED_STATES[action],
    )


def _filter_recheck_candidate(pressure: ActivePressure) -> ResponseFilterDecision:
    """Filter the pure recheck action."""

    if pressure.evidence.get("history_integrity_risk") or pressure.evidence.get("recheck_untrusted"):
        return ResponseFilterDecision(
            action=RECHECK_ACTION,
            result="deny",
            reasons=("history_integrity_risk",),
        )
    return ResponseFilterDecision(action=RECHECK_ACTION, result="allow")


def _filter_repair_candidate(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
) -> ResponseFilterDecision:
    """Filter the conservative repair action."""

    if runtime_state.life_state == "CRITICAL":
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("not_allowed_in_critical_state",),
        )
    if runtime_state.life_state != "STABLE":
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("not_allowed_in_degraded_state",),
        )
    if _pressure_reason(pressure) != "recent_yield_detected":
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("too_complex_for_v1",),
        )
    if pressure.evidence.get("history_integrity_risk"):
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("history_integrity_risk",),
        )
    required_present = all(
        bool(pressure.evidence.get(key, True))
        for key in ("active_instance_present", "runtime_state_present", "events_present", "lock_present")
    )
    if not required_present:
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("integrity_violation",),
        )
    if not bool(pressure.evidence.get("runtime_writable", True)):
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("risk_to_continuity",),
        )
    if int(pressure.evidence.get("recent_distress_count", 0)) > 0:
        return ResponseFilterDecision(
            action=REPAIR_ACTION,
            result="deny",
            reasons=("heartbeat_boundary_risk",),
        )
    return ResponseFilterDecision(action=REPAIR_ACTION, result="allow")


def _bridge_policy_applies(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    bridge_policy: dict[str, Any] | None,
) -> bool:
    """Return whether the bridge policy applies in the current runtime context."""

    if not isinstance(bridge_policy, dict):
        return False
    applicability = bridge_policy.get("applicability")
    if not isinstance(applicability, dict):
        return True
    pressure_reasons = applicability.get("pressure_reasons")
    if isinstance(pressure_reasons, list) and pressure_reasons and _pressure_reason(pressure) not in pressure_reasons:
        return False
    life_states = applicability.get("life_states")
    if isinstance(life_states, list) and life_states and runtime_state.life_state not in life_states:
        return False
    return True


def _bridge_policy_action(bridge_policy: dict[str, Any] | None, key: str) -> str | None:
    """Return one action from the bridge policy selection contract."""

    if not isinstance(bridge_policy, dict):
        return None
    selection = bridge_policy.get("selection")
    if not isinstance(selection, dict):
        return None
    action = selection.get(key)
    if action in {RECHECK_ACTION, REPAIR_ACTION, ESCALATE_ACTION}:
        return str(action)
    return None


def _bridge_policy_default_path(bridge_policy: dict[str, Any] | None) -> str | None:
    """Return the explicit default path from the bridge policy selection contract."""

    if not isinstance(bridge_policy, dict):
        return None
    selection = bridge_policy.get("selection")
    if not isinstance(selection, dict):
        return None
    default_path = selection.get("default_path")
    if default_path in {"pressure_default", "first_allowed"}:
        return str(default_path)
    return None


def _preferred_action_for_reason(pressure: ActivePressure, runtime_state: RuntimeState) -> str:
    """Return the default preferred action before filtering overrides it."""

    reason = _pressure_reason(pressure)
    if reason in {"runtime_files_missing", "runtime_not_writable", "recent_distress_detected"}:
        return ESCALATE_ACTION
    if reason == "instance_invalid":
        return RECHECK_ACTION
    if reason == "recent_yield_detected":
        return REPAIR_ACTION if runtime_state.life_state == "STABLE" else ESCALATE_ACTION
    return RECHECK_ACTION


def _selection_reason(
    selected_action: str,
    preferred_action: str,
    bridge_preferred_action: str | None,
    bridge_fallback_action: str | None,
) -> str:
    """Return the compact enum reason for the selected action."""

    if bridge_preferred_action is not None and selected_action == bridge_preferred_action and selected_action != preferred_action:
        return "bridge_policy_bias"
    if bridge_fallback_action is not None and selected_action == bridge_fallback_action and selected_action != preferred_action:
        return "bridge_policy_fallback"
    if selected_action != preferred_action:
        return "only_allowed_action"
    if selected_action == RECHECK_ACTION:
        return "best_information_gain"
    if selected_action == REPAIR_ACTION:
        return "state_requires_conservative_response"
    return "escalation_required_by_boundary"


def _collect_filter_reasons(decisions: list[ResponseFilterDecision]) -> tuple[str, ...]:
    """Collect unique filter reasons in candidate order."""

    ordered: list[str] = []
    for decision in decisions:
        for reason in decision.reasons:
            if reason not in ordered:
                ordered.append(reason)
    return tuple(ordered)
