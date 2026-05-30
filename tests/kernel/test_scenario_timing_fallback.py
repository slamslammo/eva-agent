"""framework-scenario-timing slice 2 — CLI→scenario timing fallback.

``build_runtime_config_from_args`` 现在接受一个可选的 ``suggested_timing``
（场景声明的 external-life 节律）。优先级：

    CLI 显式传入  >  scenario.suggested_timing  >  框架默认 ExternalLifeConfig()

实现关键：四个 timing argparse 参数默认值改成 ``None`` 哨兵，用以区分"用户显式
传入"与"未传"。未传的字段回退到 ``suggested_timing``（再回退到框架默认）；非 timing
阈值（disk / continuity / anomaly）由 ``dataclasses.replace`` 自 base 保留。
"""

from __future__ import annotations

import unittest
from unittest import mock

from eva.kernel.config import ExternalLifeConfig
from eva.kernel.main import build_runtime_config_from_args, parse_args


def _parse(*cli_args: str):
    """Parse args with a controlled argv (only --runtime-dir is required)."""

    argv = ["prog", "--runtime-dir", "/tmp/eva-timing-fallback-test", *cli_args]
    with mock.patch("sys.argv", argv):
        return parse_args()


_SCENARIO_TIMING = ExternalLifeConfig(
    shallow_patrol_interval_sec=2.0,
    deep_patrol_interval_sec=4.0,
    full_report_interval_sec=8.0,
    recent_event_window_sec=16.0,
)


class TimingArgparseSentinelTests(unittest.TestCase):
    def test_timing_defaults_are_none_sentinels(self) -> None:
        # 哨兵：未传 timing flag 时 argparse 值必须是 None（而非旧的硬编码 300/1800/...），
        # 否则无法区分"显式传"与"未传"。
        args = _parse()
        self.assertIsNone(args.shallow_patrol_interval)
        self.assertIsNone(args.deep_patrol_interval)
        self.assertIsNone(args.full_report_interval)
        self.assertIsNone(args.recent_event_window)


class TimingFallbackPriorityTests(unittest.TestCase):
    def test_no_scenario_no_cli_uses_framework_defaults(self) -> None:
        # 既有行为不变：无 scenario、无 CLI → 框架默认 300/1800/86400/1800。
        config = build_runtime_config_from_args(_parse())
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 300.0)
        self.assertEqual(el.deep_patrol_interval_sec, 1800.0)
        self.assertEqual(el.full_report_interval_sec, 86400.0)
        self.assertEqual(el.recent_event_window_sec, 1800.0)

    def test_scenario_timing_used_when_cli_absent(self) -> None:
        config = build_runtime_config_from_args(_parse(), suggested_timing=_SCENARIO_TIMING)
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 2.0)
        self.assertEqual(el.deep_patrol_interval_sec, 4.0)
        self.assertEqual(el.full_report_interval_sec, 8.0)
        self.assertEqual(el.recent_event_window_sec, 16.0)

    def test_cli_overrides_scenario_timing(self) -> None:
        args = _parse(
            "--shallow-patrol-interval", "0.5",
            "--deep-patrol-interval", "1.5",
            "--full-report-interval", "2.5",
            "--recent-event-window", "3.5",
        )
        config = build_runtime_config_from_args(args, suggested_timing=_SCENARIO_TIMING)
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 0.5)
        self.assertEqual(el.deep_patrol_interval_sec, 1.5)
        self.assertEqual(el.full_report_interval_sec, 2.5)
        self.assertEqual(el.recent_event_window_sec, 3.5)

    def test_partial_cli_override_falls_back_per_field(self) -> None:
        # 只显式传 shallow，其余回退到 scenario 声明（逐字段决策）。
        args = _parse("--shallow-patrol-interval", "0.5")
        config = build_runtime_config_from_args(args, suggested_timing=_SCENARIO_TIMING)
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 0.5)  # CLI
        self.assertEqual(el.deep_patrol_interval_sec, 4.0)  # scenario
        self.assertEqual(el.full_report_interval_sec, 8.0)  # scenario
        self.assertEqual(el.recent_event_window_sec, 16.0)  # scenario

    def test_cli_over_framework_default_when_no_scenario(self) -> None:
        # 无 scenario 但有 CLI → CLI 值生效，未传字段回退框架默认。
        args = _parse("--deep-patrol-interval", "1.5")
        config = build_runtime_config_from_args(args)
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 300.0)  # framework default
        self.assertEqual(el.deep_patrol_interval_sec, 1.5)  # CLI
        self.assertEqual(el.full_report_interval_sec, 86400.0)  # framework default
        self.assertEqual(el.recent_event_window_sec, 1800.0)  # framework default


class TimingNonTimingFieldsPreservedTests(unittest.TestCase):
    def test_scenario_non_timing_thresholds_survive_replace(self) -> None:
        # suggested_timing 携带的非 timing 阈值（disk 等）在 CLI 覆盖 timing 字段后仍保留。
        scenario_timing = ExternalLifeConfig(
            shallow_patrol_interval_sec=2.0,
            disk_degraded_free_bytes=123,
            anomaly_critical_count=99,
        )
        args = _parse("--shallow-patrol-interval", "0.5")
        config = build_runtime_config_from_args(args, suggested_timing=scenario_timing)
        el = config.external_life
        self.assertEqual(el.shallow_patrol_interval_sec, 0.5)  # CLI override
        self.assertEqual(el.disk_degraded_free_bytes, 123)  # preserved from scenario
        self.assertEqual(el.anomaly_critical_count, 99)  # preserved from scenario


if __name__ == "__main__":
    unittest.main()
