from __future__ import annotations
import tempfile
import unittest
from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation import build_deliberation_input
from eva.l3_deliberation import build_learning_outcome_record, evaluate_response_outcome
from eva.l3_deliberation.memory import derive_habit_skills
from eva.l3_deliberation.reasoning import build_working_memory_context, build_working_memory_context_from_store, summarize_habit_bias
from eva.l3_deliberation.memory import (
    ClientBackedWorkingMemoryAdapter,
    HeuristicWorkingMemoryAdapter,
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
    WorkingMemoryAdapterResponse,
)
from eva.l3_deliberation.memory import (
    HeuristicWorkingMemoryModelClient,
    MODEL_CLIENT_MODE_HEURISTIC,
    NullWorkingMemoryModelClient,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
    WorkingMemoryModelClientResponse,
    build_builtin_working_memory_model_client,
)


class CapturingWorkingMemoryAdapter:
    def __init__(self, response: WorkingMemoryAdapterResponse | None) -> None:
        self.response = response
        self.called = False
        self.request: WorkingMemoryAdapterRequest | None = None

    def build_advisory_context(
        self,
        request: WorkingMemoryAdapterRequest,
    ) -> WorkingMemoryAdapterResponse | None:
        self.called = True
        self.request = request
        return self.response


class WorkingMemoryReasoningTests(unittest.TestCase):
    def test_build_working_memory_context_returns_empty_safe_defaults(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
        )

        self.assertEqual(context.situation_key, "curiosity|STABLE|none")
        self.assertEqual(context.bias_summaries, [])
        self.assertEqual(context.habit_skills, [])
        self.assertEqual(context.recent_relevant_outcomes, [])
        self.assertEqual(context.confidence, 0.0)
        self.assertEqual(context.advisory_context, {})

    def test_build_working_memory_context_from_store_uses_local_backend_by_default(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(store, deliberation_input)

        self.assertEqual(context.source_backend, "local_rule_based")
        self.assertEqual(context.advisory_context, {})
        self.assertEqual(context.situation_key, "curiosity|STABLE|none")

    def test_build_working_memory_context_from_store_can_attach_llm_advisory_context(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        adapter = CapturingWorkingMemoryAdapter(
            WorkingMemoryAdapterResponse(
                candidate_suggestions=("observe_first",),
                prediction_hints=("likely_information_gain",),
                reasoning_trace=("integrity_conflict_detected",),
                confidence=0.61,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                backend="llm_assisted",
                llm_adapter=adapter,
            )

        self.assertEqual(context.source_backend, "llm_assisted")
        self.assertEqual(context.situation_key, "integrity|STABLE|none")
        self.assertGreaterEqual(context.confidence, 0.61)
        self.assertEqual(
            context.advisory_context,
            {
                "candidate_suggestions": ["observe_first"],
                "prediction_hints": ["likely_information_gain"],
                "reasoning_trace": ["integrity_conflict_detected"],
                "confidence": 0.61,
            },
        )
        self.assertTrue(adapter.called)
        self.assertIsNotNone(adapter.request)
        assert adapter.request is not None
        self.assertEqual(adapter.request.situation_key, "integrity|STABLE|none")
        self.assertEqual(adapter.request.drive_broadcast, deliberation_input.drive_broadcast)
        self.assertEqual(adapter.request.runtime_gate_context, deliberation_input.runtime_gate_context)
        self.assertIsInstance(adapter.request, WorkingMemoryAdapterRequest)
        self.assertIsInstance(adapter.request.to_dict(), dict)
        self.assertEqual(adapter.request.to_dict()["local_confidence"], 0.0)
        self.assertIn("bias_summaries", adapter.request.to_dict())
        self.assertIn("habit_skills", adapter.request.to_dict())
        self.assertIn("recent_relevant_outcomes", adapter.request.to_dict())

    def test_auto_backend_prefers_local_when_crystallized_habit_is_confident(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        adapter = CapturingWorkingMemoryAdapter(
            WorkingMemoryAdapterResponse(
                candidate_suggestions=("observe_first",),
                confidence=0.8,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            store.append_habit_bias(
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|none",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 4,
                    "habit_skill_hit_count": 3,
                    "habit_narrowed_count": 1,
                    "stability_score": 0.8,
                    "confidence": 0.85,
                    "bias_strength": 0.75,
                }
            )
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                backend="auto",
                llm_adapter=adapter,
            )

        self.assertEqual(context.source_backend, "local_rule_based")
        self.assertEqual(context.advisory_context, {})
        self.assertFalse(adapter.called)

    def test_auto_backend_uses_llm_when_local_context_is_weak(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        adapter = CapturingWorkingMemoryAdapter(
            WorkingMemoryAdapterResponse(
                candidate_suggestions=("observe_first",),
                prediction_hints=("explore_low_pressure_state",),
                reasoning_trace=("local_signal_insufficient",),
                confidence=0.66,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                backend="auto",
                llm_adapter=adapter,
            )

        self.assertEqual(context.source_backend, "llm_assisted")
        self.assertTrue(adapter.called)
        self.assertEqual(context.advisory_context["candidate_suggestions"], ["observe_first"])
        self.assertEqual(context.advisory_context["prediction_hints"], ["explore_low_pressure_state"])
        self.assertEqual(context.advisory_context["reasoning_trace"], ["local_signal_insufficient"])
        self.assertEqual(context.advisory_context["confidence"], 0.66)

    def test_auto_backend_without_adapter_falls_back_to_local(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(store, deliberation_input, backend="auto")

        self.assertEqual(context.source_backend, "local_rule_based")
        self.assertEqual(context.advisory_context, {})

    def test_build_working_memory_context_from_store_requires_adapter_for_llm_backend(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            with self.assertRaisesRegex(ValueError, "llm_adapter is required"):
                build_working_memory_context_from_store(store, deliberation_input, backend="llm_assisted")

    def test_llm_backend_accepts_null_working_memory_adapter(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}],
                "summary": {
                    "signal_count": 1,
                    "status_signal_count": 1,
                    "threat_signal_count": 0,
                    "background_signal_count": 0,
                    "has_threat_signal": False,
                },
            },
            drive_broadcast={
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                backend="llm_assisted",
                llm_adapter=NullWorkingMemoryAdapter(),
            )

        self.assertEqual(context.source_backend, "llm_assisted")
        self.assertEqual(context.advisory_context, {})

    def test_summarize_habit_bias_prefers_positive_profile(self) -> None:
        summaries = summarize_habit_bias(
            [
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": 1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "candidate_profile": "stabilize_first",
                    "selected_action": "shrink_to_conservative_mode",
                    "outcome_delta": -1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
            ],
            situation_key="integrity|STABLE|recent_yield_detected",
        )

        self.assertEqual(summaries[0].candidate_profile, "observe_first")
        self.assertGreater(summaries[0].bias_strength, 0.0)
        self.assertGreaterEqual(summaries[0].evidence_count, 1)
        self.assertGreaterEqual(summaries[0].confidence, 0.0)
        self.assertEqual(summaries[1].candidate_profile, "stabilize_first")
        self.assertLess(summaries[1].bias_strength, 0.0)

    def test_build_working_memory_context_uses_latest_append_only_habit_bias_entry(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "situation_key": "integrity|STABLE|none",
                    "candidate_profile": "observe_first",
                    "bias_strength": 0.8,
                    "support_count": 1,
                    "failure_count": 0,
                    "evidence_count": 1,
                    "recent_negative_count": 0,
                    "stability_score": 0.8,
                    "confidence": 0.5,
                    "last_outcome_delta": 1.0,
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "situation_key": "integrity|STABLE|none",
                    "candidate_profile": "observe_first",
                    "bias_strength": -1.0,
                    "support_count": 1,
                    "failure_count": 1,
                    "evidence_count": 2,
                    "recent_negative_count": 1,
                    "stability_score": 0.75,
                    "confidence": 0.7,
                    "last_outcome_delta": -1.0,
                    "avoid_action": "recheck_runtime_integrity",
                },
            ],
            response_history=[],
            memory_stubs=[],
        )

        self.assertEqual(len(context.bias_summaries), 1)
        self.assertEqual(context.bias_summaries[0]["candidate_profile"], "observe_first")
        self.assertEqual(context.bias_summaries[0]["bias_strength"], -1.0)
        self.assertFalse(context.bias_summaries[0]["habit_eligible"])
        self.assertIn("last_outcome_negative", context.bias_summaries[0]["habit_eligibility_reasons"])
        self.assertEqual(context.bias_summaries[0]["avoid_action"], "recheck_runtime_integrity")
        self.assertEqual(len(context.habit_skills), 1)
        self.assertFalse(context.habit_skills[0]["crystallized"])

    def test_summarize_habit_bias_tracks_evidence_stability_and_confidence(self) -> None:
        summaries = summarize_habit_bias(
            [
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": 1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": 1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": -0.5,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                    },
                },
            ],
            situation_key="integrity|STABLE|recent_yield_detected",
        )

        self.assertEqual(summaries[0].evidence_count, 3)
        self.assertEqual(summaries[0].recent_negative_count, 1)
        self.assertGreater(summaries[0].stability_score, 0.0)
        self.assertGreater(summaries[0].confidence, 0.0)

    def test_summarize_habit_bias_tracks_habit_hit_and_narrowed_counts(self) -> None:
        summaries = summarize_habit_bias(
            [
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": 1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "habit_skill_match": True,
                        "habit_narrowed": True,
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": 1.0,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "habit_skill_match": True,
                        "habit_narrowed": False,
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "outcome_delta": -0.5,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "habit_skill_match": False,
                        "habit_narrowed": False,
                    },
                },
            ],
            situation_key="integrity|STABLE|recent_yield_detected",
        )

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].habit_skill_hit_count, 2)
        self.assertEqual(summaries[0].habit_narrowed_count, 1)
        self.assertEqual(summaries[0].evidence_count, 3)

    def test_build_working_memory_context_surfaces_recent_habit_hit_metadata(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
            pressure_table={
                "pressures": [
                    {
                        "type": "integrity",
                        "evidence": {"reason": "recent_yield_detected"},
                    }
                ]
            },
        )

        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "observed_outcome": "relieved",
                    "evaluation_label": "positive",
                    "outcome_delta": 1.0,
                    "confidence": 0.9,
                    "content": {
                        "top_drive": "integrity",
                        "life_state": "STABLE",
                        "pressure_reason": "recent_yield_detected",
                        "situation_key": "integrity|STABLE|recent_yield_detected",
                        "habit_skill_match": True,
                        "habit_narrowed": True,
                    },
                }
            ],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
        )

        self.assertEqual(len(context.recent_relevant_outcomes), 1)
        self.assertTrue(context.recent_relevant_outcomes[0]["habit_skill_match"])
        self.assertTrue(context.recent_relevant_outcomes[0]["habit_narrowed"])
        self.assertEqual(context.recent_relevant_outcomes[0]["habitual_trace"], "habitual_support")
        self.assertIn("habit_skill_match", context.recent_relevant_outcomes[0]["habitual_trace_reasons"])
        self.assertIn("habit_narrowed", context.recent_relevant_outcomes[0]["habitual_trace_reasons"])
        self.assertIn("recent_positive_feedback", context.recent_relevant_outcomes[0]["habitual_trace_reasons"])
        self.assertEqual(len(context.bias_summaries), 1)
        self.assertEqual(context.bias_summaries[0]["habit_skill_hit_count"], 1)
        self.assertEqual(context.bias_summaries[0]["habit_narrowed_count"], 1)
        self.assertFalse(context.bias_summaries[0]["habit_eligible"])
        self.assertIn("insufficient_evidence", context.bias_summaries[0]["habit_eligibility_reasons"])

        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
        )

        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[],
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|none",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 4,
                    "habit_skill_hit_count": 3,
                    "habit_narrowed_count": 1,
                    "stability_score": 0.8,
                    "confidence": 0.85,
                    "bias_strength": 0.75,
                }
            ],
            response_history=[],
            memory_stubs=[],
        )

        self.assertEqual(len(context.habit_skills), 1)
        self.assertEqual(context.habit_skills[0]["candidate_profile"], "observe_first")
        self.assertEqual(context.habit_skills[0]["preferred_action"], "recheck_runtime_integrity")
        self.assertTrue(context.habit_skills[0]["crystallized"])
        self.assertEqual(context.habit_skills[0]["crystallization_reasons"], [])
        self.assertTrue(context.bias_summaries[0]["habit_eligible"])
        self.assertEqual(context.bias_summaries[0]["habit_eligibility_reasons"], [])

    def test_build_working_memory_context_surfaces_recent_negative_habitual_suppression_trace(self) -> None:
        deliberation_input = build_deliberation_input(
            signal_batch={
                "signals": [{"class": "status"}, {"class": "threat"}],
                "summary": {
                    "signal_count": 2,
                    "status_signal_count": 1,
                    "threat_signal_count": 1,
                    "background_signal_count": 0,
                    "has_threat_signal": True,
                },
            },
            drive_broadcast={
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
            },
            pressure_table={
                "pressures": [
                    {
                        "type": "integrity",
                        "evidence": {"reason": "recent_yield_detected"},
                    }
                ]
            },
        )

        context = build_working_memory_context(
            deliberation_input,
            learning_outcomes=[
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "recheck_runtime_integrity",
                    "observed_outcome": "failed",
                    "evaluation_label": "negative",
                    "outcome_delta": -1.0,
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
            ],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
        )

        self.assertEqual(len(context.recent_relevant_outcomes), 1)
        self.assertEqual(context.recent_relevant_outcomes[0]["habitual_trace"], "habitual_suppression")
        self.assertIn("recent_negative_feedback", context.recent_relevant_outcomes[0]["habitual_trace_reasons"])
        self.assertIn("habit_narrowed", context.recent_relevant_outcomes[0]["habitual_trace_reasons"])

        skills = derive_habit_skills(
            situation_key="integrity|STABLE|recent_yield_detected",
            habit_bias_entries=[
                {
                    "recorded_at": "2026-04-29T10:00:03+00:00",
                    "situation_key": "integrity|STABLE|recent_yield_detected",
                    "candidate_profile": "observe_first",
                    "preferred_action": "recheck_runtime_integrity",
                    "evidence_count": 4,
                    "habit_skill_hit_count": 3,
                    "habit_narrowed_count": 1,
                    "stability_score": 0.8,
                    "confidence": 0.85,
                    "bias_strength": 0.75,
                }
            ],
        )

        self.assertEqual(len(skills), 1)
        self.assertTrue(skills[0].crystallized)
        self.assertEqual(skills[0].candidate_profile, "observe_first")
        self.assertEqual(skills[0].preferred_action, "recheck_runtime_integrity")


if __name__ == "__main__":
    unittest.main()
