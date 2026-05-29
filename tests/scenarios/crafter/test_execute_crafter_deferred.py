"""PR-S1 Slice 3: execute_crafter_action honors is_deferred → skip env.step.

Plan §3.3: when bridge signals ``is_deferred=True``, the runtime's
``step_external_action`` (which wraps env.step) must NOT be invoked. The
payload returned must mark ``env_step_invoked=False`` + ``execution_status=
"deferred"`` so downstream telemetry (response_history, transcript v1.2)
can distinguish effective scenario_step_index advancement.

Red lines:
- R4 core: clock_source="step" + is_deferred → no env.step
- R6: env.step advancement bound to mediated executable action only — defer
  means no mediated executable action emerged.
"""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass

from eva.kernel import ActivePressure, StateStore, build_runtime_paths, utc_now
from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions import execute_crafter_action


@dataclass
class _RecordingRuntime:
    """Stub runtime that records every step_external_action call."""

    actions: list[str]

    def step_external_action(self, action_name: str):
        self.actions.append(action_name)
        # Stub minimal step_result-ish object so non-deferred path can read it.
        return type("StepResult", (), {
            "agent_observation": {"visible": {}},
            "before_observation": {"visible": {}},
            "after_action_observation": {"visible": {}},
            "done": False,
            "raw_observation": None,
            "reward": 0.0,
            "raw_info": {},
        })()


def _pressure() -> ActivePressure:
    return ActivePressure(
        pressure_id="p-test", type="acquisition", severity="degraded",
        evidence={"reason": "test"},
        first_seen_at=utc_now(), last_seen_at=utc_now(), trend="stable",
    )


def _selection(is_deferred: bool, reason: str | None = None) -> ResponseSelection:
    return ResponseSelection(
        pressure_id="p-test",
        selected_action="noop",
        selected_posture="crafter_candidate",
        selected_action_reason="x",
        filter_result="allow",
        candidate_actions=(),
        denied_actions=(),
        discouraged_actions=(),
        filter_reasons=(),
        state_mode="normal",
        is_deferred=is_deferred,
        deferred_reason=reason,
    )


class ExecuteCrafterActionDeferredTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_deferred_selection_does_not_call_step_external_action(self) -> None:
        runtime = _RecordingRuntime(actions=[])
        sel = _selection(is_deferred=True, reason="no_valid_raw_action")
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            payload = execute_crafter_action(store, _pressure(), sel, runtime=runtime)
        self.assertEqual(runtime.actions, [], "step_external_action must NOT be called when is_deferred=True")
        self.assertFalse(payload.get("env_step_invoked"),
                         "deferred payload must mark env_step_invoked=False")
        self.assertEqual(payload.get("execution_status"), "deferred")
        self.assertEqual(payload.get("deferred_reason"), "no_valid_raw_action")

    def test_non_deferred_selection_calls_step_external_action(self) -> None:
        runtime = _RecordingRuntime(actions=[])
        sel = _selection(is_deferred=False)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            payload = execute_crafter_action(store, _pressure(), sel, runtime=runtime)
        self.assertEqual(runtime.actions, ["noop"], "step_external_action must be called when is_deferred=False")
        self.assertTrue(payload.get("env_step_invoked"),
                        "non-deferred payload must mark env_step_invoked=True")
        self.assertNotEqual(payload.get("execution_status"), "deferred")

    def test_deferred_selection_without_runtime_still_skips_env_step(self) -> None:
        """No runtime → no env.step regardless; deferred semantic still recorded."""
        sel = _selection(is_deferred=True, reason="no_valid_raw_action")
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            payload = execute_crafter_action(store, _pressure(), sel, runtime=None)
        self.assertFalse(payload.get("env_step_invoked"))
        self.assertEqual(payload.get("execution_status"), "deferred")


if __name__ == "__main__":
    unittest.main()
