from __future__ import annotations
import json
import tempfile
import unittest
from datetime import timedelta
from eva.kernel import EventRecord, ActiveInstanceRecord, InstanceGuard, LifecycleConfig, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.kernel.lifecycle import LifeState, LifecycleRuntime, WorkSlice
from scenarios.linux_runtime import activate_linux_runtime_scenario


class LifecycleRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_linux_runtime_scenario()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StateStore(build_runtime_paths(self.temp_dir.name))
        self.lifecycle = LifecycleConfig(
            heartbeat_interval_sec=1.0,
            degraded_after_missed_beats=2,
            critical_after_missed_beats=4,
            lease_duration_sec=3.0,
            recovering_window_sec=1.0,
            turn_guard_window_sec=0.2,
        )
        self.guard = InstanceGuard(self.store.paths.lock_file, self.store, self.lifecycle)
        self.guard.acquire()
        self.guard.start_instance("eva-lifecycle")
        self.runtime = LifecycleRuntime(self.store, self.guard, self.lifecycle)

    def tearDown(self) -> None:
        self.guard.release()
        self.temp_dir.cleanup()

    def test_compute_life_state_recovering_then_stable(self) -> None:
        now = utc_now()
        state = RuntimeState(last_heartbeat_at=now, recovering_until=now + timedelta(seconds=0.5))
        snapshot = self.guard.snapshot(now)
        self.assertEqual(self.runtime.compute_life_state(state, snapshot, now), LifeState.RECOVERING)
        later = now + timedelta(seconds=2)
        self.assertEqual(self.runtime.compute_life_state(state, snapshot, later), LifeState.DEGRADED)

    def test_compute_life_state_degraded_and_critical(self) -> None:
        now = utc_now()
        snapshot = self.guard.snapshot(now)
        degraded_state = RuntimeState(last_heartbeat_at=now - timedelta(seconds=2.1), recovering_until=now - timedelta(seconds=1))
        critical_state = RuntimeState(last_heartbeat_at=now - timedelta(seconds=4.1), recovering_until=now - timedelta(seconds=1))
        self.assertEqual(self.runtime.compute_life_state(degraded_state, snapshot, now), LifeState.DEGRADED)
        self.assertEqual(self.runtime.compute_life_state(critical_state, snapshot, now), LifeState.CRITICAL)

    def test_run_turn_yields_when_heartbeat_deadline_near(self) -> None:
        now = utc_now()
        state = RuntimeState(life_state=LifeState.STABLE.value, instance_valid=True, recovering_until=now - timedelta(seconds=1))
        result = self.runtime.run_turn(state, next_heartbeat_at=now + timedelta(seconds=0.1), now=now)
        self.assertFalse(result.executed)
        self.assertTrue(result.yielded_to_heartbeat)
        self.assertEqual(result.details["runtime_gate_context"]["turn_allowed"], True)
        self.assertEqual(result.details["runtime_gate_context"]["critical_blocked"], False)

    def test_run_turn_blocks_when_instance_invalid(self) -> None:
        now = utc_now()
        current = self.store.read_active_instance()
        assert current is not None
        self.store.write_active_instance(
            ActiveInstanceRecord(
                instance_id=current.instance_id,
                generation=current.generation,
                lease_expires_at=now - timedelta(seconds=1),
                lock_holder=True,
                updated_at=now,
            )
        )
        state = RuntimeState(life_state=LifeState.STABLE.value, instance_valid=True, recovering_until=now - timedelta(seconds=1))
        result = self.runtime.run_turn(state, next_heartbeat_at=now + timedelta(seconds=1), now=now)
        self.assertFalse(result.executed)
        self.assertFalse(result.yielded_to_heartbeat)
        self.assertEqual(result.details["runtime_gate_context"]["instance_valid"], False)
        self.assertEqual(result.details["runtime_gate_context"]["turn_allowed"], False)
        self.assertEqual(result.details["reason"], "lease_expired")

    def test_run_tick_emits_yield_with_specific_reason(self) -> None:
        now = utc_now()
        current = self.store.read_active_instance()
        assert current is not None
        self.store.write_active_instance(
            ActiveInstanceRecord(
                instance_id=current.instance_id,
                generation=current.generation + 1,
                lease_expires_at=current.lease_expires_at,
                lock_holder=True,
                updated_at=now,
            )
        )
        state = RuntimeState(life_state=LifeState.STABLE.value, last_heartbeat_at=now - timedelta(seconds=1), recovering_until=now - timedelta(seconds=1))
        self.runtime.run_tick(state, now=now)
        events = self.store.read_events()
        yield_events = [event for event in events if event["event_type"] == "yield"]
        self.assertEqual(len(yield_events), 1)
        self.assertEqual(yield_events[0]["details"]["reason"], "generation_mismatch")
        self.assertEqual(yield_events[0]["details"]["action_taken"], "stop_turns_and_exit")

    def test_run_tick_emits_distress_from_injection_file(self) -> None:
        now = utc_now()
        self.store.paths.distress_injection_file.write_text(
            json.dumps({"reason": "manual_distress_test"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        state = RuntimeState(life_state=LifeState.STABLE.value, last_heartbeat_at=now - timedelta(seconds=1), recovering_until=now - timedelta(seconds=1))
        result = self.runtime.run_tick(state, now=now)
        self.assertEqual(result.life_state, LifeState.CRITICAL)
        self.assertTrue(result.instance_valid)
        self.assertFalse(self.store.paths.distress_injection_file.exists())
        events = self.store.read_events()
        distress_events = [event for event in events if event["event_type"] == "distress"]
        self.assertEqual(len(distress_events), 1)
        self.assertEqual(distress_events[0]["details"]["reason"], "manual_distress_test")
        self.assertEqual(distress_events[0]["details"]["source"], "distress_injection_file")
        self.assertTrue(distress_events[0]["details"]["instance_valid"])

    def test_patrol_turn_reports_signal_summary_without_bypassing_guard(self) -> None:
        now = utc_now()
        state = RuntimeState(life_state=LifeState.STABLE.value, instance_valid=True, recovering_until=now - timedelta(seconds=1))
        self.store.write_runtime_state(state)
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))

        guarded = self.runtime.run_turn(state, next_heartbeat_at=now + timedelta(seconds=0.1), now=now)
        self.assertFalse(guarded.executed)
        self.assertEqual(guarded.details["reason"], "heartbeat_deadline_near")
        self.assertIn("runtime_gate_context", guarded.details)

        later = now + timedelta(seconds=1)
        executed = self.runtime.run_turn(state, next_heartbeat_at=later + timedelta(seconds=1), now=later)
        self.assertTrue(executed.executed)
        self.assertEqual(executed.details["work_kind"], "patrol")
        self.assertEqual(executed.details["signal_summary"]["signal_count"], 1)
        self.assertEqual(executed.details["signal_batch"]["summary"], executed.details["signal_summary"])
        self.assertEqual(executed.details["signal_batch"]["signals"][0]["class"], "status")
        self.assertEqual(executed.details["signal_summary"]["status_signal_count"], 1)
        self.assertEqual(executed.details["signal_summary"]["threat_signal_count"], 0)
        self.assertEqual(
            executed.details["signal_routing"],
            {
                "urgency": "normal",
                "dispatch_hint": "deliberation_only",
                "has_threat_signal": False,
                "deliberation_allowed": True,
                "compatibility_bridge_candidate": False,
                "reasons": ["status_signal_present"],
            },
        )
        self.assertEqual(executed.details["drive_summary"]["top_drive"], "curiosity")
        self.assertEqual(executed.details["runtime_gate_context"]["instance_valid"], True)
        self.assertEqual(executed.details["runtime_gate_context"]["turn_allowed"], True)
        self.assertEqual(executed.details["execution_lane"], "slow")
        self.assertIn("deliberation", executed.details)
        self.assertEqual(executed.details["deliberation"]["outcome"], "withhold")
        self.assertEqual(
            set(executed.details["deliberation"].keys()),
            {"outcome", "selected_action", "selected_candidate_id", "habit_narrowed", "habit_narrowed_from", "release_authorized"},
        )
        self.assertIsNone(executed.details["deliberation"]["selected_candidate_id"])
        self.assertFalse(executed.details["deliberation"]["habit_narrowed"])
        self.assertIsNone(executed.details["deliberation"]["habit_narrowed_from"])
        self.assertIn("curiosity", executed.details["drive_broadcast"]["drive_levels"])
        self.assertIn("working_memory_context", self.store.read_deliberation_audit()[0]["deliberation_input"])
        self.assertEqual(self.store.read_deliberation_audit()[0]["deliberation_input"]["working_memory_context"]["habit_skills"], [])
        self.assertEqual(
            self.store.read_deliberation_audit()[0]["deliberation_input"]["working_memory_context"]["advisory_source"],
            "local_rule_based",
        )
        self.assertEqual(self.store.read_learning_outcomes(), [])
        response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(response_events, [])

    def test_conservative_window_keeps_heartbeat_guard_and_critical_block(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="self_check"))
        self.runtime.activate_conservative_until_next_patrol()
        state = RuntimeState(life_state=LifeState.STABLE.value, instance_valid=True, recovering_until=now - timedelta(seconds=1))

        yielded = self.runtime.run_turn(state, next_heartbeat_at=now + timedelta(seconds=0.1), now=now)
        self.assertFalse(yielded.executed)
        self.assertTrue(yielded.yielded_to_heartbeat)
        self.assertEqual(yielded.details["reason"], "heartbeat_deadline_near")

        later = now + timedelta(seconds=1)
        state.life_state = LifeState.CRITICAL.value
        blocked = self.runtime.run_turn(state, next_heartbeat_at=later + timedelta(seconds=1), now=later)
        self.assertFalse(blocked.executed)
        self.assertFalse(blocked.yielded_to_heartbeat)
        self.assertEqual(blocked.details["runtime_gate_context"]["critical_blocked"], True)
        self.assertEqual(blocked.details["runtime_gate_context"]["turn_allowed"], False)
        self.assertEqual(blocked.details["reason"], "critical_life_state")
        self.assertTrue(self.runtime._conservative_until_next_patrol)


if __name__ == "__main__":
    unittest.main()
