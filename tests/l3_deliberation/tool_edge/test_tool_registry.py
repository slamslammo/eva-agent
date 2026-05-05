from __future__ import annotations

import unittest

from eva.kernel import ActivePressure, RuntimeState, utc_now
from eva.l3_deliberation.tool_edge.tool_registry import (
    ACTION_TO_ALLOWED_STATES,
    ACTION_TO_POSTURE,
    ACTION_TO_STATE_MODE,
    ESCALATE_ACTION,
    RECHECK_ACTION,
    REPAIR_ACTION,
    bridge_policy_from_release_context,
    build_integrity_response_candidates,
    filter_response_candidates,
    response_mode_from_release_context,
    select_integrity_response,
    select_response_action,
)


class ToolRegistryTests(unittest.TestCase):
    def _pressure(self, reason: str, *, pressure_type: str = "integrity", **evidence: object) -> ActivePressure:
        now = utc_now()
        base_evidence = {"reason": reason}
        base_evidence.update(evidence)
        return ActivePressure(
            pressure_id=f"pressure-{pressure_type}-{reason}",
            type=pressure_type,
            severity="critical",
            evidence=base_evidence,
            first_seen_at=now,
            last_seen_at=now,
            trend="worsening",
            active=True,
        )

    def _state(self, life_state: str = "STABLE") -> RuntimeState:
        return RuntimeState(life_state=life_state, instance_valid=True, heartbeat_ok=True, tick_ok=True)

    def test_tool_registry_extracts_bridge_policy_and_response_mode(self) -> None:
        release_context = {
            "bridge_target": "pressure_led_compatibility",
            "response_mode": "protective_reflex",
            "bridge_policy": {
                "selection": {
                    "preferred_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                }
            },
        }

        self.assertEqual(
            bridge_policy_from_release_context(release_context),
            {
                "selection": {
                    "preferred_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                }
            },
        )
        self.assertEqual(response_mode_from_release_context(release_context), "protective_reflex")
        self.assertEqual(response_mode_from_release_context(None), "pressure_led_compatibility")

    def test_tool_registry_exposes_static_action_metadata(self) -> None:
        self.assertEqual(ACTION_TO_POSTURE[RECHECK_ACTION], "recheck_or_observe")
        self.assertEqual(ACTION_TO_STATE_MODE[REPAIR_ACTION], "conservative")
        self.assertEqual(ACTION_TO_ALLOWED_STATES[ESCALATE_ACTION], ("RECOVERING", "STABLE", "DEGRADED", "CRITICAL"))

    def test_tool_registry_select_integrity_response_consumes_release_context(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")

        selection = select_integrity_response(
            pressure,
            state,
            release_context={
                "bridge_policy": {
                    "selection": {
                        "preferred_action": RECHECK_ACTION,
                        "fallback_action": ESCALATE_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                }
            },
        )

        self.assertEqual(selection.selected_action, RECHECK_ACTION)
        self.assertEqual(selection.selected_action_reason, "bridge_policy_bias")

    def test_tool_registry_select_integrity_response_prefers_escalation_for_escalate_first_policy(self) -> None:
        pressure = self._pressure("runtime_files_missing", runtime_state_present=False)
        state = self._state("STABLE")

        selection = select_integrity_response(
            pressure,
            state,
            release_context={
                "bridge_policy": {
                    "selection": {
                        "preferred_action": ESCALATE_ACTION,
                        "fallback_action": RECHECK_ACTION,
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["runtime_files_missing", "runtime_not_writable", "recent_distress_detected"],
                        "life_states": ["RECOVERING", "STABLE", "DEGRADED", "CRITICAL"],
                    },
                }
            },
        )

        self.assertEqual(selection.selected_action, ESCALATE_ACTION)
        self.assertEqual(selection.selected_action_reason, "escalation_required_by_boundary")

        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=False,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        decisions = filter_response_candidates(
            pressure,
            self._state("STABLE"),
            build_integrity_response_candidates(pressure, self._state("STABLE")),
        )

        decisions_by_action = {decision.action: decision for decision in decisions}
        self.assertEqual(decisions_by_action[REPAIR_ACTION].result, "deny")
        self.assertEqual(decisions_by_action[REPAIR_ACTION].reasons, ("risk_to_continuity",))

    def test_tool_registry_prefers_bridge_policy_fallback_when_preferred_is_denied(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            runtime_writable=False,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")
        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)

        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": REPAIR_ACTION,
                    "fallback_action": RECHECK_ACTION,
                    "default_path": "pressure_default",
                },
                "applicability": {
                    "pressure_reasons": ["recent_yield_detected"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, RECHECK_ACTION)
        self.assertEqual(selection.selected_action_reason, "bridge_policy_fallback")

    def test_tool_registry_falls_back_to_escalate_when_no_candidate_is_allowed(self) -> None:
        pressure = self._pressure(
            "recent_yield_detected",
            history_integrity_risk=True,
            active_instance_present=True,
            runtime_state_present=True,
            events_present=True,
            lock_present=True,
            runtime_writable=True,
            recent_distress_count=0,
        )
        state = self._state("STABLE")
        candidates = build_integrity_response_candidates(pressure, state)
        decisions = filter_response_candidates(pressure, state, candidates)

        selection = select_response_action(
            pressure,
            state,
            candidates,
            decisions,
            bridge_policy={
                "selection": {
                    "preferred_action": REPAIR_ACTION,
                    "fallback_action": RECHECK_ACTION,
                    "default_path": "first_allowed",
                },
                "applicability": {
                    "pressure_reasons": ["recent_yield_detected"],
                    "life_states": ["STABLE"],
                },
            },
        )

        self.assertEqual(selection.selected_action, ESCALATE_ACTION)
        self.assertEqual(selection.selected_action_reason, "only_allowed_action")


if __name__ == "__main__":
    unittest.main()
