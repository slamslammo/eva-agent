from __future__ import annotations
import tempfile
import unittest
from datetime import timedelta
from eva.kernel import DriveStateTable, EventRecord, ExternalLifeConfig, InstanceGuard, LifecycleConfig, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.l1_sensing import SensorOutput, SensorSpec, build_sensor_registry, execute_patrol
from eva.kernel.lifecycle import LifeState, LifecycleRuntime, WorkSlice
from eva.l3_deliberation.tool_edge import RECHECK_ACTION, REPAIR_ACTION


class PatrolRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StateStore(build_runtime_paths(self.temp_dir.name))
        self.lifecycle = LifecycleConfig(
            heartbeat_interval_sec=0.2,
            lease_duration_sec=1.0,
            recovering_window_sec=0.05,
            turn_guard_window_sec=0.01,
        )
        self.external_life = ExternalLifeConfig(
            shallow_patrol_interval_sec=0.01,
            deep_patrol_interval_sec=0.02,
            full_report_interval_sec=0.03,
            recent_event_window_sec=60.0,
        )
        self.guard = InstanceGuard(self.store.paths.lock_file, self.store, self.lifecycle)
        self.guard.acquire()
        self.active_record = self.guard.start_instance("eva-patrol")
        self.state = RuntimeState(
            life_state=LifeState.STABLE.value,
            instance_valid=True,
            heartbeat_ok=True,
            tick_ok=True,
            recovering_until=utc_now() - timedelta(seconds=1),
        )
        self.store.write_runtime_state(self.state)
        self.store.append_event(
            EventRecord(
                event_type="startup",
                timestamp=utc_now(),
                instance_id=self.active_record.instance_id,
                generation=self.active_record.generation,
            )
        )
        self.runtime = LifecycleRuntime(self.store, self.guard, self.lifecycle, self.external_life)

    def tearDown(self) -> None:
        self.guard.release()
        self.temp_dir.cleanup()

    def test_execute_patrol_emits_status_signal_with_rate_context(self) -> None:
        now = utc_now()

        result = execute_patrol(
            "deep",
            self.store,
            self.state,
            self.external_life,
            now,
            due_at=now - timedelta(seconds=1),
        )

        self.assertEqual(result.signal_summary.signal_count, 1)
        self.assertEqual(result.signal_batch["summary"], result.signal_summary.to_dict())
        self.assertEqual(len(result.signal_batch["signals"]), 1)
        self.assertEqual(result.signal_batch["signals"][0]["class"], "status")
        self.assertEqual(result.signal_summary.status_signal_count, 1)
        self.assertEqual(result.signal_summary.threat_signal_count, 0)
        self.assertFalse(result.signal_summary.has_threat_signal)
        self.assertEqual(result.routing_decision.urgency, "normal")
        self.assertEqual(result.routing_decision.dispatch_hint, "deliberation_only")
        self.assertFalse(result.routing_decision.has_threat_signal)
        self.assertFalse(result.routing_decision.compatibility_bridge_candidate)
        self.assertEqual(result.routing_decision.reasons, ("status_signal_present",))
        self.assertEqual(len(result.signals), 1)
        self.assertEqual({drive.drive_type for drive in result.drive_state.drives}, {"survival", "integrity", "continuity", "curiosity"})
        self.assertEqual(result.drive_summary.top_drive, "curiosity")
        self.assertEqual(result.drive_broadcast.top_drive, "curiosity")
        self.assertIn("curiosity", result.drive_broadcast.drive_levels)

        status_signal = result.signals[0].to_dict()
        self.assertEqual(status_signal["source"], "deep")
        self.assertEqual(status_signal["class"], "status")
        self.assertEqual(status_signal["captured_at"], result.snapshot.to_dict()["captured_at"])
        self.assertEqual(status_signal["payload"], result.snapshot.to_dict())
        self.assertIn("host_continuity", status_signal["rate_context"])
        self.assertFalse(status_signal["rate_context"]["host_continuity"]["available"])

        self.runtime.pending_work.clear()
        start = utc_now()

        self.runtime.queue_due_patrols(start)
        self.assertEqual(len(self.runtime.pending_work), 0)

        self.runtime.queue_due_patrols(start + timedelta(seconds=0.05))
        queued = list(self.runtime.pending_work)
        self.assertEqual([item.name for item in queued], ["shallow", "deep", "full"])
        self.assertTrue(all(item.kind == "patrol" for item in queued))

        self.runtime.queue_due_patrols(start + timedelta(seconds=0.06))
        self.assertEqual(len(self.runtime.pending_work), 3)


    def test_execute_patrol_uses_injected_sensor_registry(self) -> None:
        registry = build_sensor_registry(
            (
                SensorSpec(
                    name="host_continuity",
                    collect=lambda context: SensorOutput(
                        dimension="host_continuity",
                        payload={
                            "process_running": True,
                            "recent_restart_count": 0,
                            "schedule_drift_sec": 0.0,
                            "rate_context": {"available": False, "direction": "unknown"},
                        },
                    ),
                ),
                SensorSpec(
                    name="runtime_integrity",
                    collect=lambda context: SensorOutput(
                        dimension="runtime_integrity",
                        payload={
                            "instance_valid": True,
                            "runtime_writable": True,
                            "active_instance_present": True,
                            "runtime_state_present": True,
                            "events_present": True,
                            "lock_present": True,
                            "recent_yield_count": 0,
                            "recent_distress_count": 0,
                            "heartbeat_age_sec": context.runtime_state.heartbeat_age_sec,
                            "consecutive_failures": context.runtime_state.consecutive_failures,
                            "rate_context": {"available": False, "direction": "unknown"},
                        },
                    ),
                ),
                SensorSpec(
                    name="resource_state",
                    collect=lambda context: SensorOutput(
                        dimension="resource_state",
                        payload={
                            "runtime_path_exists": True,
                            "runtime_writable": True,
                            "disk_free_bytes": 10**10,
                            "rate_context": {"available": False, "direction": "unknown"},
                        },
                    ),
                ),
                SensorSpec(
                    name="anomaly_accumulation",
                    collect=lambda context: SensorOutput(
                        dimension="anomaly_accumulation",
                        payload={
                            "recent_error_count": 0,
                            "recent_yield_count": 0,
                            "recent_distress_count": 0,
                            "recent_restart_count": 0,
                            "anomaly_count": 0,
                            "rate_context": {"available": False, "direction": "unknown"},
                        },
                    ),
                ),
            )
        )
        now = utc_now()

        result = execute_patrol(
            "deep",
            self.store,
            self.state,
            self.external_life,
            now,
            sensor_registry=registry,
        )

        self.assertEqual(result.signal_summary.status_signal_count, 1)
        self.assertEqual(result.snapshot.overall_status, "healthy")


if __name__ == "__main__":
    unittest.main()
