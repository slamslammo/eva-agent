"""framework-scenario-timing slice 3 — Crafter declares sec-level timing.

Crafter declares its external-life timing on the scenario bundle so the runner
and tests don't re-construct ``ExternalLifeConfig`` by hand. The framework's
``build_runtime_config_from_args`` falls back to this declaration when CLI
timing flags are absent (slice 2 mechanism).

NOTE (clock_source="step"): Crafter is step-clocked. The step loop does not
consume the shallow/deep/full_report patrol intervals (those drive the
wall-clock patrol scheduler only); under step clock they are declarative.
``recent_event_window_sec`` IS consumed in step mode (sensing event filter),
so it carries behavior. The declaration still documents Crafter's intended
fast tempo and gives the one behavior-bearing field a scenario-owned value.
"""

from __future__ import annotations

import unittest
from unittest import mock

from eva.kernel.config import ExternalLifeConfig
from eva.kernel.main import build_runtime_config_from_args, parse_args
from scenarios.crafter import CRAFTER_SCENARIO_BUNDLE

# Linux / framework calendar defaults — Crafter must be clearly faster than these.
_LINUX_SHALLOW = 300.0
_LINUX_DEEP = 1800.0
_LINUX_FULL = 86400.0


def _parse_no_timing():
    argv = ["prog", "--runtime-dir", "/tmp/eva-crafter-timing-test"]
    with mock.patch("sys.argv", argv):
        return parse_args()


class CrafterSuggestedTimingDeclarationTests(unittest.TestCase):
    def test_crafter_declares_suggested_timing(self) -> None:
        timing = CRAFTER_SCENARIO_BUNDLE.suggested_timing
        self.assertIsInstance(timing, ExternalLifeConfig)

    def test_crafter_timing_is_sec_level_faster_than_linux(self) -> None:
        timing = CRAFTER_SCENARIO_BUNDLE.suggested_timing
        assert timing is not None
        self.assertLess(timing.shallow_patrol_interval_sec, _LINUX_SHALLOW)
        self.assertLess(timing.deep_patrol_interval_sec, _LINUX_DEEP)
        self.assertLess(timing.full_report_interval_sec, _LINUX_FULL)

    def test_crafter_timing_preserves_shallow_deep_full_ordering(self) -> None:
        timing = CRAFTER_SCENARIO_BUNDLE.suggested_timing
        assert timing is not None
        self.assertLess(timing.shallow_patrol_interval_sec, timing.deep_patrol_interval_sec)
        self.assertLess(timing.deep_patrol_interval_sec, timing.full_report_interval_sec)

    def test_recent_event_window_is_positive(self) -> None:
        # The one step-mode behavior-bearing field must be a sane positive window.
        timing = CRAFTER_SCENARIO_BUNDLE.suggested_timing
        assert timing is not None
        self.assertGreater(timing.recent_event_window_sec, 0.0)


class CrafterTimingFlowsThroughConfigTests(unittest.TestCase):
    def test_config_picks_up_crafter_timing_without_cli_flags(self) -> None:
        # Dedup exemplar: pull timing from the bundle declaration rather than
        # re-constructing ExternalLifeConfig in the test/runner.
        timing = CRAFTER_SCENARIO_BUNDLE.suggested_timing
        assert timing is not None
        config = build_runtime_config_from_args(_parse_no_timing(), suggested_timing=timing)
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, timing.shallow_patrol_interval_sec)
        self.assertEqual(el.deep_patrol_interval_sec, timing.deep_patrol_interval_sec)
        self.assertEqual(el.full_report_interval_sec, timing.full_report_interval_sec)
        self.assertEqual(el.recent_event_window_sec, timing.recent_event_window_sec)


if __name__ == "__main__":
    unittest.main()
