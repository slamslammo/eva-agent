from __future__ import annotations
import unittest

from eva.l3_deliberation.memory import (
    HeuristicWorkingMemoryModelClient,
    MODEL_CLIENT_MODE_HEURISTIC,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
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
                    # Round 1.B-1-d: drive_levels is now consulted for the
                    # high-drive routing threshold; supplying explicit
                    # integrity=0.85 keeps the test's intent.
                    "drive_broadcast": {"top_drive": "integrity", "drive_levels": {"integrity": 0.85}, "drive_trends": {}},
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
