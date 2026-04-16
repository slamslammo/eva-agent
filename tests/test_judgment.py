from __future__ import annotations

import unittest

from eva.config import ExternalLifeConfig
from eva.judgment import determine_overall_status, determine_primary_gap, determine_trend, evaluate_dimensions
from eva.state import DimensionSnapshot, ExternalLifeSnapshot, utc_now


class JudgmentTests(unittest.TestCase):
    def test_evaluate_dimensions_returns_healthy_snapshot_when_inputs_are_clean(self) -> None:
        config = ExternalLifeConfig()
        inputs = {
            "host_continuity": {
                "process_running": True,
                "recent_restart_count": 1,
                "schedule_drift_sec": 0.0,
            },
            "runtime_integrity": {
                "instance_valid": True,
                "runtime_writable": True,
                "active_instance_present": True,
                "runtime_state_present": True,
                "events_present": True,
                "lock_present": True,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
            },
            "resource_state": {
                "runtime_path_exists": True,
                "runtime_writable": True,
                "disk_free_bytes": config.disk_degraded_free_bytes + 1,
            },
            "anomaly_accumulation": {
                "recent_error_count": 0,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
                "recent_restart_count": 1,
            },
        }

        dimensions = evaluate_dimensions(inputs, config)

        self.assertTrue(all(snapshot.status == "healthy" for snapshot in dimensions.values()))
        self.assertEqual(determine_overall_status(dimensions), "healthy")
        self.assertEqual(determine_primary_gap(dimensions), {"type": "none", "reason": "none"})

    def test_runtime_integrity_has_highest_priority_when_runtime_files_are_missing(self) -> None:
        config = ExternalLifeConfig()
        inputs = {
            "host_continuity": {
                "process_running": True,
                "recent_restart_count": 0,
                "schedule_drift_sec": 0.0,
            },
            "runtime_integrity": {
                "instance_valid": True,
                "runtime_writable": True,
                "active_instance_present": True,
                "runtime_state_present": False,
                "events_present": True,
                "lock_present": True,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
            },
            "resource_state": {
                "runtime_path_exists": True,
                "runtime_writable": True,
                "disk_free_bytes": config.disk_degraded_free_bytes + 1,
            },
            "anomaly_accumulation": {
                "recent_error_count": 0,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
                "recent_restart_count": 0,
            },
        }

        dimensions = evaluate_dimensions(inputs, config)

        self.assertEqual(dimensions["runtime_integrity"].status, "critical")
        self.assertEqual(dimensions["runtime_integrity"].evidence["reason"], "runtime_files_missing")
        self.assertEqual(determine_overall_status(dimensions), "critical")
        self.assertEqual(determine_primary_gap(dimensions), {"type": "runtime_integrity", "reason": "runtime_files_missing"})

    def test_determine_trend_compares_previous_overall_status(self) -> None:
        now = utc_now()
        previous = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="shallow",
            dimensions={"runtime_integrity": DimensionSnapshot(status="healthy", evidence={})},
            overall_status="degraded",
            primary_gap={"type": "runtime_integrity", "reason": "recent_yield_detected"},
            trend="stable",
            updated_at=now,
        )

        self.assertEqual(determine_trend("critical", previous), "worsening")
        self.assertEqual(determine_trend("healthy", previous), "improving")
        self.assertEqual(determine_trend("degraded", previous), "stable")
        self.assertEqual(determine_trend("healthy", None), "unknown")


if __name__ == "__main__":
    unittest.main()
