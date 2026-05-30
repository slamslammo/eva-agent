"""framework-scenario-timing slice 5 — red-line regression guards.

Named guards for the three task red lines, so future changes can't silently
regress them:

1. Linux timing unchanged — the Linux bundle declares no ``suggested_timing``,
   so a Linux run with no CLI timing flags resolves to the framework calendar
   default (300 / 1800 / 86400 / 1800), exactly as before this task.
2. CLI override priority preserved — explicit CLI timing still wins over both
   scenario declaration and framework default.
3. dlPFC producer independent of adapter_mode — the observation-2 default flip
   (adapter_mode inert -> heuristic) must not change whether / how the dlPFC
   candidate producer is built. ``_build_candidate_producer`` gates only on
   backend + model client mode; it must not reference ``adapter_mode``.
"""

from __future__ import annotations

import inspect
import unittest
from unittest import mock

from eva.kernel.config import ExternalLifeConfig
from eva.kernel.main import build_runtime_config_from_args, parse_args
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE

_FRAMEWORK_DEFAULT = ExternalLifeConfig()


def _parse(*cli_args: str):
    argv = ["prog", "--runtime-dir", "/tmp/eva-linux-timing-regression", *cli_args]
    with mock.patch("sys.argv", argv):
        return parse_args()


class LinuxTimingUnchangedTests(unittest.TestCase):
    def test_linux_bundle_declares_no_suggested_timing(self) -> None:
        # Red line: Linux keeps the framework calendar tempo; it must NOT
        # silently acquire a scenario-declared timing.
        self.assertIsNone(LINUX_RUNTIME_SCENARIO_BUNDLE.suggested_timing)

    def test_linux_effective_timing_is_framework_default(self) -> None:
        config = build_runtime_config_from_args(
            _parse(), suggested_timing=LINUX_RUNTIME_SCENARIO_BUNDLE.suggested_timing
        )
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, _FRAMEWORK_DEFAULT.shallow_patrol_interval_sec)
        self.assertEqual(el.deep_patrol_interval_sec, _FRAMEWORK_DEFAULT.deep_patrol_interval_sec)
        self.assertEqual(el.full_report_interval_sec, _FRAMEWORK_DEFAULT.full_report_interval_sec)
        self.assertEqual(el.recent_event_window_sec, _FRAMEWORK_DEFAULT.recent_event_window_sec)

    def test_linux_cli_override_still_wins(self) -> None:
        args = _parse(
            "--shallow-patrol-interval", "0.01",
            "--deep-patrol-interval", "0.02",
            "--full-report-interval", "0.03",
            "--recent-event-window", "60",
        )
        config = build_runtime_config_from_args(
            args, suggested_timing=LINUX_RUNTIME_SCENARIO_BUNDLE.suggested_timing
        )
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 0.01)
        self.assertEqual(el.deep_patrol_interval_sec, 0.02)
        self.assertEqual(el.full_report_interval_sec, 0.03)
        self.assertEqual(el.recent_event_window_sec, 60.0)


class DlpfcProducerAdapterModeIndependenceTests(unittest.TestCase):
    def test_build_candidate_producer_does_not_reference_adapter_mode(self) -> None:
        # Red line: the observation-2 adapter_mode flip must not couple into the
        # dlPFC producer. Its gating reads backend + model client mode only.
        from runners.run_crafter import _build_candidate_producer

        src = inspect.getsource(_build_candidate_producer)
        self.assertNotIn("adapter_mode", src)
        self.assertIn("working_memory_backend", src)
        self.assertIn("working_memory_model_client_mode", src)


if __name__ == "__main__":
    unittest.main()
