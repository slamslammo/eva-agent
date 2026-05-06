from __future__ import annotations
import os
import unittest
from unittest.mock import patch

from eva.l3_deliberation.memory import (
    AnthropicWorkingMemoryModelClient,
    DEFAULT_ANTHROPIC_MODEL,
    HeuristicWorkingMemoryModelClient,
    MODEL_CLIENT_MODE_ANTHROPIC,
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

    def test_build_builtin_working_memory_model_client_returns_anthropic_client(self) -> None:
        client = build_builtin_working_memory_model_client(MODEL_CLIENT_MODE_ANTHROPIC)
        self.assertIsInstance(client, AnthropicWorkingMemoryModelClient)
        self.assertEqual(client.config.provider, "anthropic")
        self.assertEqual(client.config.model, DEFAULT_ANTHROPIC_MODEL)

    def test_anthropic_working_memory_model_client_shapes_request_and_sanitizes_response(self) -> None:
        captured: dict[str, object] = {}

        def transport(payload: dict[str, object], api_key: str, timeout_sec: float) -> dict[str, object]:
            captured["payload"] = payload
            captured["api_key"] = api_key
            captured["timeout_sec"] = timeout_sec
            return {
                "content": [
                    {
                        "type": "text",
                        "text": '{"candidate_suggestions":["observe_first","invented"],"prediction_hints":["bounded_hint"],"reasoning_trace":["model_trace"],"confidence":1.4,"selected_action":"drop_me"}',
                    }
                ]
            }

        client = AnthropicWorkingMemoryModelClient(
            WorkingMemoryModelClientConfig(provider="anthropic", model="claude-sonnet-4-6", request_timeout_sec=7.5),
            transport=transport,
        )

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            response = client.build_working_memory_advisory(
                WorkingMemoryModelClientRequest(
                    payload={
                        "situation_key": "curiosity|STABLE|none",
                        "drive_broadcast": {"top_drive": "curiosity"},
                        "runtime_gate_context": {"turn_allowed": True, "conservative_mode": False},
                        "local_confidence": 0.2,
                    }
                )
            )

        assert response is not None
        self.assertEqual(captured["api_key"], "test-key")
        self.assertEqual(captured["timeout_sec"], 7.5)
        payload = captured["payload"]
        assert isinstance(payload, dict)
        self.assertEqual(payload["model"], "claude-sonnet-4-6")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["max_tokens"], 220)
        self.assertIn("Respond with JSON only", str(payload["system"]))
        self.assertEqual(
            response.to_dict(),
            {
                "candidate_suggestions": ["observe_first"],
                "prediction_hints": ["bounded_hint"],
                "reasoning_trace": ["model_trace"],
                "confidence": 1.0,
            },
        )

    def test_anthropic_working_memory_model_client_raises_when_api_key_missing(self) -> None:
        client = AnthropicWorkingMemoryModelClient()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "anthropic_api_key_missing"):
                client.build_working_memory_advisory(WorkingMemoryModelClientRequest(payload={}))

    def test_anthropic_working_memory_model_client_rejects_non_json_response(self) -> None:
        client = AnthropicWorkingMemoryModelClient(
            transport=lambda payload, api_key, timeout_sec: {"content": [{"type": "text", "text": "not json"}]}
        )
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "anthropic_response_not_json"):
                client.build_working_memory_advisory(WorkingMemoryModelClientRequest(payload={}))


if __name__ == "__main__":
    unittest.main()
