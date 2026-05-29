"""PR-S1 Slice 2: select_response_action sets is_deferred on fallback path.

Per plan §3.2: Crafter bridge's defer fallback must now signal is_deferred=True
+ deferred_reason="no_valid_raw_action" instead of silently returning a
ResponseSelection that the kernel would then forward to env.step. This lets
the kernel (Slice 4) skip env.step when clock_source="step".

Behavior preserved for the success path (valid raw_action → is_deferred=False).
"""

from __future__ import annotations

import unittest

from eva.kernel import ActivePressure, RuntimeState, utc_now
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions import select_response_action


def _pressure() -> ActivePressure:
    return ActivePressure(
        pressure_id="p-test",
        type="acquisition",
        severity="degraded",
        evidence={"reason": "test"},
        first_seen_at=utc_now(),
        last_seen_at=utc_now(),
        trend="stable",
    )


def _runtime_state() -> RuntimeState:
    return RuntimeState(life_state="STABLE", instance_valid=True)


class SelectResponseActionDeferredSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_valid_raw_action_path_is_not_deferred(self) -> None:
        sel = select_response_action(
            _pressure(), _runtime_state(), [], [],
            bridge_policy={"action_hint": "do"},
        )
        self.assertFalse(sel.is_deferred)
        self.assertIsNone(sel.deferred_reason)
        self.assertEqual(sel.selected_action, "do")
        self.assertEqual(sel.selected_action_reason, "crafter_raw_action_execution")

    def test_no_action_hint_falls_back_to_deferred(self) -> None:
        sel = select_response_action(
            _pressure(), _runtime_state(), [], [],
            bridge_policy={},
        )
        self.assertTrue(sel.is_deferred, "no raw action → must set is_deferred=True")
        self.assertEqual(sel.deferred_reason, "no_valid_raw_action")
        # selected_action_reason still meaningful for existing trace consumers.
        self.assertEqual(sel.selected_action_reason, "crafter_bridge_defer_no_raw_action")

    def test_unknown_action_falls_back_to_deferred(self) -> None:
        sel = select_response_action(
            _pressure(), _runtime_state(), [], [],
            bridge_policy={"action_hint": "invented_action"},
        )
        self.assertTrue(sel.is_deferred)
        self.assertEqual(sel.deferred_reason, "no_valid_raw_action")

    def test_none_bridge_policy_falls_back_to_deferred(self) -> None:
        sel = select_response_action(
            _pressure(), _runtime_state(), [], [],
            bridge_policy=None,
        )
        self.assertTrue(sel.is_deferred)
        self.assertEqual(sel.deferred_reason, "no_valid_raw_action")


if __name__ == "__main__":
    unittest.main()
