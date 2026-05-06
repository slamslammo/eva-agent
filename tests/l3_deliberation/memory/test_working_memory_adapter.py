from __future__ import annotations
import unittest

from eva.l3_deliberation.memory import (
    ClientBackedWorkingMemoryAdapter,
    HeuristicWorkingMemoryAdapter,
    NullWorkingMemoryAdapter,
    WorkingMemoryAdapterRequest,
    WorkingMemoryAdapterResponse,
    NullWorkingMemoryModelClient,
    WorkingMemoryModelClientRequest,
    WorkingMemoryModelClientResponse,
)


class CapturingWorkingMemoryModelClient:
    def __init__(self, response: WorkingMemoryModelClientResponse | None) -> None:
        self.response = response
        self.called = False
        self.request: WorkingMemoryModelClientRequest | None = None

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None:
        self.called = True
        self.request = request
        return self.response


class WorkingMemoryAdapterTests(unittest.TestCase):
    def test_client_backed_working_memory_adapter_normalizes_model_client_payload(self) -> None:
        client = CapturingWorkingMemoryModelClient(
            WorkingMemoryModelClientResponse(
                payload={
                    "candidate_suggestions": ["observe_first", "", "invented_profile"],
                    "prediction_hints": ["bounded_client_hint"],
                    "reasoning_trace": ["client_shell_invoked"],
                    "confidence": 1.3,
                    "selected_action": "should_be_dropped",
                }
            )
        )
        adapter = ClientBackedWorkingMemoryAdapter(client)
        response = adapter.build_advisory_context(
            WorkingMemoryAdapterRequest(
                situation_key="curiosity|STABLE|none",
                drive_broadcast={"top_drive": "curiosity", "drive_levels": {}, "drive_trends": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                },
                bias_summaries=[],
                habit_skills=[],
                recent_relevant_outcomes=[],
                local_confidence=0.2,
            )
        )

        self.assertTrue(client.called)
        self.assertIsNotNone(client.request)
        assert client.request is not None
        self.assertEqual(client.request.to_dict()["situation_key"], "curiosity|STABLE|none")
        assert response is not None
        self.assertEqual(
            response.to_dict(),
            {
                "candidate_suggestions": ["observe_first"],
                "prediction_hints": ["bounded_client_hint"],
                "reasoning_trace": ["client_shell_invoked"],
                "confidence": 1.0,
            },
        )

    def test_heuristic_working_memory_adapter_returns_bounded_advisory_payload(self) -> None:
        adapter = HeuristicWorkingMemoryAdapter()
        response = adapter.build_advisory_context(
            WorkingMemoryAdapterRequest(
                situation_key="integrity|STABLE|none",
                drive_broadcast={"top_drive": "integrity", "drive_levels": {}, "drive_trends": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                },
                bias_summaries=[{"candidate_profile": "stabilize_first"}],
                habit_skills=[],
                recent_relevant_outcomes=[],
                local_confidence=0.45,
            )
        )

        assert response is not None
        payload = response.to_dict()
        self.assertEqual(payload["candidate_suggestions"], ["stabilize_first"])
        self.assertEqual(payload["prediction_hints"], ["integrity_pressure_prefers_stabilization"])
        self.assertIn("top_drive_integrity", payload["reasoning_trace"])
        self.assertIn("bias_summaries_present", payload["reasoning_trace"])
        self.assertEqual(payload["confidence"], 0.55)

    def test_client_backed_working_memory_adapter_accepts_null_model_client(self) -> None:
        adapter = ClientBackedWorkingMemoryAdapter(NullWorkingMemoryModelClient())
        response = adapter.build_advisory_context(
            WorkingMemoryAdapterRequest(
                situation_key="curiosity|STABLE|none",
                drive_broadcast={"top_drive": "curiosity", "drive_levels": {}, "drive_trends": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                },
                bias_summaries=[],
                habit_skills=[],
                recent_relevant_outcomes=[],
                local_confidence=0.2,
            )
        )

        self.assertIsNone(response)

        adapter = NullWorkingMemoryAdapter()
        response = adapter.build_advisory_context(
            WorkingMemoryAdapterRequest(
                situation_key="integrity|STABLE|none",
                drive_broadcast={"top_drive": "integrity", "drive_levels": {}, "drive_trends": {}},
                runtime_gate_context={
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                },
                bias_summaries=[],
                habit_skills=[],
                recent_relevant_outcomes=[],
                local_confidence=0.2,
            )
        )

        self.assertIsNone(response)

    def test_working_memory_adapter_response_serializes_only_bounded_fields(self) -> None:
        payload = WorkingMemoryAdapterResponse(
            candidate_suggestions=("observe_first", "", "invented_profile"),
            prediction_hints=("likely_information_gain",),
            reasoning_trace=("integrity_conflict_detected",),
            confidence=1.5,
        ).to_dict()

        self.assertEqual(
            payload,
            {
                "candidate_suggestions": ["observe_first"],
                "prediction_hints": ["likely_information_gain"],
                "reasoning_trace": ["integrity_conflict_detected"],
                "confidence": 1.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
