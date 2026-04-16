from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.config import ExternalLifeConfig, LifecycleConfig, build_runtime_paths
from eva.instance import InstanceGuard
from eva.lifecycle import LifeState, LifecycleRuntime, WorkSlice
from eva.state import EventRecord, RuntimeState, StateStore, utc_now


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

    def test_queue_due_patrols_adds_patrol_work_without_duplicates(self) -> None:
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

    def test_run_turn_executes_deep_patrol_and_persists_artifacts(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))

        result = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=now + timedelta(seconds=1),
            now=now,
        )

        self.assertTrue(result.executed)
        self.assertEqual(result.work_slice, "deep")
        self.assertEqual(result.work_kind, "patrol")
        self.assertEqual(result.details["status"], "completed")
        self.assertEqual(result.details["overall_status"], "healthy")
        self.assertEqual(result.details["pressure_count"], 0)

        snapshot = self.store.read_external_life_snapshot()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.source_patrol, "deep")
        self.assertEqual(snapshot.overall_status, "healthy")
        self.assertEqual(snapshot.primary_gap["type"], "none")

        pressure_table = self.store.read_active_pressures()
        self.assertEqual(len(pressure_table.pressures), 0)

        survival_log = self.store.read_survival_log()
        self.assertEqual(len(survival_log), 1)
        self.assertEqual(survival_log[0]["event_type"], "survival_snapshot")
        self.assertEqual(survival_log[0]["source_patrol"], "deep")

        turn_events = [event for event in self.store.read_events() if event["event_type"] == "turn_completed"]
        self.assertEqual(len(turn_events), 1)
        self.assertEqual(turn_events[0]["details"]["work_kind"], "patrol")
        self.assertEqual(turn_events[0]["details"]["work_slice"], "deep")

    def test_patrol_history_records_pressure_opened_and_resolved(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.state.instance_valid = False
        self.store.write_runtime_state(self.state)
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))

        first = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=now + timedelta(seconds=1),
            now=now,
        )
        self.assertTrue(first.executed)
        self.assertEqual(first.details["pressure_count"], 1)
        self.assertEqual(first.details["opened_count"], 1)
        self.assertEqual(first.details["resolved_count"], 0)

        pressure_table = self.store.read_active_pressures()
        self.assertEqual(len(pressure_table.pressures), 1)
        self.assertEqual(pressure_table.pressures[0].type, "integrity")

        self.state.instance_valid = True
        self.store.write_runtime_state(self.state)
        later = now + timedelta(seconds=0.5)
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=later - timedelta(seconds=1)))
        second = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=later + timedelta(seconds=1),
            now=later,
        )
        self.assertTrue(second.executed)
        self.assertEqual(second.details["pressure_count"], 0)
        self.assertEqual(second.details["opened_count"], 0)
        self.assertEqual(second.details["resolved_count"], 1)

        survival_events = [entry["event_type"] for entry in self.store.read_survival_log()]
        self.assertIn("pressure_opened", survival_events)
        self.assertIn("pressure_resolved", survival_events)
        self.assertIn("survival_snapshot", survival_events)


if __name__ == "__main__":
    unittest.main()
