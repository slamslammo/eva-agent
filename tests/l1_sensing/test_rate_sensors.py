from __future__ import annotations

import unittest
from datetime import timedelta

from eva.kernel import DimensionSnapshot, ExternalLifeSnapshot, RuntimeState, utc_now
from eva.l1_sensing.rate_sensors import elapsed_since_previous
from scenarios.linux_runtime.sensors.rate_context import (
    anomaly_accumulation_rate_context,
    host_continuity_rate_context,
    resource_state_rate_context,
    runtime_integrity_rate_context,
)


class RateSensorsTests(unittest.TestCase):
    def test_elapsed_since_previous_returns_none_without_snapshot(self) -> None:
        self.assertIsNone(elapsed_since_previous(None, utc_now()))

    def test_elapsed_since_previous_returns_elapsed_seconds(self) -> None:
        now = utc_now()
        previous = ExternalLifeSnapshot(
            captured_at=now - timedelta(seconds=10),
            source_patrol="deep",
            dimensions={},
            overall_status="healthy",
            primary_gap={"type": "none", "reason": "none"},
            trend="stable",
            updated_at=now - timedelta(seconds=10),
        )

        self.assertEqual(elapsed_since_previous(previous, now), 10.0)

    def test_rate_context_helpers_preserve_expected_shapes(self) -> None:
        previous = ExternalLifeSnapshot(
            captured_at=utc_now() - timedelta(seconds=10),
            source_patrol="deep",
            dimensions={
                "host_continuity": DimensionSnapshot(status="healthy", evidence={"recent_restart_count": 0, "schedule_drift_sec": 1.0}),
                "runtime_integrity": DimensionSnapshot(
                    status="healthy",
                    evidence={
                        "recent_yield_count": 0,
                        "recent_distress_count": 0,
                        "heartbeat_age_sec": 0.0,
                        "consecutive_failures": 0,
                    },
                ),
                "resource_state": DimensionSnapshot(status="healthy", evidence={"disk_free_bytes": 1}),
                "anomaly_accumulation": DimensionSnapshot(
                    status="healthy",
                    evidence={
                        "recent_error_count": 0,
                        "recent_yield_count": 0,
                        "recent_distress_count": 0,
                        "recent_restart_count": 0,
                        "anomaly_count": 0,
                    },
                ),
            },
            overall_status="healthy",
            primary_gap={"type": "none", "reason": "none"},
            trend="stable",
            updated_at=utc_now() - timedelta(seconds=10),
        )
        runtime_state = RuntimeState(
            instance_valid=True,
            heartbeat_ok=True,
            tick_ok=True,
            heartbeat_age_sec=2.0,
            consecutive_failures=1,
        )
        facts = {
            "recent_restart_count": 1,
            "recent_yield_count": 1,
            "recent_distress_count": 1,
            "recent_error_count": 1,
            "anomaly_count": 3,
            "schedule_drift_sec": 3.0,
            "elapsed_sec": 10.0,
            "rate_available": True,
            "disk_usage": type("DiskUsage", (), {"free": 100})(),
        }

        host = host_continuity_rate_context(facts=facts, previous_snapshot=previous, window_sec=60.0)
        runtime = runtime_integrity_rate_context(
            facts=facts,
            previous_snapshot=previous,
            runtime_state=runtime_state,
            window_sec=60.0,
        )
        resource = resource_state_rate_context(facts=facts, previous_snapshot=previous)
        anomaly = anomaly_accumulation_rate_context(facts=facts, previous_snapshot=previous, window_sec=60.0)

        self.assertEqual(host["direction"], "worsening")
        self.assertEqual(host["schedule_drift_direction"], "worsening")
        self.assertEqual(runtime["direction"], "worsening")
        self.assertEqual(runtime["heartbeat_age_direction"], "worsening")
        self.assertEqual(resource["direction"], "improving")
        self.assertIn("disk_free_bytes_delta", resource)
        self.assertEqual(anomaly["direction"], "worsening")
        self.assertIn("anomaly_count_delta", anomaly)


if __name__ == "__main__":
    unittest.main()
