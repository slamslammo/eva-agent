from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.config import ExternalLifeConfig, LifecycleConfig, build_runtime_paths
from eva.instance import InstanceGuard
from eva.lifecycle import LifeState, LifecycleRuntime, WorkSlice
from eva.response import RECHECK_ACTION, REPAIR_ACTION
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
        self.assertNotIn("response", result.details)

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
        response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(response_events, [])
        self.assertEqual(self.store.read_response_history(), [])

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
        self.assertIn("response", first.details)
        self.assertEqual(first.details["response"]["pressure_type"], "integrity")
        self.assertEqual(first.details["response"]["selected_action"], RECHECK_ACTION)
        self.assertEqual(first.details["response"]["execution_status"], "completed")
        response_history = self.store.read_response_history()
        self.assertEqual(len(response_history), 1)
        self.assertEqual(response_history[0]["selected_action"], RECHECK_ACTION)
        response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(len(response_events), 1)
        self.assertEqual(response_events[0]["turn_id"], first.turn_id)
        self.assertEqual(response_events[0]["details"]["selected_action"], RECHECK_ACTION)
        self.assertEqual(response_events[0]["details"]["pressure_type"], "integrity")

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
        self.assertNotIn("response", second.details)

        later_response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(len(later_response_events), 1)

        survival_events = [entry["event_type"] for entry in self.store.read_survival_log()]
        self.assertIn("pressure_opened", survival_events)
        self.assertIn("pressure_resolved", survival_events)
        self.assertIn("survival_snapshot", survival_events)

    def test_repair_response_pauses_maintenance_until_next_patrol(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))
        self.runtime.pending_work.append(WorkSlice(name="self_check"))
        self.store.append_event(
            EventRecord(
                event_type="yield",
                timestamp=now - timedelta(seconds=0.1),
                details={"reason": "manual_test_yield"},
            )
        )

        first = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=now + timedelta(seconds=1),
            now=now,
        )
        self.assertTrue(first.executed)
        self.assertIn("response", first.details)
        self.assertEqual(first.details["response"]["selected_action"], REPAIR_ACTION)
        self.assertTrue(self.runtime._conservative_until_next_patrol)
        response_history = self.store.read_response_history()
        self.assertEqual(response_history[0]["side_effects"], ["temporary_conservative_until_next_patrol"])
        self.assertEqual([work.name for work in self.runtime.pending_work], ["self_check"])
        self.assertFalse(self.runtime.has_pending_work())

        blocked_at = now + timedelta(seconds=0.05)
        blocked = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=blocked_at + timedelta(seconds=1),
            now=blocked_at,
        )
        self.assertFalse(blocked.executed)
        self.assertEqual(blocked.details["reason"], "conservative_mode_waiting_for_patrol")
        self.assertEqual([work.name for work in self.runtime.pending_work], ["self_check"])

        patrol_at = now + timedelta(seconds=0.2)
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=patrol_at - timedelta(seconds=1)))
        self.assertTrue(self.runtime.has_pending_work())
        second = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=patrol_at + timedelta(seconds=1),
            now=patrol_at,
        )
        self.assertTrue(second.executed)
        self.assertEqual(second.work_slice, "deep")
        self.assertFalse(self.runtime._conservative_until_next_patrol)
        self.assertEqual([work.name for work in self.runtime.pending_work], ["self_check"])
        self.assertTrue(self.runtime.has_pending_work())

