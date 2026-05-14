from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.kernel import ActiveInstanceRecord, DimensionSnapshot, EventRecord, ExternalLifeConfig, ExternalLifeSnapshot, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.l1_sensing.sensor_registry import SensingContext
from eva.l1_sensing.state_sensors import build_state_sensor_specs, built_in_sensor_providers
from scenarios.linux_runtime import activate_linux_runtime_scenario
from scenarios.linux_runtime.sensors.rate_context import host_continuity_rate_context


class StateSensorsTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()

    def test_build_state_sensor_specs_preserves_order_and_names(self) -> None:
        specs = build_state_sensor_specs()

        self.assertEqual(
            tuple(spec.name for spec in specs),
            ("host_continuity", "runtime_integrity", "resource_state", "anomaly_accumulation"),
        )
        self.assertEqual(
            tuple(spec.name for provider in built_in_sensor_providers() for spec in provider()),
            tuple(spec.name for spec in specs),
        )

    def test_state_sensor_specs_collect_expected_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.ensure_runtime_dir()
            now = utc_now()
            store.write_active_instance(
                ActiveInstanceRecord(
                    instance_id="eva-sensing",
                    generation=1,
                    lease_expires_at=now + timedelta(seconds=30),
                    lock_holder=True,
                    updated_at=now,
                )
            )
            runtime_state = RuntimeState(
                instance_valid=True,
                heartbeat_ok=True,
                tick_ok=True,
                heartbeat_age_sec=2.0,
                consecutive_failures=1,
                updated_at=now,
            )
            store.write_runtime_state(runtime_state)
            store.paths.lock_file.write_text("", encoding="utf-8")
            store.append_event(EventRecord(event_type="startup", timestamp=now - timedelta(seconds=2)))
            store.append_event(EventRecord(event_type="yield", timestamp=now - timedelta(seconds=1)))
            store.append_event(EventRecord(event_type="error", timestamp=now - timedelta(seconds=1)))
            store.append_event(EventRecord(event_type="distress", timestamp=now - timedelta(seconds=1)))

            previous_time = now - timedelta(seconds=10)
            previous_snapshot = ExternalLifeSnapshot(
                captured_at=previous_time,
                source_patrol="deep",
                dimensions={
                    "host_continuity": DimensionSnapshot(
                        status="healthy",
                        evidence={
                            "recent_restart_count": 0,
                            "schedule_drift_sec": 1.0,
                        },
                    ),
                    "runtime_integrity": DimensionSnapshot(
                        status="healthy",
                        evidence={
                            "recent_yield_count": 0,
                            "recent_distress_count": 0,
                            "heartbeat_age_sec": 0.0,
                            "consecutive_failures": 0,
                        },
                    ),
                    "resource_state": DimensionSnapshot(
                        status="healthy",
                        evidence={"disk_free_bytes": 1},
                    ),
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
                updated_at=previous_time,
            )
            recent_events = store.read_events()
            context = SensingContext(
                store=store,
                runtime_state=runtime_state,
                config=ExternalLifeConfig(recent_event_window_sec=60.0),
                now=now,
                due_at=now - timedelta(seconds=3),
                previous_snapshot=previous_snapshot,
                shared_facts={
                    "recent_events": recent_events,
                    "runtime_exists": True,
                    "runtime_writable": True,
                    "disk_usage": __import__("shutil").disk_usage(store.paths.runtime_dir),
                    "recent_restart_count": 1,
                    "recent_yield_count": 1,
                    "recent_distress_count": 1,
                    "recent_error_count": 1,
                    "anomaly_count": 3,
                    "schedule_drift_sec": 3.0,
                    "elapsed_sec": 10.0,
                    "rate_available": True,
                },
            )

            outputs = [spec.collect(context) for spec in build_state_sensor_specs()]

            self.assertEqual(
                [output.dimension for output in outputs],
                ["host_continuity", "runtime_integrity", "resource_state", "anomaly_accumulation"],
            )
            outputs_by_dimension = {output.dimension: output.payload for output in outputs}
            self.assertTrue(outputs_by_dimension["host_continuity"]["process_running"])
            self.assertTrue(outputs_by_dimension["runtime_integrity"]["active_instance_present"])
            self.assertTrue(outputs_by_dimension["resource_state"]["runtime_path_exists"])
            self.assertEqual(outputs_by_dimension["anomaly_accumulation"]["recent_error_count"], 1)
            self.assertEqual(outputs_by_dimension["host_continuity"]["rate_context"]["direction"], "worsening")
            self.assertEqual(
                host_continuity_rate_context(
                    facts=context.shared_facts,
                    previous_snapshot=context.previous_snapshot,
                    window_sec=context.config.recent_event_window_sec,
                )["direction"],
                "worsening",
            )
            self.assertEqual(outputs_by_dimension["runtime_integrity"]["rate_context"]["direction"], "worsening")
            self.assertIn("direction", outputs_by_dimension["resource_state"]["rate_context"])
            self.assertEqual(outputs_by_dimension["anomaly_accumulation"]["rate_context"]["direction"], "worsening")


if __name__ == "__main__":
    unittest.main()
