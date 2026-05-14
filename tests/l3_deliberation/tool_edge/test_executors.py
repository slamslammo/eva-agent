from __future__ import annotations

import tempfile
import unittest

from eva.kernel import ActivePressure, ActivePressureTable, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.l3_deliberation import ReleaseToken
from eva.l3_deliberation.tool_edge.executors import execute_integrity_selection, execute_response_action
from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection
from eva.scenario_bundle import activate_runtime_scenario
from scenarios.linux_runtime import ESCALATE_ACTION, RECHECK_ACTION, REPAIR_ACTION, activate_linux_runtime_scenario


class StubRuntime:
    def __init__(self) -> None:
        self.activated = False

    def activate_conservative_until_next_patrol(self) -> None:
        self.activated = True


class ExecutorsTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def _pressure(self, reason: str) -> ActivePressure:
        now = utc_now()
        return ActivePressure(
            pressure_id=f"pressure-integrity-{reason}",
            type="integrity",
            severity="critical",
            evidence={"reason": reason},
            first_seen_at=now,
            last_seen_at=now,
            trend="worsening",
            active=True,
        )

    def _state(self) -> RuntimeState:
        return RuntimeState(life_state="STABLE", instance_valid=True, heartbeat_ok=True, tick_ok=True)

    def _selection(self, action: str) -> ResponseSelection:
        return ResponseSelection(
            pressure_id="pressure-integrity-test",
            selected_action=action,
            selected_posture="test_posture",
            selected_action_reason="test_reason",
            filter_result="allow",
            candidate_actions=(action,),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode="normal",
        )

    def _token(self) -> ReleaseToken:
        return ReleaseToken(
            token_id="release-token::candidate-compatibility-stabilize-first",
            outcome="compatibility_release",
            candidate_id="candidate-compatibility-stabilize-first",
            candidate_profile="stabilize_first",
        )

    def test_execute_integrity_selection_applies_release_context_bridge_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            runtime = StubRuntime()

            result = execute_integrity_selection(
                store,
                self._pressure("recent_yield_detected"),
                self._state(),
                self._selection(REPAIR_ACTION),
                runtime=runtime,
                allow_repair_side_effects=True,
                release_context={
                    "bridge_policy": {
                        "execution": {
                            "allow_repair_side_effects": False,
                        }
                    }
                },
                release_token=self._token(),
                selected_candidate_id=self._token().candidate_id,
            )

            self.assertFalse(runtime.activated)
            self.assertEqual(result["side_effects"], [])
            self.assertTrue(result["followup_needed"])

    def test_execute_response_action_recheck_fails_when_artifacts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))

            result = execute_response_action(
                store,
                self._pressure("instance_invalid"),
                self._state(),
                self._selection(RECHECK_ACTION),
                release_token=self._token(),
                selected_candidate_id=self._token().candidate_id,
            )

            self.assertEqual(result["execution_status"], "failed")
            self.assertEqual(result["pressure_outcome"], "unknown")
            self.assertEqual(result["integration_hint"], "needs_human_review")

    def test_execute_response_action_recheck_relieves_when_pressure_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.paths.active_instance_file.write_text("{}\n", encoding="utf-8")
            store.paths.runtime_state_file.write_text("{}\n", encoding="utf-8")
            store.paths.active_pressures_file.write_text('{"captured_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "pressures": []}\n', encoding="utf-8")
            store.paths.events_file.write_text('{"event_type": "startup"}\n', encoding="utf-8")

            result = execute_response_action(
                store,
                self._pressure("instance_invalid"),
                self._state(),
                self._selection(RECHECK_ACTION),
                release_token=self._token(),
                selected_candidate_id=self._token().candidate_id,
            )

            self.assertEqual(result["execution_status"], "completed")
            self.assertEqual(result["pressure_outcome"], "relieved")
            self.assertFalse(result["followup_needed"])

    def test_execute_response_action_repair_applies_side_effect_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            runtime = StubRuntime()

            result = execute_response_action(
                store,
                self._pressure("recent_yield_detected"),
                self._state(),
                self._selection(REPAIR_ACTION),
                runtime=runtime,
                allow_repair_side_effects=True,
                release_token=self._token(),
                selected_candidate_id=self._token().candidate_id,
            )

            self.assertTrue(runtime.activated)
            self.assertEqual(result["execution_status"], "completed")
            self.assertEqual(result["side_effects"], ["temporary_conservative_until_next_patrol"])

    def test_execute_response_action_repair_blocks_side_effect_when_disallowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            runtime = StubRuntime()

            result = execute_response_action(
                store,
                self._pressure("recent_yield_detected"),
                self._state(),
                self._selection(REPAIR_ACTION),
                runtime=runtime,
                allow_repair_side_effects=False,
                release_token=self._token(),
                selected_candidate_id=self._token().candidate_id,
            )

            self.assertFalse(runtime.activated)
            self.assertEqual(result["side_effects"], [])
            self.assertTrue(result["followup_needed"])

    def test_execute_response_action_escalate_keeps_existing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))

            result = execute_response_action(
                store,
                self._pressure("runtime_files_missing"),
                self._state(),
                self._selection(ESCALATE_ACTION),
                release_token=self._token(),
                selected_candidate_id=self._token().candidate_id,
            )

            self.assertEqual(result["execution_status"], "escalated")
            self.assertEqual(result["pressure_outcome"], "unchanged")
            self.assertEqual(result["side_effects"], [])
            self.assertEqual(result["integration_hint"], "needs_human_review")


if __name__ == "__main__":
    unittest.main()
