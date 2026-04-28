"""Rule-based compatibility response selection for integrity pressures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .kernel import ActivePressure, RuntimeState, StateStore, to_iso8601
from .l2_drive import DriveBroadcast

__all__ = [
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "ESCALATE_ACTION",
    "ResponseCandidate",
    "ResponseFilterDecision",
    "ResponseSelection",
    "build_integrity_response_candidates",
    "filter_response_candidates",
    "select_response_action",
    "execute_response_action",
    "append_response_history",
    "respond_to_integrity_pressure",
    "maybe_respond_after_patrol",
    "build_response_selected_event_details",
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


class ConservativeRuntime(Protocol):
    """Minimal runtime hook used by repair actions."""

    def activate_conservative_until_next_patrol(self) -> None: ...


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


def execute_response_action(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    selection: ResponseSelection,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
) -> dict[str, Any]:
    """Execute the selected v1 action and return a structured result."""

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


def append_response_history(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    selection: ResponseSelection,
    execution_result: dict[str, Any],
    now: datetime,
    drive_context: dict[str, Any] | None = None,
    release_context: dict[str, Any] | None = None,
    response_mode: str = "pressure_led_compatibility",
) -> dict[str, Any]:
    """Append one complete Step 2 response record and return it."""

    payload = {
        "response_id": f"resp-{selection.pressure_id}-{int(now.timestamp())}",
        "recorded_at": to_iso8601(now),
        "response_mode": response_mode,
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "pressure_severity": pressure.severity,
        "pressure_trend": pressure.trend,
        "pressure_reason": _pressure_reason(pressure),
        "life_state": runtime_state.life_state,
        "instance_valid": runtime_state.instance_valid,
        "state_mode": selection.state_mode,
        "candidate_actions": list(selection.candidate_actions),
        "selected_action": selection.selected_action,
        "selected_posture": selection.selected_posture,
        "selected_action_reason": selection.selected_action_reason,
        "filter_result": selection.filter_result,
        "denied_actions": list(selection.denied_actions),
        "discouraged_actions": list(selection.discouraged_actions),
        "filter_reasons": list(selection.filter_reasons),
        "execution_status": execution_result["execution_status"],
        "pressure_outcome": execution_result["pressure_outcome"],
        "side_effects": execution_result["side_effects"],
        "uncertainty_after_action": execution_result["uncertainty_after_action"],
        "integration_hint": execution_result["integration_hint"],
        "followup_needed": execution_result["followup_needed"],
    }
    if drive_context is not None:
        payload["drive_context"] = drive_context
    if release_context is not None:
        payload["release_context"] = dict(release_context)
    store.append_response_history(payload)
    return payload


def respond_to_integrity_pressure(
    store: StateStore,
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    now: datetime,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
    drive_context: DriveBroadcast | dict[str, Any] | None = None,
    release_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the compatibility-only response closure for one integrity pressure."""

    candidates = build_integrity_response_candidates(pressure, runtime_state)
    decisions = filter_response_candidates(pressure, runtime_state, candidates)
    selection = select_response_action(
        pressure,
        runtime_state,
        candidates,
        decisions,
        bridge_policy=((release_context or {}).get("bridge_policy") if isinstance((release_context or {}).get("bridge_policy"), dict) else None),
    )
    normalized_release_context = None if release_context is None else dict(release_context)
    effective_allow_repair_side_effects = _allow_repair_side_effects(
        bridge_policy=((normalized_release_context or {}).get("bridge_policy") if isinstance((normalized_release_context or {}).get("bridge_policy"), dict) else None),
        default=allow_repair_side_effects,
    )
    execution_result = execute_response_action(
        store,
        pressure,
        runtime_state,
        selection,
        runtime=runtime,
        allow_repair_side_effects=effective_allow_repair_side_effects,
    )
    response_mode = str((normalized_release_context or {}).get("response_mode") or "pressure_led_compatibility")
    drive_context_payload = None if drive_context is None else (drive_context.to_dict() if isinstance(drive_context, DriveBroadcast) else dict(drive_context))
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
    return {
        "pressure_id": pressure.pressure_id,
        "pressure_type": pressure.type,
        "selected_action": selection.selected_action,
        "selected_posture": selection.selected_posture,
        "execution_status": execution_result["execution_status"],
        "pressure_outcome": execution_result["pressure_outcome"],
        "followup_needed": execution_result["followup_needed"],
        "drive_context": drive_context_payload,
        "response_mode": response_mode,
    }


def maybe_respond_after_patrol(
    store: StateStore,
    runtime_state: RuntimeState,
    now: datetime,
    runtime: ConservativeRuntime | None = None,
    *,
    allow_repair_side_effects: bool = True,
    drive_context: DriveBroadcast | dict[str, Any] | None = None,
    release_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run the compatibility-only post-patrol response when an integrity pressure exists."""

    pressure_table = store.read_active_pressures()
    for pressure in pressure_table.pressures:
        if pressure.type == "integrity":
            return respond_to_integrity_pressure(
                store,
                pressure,
                runtime_state,
                now,
                runtime=runtime,
                allow_repair_side_effects=allow_repair_side_effects,
                drive_context=drive_context,
                release_context=release_context,
            )
    return None


def build_response_selected_event_details(
    response_summary: dict[str, Any],
    *,
    work_slice: str,
    work_kind: str,
) -> dict[str, Any]:
    """Build the minimal downstream response_selected event payload."""

    return {
        "work_slice": work_slice,
        "work_kind": work_kind,
        "pressure_id": response_summary["pressure_id"],
        "pressure_type": response_summary["pressure_type"],
        "selected_action": response_summary["selected_action"],
    }


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
