from __future__ import annotations
import json
import tempfile
import unittest
from datetime import timedelta
from eva.kernel import EventRecord, ActiveInstanceRecord, InstanceGuard, LifecycleConfig, RuntimeState, StateStore, build_runtime_paths, utc_now
from eva.kernel.lifecycle import LifeState, LifecycleRuntime, WorkSlice
from eva.scenario_bundle import activate_runtime_scenario
from scenarios.linux_runtime import LINUX_RUNTIME_SCENARIO_BUNDLE


class LifecyclePatrolLearningTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_runtime_scenario(LINUX_RUNTIME_SCENARIO_BUNDLE)
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

    def test_patrol_turn_writes_learning_outcome_after_compatibility_response(self) -> None:
        now = utc_now()
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))
        state = RuntimeState(
            life_state=LifeState.STABLE.value,
            instance_valid=False,
            recovering_until=now - timedelta(seconds=1),
        )
        self.store.write_runtime_state(state)

        later = now + timedelta(seconds=1)
        executed = self.runtime.run_turn(state, next_heartbeat_at=later + timedelta(seconds=1), now=later)

        self.assertIn("response", executed.details)
        self.assertEqual(executed.details["execution_lane"], "fast")
        self.assertNotIn("deliberation", executed.details)
        self.assertIn("reflex", executed.details)
        self.assertEqual(executed.details["reflex"]["selected_candidate_id"], "candidate-compatibility-observe-first")
        self.assertEqual(self.store.read_deliberation_audit(), [])
        learning_outcomes = self.store.read_learning_outcomes()
        self.assertEqual(len(learning_outcomes), 1)
        self.assertIn(learning_outcomes[0]["evaluation_label"], {"positive", "negative", "neutral", "uncertain"})
        self.assertIn("situation_key", learning_outcomes[0]["content"])
        self.assertFalse(learning_outcomes[0]["content"]["habit_narrowed"])
        self.assertEqual(learning_outcomes[0]["outcome_vector"]["viability_delta"], {"level_1": learning_outcomes[0]["outcome_delta"]})
        habit_bias = self.store.read_habit_bias()
        self.assertEqual(len(habit_bias), 1)
        self.assertIn("evidence_count", habit_bias[0])
        self.assertIn("stability_score", habit_bias[0])
        self.assertIn("confidence", habit_bias[0])

    def test_patrol_turn_does_not_narrow_when_skill_has_degraded_from_recent_negative_outcomes(self) -> None:
        now = utc_now()
        self.store.append_habit_bias(
            {
                "recorded_at": now.isoformat(),
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "candidate_profile": "observe_first",
                "preferred_action": "recheck_runtime_integrity",
                "evidence_count": 5,
                "habit_skill_hit_count": 4,
                "habit_narrowed_count": 2,
                "stability_score": 0.8,
                "confidence": 0.85,
                "bias_strength": 0.4,
                "support_count": 3,
                "failure_count": 2,
                "recent_negative_count": 2,
                "last_outcome_delta": -0.5,
            }
        )
        self.store.append_event(
            EventRecord(
                event_type="yield",
                timestamp=now - timedelta(seconds=1),
                life_state=LifeState.STABLE.value,
                details={"reason": "recent_yield_detected"},
            )
        )
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))
        state = RuntimeState(
            life_state=LifeState.STABLE.value,
            instance_valid=True,
            heartbeat_ok=True,
            last_heartbeat_at=now - timedelta(seconds=1),
            recovering_until=now - timedelta(seconds=1),
        )
        self.store.write_runtime_state(state)

        later = now + timedelta(seconds=1)
        executed = self.runtime.run_turn(state, next_heartbeat_at=later + timedelta(seconds=1), now=later)

        self.assertTrue(executed.executed)
        self.assertFalse(executed.details["deliberation"]["habit_narrowed"])
        self.assertIsNone(executed.details["deliberation"]["habit_narrowed_from"])
        deliberation_audit = self.store.read_deliberation_audit()[0]
        self.assertEqual(len(deliberation_audit["candidates"]), 2)
        self.assertEqual(deliberation_audit["candidates"][0]["parameter_domain"]["habitual_trace"], "habitual_suppression")
        self.assertIn("recent_negative_feedback", deliberation_audit["candidates"][0]["parameter_domain"]["habitual_trace_reasons"])
        self.assertFalse(deliberation_audit["deliberation_input"]["working_memory_context"]["habit_skills"][0]["crystallized"])
        self.assertFalse(deliberation_audit["deliberation_input"]["working_memory_context"]["bias_summaries"][0]["habit_eligible"])
        self.assertEqual(deliberation_audit["deliberation_input"]["working_memory_context"]["recent_relevant_outcomes"], [])
        self.assertIn("recent_negative_streak", deliberation_audit["deliberation_input"]["working_memory_context"]["habit_skills"][0]["crystallization_reasons"])
        self.assertIn("recent_negative_streak", deliberation_audit["deliberation_input"]["working_memory_context"]["bias_summaries"][0]["habit_eligibility_reasons"])
        self.assertIn("last_outcome_negative", deliberation_audit["deliberation_input"]["working_memory_context"]["habit_skills"][0]["crystallization_reasons"])
        self.assertIn("last_outcome_negative", deliberation_audit["deliberation_input"]["working_memory_context"]["bias_summaries"][0]["habit_eligibility_reasons"])
        self.assertNotIn("habit_candidate_narrowing", deliberation_audit["assessments"][0]["reasons"])

    def test_patrol_turn_surfaces_recent_habitual_trace_from_prior_learning_outcome(self) -> None:
        now = utc_now()
        self.store.append_learning_outcome(
            {
                "recorded_at": now.isoformat(),
                "source": "l3_learning",
                "linked_audit_recorded_at": now.isoformat(),
                "selected_action": "recheck_runtime_integrity",
                "candidate_profile": "observe_first",
                "pressure_reason": "recent_yield_detected",
                "expected_outcome": "improve_information_under_pressure",
                "observed_outcome": "failed",
                "outcome_delta": -1.0,
                "rpe_like_score": -1.0,
                "evaluation_label": "negative",
                "confidence": 0.95,
                "content": {
                    "top_drive": "integrity",
                    "life_state": "STABLE",
                    "pressure_reason": "recent_yield_detected",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "habit_skill_match": True,
                    "habit_narrowed": True,
                },
            }
        )
        self.store.append_event(
            EventRecord(
                event_type="yield",
                timestamp=now - timedelta(seconds=1),
                life_state=LifeState.STABLE.value,
                details={"reason": "recent_yield_detected"},
            )
        )
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))
        state = RuntimeState(
            life_state=LifeState.STABLE.value,
            instance_valid=True,
            heartbeat_ok=True,
            last_heartbeat_at=now - timedelta(seconds=1),
            recovering_until=now - timedelta(seconds=1),
        )
        self.store.write_runtime_state(state)

        later = now + timedelta(seconds=1)
        executed = self.runtime.run_turn(state, next_heartbeat_at=later + timedelta(seconds=1), now=later)

        self.assertTrue(executed.executed)
        deliberation_audit = self.store.read_deliberation_audit()[0]
        self.assertEqual(
            deliberation_audit["deliberation_input"]["working_memory_context"]["recent_relevant_outcomes"][0]["habitual_trace"],
            "habitual_suppression",
        )
        self.assertIn(
            "recent_negative_feedback",
            deliberation_audit["deliberation_input"]["working_memory_context"]["recent_relevant_outcomes"][0]["habitual_trace_reasons"],
        )
        self.assertIn(
            "habit_narrowed",
            deliberation_audit["deliberation_input"]["working_memory_context"]["recent_relevant_outcomes"][0]["habitual_trace_reasons"],
        )

    def test_patrol_turn_persists_habit_narrowing_trace_when_single_strong_skill_matches(self) -> None:
        now = utc_now()
        self.store.append_habit_bias(
            {
                "recorded_at": now.isoformat(),
                "situation_key": "integrity|STABLE|recent_yield_detected",
                "candidate_profile": "observe_first",
                "preferred_action": "recheck_runtime_integrity",
                "evidence_count": 4,
                "habit_skill_hit_count": 3,
                "habit_narrowed_count": 1,
                "stability_score": 0.8,
                "confidence": 0.85,
                "bias_strength": 0.75,
                "support_count": 4,
                "failure_count": 0,
                "recent_negative_count": 0,
                "last_outcome_delta": 1.0,
            }
        )
        self.store.append_event(
            EventRecord(
                event_type="yield",
                timestamp=now - timedelta(seconds=1),
                life_state=LifeState.STABLE.value,
                details={"reason": "recent_yield_detected"},
            )
        )
        self.runtime.pending_work.clear()
        self.runtime.pending_work.append(WorkSlice(name="deep", kind="patrol", due_at=now - timedelta(seconds=1)))
        state = RuntimeState(
            life_state=LifeState.STABLE.value,
            instance_valid=True,
            heartbeat_ok=True,
            last_heartbeat_at=now - timedelta(seconds=1),
            recovering_until=now - timedelta(seconds=1),
        )
        self.store.write_runtime_state(state)

        later = now + timedelta(seconds=1)
        executed = self.runtime.run_turn(state, next_heartbeat_at=later + timedelta(seconds=1), now=later)

        self.assertTrue(executed.executed)
        self.assertIn("response", executed.details)
        self.assertTrue(executed.details["deliberation"]["habit_narrowed"])
        self.assertEqual(executed.details["deliberation"]["selected_candidate_id"], "candidate-compatibility-observe-first")
        self.assertEqual(executed.details["deliberation"]["habit_narrowed_from"], 2)
        self.assertEqual(executed.details["response"]["selected_action"], "recheck_runtime_integrity")
        self.assertTrue(executed.details["response"]["habit_narrowed"])
        self.assertEqual(executed.details["response"]["habit_narrowed_from"], 2)
        deliberation_audit = self.store.read_deliberation_audit()[0]
        self.assertEqual(deliberation_audit["release_decision"]["selected_candidate_id"], "candidate-compatibility-observe-first")
        self.assertEqual(deliberation_audit["candidates"][0]["parameter_domain"]["habitual_trace"], "habitual_neutral")
        self.assertTrue(deliberation_audit["release_decision"]["learning_context"]["habit_narrowed"])
        self.assertEqual(deliberation_audit["deliberation_input"]["working_memory_context"]["habit_skills"][0]["candidate_profile"], "observe_first")
        self.assertTrue(deliberation_audit["deliberation_input"]["working_memory_context"]["habit_skills"][0]["crystallized"])
        self.assertEqual(len(deliberation_audit["candidates"]), 1)
        self.assertTrue(deliberation_audit["candidates"][0]["parameter_domain"]["habit_narrowed"])
        self.assertIn("habit_candidate_narrowing", deliberation_audit["candidates"][0]["justification"])
        self.assertIn("habit_candidate_narrowing", deliberation_audit["assessments"][0]["reasons"])
        learning_outcomes = self.store.read_learning_outcomes()
        self.assertEqual(len(learning_outcomes), 1)
        self.assertEqual(deliberation_audit["deliberation_input"]["working_memory_context"]["recent_relevant_outcomes"], [])
        self.assertTrue(learning_outcomes[0]["content"]["habit_narrowed"])
        self.assertEqual(learning_outcomes[0]["candidate_profile"], "observe_first")
        self.assertEqual(learning_outcomes[0]["selected_action"], "recheck_runtime_integrity")
        self.assertEqual(learning_outcomes[0]["content"]["situation_key"], "integrity|STABLE|recent_yield_detected")
        self.assertEqual(learning_outcomes[0]["outcome_vector"]["viability_delta"], {"level_1": learning_outcomes[0]["outcome_delta"]})
        response_events = [event for event in self.store.read_events() if event["event_type"] == "response_selected"]
        self.assertEqual(len(response_events), 1)
        self.assertEqual(response_events[0]["details"]["selected_candidate_id"], "candidate-compatibility-observe-first")
        self.assertTrue(response_events[0]["details"]["habit_narrowed"])
        self.assertEqual(response_events[0]["details"]["habit_narrowed_from"], 2)


if __name__ == "__main__":
    unittest.main()
