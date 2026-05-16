from __future__ import annotations

import unittest

from eva.kernel import DimensionSnapshot, ExternalLifeConfig, ExternalLifeSnapshot, utc_now
from eva.l1_sensing import (
    DimensionSpec,
    determine_overall_status,
    determine_primary_gap,
    determine_trend,
    evaluate_dimensions,
    register_default_dimension_specs,
)
from eva.persistence_targets import build_linux_runtime_persistence_hierarchy, register_default_persistence_hierarchy
import eva.persistence_targets as persistence_targets
from eva.l1_sensing import dimension_specs as dimension_specs_module
from scenarios.linux_runtime.dimensions import LINUX_RUNTIME_DIMENSION_SPECS


class JudgmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_hierarchy = persistence_targets._DEFAULT_PERSISTENCE_HIERARCHY
        self._original_dimension_specs = dimension_specs_module._DEFAULT_DIMENSION_SPECS
        register_default_persistence_hierarchy(build_linux_runtime_persistence_hierarchy())
        register_default_dimension_specs(LINUX_RUNTIME_DIMENSION_SPECS)

    def tearDown(self) -> None:
        persistence_targets._DEFAULT_PERSISTENCE_HIERARCHY = self._original_hierarchy
        dimension_specs_module._DEFAULT_DIMENSION_SPECS = self._original_dimension_specs

    def test_evaluate_dimensions_returns_healthy_snapshot_when_inputs_are_clean(self) -> None:
        config = ExternalLifeConfig()
        inputs = {
            "host_continuity": {
                "process_running": True,
                "recent_restart_count": 1,
                "schedule_drift_sec": 0.0,
                "rate_context": {"direction": "stable"},
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
                "rate_context": {"direction": "stable"},
            },
            "resource_state": {
                "runtime_path_exists": True,
                "runtime_writable": True,
                "disk_free_bytes": config.disk_degraded_free_bytes + 1,
                "rate_context": {"direction": "stable"},
            },
            "anomaly_accumulation": {
                "recent_error_count": 0,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
                "recent_restart_count": 1,
                "rate_context": {"direction": "stable"},
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
                "rate_context": {"direction": "stable"},
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
                "rate_context": {"direction": "stable"},
            },
            "resource_state": {
                "runtime_path_exists": True,
                "runtime_writable": True,
                "disk_free_bytes": config.disk_degraded_free_bytes + 1,
                "rate_context": {"direction": "stable"},
            },
            "anomaly_accumulation": {
                "recent_error_count": 0,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
                "recent_restart_count": 0,
                "rate_context": {"direction": "stable"},
            },
        }

        dimensions = evaluate_dimensions(inputs, config)

        self.assertEqual(dimensions["runtime_integrity"].status, "critical")
        self.assertEqual(dimensions["runtime_integrity"].evidence["reason"], "runtime_files_missing")
        self.assertEqual(dimensions["runtime_integrity"].evidence["persistence_hierarchy"]["failed_levels"], [4])
        self.assertEqual(determine_overall_status(dimensions), "critical")
        self.assertEqual(determine_primary_gap(dimensions), {"type": "runtime_integrity", "reason": "runtime_files_missing"})

    def test_rate_context_can_raise_near_threshold_dimension_to_degraded(self) -> None:
        config = ExternalLifeConfig(
            continuity_restart_degraded_count=2,
            anomaly_degraded_count=2,
            disk_degraded_free_bytes=100,
            disk_critical_free_bytes=50,
        )
        inputs = {
            "host_continuity": {
                "process_running": True,
                "recent_restart_count": 1,
                "schedule_drift_sec": 0.0,
                "rate_context": {"available": True, "direction": "degrading"},
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
                "heartbeat_age_sec": 1.0,
                "consecutive_failures": 1,
                "rate_context": {"available": True, "direction": "degrading"},
            },
            "resource_state": {
                "runtime_path_exists": True,
                "runtime_writable": True,
                "disk_free_bytes": 105,
                "rate_context": {
                    "available": True,
                    "direction": "degrading",
                    "disk_free_bytes_delta": -10.0,
                },
            },
            "anomaly_accumulation": {
                "recent_error_count": 1,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
                "recent_restart_count": 1,
                "anomaly_count": 1,
                "rate_context": {"available": True, "direction": "degrading"},
            },
        }

        dimensions = evaluate_dimensions(inputs, config)

        self.assertEqual(dimensions["host_continuity"].status, "degraded")
        self.assertEqual(dimensions["runtime_integrity"].status, "degraded")
        self.assertEqual(dimensions["resource_state"].status, "degraded")
        self.assertEqual(dimensions["anomaly_accumulation"].status, "degraded")

        now = utc_now()
        previous = ExternalLifeSnapshot(
            captured_at=now,
            source_patrol="deep",
            dimensions={
                "runtime_integrity": DimensionSnapshot(
                    status="degraded",
                    evidence={"reason": "recent_yield_detected"},
                ),
                "host_continuity": DimensionSnapshot(status="healthy", evidence={}),
                "resource_state": DimensionSnapshot(status="healthy", evidence={}),
                "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={}),
            },
            overall_status="degraded",
            primary_gap={"type": "runtime_integrity", "reason": "recent_yield_detected"},
            trend="stable",
            updated_at=now,
        )
        current_dimensions = {
            "runtime_integrity": DimensionSnapshot(
                status="degraded",
                evidence={
                    "reason": "recent_yield_detected",
                    "rate_context": {"direction": "degrading"},
                },
            ),
            "host_continuity": DimensionSnapshot(status="healthy", evidence={}),
            "resource_state": DimensionSnapshot(status="healthy", evidence={}),
            "anomaly_accumulation": DimensionSnapshot(status="healthy", evidence={}),
        }

        self.assertEqual(
            determine_trend("degraded", previous, current_dimensions=current_dimensions),
            "worsening",
        )

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

    def test_runtime_integrity_requires_registered_persistence_hierarchy(self) -> None:
        persistence_targets._DEFAULT_PERSISTENCE_HIERARCHY = None
        config = ExternalLifeConfig()
        inputs = {
            "host_continuity": {
                "process_running": True,
                "recent_restart_count": 1,
                "schedule_drift_sec": 0.0,
                "rate_context": {"direction": "stable"},
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
                "rate_context": {"direction": "stable"},
            },
            "resource_state": {
                "runtime_path_exists": True,
                "runtime_writable": True,
                "disk_free_bytes": config.disk_degraded_free_bytes + 1,
                "rate_context": {"direction": "stable"},
            },
            "anomaly_accumulation": {
                "recent_error_count": 0,
                "recent_yield_count": 0,
                "recent_distress_count": 0,
                "recent_restart_count": 1,
                "rate_context": {"direction": "stable"},
            },
        }

        with self.assertRaisesRegex(RuntimeError, "no persistence hierarchy registered"):
            evaluate_dimensions(inputs, config)

    def test_evaluate_dimensions_requires_registered_dimension_specs(self) -> None:
        dimension_specs_module._DEFAULT_DIMENSION_SPECS = ()
        with self.assertRaisesRegex(RuntimeError, "no dimension specs registered"):
            evaluate_dimensions({}, ExternalLifeConfig())

    def test_evaluate_dimensions_accepts_synthetic_non_linux_dimension_specs(self) -> None:
        def synthetic_snapshot(inputs: dict[str, object], config: ExternalLifeConfig) -> DimensionSnapshot:
            del config
            status = "critical" if bool(inputs.get("trip", False)) else "healthy"
            return DimensionSnapshot(status=status, evidence={"reason": "trip_detected" if status == "critical" else "synthetic_ok"})

        register_default_dimension_specs(
            (
                DimensionSpec(name="synthetic_alpha", priority=1, pressure_type="integrity", snapshot_fn=synthetic_snapshot),
                DimensionSpec(name="synthetic_beta", priority=0, pressure_type="integrity", snapshot_fn=synthetic_snapshot),
            )
        )
        dimensions = evaluate_dimensions(
            {
                "synthetic_alpha": {"trip": False},
                "synthetic_beta": {"trip": True},
            },
            ExternalLifeConfig(),
        )

        self.assertEqual(set(dimensions.keys()), {"synthetic_alpha", "synthetic_beta"})
        self.assertEqual(determine_primary_gap(dimensions), {"type": "synthetic_beta", "reason": "trip_detected"})


if __name__ == "__main__":
    unittest.main()
