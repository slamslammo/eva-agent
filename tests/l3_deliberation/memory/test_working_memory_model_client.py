from __future__ import annotations
import tempfile
import unittest
from eva.kernel import StateStore, build_runtime_paths
from eva.l3_deliberation import build_deliberation_input, build_learning_outcome_record, evaluate_response_outcome
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


class WorkingMemoryModelClientTests(unittest.TestCase):
    def test_heuristic_working_memory_model_client_returns_bounded_payload(self) -> None:
        client = HeuristicWorkingMemoryModelClient(
            WorkingMemoryModelClientConfig(provider="heuristic", model="local-test-client", request_timeout_sec=1.5)
        )
        response = client.build_working_memory_advisory(
            WorkingMemoryModelClientRequest(
                payload={
                    "situation_key": "integrity|STABLE|none",
                    "drive_broadcast": {"top_drive": "integrity", "drive_levels": {}, "drive_trends": {}},
                    "runtime_gate_context": {
                        "instance_valid": True,
                        "turn_allowed": True,
                        "critical_blocked": False,
                        "conservative_mode": False,
                        "life_state": "STABLE",
                    },
                    "local_confidence": 0.4,
                }
            )
        )

        assert response is not None
        self.assertEqual(
            response.to_dict(),
            {
                "candidate_suggestions": ["stabilize_first"],
                "prediction_hints": ["client_prefers_stabilize_first"],
                "reasoning_trace": [
                    "model_client_provider_heuristic",
                    "model_client_local-test-client",
                    "model_client_prefers_stabilization",
                ],
                "confidence": 0.5,
            },
        )

    def test_build_builtin_working_memory_model_client_returns_heuristic_placeholder(self) -> None:
        client = build_builtin_working_memory_model_client(
            MODEL_CLIENT_MODE_HEURISTIC,
            WorkingMemoryModelClientConfig(provider="heuristic", model="placeholder-client", request_timeout_sec=2.0),
        )
        response = client.build_working_memory_advisory(
            WorkingMemoryModelClientRequest(
                payload={
                    "drive_broadcast": {"top_drive": "curiosity"},
                    "runtime_gate_context": {"turn_allowed": True, "conservative_mode": False},
                    "local_confidence": 0.2,
                }
            )
        )

        assert response is not None
        self.assertEqual(response.to_dict()["candidate_suggestions"], ["observe_first"])


if __name__ == "__main__":
    unittest.main()
