from __future__ import annotations
import tempfile
import unittest
from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation import build_deliberation_input
from eva.l3_deliberation import build_learning_outcome_record, evaluate_response_outcome
from eva.l3_deliberation.memory import derive_habit_skills, summarize_habit_bias
from eva.l3_deliberation.reasoning import build_working_memory_context, build_working_memory_context_from_store
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


class FailingWorkingMemoryAdapter:
    def __init__(self, message: str = "anthropic_transport_unavailable") -> None:
        self.message = message
        self.called = False

    def build_advisory_context(
        self,
        request: WorkingMemoryAdapterRequest,
    ) -> WorkingMemoryAdapterResponse | None:
        self.called = True
        del request
        raise RuntimeError(self.message)


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
        self.assertEqual(context.advisory_source, "local_rule_based")
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
                candidate_suggestions=("observe_first", "invented_profile"),
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
        self.assertEqual(context.advisory_source, "explicit_adapter")
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
        self.assertEqual(context.advisory_source, "auto_preferred_local")
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
        self.assertEqual(context.advisory_source, "explicit_adapter")
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
        self.assertEqual(context.advisory_source, "auto_no_adapter")
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
        self.assertEqual(context.advisory_source, "null_adapter")
        self.assertEqual(context.advisory_context, {})

    def test_build_working_memory_context_from_store_honors_explicit_advisory_source(self) -> None:
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
                confidence=0.66,
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                backend="llm_assisted",
                llm_adapter=adapter,
                advisory_source="client_backed_model_shell",
            )

        self.assertEqual(context.advisory_source, "client_backed_model_shell")

    def test_llm_backend_falls_back_to_local_context_and_writes_audit_record(self) -> None:
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

        adapter = FailingWorkingMemoryAdapter("anthropic_transport_unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(build_runtime_paths(temp_dir))
            context = build_working_memory_context_from_store(
                store,
                deliberation_input,
                backend="llm_assisted",
                llm_adapter=adapter,
                advisory_source="client_backed_anthropic",
            )
            llm_audit = store.read_llm_advisory_audit()

        self.assertTrue(adapter.called)
        self.assertEqual(context.source_backend, "local_rule_based")
        self.assertEqual(context.advisory_source, "client_backed_anthropic:fallback")
        self.assertEqual(context.advisory_context, {})
        self.assertTrue(context.advisory_fallback)
        self.assertEqual(len(llm_audit), 1)
        self.assertEqual(llm_audit[0]["provider"], "anthropic")
        self.assertEqual(llm_audit[0]["model"], "claude-sonnet-4-6")
        self.assertEqual(llm_audit[0]["outcome"], "fallback_local")
        self.assertEqual(llm_audit[0]["error"], "anthropic_transport_unavailable")

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

    def test_build_working_memory_context_uses_memory_stub_fallback_traces(self) -> None:
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
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[
                {
                    "recorded_at": "2026-05-03T10:00:00+00:00",
                    "source": "l3_deliberation",
                    "salience": 1.0,
                    "memory_type": "threat_trace",
                    "write_reason": "threat_signal_present",
                    "linked_audit_recorded_at": "2026-05-03T10:00:00+00:00",
                    "content": {
                        "top_drive": "integrity",
                        "selected_action": "compatibility_release",
                        "candidate_profile": "stabilize_first",
                        "drive_state_at_encoding": {
                            "top_drive": "integrity",
                            "drive_levels": {"integrity": 0.8},
                            "drive_trends": {"integrity": "worsening"},
                        },
                    },
                },
                {
                    "recorded_at": "2026-05-03T10:05:00+00:00",
                    "source": "l3_deliberation",
                    "salience": 0.75,
                    "memory_type": "release_trace",
                    "write_reason": "release_outcome=compatibility_release",
                    "linked_audit_recorded_at": "2026-05-03T10:05:00+00:00",
                    "content": {
                        "top_drive": "curiosity",
                        "selected_action": "compatibility_release",
                        "candidate_profile": "observe_first",
                        "drive_state_at_encoding": {
                            "top_drive": "curiosity",
                            "drive_levels": {"curiosity": 0.8},
                            "drive_trends": {"curiosity": "improving"},
                        },
                    },
                },
            ],
        )

        self.assertEqual(len(context.recent_relevant_outcomes), 1)
        self.assertEqual(context.recent_relevant_outcomes[0]["candidate_profile"], "stabilize_first")
        self.assertEqual(context.recent_relevant_outcomes[0]["selected_action"], "compatibility_release")
        self.assertEqual(context.recent_relevant_outcomes[0]["memory_type"], "threat_trace")
        self.assertEqual(context.recent_relevant_outcomes[0]["habitual_trace"], "habitual_suppression")
        self.assertEqual(
            context.recent_relevant_outcomes[0]["habitual_trace_reasons"],
            ["threat_trace", "high_salience"],
        )
        self.assertEqual(
            context.recent_relevant_outcomes[0]["drive_state_at_encoding"],
            {
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.8},
                "drive_trends": {"integrity": "worsening"},
            },
        )
        self.assertAlmostEqual(context.recent_relevant_outcomes[0]["salience"], 1.0)
        self.assertNotIn("memory_stubs", context.to_dict())
        self.assertEqual(context.confidence, 0.2)

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
    def test_build_working_memory_context_ranks_similar_drive_learning_outcomes(self) -> None:
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
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.9, "curiosity": 0.8, "survival": 0.1},
                "drive_trends": {"integrity": "worsening", "curiosity": "improving", "survival": "stable"},
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
            learning_outcomes=[
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "candidate_profile": "observe_first",
                    "selected_action": "curiosity_probe",
                    "observed_outcome": "relieved",
                    "evaluation_label": "positive",
                    "outcome_delta": 0.5,
                    "confidence": 0.7,
                    "content": {
                        "top_drive": "curiosity",
                        "life_state": "STABLE",
                        "pressure_reason": "none",
                        "situation_key": "curiosity|STABLE|none",
                    },
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "candidate_profile": "stabilize_first",
                    "selected_action": "survival_patch",
                    "observed_outcome": "unchanged",
                    "evaluation_label": "neutral",
                    "outcome_delta": 0.0,
                    "confidence": 0.7,
                    "content": {
                        "top_drive": "survival",
                        "life_state": "STABLE",
                        "pressure_reason": "none",
                        "situation_key": "survival|STABLE|none",
                    },
                },
            ],
            habit_bias_entries=[],
            response_history=[],
            memory_stubs=[],
            max_recent_outcomes=1,
        )

        self.assertEqual(len(context.recent_relevant_outcomes), 1)
        self.assertEqual(context.recent_relevant_outcomes[0]["top_drive"], "curiosity")
        self.assertEqual(context.recent_relevant_outcomes[0]["selected_action"], "curiosity_probe")

    def test_build_working_memory_context_uses_similar_drive_response_history_fallback(self) -> None:
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
                "top_drive": "integrity",
                "drive_levels": {"integrity": 0.9, "curiosity": 0.8, "survival": 0.1},
                "drive_trends": {"integrity": "worsening", "curiosity": "improving", "survival": "stable"},
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
            response_history=[
                {
                    "recorded_at": "2026-04-29T10:00:01+00:00",
                    "selected_action": "survival_patch",
                    "pressure_outcome": "unchanged",
                    "execution_status": "completed",
                    "followup_needed": False,
                    "drive_context": {"top_drive": "survival"},
                    "life_state": "STABLE",
                    "pressure_reason": "none",
                },
                {
                    "recorded_at": "2026-04-29T10:00:02+00:00",
                    "selected_action": "curiosity_probe",
                    "pressure_outcome": "relieved",
                    "execution_status": "completed",
                    "followup_needed": False,
                    "drive_context": {"top_drive": "curiosity"},
                    "life_state": "STABLE",
                    "pressure_reason": "none",
                },
            ],
            memory_stubs=[],
            max_recent_outcomes=1,
        )

        self.assertEqual(len(context.recent_relevant_outcomes), 1)
        self.assertEqual(context.recent_relevant_outcomes[0]["top_drive"], "curiosity")
        self.assertEqual(context.recent_relevant_outcomes[0]["selected_action"], "curiosity_probe")


if __name__ == "__main__":
    unittest.main()
