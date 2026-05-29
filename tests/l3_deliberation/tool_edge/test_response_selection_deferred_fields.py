"""PR-S1 Slice 1: ResponseSelection is_deferred + deferred_reason fields.

Plan §3.2: ResponseSelection adds two optional fields (defaults False / None)
so the bridge can distinguish "do not advance scenario time" from "execute".

Red lines:
- R1/R2 Linux compat: existing constructions without the new fields keep working
- R3: clock_source field already exists; this PR only adds bridge-side signaling
"""

from __future__ import annotations

import unittest


class ResponseSelectionDeferredFieldsTests(unittest.TestCase):
    def test_construction_without_deferred_fields_defaults_false_none(self) -> None:
        from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection
        sel = ResponseSelection(
            pressure_id="p1",
            selected_action="noop",
            selected_posture="x",
            selected_action_reason="r",
            filter_result="allow",
            candidate_actions=("noop",),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode="normal",
        )
        # PR-S1 §3.2 default values must preserve old call sites unchanged.
        self.assertFalse(sel.is_deferred)
        self.assertIsNone(sel.deferred_reason)

    def test_can_set_is_deferred_true_with_reason(self) -> None:
        from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection
        sel = ResponseSelection(
            pressure_id="p1",
            selected_action="noop",
            selected_posture="x",
            selected_action_reason="defer_no_raw_action",
            filter_result="allow",
            candidate_actions=(),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode="normal",
            is_deferred=True,
            deferred_reason="no_valid_raw_action",
        )
        self.assertTrue(sel.is_deferred)
        self.assertEqual(sel.deferred_reason, "no_valid_raw_action")

    def test_response_selection_is_frozen(self) -> None:
        from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection
        sel = ResponseSelection(
            pressure_id="p1",
            selected_action="noop",
            selected_posture="x",
            selected_action_reason="r",
            filter_result="allow",
            candidate_actions=(),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode="normal",
        )
        with self.assertRaises(Exception):
            sel.is_deferred = True  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
