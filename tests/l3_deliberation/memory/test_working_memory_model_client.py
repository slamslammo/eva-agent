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


class DeepSeekWorkingMemoryModelClientTests(unittest.TestCase):
    """Phase 1.6: validate DeepSeek model client path end-to-end with a
    mocked transport. The OpenAI-compatible chat-completions envelope must
    be parsed correctly (single-string content AND multi-block content)
    and the same JSON-advisory sanitization must apply."""

    def test_deepseek_client_returns_bounded_payload(self) -> None:
        from eva.l3_deliberation.memory import (
            DeepSeekWorkingMemoryModelClient,
            DEFAULT_DEEPSEEK_MODEL,
            WorkingMemoryModelClientConfig,
            WorkingMemoryModelClientRequest,
        )
        canned_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"candidate_suggestions": ["stabilize_first"], '
                            '"prediction_hints": ["maintain"], '
                            '"reasoning_trace": ["safety_priority"], '
                            '"confidence": 0.65}'
                        ),
                    }
                }
            ]
        }
        client = DeepSeekWorkingMemoryModelClient(
            WorkingMemoryModelClientConfig(provider="deepseek", model=DEFAULT_DEEPSEEK_MODEL, request_timeout_sec=2.0),
            transport=lambda payload, api_key, timeout_sec: canned_response,
        )
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            response = client.build_working_memory_advisory(
                WorkingMemoryModelClientRequest(payload={"situation_key": "t|STABLE|none"})
            )
        assert response is not None
        out = response.to_dict()
        self.assertEqual(out["candidate_suggestions"], ["stabilize_first"])
        self.assertEqual(out["prediction_hints"], ["maintain"])
        self.assertEqual(out["confidence"], 0.65)

    def test_deepseek_client_raises_when_api_key_missing(self) -> None:
        from eva.l3_deliberation.memory import DeepSeekWorkingMemoryModelClient, WorkingMemoryModelClientRequest
        client = DeepSeekWorkingMemoryModelClient(transport=lambda *args, **kwargs: {})
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "deepseek_api_key_missing"):
                client.build_working_memory_advisory(WorkingMemoryModelClientRequest(payload={}))

    def test_deepseek_client_rejects_missing_choices(self) -> None:
        from eva.l3_deliberation.memory import DeepSeekWorkingMemoryModelClient, WorkingMemoryModelClientRequest
        client = DeepSeekWorkingMemoryModelClient(
            transport=lambda payload, api_key, timeout_sec: {"id": "x"}  # no choices field
        )
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "deepseek_response_missing_choices"):
                client.build_working_memory_advisory(WorkingMemoryModelClientRequest(payload={}))

    def test_deepseek_client_accepts_block_content_format(self) -> None:
        """Some OpenAI-compatible proxies emit content as a list of typed blocks."""
        from eva.l3_deliberation.memory import DeepSeekWorkingMemoryModelClient, WorkingMemoryModelClientRequest
        canned_response = {
            "choices": [
                {"message": {"content": [{"type": "text", "text": '{"confidence": 0.4}'}]}}
            ]
        }
        client = DeepSeekWorkingMemoryModelClient(
            transport=lambda payload, api_key, timeout_sec: canned_response,
        )
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
            response = client.build_working_memory_advisory(WorkingMemoryModelClientRequest(payload={}))
        assert response is not None
        self.assertEqual(response.to_dict().get("confidence"), 0.4)


class DeepSeekApiBaseUrlResolutionTests(unittest.TestCase):
    def test_default_base_url_when_env_unset(self) -> None:
        from eva.l3_deliberation.memory.working_memory_model_client import _resolve_deepseek_chat_url
        with patch.dict(os.environ, {}, clear=True):
            url = _resolve_deepseek_chat_url()
        self.assertEqual(url, "https://api.deepseek.com/v1/chat/completions")

    def test_env_override_with_bare_host(self) -> None:
        from eva.l3_deliberation.memory.working_memory_model_client import _resolve_deepseek_chat_url
        with patch.dict(os.environ, {"DEEPSEEK_API_BASE_URL": "https://proxy.example.com"}, clear=False):
            url = _resolve_deepseek_chat_url()
        self.assertEqual(url, "https://proxy.example.com/v1/chat/completions")


class AnthropicApiBaseUrlResolutionTests(unittest.TestCase):
    """Phase 1 pre-work: verify ``ANTHROPIC_API_BASE_URL`` env override works
    for validation runs that target an enterprise relay rather than the
    production Anthropic endpoint."""

    def test_default_base_url_when_env_unset(self) -> None:
        from eva.l3_deliberation.memory.working_memory_model_client import _resolve_anthropic_messages_url
        with patch.dict(os.environ, {}, clear=True):
            url = _resolve_anthropic_messages_url()
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")

    def test_env_override_with_bare_host(self) -> None:
        from eva.l3_deliberation.memory.working_memory_model_client import _resolve_anthropic_messages_url
        with patch.dict(os.environ, {"ANTHROPIC_API_BASE_URL": "http://cccai.cfd"}, clear=False):
            url = _resolve_anthropic_messages_url()
        self.assertEqual(url, "http://cccai.cfd/v1/messages")

    def test_env_override_with_trailing_slash(self) -> None:
        from eva.l3_deliberation.memory.working_memory_model_client import _resolve_anthropic_messages_url
        with patch.dict(os.environ, {"ANTHROPIC_API_BASE_URL": "http://cccai.cfd/"}, clear=False):
            url = _resolve_anthropic_messages_url()
        self.assertEqual(url, "http://cccai.cfd/v1/messages")

    def test_env_override_with_explicit_path_preserved(self) -> None:
        from eva.l3_deliberation.memory.working_memory_model_client import _resolve_anthropic_messages_url
        with patch.dict(os.environ, {"ANTHROPIC_API_BASE_URL": "http://example.com/v1/messages"}, clear=False):
            url = _resolve_anthropic_messages_url()
        self.assertEqual(url, "http://example.com/v1/messages")


if __name__ == "__main__":
    unittest.main()
