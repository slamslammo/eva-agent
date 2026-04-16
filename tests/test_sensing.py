from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.config import ExternalLifeConfig, build_runtime_paths
from eva.sensing import collect_external_life_inputs
from eva.state import ActiveInstanceRecord, EventRecord, RuntimeState, StateStore, utc_now


class SensingTests(unittest.TestCase):
    def test_collect_external_life_inputs_reads_runtime_and_recent_events(self) -> None:
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
            runtime_state = RuntimeState(instance_valid=True, heartbeat_ok=True, tick_ok=True, updated_at=now)
            store.write_runtime_state(runtime_state)
            store.paths.lock_file.write_text("", encoding="utf-8")
            store.append_event(EventRecord(event_type="startup", timestamp=now - timedelta(seconds=2)))
            store.append_event(EventRecord(event_type="yield", timestamp=now - timedelta(seconds=1)))
            store.append_event(EventRecord(event_type="error", timestamp=now - timedelta(seconds=1)))
            store.append_event(EventRecord(event_type="distress", timestamp=now - timedelta(seconds=1)))
            store.append_event(EventRecord(event_type="startup", timestamp=now - timedelta(seconds=120)))

            inputs = collect_external_life_inputs(
                store,
                runtime_state,
                ExternalLifeConfig(recent_event_window_sec=60.0),
                now,
                due_at=now - timedelta(seconds=3),
            )

            self.assertTrue(inputs["host_continuity"]["process_running"])
            self.assertEqual(inputs["host_continuity"]["recent_restart_count"], 1)
            self.assertAlmostEqual(inputs["host_continuity"]["schedule_drift_sec"], 3.0, places=1)
            self.assertTrue(inputs["runtime_integrity"]["active_instance_present"])
            self.assertTrue(inputs["runtime_integrity"]["runtime_state_present"])
            self.assertTrue(inputs["runtime_integrity"]["events_present"])
            self.assertTrue(inputs["runtime_integrity"]["lock_present"])
            self.assertTrue(inputs["runtime_integrity"]["runtime_writable"])
            self.assertEqual(inputs["runtime_integrity"]["recent_yield_count"], 1)
            self.assertEqual(inputs["runtime_integrity"]["recent_distress_count"], 1)
            self.assertTrue(inputs["resource_state"]["runtime_path_exists"])
            self.assertGreater(inputs["resource_state"]["disk_free_bytes"], 0)
            self.assertEqual(inputs["anomaly_accumulation"]["recent_error_count"], 1)
            self.assertEqual(inputs["anomaly_accumulation"]["recent_restart_count"], 1)


if __name__ == "__main__":
    unittest.main()
