from __future__ import annotations
import tempfile
import unittest
from datetime import timedelta
from eva.kernel import DriveStateTable, EventRecord, ExternalLifeConfig, InstanceGuard, LifecycleConfig, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.kernel.lifecycle import LifeState, LifecycleRuntime, WorkSlice
from eva.l3_deliberation.tool_edge import RECHECK_ACTION, REPAIR_ACTION


class PatrolTurnFlowTests(unittest.TestCase):
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
        self.assertEqual(result.details["signal_summary"]["signal_count"], 1)
        self.assertEqual(result.details["signal_batch"]["summary"], result.details["signal_summary"])
        self.assertEqual(len(result.details["signal_batch"]["signals"]), 1)
        self.assertEqual(result.details["signal_batch"]["signals"][0]["class"], "status")
        self.assertEqual(result.details["signal_summary"]["status_signal_count"], 1)
        self.assertEqual(result.details["signal_summary"]["threat_signal_count"], 0)
        self.assertFalse(result.details["signal_summary"]["has_threat_signal"])
        self.assertEqual(
            result.details["signal_routing"],
            {
                "urgency": "normal",
                "dispatch_hint": "deliberation_only",
                "has_threat_signal": False,
                "deliberation_allowed": True,
                "compatibility_bridge_candidate": False,
                "reasons": ["status_signal_present"],
            },
        )
        self.assertEqual(result.details["drive_summary"]["top_drive"], "curiosity")
        self.assertEqual(result.details["runtime_gate_context"]["instance_valid"], True)
        self.assertEqual(result.details["runtime_gate_context"]["turn_allowed"], True)
        self.assertEqual(result.details["runtime_gate_context"]["critical_blocked"], False)
        self.assertEqual(result.details["runtime_gate_context"]["conservative_mode"], False)
        self.assertIn("curiosity", result.details["drive_summary"]["drive_levels"])
        self.assertEqual(result.details["drive_broadcast"]["top_drive"], "curiosity")
        self.assertIn("curiosity", result.details["drive_broadcast"]["drive_levels"])
        self.assertIn("deliberation", result.details)
        self.assertEqual(result.details["deliberation"]["outcome"], "withhold")
        self.assertEqual(
            set(result.details["deliberation"].keys()),
            {"outcome", "selected_action", "selected_candidate_id", "habit_narrowed", "habit_narrowed_from", "release_authorized"},
        )
        self.assertIsNone(result.details["deliberation"]["selected_candidate_id"])
        self.assertFalse(result.details["deliberation"]["habit_narrowed"])
        self.assertIsNone(result.details["deliberation"]["habit_narrowed_from"])
        self.assertFalse(self.store.paths.deliberation_audit_file.exists() == False)
        self.assertFalse(self.store.paths.cognitive_memory_stub_file.exists())
        self.assertNotIn("response", result.details)

        snapshot = self.store.read_external_life_snapshot()
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.source_patrol, "deep")
        self.assertEqual(snapshot.overall_status, "healthy")
        self.assertEqual(snapshot.primary_gap["type"], "none")
        self.assertIn("rate_context", snapshot.dimensions["host_continuity"].evidence)
        self.assertFalse(snapshot.dimensions["host_continuity"].evidence["rate_context"]["available"])

        pressure_table = self.store.read_active_pressures()
        self.assertEqual(len(pressure_table.pressures), 0)
        drive_state = self.store.read_drive_state()
        self.assertIsNotNone(drive_state)
        assert drive_state is not None
        self.assertEqual(len(drive_state.drives), 4)

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
        self.assertEqual(first.details["signal_summary"]["signal_count"], 2)
        self.assertEqual(first.details["signal_batch"]["summary"], first.details["signal_summary"])
        self.assertEqual([signal["class"] for signal in first.details["signal_batch"]["signals"]], ["status", "threat"])
        self.assertEqual(first.details["signal_summary"]["status_signal_count"], 1)
        self.assertEqual(first.details["signal_summary"]["threat_signal_count"], 1)
        self.assertTrue(first.details["signal_summary"]["has_threat_signal"])
        self.assertEqual(
            first.details["signal_routing"],
            {
                "urgency": "high",
                "dispatch_hint": "protective_lane",
                "has_threat_signal": True,
                "deliberation_allowed": True,
                "compatibility_bridge_candidate": True,
                "reasons": ["threat_signal_present"],
            },
        )
        self.assertEqual(first.details["drive_summary"]["top_drive"], "integrity")
        self.assertIn("deliberation", first.details)
        self.assertEqual(first.details["deliberation"]["outcome"], "compatibility_release")
        self.assertEqual(first.details["deliberation"]["selected_candidate_id"], "candidate-compatibility-stabilize-first")
        self.assertFalse(first.details["deliberation"]["habit_narrowed"])
        self.assertIsNone(first.details["deliberation"]["habit_narrowed_from"])

        pressure_table = self.store.read_active_pressures()
        self.assertEqual(len(pressure_table.pressures), 1)
        self.assertEqual(pressure_table.pressures[0].type, "integrity")
        self.assertEqual(len(first.details["signal_summary"]), 5)
        self.assertIn("response", first.details)
        self.assertEqual(
            first.details["response"],
            {
                "pressure_id": pressure_table.pressures[0].pressure_id,
                "pressure_type": "integrity",
                "selected_action": RECHECK_ACTION,
                "habit_narrowed": False,
                "habit_narrowed_from": None,
            },
        )
        response_history = self.store.read_response_history()
        self.assertEqual(len(response_history), 1)
        self.assertEqual(response_history[0]["selected_action"], RECHECK_ACTION)
        self.assertEqual(response_history[0]["response_mode"], "pressure_led_compatibility")
        self.assertEqual(
            response_history[0]["release_context"],
            {
                "bridge_target": "pressure_led_compatibility",
                "response_mode": "pressure_led_compatibility",
                "candidate_profile": "stabilize_first",
                "bridge_policy": {
                    "policy_name": "stabilize_first_bias",
                    "selection": {
                        "preferred_action": "shrink_to_conservative_mode",
                        "fallback_action": "recheck_runtime_integrity",
                        "default_path": "pressure_default",
                    },
                    "applicability": {
                        "pressure_reasons": ["recent_yield_detected"],
                        "life_states": ["STABLE"],
                    },
                    "execution": {
                        "allow_repair_side_effects": True,
                    },
                },
            },
        )
        response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(len(response_events), 1)
        self.assertEqual(response_events[0]["turn_id"], first.turn_id)
        self.assertEqual(
            response_events[0]["details"],
            {
                "work_slice": "deep",
                "work_kind": "patrol",
                "pressure_id": pressure_table.pressures[0].pressure_id,
                "pressure_type": "integrity",
                "selected_action": RECHECK_ACTION,
                "selected_candidate_id": "candidate-compatibility-stabilize-first",
            },
        )

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
        self.assertEqual(second.details["signal_summary"]["signal_count"], 1)
        self.assertEqual(second.details["signal_summary"]["threat_signal_count"], 0)
        self.assertFalse(second.details["signal_summary"]["has_threat_signal"])
        self.assertEqual(second.details["drive_summary"]["top_drive"], "integrity")
        self.assertNotIn("response", second.details)
        snapshot_after_second = self.store.read_external_life_snapshot()
        self.assertIsNotNone(snapshot_after_second)
        assert snapshot_after_second is not None
        self.assertTrue(snapshot_after_second.dimensions["runtime_integrity"].evidence["rate_context"]["available"])
        self.assertEqual(snapshot_after_second.dimensions["runtime_integrity"].status, "healthy")

        later_response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(len(later_response_events), 1)

        survival_events = [entry["event_type"] for entry in self.store.read_survival_log()]
        self.assertIn("pressure_opened", survival_events)
        self.assertIn("pressure_resolved", survival_events)
        self.assertIn("survival_snapshot", survival_events)

    def test_run_turn_exposes_b0_minimal_input_contract(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))

        result = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=now + timedelta(seconds=1),
            now=now,
        )

        self.assertTrue(result.executed)
        self.assertEqual(set(result.details["signal_batch"].keys()), {"signals", "summary"})
        self.assertIn("signal_routing", result.details)
        self.assertEqual(
            set(result.details["signal_routing"].keys()),
            {"urgency", "dispatch_hint", "has_threat_signal", "deliberation_allowed", "compatibility_bridge_candidate", "reasons"},
        )
        self.assertIn("drive_broadcast", result.details)
        self.assertIn("drive_trends", result.details["drive_broadcast"])
        self.assertIn("deliberation", result.details)
        self.assertEqual(result.details["deliberation"]["outcome"], "withhold")
        self.assertEqual(
            set(result.details["deliberation"].keys()),
            {"outcome", "selected_action", "selected_candidate_id", "habit_narrowed", "habit_narrowed_from", "release_authorized"},
        )
        self.assertIsNone(result.details["deliberation"]["selected_candidate_id"])
        self.assertFalse(result.details["deliberation"]["habit_narrowed"])
        self.assertIsNone(result.details["deliberation"]["habit_narrowed_from"])
        self.assertEqual(
            set(result.details["runtime_gate_context"].keys()),
            {"instance_valid", "turn_allowed", "critical_blocked", "conservative_mode", "life_state", "seconds_to_heartbeat"},
        )
        self.assertEqual(result.details["runtime_gate_context"]["turn_allowed"], True)

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
        self.assertFalse(first.details["response"]["habit_narrowed"])
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


    def test_high_risk_integrity_reason_releases_escalate_first_response(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.store.paths.runtime_state_file.unlink(missing_ok=True)
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))

        result = self.runtime.run_turn(
            self.state,
            next_heartbeat_at=now + timedelta(seconds=1),
            now=now,
        )

        self.assertTrue(result.executed)
        self.assertEqual(result.details["deliberation"]["outcome"], "compatibility_release")
        self.assertEqual(result.details["deliberation"]["selected_candidate_id"], "candidate-compatibility-escalate-first")
        self.assertEqual(result.details["response"]["selected_action"], "escalate_integrity_risk")
        response_history = self.store.read_response_history()
        self.assertEqual(response_history[0]["release_context"]["candidate_profile"], "escalate_first")
        self.assertEqual(response_history[0]["selected_action"], "escalate_integrity_risk")

