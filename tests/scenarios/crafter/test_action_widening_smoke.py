"""PR-4: Crafter bridge executor smoke tests.

Verifies the new select_response_action / select_integrity_response behavior:
- raw-action execution path (action_hint in release_context)
- fallback-defer path (no valid action_hint)
"""

from __future__ import annotations

import unittest

from eva.kernel import ActivePressure, RuntimeState, utc_now
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions import (
    filter_response_candidates,
    select_integrity_response,
    select_response_action,
)


def _pressure(reason: str = "inventory_sparse") -> ActivePressure:
    return ActivePressure(
        pressure_id="pressure-test",
        type="acquisition",
        severity="critical",
        evidence={"reason": reason},
        first_seen_at=utc_now(),
        last_seen_at=utc_now(),
        trend="worsening",
    )


def _runtime_state() -> RuntimeState:
    return RuntimeState(life_state="STABLE", instance_valid=True)


class CrafterBridgeExecutorTests(unittest.TestCase):
    """PR-4: bridge reads raw action from release_context["action_hint"]."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def _release_context(self, action_hint: str | None = None) -> dict:
        ctx: dict = {
            "bridge_target": "pressure_led_compatibility",
            "candidate_profile": "crafter_raw_action",
        }
        if action_hint is not None:
            ctx["action_hint"] = action_hint
        return ctx

    def test_valid_raw_action_hint_is_executed(self) -> None:
        selection = select_integrity_response(
            _pressure(),
            _runtime_state(),
            release_context=self._release_context("move_left"),
        )
        self.assertEqual(selection.selected_action, "move_left")
        self.assertEqual(selection.selected_action_reason, "crafter_raw_action_execution")

    def test_all_move_actions_can_be_executed(self) -> None:
        for action in ("move_left", "move_right", "move_up", "move_down"):
            selection = select_integrity_response(
                _pressure(),
                _runtime_state(),
                release_context=self._release_context(action),
            )
            self.assertEqual(selection.selected_action, action)
            self.assertEqual(selection.selected_action_reason, "crafter_raw_action_execution")

    def test_do_and_sleep_can_be_executed(self) -> None:
        for action in ("do", "sleep"):
            selection = select_integrity_response(
                _pressure(),
                _runtime_state(),
                release_context=self._release_context(action),
            )
            self.assertEqual(selection.selected_action, action)

    def test_make_action_can_be_executed(self) -> None:
        selection = select_integrity_response(
            _pressure(),
            _runtime_state(),
            release_context=self._release_context("make_wood_pickaxe"),
        )
        self.assertEqual(selection.selected_action, "make_wood_pickaxe")
        self.assertEqual(selection.selected_action_reason, "crafter_raw_action_execution")

    def test_no_action_hint_falls_back_to_defer(self) -> None:
        selection = select_integrity_response(
            _pressure(),
            _runtime_state(),
            release_context=self._release_context(),  # no action_hint
        )
        self.assertEqual(selection.selected_action_reason, "crafter_bridge_defer_no_raw_action")

    def test_unknown_action_hint_falls_back_to_defer(self) -> None:
        selection = select_integrity_response(
            _pressure(),
            _runtime_state(),
            release_context=self._release_context("invented_action"),
        )
        self.assertEqual(selection.selected_action_reason, "crafter_bridge_defer_no_raw_action")

    def test_none_release_context_falls_back_to_defer(self) -> None:
        selection = select_integrity_response(
            _pressure(),
            _runtime_state(),
            release_context=None,
        )
        self.assertEqual(selection.selected_action_reason, "crafter_bridge_defer_no_raw_action")

    def test_select_response_action_reads_from_bridge_policy(self) -> None:
        # bridge_policy IS release_context (passed as-is by select_integrity_response)
        selection = select_response_action(
            _pressure(),
            _runtime_state(),
            [],
            [],
            bridge_policy={"action_hint": "do"},
        )
        self.assertEqual(selection.selected_action, "do")
        self.assertEqual(selection.selected_action_reason, "crafter_raw_action_execution")

    def test_filter_response_candidates_passthrough(self) -> None:
        # filter_response_candidates still allows all candidates (unchanged)
        from eva.l3_deliberation.tool_edge.tool_registry import ResponseCandidate
        candidates = [ResponseCandidate(action="move_left", posture="crafter_candidate", allowed_in_states=("STABLE",))]
        decisions = filter_response_candidates(_pressure(), _runtime_state(), candidates)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].result, "allow")


if __name__ == "__main__":
    unittest.main()
