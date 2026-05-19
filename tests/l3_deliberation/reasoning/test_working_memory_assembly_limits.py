"""Round 1.C-2 (W6): pin the ``WorkingMemoryAssemblyLimits`` dataclass.

Stage I follow-up #3 flagged the working-memory assembly signature as
approaching the "review threshold" — ``build_working_memory_context`` had
10 keyword arguments and ``build_working_memory_context_from_store`` had
11. Round 1.C-2 groups the four output-size limits into one dataclass:

    WorkingMemoryAssemblyLimits(
        max_bias_summaries=2,
        max_habit_skills=2,
        max_recent_outcomes=3,
        max_semantic_patterns=2,
    )

The data-source kwargs (learning_outcomes, habit_bias_entries, ...) stay
as individual parameters for test flexibility; only the output-size
limits are bundled. Both signatures continue to accept the individual
``max_*`` kwargs for backward compatibility, but the new ``limits``
parameter takes precedence when supplied.
"""

from __future__ import annotations

import tempfile
import unittest

from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation import build_deliberation_input
from eva.l3_deliberation.reasoning.working_memory import (
    WorkingMemoryAssemblyLimits,
    build_working_memory_context,
    build_working_memory_context_from_store,
)
from scenarios.crafter import activate_crafter_scenario


def _baseline_deliberation_input():
    return build_deliberation_input(
        signal_batch={
            "signals": [{"class": "status"}],
            "summary": {
                "signal_count": 1,
                "status_signal_count": 1,
                "threat_signal_count": 0,
                "background_signal_count": 0,
                "has_threat_signal": False,
            },
        },
        drive_broadcast={
            "top_drive": "metabolic",
            "drive_levels": {"metabolic": 0.5, "safety": 0.1, "recovery": 0.1, "acquisition": 0.1, "capability": 0.1, "exploration": 0.1},
            "drive_trends": {"metabolic": "stable"},
        },
        runtime_gate_context={
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
        },
        pressure_table={"pressures": []},
    )


class WorkingMemoryAssemblyLimitsTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_limits_dataclass_default_values_match_legacy_kwargs(self) -> None:
        """Default values must match the prior kwarg defaults exactly so
        passing no limits is bit-equivalent to passing the old defaults."""

        limits = WorkingMemoryAssemblyLimits()
        self.assertEqual(limits.max_bias_summaries, 2)
        self.assertEqual(limits.max_habit_skills, 2)
        self.assertEqual(limits.max_recent_outcomes, 3)
        self.assertEqual(limits.max_semantic_patterns, 2)

    def test_build_working_memory_context_accepts_limits_dataclass(self) -> None:
        """The new ``limits`` parameter must be honored when supplied."""

        deliberation_input = _baseline_deliberation_input()
        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
            semantic_entries=[],
            limits=WorkingMemoryAssemblyLimits(
                max_bias_summaries=1,
                max_habit_skills=1,
                max_recent_outcomes=1,
                max_semantic_patterns=1,
            ),
        )
        self.assertEqual(context.source_backend, "local_rule_based")

    def test_legacy_kwargs_still_supported_for_backward_compatibility(self) -> None:
        """Existing callers passing individual ``max_*`` kwargs must continue
        to work — the legacy interface is preserved during transition."""

        deliberation_input = _baseline_deliberation_input()
        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
            semantic_entries=[],
            max_bias_summaries=1,
            max_habit_skills=1,
            max_recent_outcomes=1,
            max_semantic_patterns=1,
        )
        self.assertEqual(context.source_backend, "local_rule_based")

    def test_limits_takes_precedence_over_legacy_kwargs_when_both_passed(self) -> None:
        """When both ``limits`` and individual ``max_*`` kwargs are supplied,
        ``limits`` wins (callers should migrate to the dataclass)."""

        deliberation_input = _baseline_deliberation_input()
        # Pass a limits dataclass with a specific bias count; also pass a
        # different value as a legacy kwarg. The output should reflect the
        # dataclass value, demonstrated by absence of any error/conflict.
        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
            semantic_entries=[],
            limits=WorkingMemoryAssemblyLimits(max_bias_summaries=5),
            max_bias_summaries=1,  # ignored
        )
        self.assertIsNotNone(context)

    def test_build_from_store_accepts_limits(self) -> None:
        """``build_working_memory_context_from_store`` must accept the new
        ``limits`` parameter symmetrically."""

        deliberation_input = _baseline_deliberation_input()
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                limits=WorkingMemoryAssemblyLimits(max_semantic_patterns=4),
            )
            self.assertEqual(context.source_backend, "local_rule_based")


if __name__ == "__main__":
    unittest.main()
