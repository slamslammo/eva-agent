from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta

from eva.kernel import (
    ActiveInstanceRecord,
    ActivePressure,
    ActivePressureTable,
    DimensionSnapshot,
    DriveState,
    DriveStateTable,
    EventRecord,
    ExternalLifeSnapshot,
    RuntimeState,
    StateStore,
    build_runtime_paths,
    utc_now,
)


class StateStoreTests(unittest.TestCase):
    def test_build_runtime_paths_includes_step1_and_step2_files(self) -> None:
        paths = build_runtime_paths("/tmp/eva-state-test")
        self.assertTrue(str(paths.external_life_snapshot_file).endswith("external_life_snapshot.json"))
        self.assertTrue(str(paths.drive_state_file).endswith("drive_state.json"))
        self.assertTrue(str(paths.active_pressures_file).endswith("active_pressures.json"))
        self.assertTrue(str(paths.survival_log_file).endswith("survival_log.jsonl"))
        self.assertTrue(str(paths.response_history_file).endswith("response_history.jsonl"))
        self.assertTrue(str(paths.deliberation_audit_file).endswith("deliberation_audit.jsonl"))
        self.assertTrue(str(paths.cognitive_memory_stub_file).endswith("cognitive_memory_stub.jsonl"))
        self.assertTrue(str(paths.learning_outcomes_file).endswith("learning_outcomes.jsonl"))
        self.assertTrue(str(paths.habit_bias_file).endswith("habit_bias.jsonl"))

    def test_write_and_read_active_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            record = ActiveInstanceRecord(
                instance_id="eva-test-001",
                generation=1,
                lease_expires_at=now + timedelta(seconds=5),
                lock_holder=True,
                updated_at=now,
            )
            store.write_active_instance(record)
            loaded = store.read_active_instance()
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.instance_id, record.instance_id)
            self.assertEqual(loaded.generation, record.generation)
            self.assertTrue(loaded.lock_holder)

    def test_write_and_read_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            state = RuntimeState(
                life_state="STABLE",
                last_tick_id="tick-0001",
                last_turn_id="turn-0001",
                heartbeat_ok=True,
                tick_ok=True,
                state_io_ok=True,
                instance_valid=True,
                updated_at=now,
            )
            store.write_runtime_state(state)
            loaded = store.read_runtime_state()
            self.assertEqual(loaded.life_state, "STABLE")
            self.assertEqual(loaded.last_tick_id, "tick-0001")
            self.assertTrue(loaded.instance_valid)

    def test_write_and_read_external_life_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            snapshot = ExternalLifeSnapshot(
                captured_at=now,
                source_patrol="shallow",
                dimensions={
                    "host_continuity": DimensionSnapshot(
                        status="healthy",
                        evidence={"process_running": True},
                    )
                },
                overall_status="healthy",
                primary_gap={"type": "none", "reason": "none"},
                trend="stable",
                updated_at=now,
            )
            store.write_external_life_snapshot(snapshot)
            loaded = store.read_external_life_snapshot()
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.source_patrol, "shallow")
            self.assertEqual(loaded.overall_status, "healthy")
            self.assertIn("host_continuity", loaded.dimensions)

    def test_write_and_read_drive_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            table = DriveStateTable(
                captured_at=now,
                drives=[
                    DriveState(
                        drive_type="survival",
                        level=0.4,
                        delta=0.1,
                        trend="worsening",
                        contributors=["resource_state.disk_space_declining"],
                        updated_at=now,
                    )
                ],
                updated_at=now,
            )
            store.write_drive_state(table)
            loaded = store.read_drive_state()
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(len(loaded.drives), 1)
            self.assertEqual(loaded.drives[0].drive_type, "survival")
            self.assertAlmostEqual(loaded.drives[0].level, 0.4)
            self.assertEqual(loaded.drives[0].contributors, ["resource_state.disk_space_declining"])

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            table = ActivePressureTable(
                captured_at=now,
                pressures=[
                    ActivePressure(
                        pressure_id="pressure-resource_state-disk_space_declining",
                        type="resource_state",
                        severity="degraded",
                        evidence={"disk_free_bytes": 1024},
                        first_seen_at=now,
                        last_seen_at=now,
                        trend="worsening",
                        active=True,
                    )
                ],
                updated_at=now,
            )
            store.write_active_pressures(table)
            loaded = store.read_active_pressures()
            self.assertEqual(len(loaded.pressures), 1)
            self.assertEqual(loaded.pressures[0].pressure_id, "pressure-resource_state-disk_space_declining")
            self.assertEqual(loaded.pressures[0].type, "resource_state")

    def test_append_survival_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            store.append_survival_log(
                {
                    "event_type": "survival_snapshot",
                    "timestamp": now.isoformat(),
                    "overall_status": "healthy",
                }
            )
            store.append_survival_log(
                {
                    "event_type": "pressure_opened",
                    "timestamp": now.isoformat(),
                    "pressure_id": "pressure-continuity-restart_loop",
                }
            )
            entries = store.read_survival_log()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["event_type"], "survival_snapshot")
            self.assertEqual(entries[1]["event_type"], "pressure_opened")

    def test_append_event_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            store.append_event(EventRecord(event_type="startup", timestamp=now, details={"step": 1}))
            store.append_event(EventRecord(event_type="shutdown", timestamp=now, details={"step": 2}))
            events = store.read_events()
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["event_type"], "startup")
            self.assertEqual(events[1]["event_type"], "shutdown")

    def test_append_and_read_response_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            now = utc_now()
            store.append_response_history(
                {
                    "response_id": "resp-001",
                    "recorded_at": now.isoformat(),
                    "pressure_id": "pressure-integrity-instance_invalid",
                    "selected_action": "recheck_runtime_integrity",
                    "execution_status": "completed",
                }
            )
            store.append_response_history(
                {
                    "response_id": "resp-002",
                    "recorded_at": now.isoformat(),
                    "pressure_id": "pressure-integrity-runtime_not_writable",
                    "selected_action": "escalate_integrity_risk",
                    "execution_status": "escalated",
                }
            )
            entries = store.read_response_history()
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["response_id"], "resp-001")
            self.assertEqual(entries[1]["selected_action"], "escalate_integrity_risk")

    def test_append_and_read_deliberation_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.append_deliberation_audit(
                {
                    "recorded_at": utc_now().isoformat(),
                    "deliberation_input": {"signal_batch": {}, "drive_broadcast": {}, "runtime_gate_context": {}},
                    "candidates": [{"candidate_id": "candidate-1"}],
                    "assessments": [{"candidate_id": "candidate-1", "disposition": "withhold"}],
                    "release_decision": {"outcome": "withhold"},
                }
            )
            entries = store.read_deliberation_audit()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["release_decision"]["outcome"], "withhold")

    def test_append_and_read_cognitive_memory_stub(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.append_cognitive_memory_stub(
                {
                    "recorded_at": utc_now().isoformat(),
                    "source": "l3_deliberation",
                    "salience": "focused",
                    "memory_type": "release_trace",
                    "write_reason": "release_outcome=compatibility_release",
                    "linked_audit_recorded_at": utc_now().isoformat(),
                    "content": {"top_drive": "curiosity", "release_outcome": "compatibility_release"},
                }
            )
            entries = store.read_cognitive_memory_stub()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["source"], "l3_deliberation")
            self.assertEqual(entries[0]["content"]["top_drive"], "curiosity")
            self.assertEqual(entries[0]["memory_type"], "release_trace")
            self.assertEqual(entries[0]["write_reason"], "release_outcome=compatibility_release")

    def test_append_and_read_learning_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.append_learning_outcome(
                {
                    "recorded_at": utc_now().isoformat(),
                    "source": "l3_learning",
                    "linked_audit_recorded_at": utc_now().isoformat(),
                    "expected_outcome": "stabilize_or_relieve_pressure",
                    "observed_outcome": "relieved",
                    "outcome_delta": 1.0,
                    "rpe_like_score": 1.0,
                    "evaluation_label": "positive",
                    "confidence": 0.9,
                    "content": {
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "habit_skill_match": True,
                        "habit_narrowed": True,
                    },
                }
            )
            entries = store.read_learning_outcomes()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["evaluation_label"], "positive")
            self.assertEqual(entries[0]["content"]["situation_key"], "integrity|STABLE|recent_yield_detected")
            self.assertTrue(entries[0]["content"]["habit_skill_match"])
            self.assertTrue(entries[0]["content"]["habit_narrowed"])

    def test_append_and_read_habit_bias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.append_habit_bias(
                {
                    "recorded_at": utc_now().isoformat(),
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "stabilize_first",
                    "preferred_action": "shrink_to_conservative_mode",
                    "support_count": 2,
                    "failure_count": 0,
                    "last_outcome_delta": 1.0,
                    "bias_strength": 1.0,
                }
            )
            entries = store.read_habit_bias()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["candidate_profile"], "stabilize_first")
            self.assertEqual(entries[0]["bias_strength"], 1.0)

    def test_runtime_state_overwrite_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            first = RuntimeState(life_state="RECOVERING")
            second = RuntimeState(life_state="STABLE", heartbeat_ok=True, instance_valid=True)
            store.write_runtime_state(first)
            store.write_runtime_state(second)
            loaded = store.read_runtime_state()
            self.assertEqual(loaded.life_state, "STABLE")
            self.assertTrue(loaded.heartbeat_ok)

    def test_runtime_state_remains_step0_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            state = RuntimeState(life_state="STABLE", heartbeat_ok=True, instance_valid=True)
            store.write_runtime_state(state)
            payload = store.paths.runtime_state_file.read_text(encoding="utf-8")
            self.assertNotIn("overall_status", payload)
            self.assertNotIn("pressures", payload)
            self.assertNotIn("drive", payload)
            self.assertNotIn("release_decision", payload)
            self.assertNotIn("memory", payload)


if __name__ == "__main__":
    unittest.main()
