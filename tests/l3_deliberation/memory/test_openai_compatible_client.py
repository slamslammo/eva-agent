"""Round 1.7-a — tests for the vendor-neutral OpenAI-compatible live client.

Covers:
- request body merges ``EVA_LLM_EXTRA_PARAMS_JSON`` opaquely
- request body omits extra params when env unset
- response parses ``choices[0].message.content`` (string and block-list shapes)
- fail-fast on each required env missing
- fail-fast on malformed ``EVA_LLM_EXTRA_PARAMS_JSON``
- URL composition appends ``/chat/completions`` to base URL
- factory ``MODEL_CLIENT_MODE_LIVE`` branch wires the new client
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from eva.l3_deliberation.memory import (
    MODEL_CLIENT_MODE_LIVE,
    OpenAICompatibleWorkingMemoryModelClient,
    OpenAICompatibleWorkingMemoryModelClientConfig,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
    build_builtin_working_memory_model_client,
)
from eva.l3_deliberation.memory.working_memory_model_client import (
    EVA_LLM_API_BASE_URL_ENV,
    EVA_LLM_API_KEY_ENV,
    EVA_LLM_EXTRA_PARAMS_JSON_ENV,
    EVA_LLM_MODEL_ENV,
    _is_retryable_openai_compatible_error,
    _load_live_config_from_env,
    _openai_compatible_request_payload,
    _openai_compatible_text_response,
    _resolve_openai_compatible_chat_url,
)


def _patched_env(env_overrides: dict[str, str]):
    """Return a patch.dict context with all EVA_LLM_* vars explicitly set.

    Any var not present in ``env_overrides`` defaults to empty string (which
    the loader treats as missing). This isolates each test from the caller's
    real environment (e.g. ``EVA_LLM_API_KEY`` sourced from ``llm.env``).
    """

    all_eva_vars: dict[str, str] = {
        EVA_LLM_API_BASE_URL_ENV: "",
        EVA_LLM_API_KEY_ENV: "",
        EVA_LLM_MODEL_ENV: "",
        EVA_LLM_EXTRA_PARAMS_JSON_ENV: "",
    }
    all_eva_vars.update(env_overrides)
    return patch.dict(os.environ, all_eva_vars, clear=False)


def _ok_env_overrides(extra_params_json: str | None = None) -> dict[str, str]:
    """Return a minimal env dict with all required EVA_LLM_* vars set."""

    overrides: dict[str, str] = {
        EVA_LLM_API_BASE_URL_ENV: "https://api.example.com/v1",
        EVA_LLM_API_KEY_ENV: "test-key",
        EVA_LLM_MODEL_ENV: "test-model",
    }
    if extra_params_json is not None:
        overrides[EVA_LLM_EXTRA_PARAMS_JSON_ENV] = extra_params_json
    return overrides


class OpenAICompatibleRequestPayloadTests(unittest.TestCase):
    """Request body construction — extra_params merge behavior."""

    def _make_request(self) -> WorkingMemoryModelClientRequest:
        return WorkingMemoryModelClientRequest(
            payload={
                "situation_key": "curiosity|STABLE|none",
                "drive_broadcast": {"top_drive": "curiosity"},
                "runtime_gate_context": {"turn_allowed": True, "conservative_mode": False},
                "local_confidence": 0.3,
            }
        )

    def test_extra_params_merged_into_body_when_present(self) -> None:
        body = _openai_compatible_request_payload(
            self._make_request(),
            model="deepseek-v4-flash",
            extra_params={"thinking": {"type": "disabled"}},
        )

        self.assertEqual(body["model"], "deepseek-v4-flash")
        self.assertIn("thinking", body)
        self.assertEqual(body["thinking"], {"type": "disabled"})
        # Base OpenAI Chat Completions structure is preserved.
        self.assertIn("messages", body)
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][1]["role"], "user")

    def test_extra_params_omitted_when_empty(self) -> None:
        body = _openai_compatible_request_payload(
            self._make_request(),
            model="gpt-4o-mini",
            extra_params={},
        )

        self.assertNotIn("thinking", body)
        self.assertNotIn("reasoning_effort", body)
        # Only the standard Chat Completions fields are present.
        self.assertEqual(
            set(body.keys()),
            {"model", "max_tokens", "temperature", "messages"},
        )


class OpenAICompatibleResponseParseTests(unittest.TestCase):
    """Response shape extraction — string and block-list content forms."""

    def test_parses_string_content(self) -> None:
        payload = {
            "choices": [
                {
                    "message": {
                        "content": '{"candidate_suggestions": ["observe_first"], "confidence": 0.4}'
                    }
                }
            ]
        }
        text = _openai_compatible_text_response(payload)
        self.assertIn("observe_first", text)

    def test_parses_block_list_content(self) -> None:
        payload = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": '{"candidate_suggestions": ["stabilize_first"]}'}
                        ]
                    }
                }
            ]
        }
        text = _openai_compatible_text_response(payload)
        self.assertIn("stabilize_first", text)


class OpenAICompatibleEnvLoaderTests(unittest.TestCase):
    """Env loader — fail-fast on missing or invalid env vars."""

    def test_missing_base_url_raises(self) -> None:
        overrides = _ok_env_overrides()
        del overrides[EVA_LLM_API_BASE_URL_ENV]
        with _patched_env(overrides):
            with self.assertRaises(RuntimeError) as ctx:
                _load_live_config_from_env(None)
        self.assertIn(EVA_LLM_API_BASE_URL_ENV, str(ctx.exception))

    def test_missing_api_key_raises(self) -> None:
        overrides = _ok_env_overrides()
        del overrides[EVA_LLM_API_KEY_ENV]
        with _patched_env(overrides):
            with self.assertRaises(RuntimeError) as ctx:
                _load_live_config_from_env(None)
        self.assertIn(EVA_LLM_API_KEY_ENV, str(ctx.exception))

    def test_missing_model_raises(self) -> None:
        overrides = _ok_env_overrides()
        del overrides[EVA_LLM_MODEL_ENV]
        with _patched_env(overrides):
            with self.assertRaises(RuntimeError) as ctx:
                _load_live_config_from_env(None)
        self.assertIn(EVA_LLM_MODEL_ENV, str(ctx.exception))

    def test_invalid_extra_params_json_not_parseable_raises(self) -> None:
        overrides = _ok_env_overrides(extra_params_json="{not valid json")
        with _patched_env(overrides):
            with self.assertRaises(RuntimeError) as ctx:
                _load_live_config_from_env(None)
        self.assertIn("not_json", str(ctx.exception))

    def test_invalid_extra_params_json_not_object_raises(self) -> None:
        overrides = _ok_env_overrides(extra_params_json="[1, 2, 3]")
        with _patched_env(overrides):
            with self.assertRaises(RuntimeError) as ctx:
                _load_live_config_from_env(None)
        self.assertIn("not_object", str(ctx.exception))

    def test_successful_resolution_populates_all_fields(self) -> None:
        overrides = _ok_env_overrides(extra_params_json='{"thinking":{"type":"disabled"}}')
        with _patched_env(overrides):
            resolved = _load_live_config_from_env(
                WorkingMemoryModelClientConfig(
                    provider="openai-compatible",
                    model="env-resolved",
                    request_timeout_sec=12.5,
                )
            )
        self.assertEqual(resolved.base_url, "https://api.example.com/v1")
        self.assertEqual(resolved.api_key, "test-key")
        self.assertEqual(resolved.model, "test-model")
        self.assertEqual(resolved.extra_params, {"thinking": {"type": "disabled"}})
        self.assertAlmostEqual(resolved.timeout_sec, 12.5)
        # Round 1.7-b: env loader now seeds retry defaults.
        self.assertEqual(resolved.max_retries, 3)
        self.assertAlmostEqual(resolved.retry_backoff_base_sec, 1.0)


class OpenAICompatibleUrlCompositionTests(unittest.TestCase):
    """URL composition — base URL + chat-completions path."""

    def test_appends_chat_completions_path(self) -> None:
        self.assertEqual(
            _resolve_openai_compatible_chat_url("https://api.deepseek.com/v1"),
            "https://api.deepseek.com/v1/chat/completions",
        )

    def test_tolerates_trailing_slash(self) -> None:
        self.assertEqual(
            _resolve_openai_compatible_chat_url("https://api.deepseek.com/v1/"),
            "https://api.deepseek.com/v1/chat/completions",
        )

    def test_does_not_double_append_when_already_present(self) -> None:
        # Some relays expose the full /v1/chat/completions path as the
        # "base URL" — tolerate that without duplicating the segment.
        self.assertEqual(
            _resolve_openai_compatible_chat_url("https://relay.example/v1/chat/completions"),
            "https://relay.example/v1/chat/completions",
        )


class OpenAICompatibleFactoryWiringTests(unittest.TestCase):
    """Factory branch — live mode produces the right client class."""

    def test_factory_returns_openai_compatible_client_for_live_mode(self) -> None:
        overrides = _ok_env_overrides(extra_params_json='{"thinking":{"type":"disabled"}}')
        with _patched_env(overrides):
            client = build_builtin_working_memory_model_client(
                MODEL_CLIENT_MODE_LIVE,
                WorkingMemoryModelClientConfig(
                    provider="openai-compatible",
                    model="env-resolved",
                    request_timeout_sec=7.5,
                ),
            )
        self.assertIsInstance(client, OpenAICompatibleWorkingMemoryModelClient)
        self.assertEqual(client.config.base_url, "https://api.example.com/v1")
        self.assertEqual(client.config.api_key, "test-key")
        self.assertEqual(client.config.model, "test-model")
        self.assertEqual(client.config.extra_params, {"thinking": {"type": "disabled"}})
        self.assertAlmostEqual(client.config.timeout_sec, 7.5)


class OpenAICompatibleClientEndToEndTests(unittest.TestCase):
    """End-to-end client behavior via injected transport (no HTTP)."""

    def test_client_shapes_request_and_sanitizes_response(self) -> None:
        captured: dict[str, object] = {}

        def transport(
            payload: dict[str, object],
            api_key: str,
            timeout_sec: float,
            base_url: str,
        ) -> dict[str, object]:
            captured["payload"] = payload
            captured["api_key"] = api_key
            captured["timeout_sec"] = timeout_sec
            captured["base_url"] = base_url
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"candidate_suggestions":["observe_first","invented"],'
                                '"prediction_hints":["bounded_hint"],'
                                '"reasoning_trace":["model_trace"],'
                                '"confidence":1.4,'
                                '"selected_action":"drop_me"}'
                            )
                        }
                    }
                ]
            }

        config = OpenAICompatibleWorkingMemoryModelClientConfig(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model="test-model",
            extra_params={"thinking": {"type": "disabled"}},
            timeout_sec=9.0,
        )
        client = OpenAICompatibleWorkingMemoryModelClient(config, transport=transport)
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
        self.assertEqual(captured["timeout_sec"], 9.0)
        self.assertEqual(captured["base_url"], "https://api.example.com/v1")
        sent_body = captured["payload"]
        assert isinstance(sent_body, dict)
        self.assertEqual(sent_body["model"], "test-model")
        self.assertEqual(sent_body["thinking"], {"type": "disabled"})
        # Sanitization: invented candidate dropped, confidence clamped to 1.0,
        # selected_action dropped (not in allowed advisory fields).
        result = response.to_dict()
        self.assertEqual(result["candidate_suggestions"], ["observe_first"])
        self.assertEqual(result["prediction_hints"], ["bounded_hint"])
        self.assertEqual(result["reasoning_trace"], ["model_trace"])
        self.assertEqual(result["confidence"], 1.0)
        self.assertNotIn("selected_action", result)


class OpenAICompatibleRetryClassifierTests(unittest.TestCase):
    """Retry classifier — which error labels are worth retrying."""

    def test_5xx_is_retryable(self) -> None:
        self.assertTrue(_is_retryable_openai_compatible_error("openai_compatible_http_503"))
        self.assertTrue(_is_retryable_openai_compatible_error("openai_compatible_http_502_bad_gateway"))
        self.assertTrue(_is_retryable_openai_compatible_error("openai_compatible_http_500"))

    def test_4xx_is_not_retryable(self) -> None:
        self.assertFalse(_is_retryable_openai_compatible_error("openai_compatible_http_401"))
        self.assertFalse(_is_retryable_openai_compatible_error("openai_compatible_http_429_rate_limited"))
        self.assertFalse(_is_retryable_openai_compatible_error("openai_compatible_http_400"))

    def test_transport_unavailable_is_retryable(self) -> None:
        self.assertTrue(_is_retryable_openai_compatible_error("openai_compatible_transport_unavailable"))

    def test_response_parsing_errors_are_not_retryable(self) -> None:
        # 200 with malformed body — retrying yields the same malformed body.
        self.assertFalse(_is_retryable_openai_compatible_error("openai_compatible_response_missing_choices"))
        self.assertFalse(_is_retryable_openai_compatible_error("openai_compatible_response_empty_content"))


class _SequencedTransport:
    """Test helper: a transport callable that returns / raises items in order."""

    def __init__(self, sequence: list[object]) -> None:
        self.sequence = list(sequence)
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        payload: dict[str, object],
        api_key: str,
        timeout_sec: float,
        base_url: str,
    ) -> dict[str, object]:
        self.calls.append(
            {"payload": payload, "api_key": api_key, "timeout_sec": timeout_sec, "base_url": base_url}
        )
        if not self.sequence:
            raise AssertionError("transport called more times than sequenced items")
        item = self.sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item  # type: ignore[return-value]


def _ok_response_payload() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": '{"candidate_suggestions":["observe_first"],"confidence":0.4}'
                }
            }
        ]
    }


def _make_test_request() -> WorkingMemoryModelClientRequest:
    return WorkingMemoryModelClientRequest(
        payload={
            "situation_key": "curiosity|STABLE|none",
            "drive_broadcast": {"top_drive": "curiosity"},
            "runtime_gate_context": {"turn_allowed": True, "conservative_mode": False},
            "local_confidence": 0.3,
        }
    )


def _make_config(*, max_retries: int = 3, backoff: float = 1.0) -> OpenAICompatibleWorkingMemoryModelClientConfig:
    return OpenAICompatibleWorkingMemoryModelClientConfig(
        base_url="https://api.example.com/v1",
        api_key="test-key",
        model="test-model",
        extra_params={},
        timeout_sec=5.0,
        max_retries=max_retries,
        retry_backoff_base_sec=backoff,
    )


class OpenAICompatibleRetryFallbackTests(unittest.TestCase):
    """End-to-end retry + fallback behavior under simulated transport failures."""

    def test_200_first_attempt_no_retry_no_fallback(self) -> None:
        transport = _SequencedTransport([_ok_response_payload()])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=3),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        self.assertEqual(len(transport.calls), 1)
        mock_sleep.assert_not_called()
        assert response is not None
        self.assertEqual(response.to_dict()["candidate_suggestions"], ["observe_first"])
        # No fallback was invoked, so no fallback reason was attached.
        reasoning = response.to_dict().get("reasoning_trace") or []
        self.assertFalse(any("live_client_fallback" in str(r) for r in reasoning))

    def test_retry_on_5xx_succeeds_on_second_attempt(self) -> None:
        transport = _SequencedTransport([
            RuntimeError("openai_compatible_http_503"),
            _ok_response_payload(),
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=3, backoff=2.0),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        self.assertEqual(len(transport.calls), 2)
        # One sleep between attempt 0 and attempt 1 — base * 2^0 = 2.0
        self.assertEqual(mock_sleep.call_count, 1)
        self.assertAlmostEqual(mock_sleep.call_args[0][0], 2.0)
        assert response is not None
        self.assertEqual(response.to_dict()["candidate_suggestions"], ["observe_first"])

    def test_retry_exhausts_then_falls_back_to_heuristic(self) -> None:
        transport = _SequencedTransport([
            RuntimeError("openai_compatible_http_503"),
            RuntimeError("openai_compatible_http_503"),
            RuntimeError("openai_compatible_http_503"),
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=2, backoff=1.0),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        # 1 initial + 2 retries = 3 transport calls
        self.assertEqual(len(transport.calls), 3)
        # Sleeps after attempt 0 (1.0) and after attempt 1 (2.0); not after attempt 2
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertAlmostEqual(mock_sleep.call_args_list[0][0][0], 1.0)
        self.assertAlmostEqual(mock_sleep.call_args_list[1][0][0], 2.0)
        # Fallback path taken — reasoning trace records the reason
        assert response is not None
        reasoning = response.to_dict().get("reasoning_trace") or []
        self.assertTrue(
            any("live_client_fallback:openai_compatible_http_503" in str(r) for r in reasoning),
            f"expected fallback reason in reasoning_trace, got {reasoning}",
        )

    def test_4xx_does_not_retry_falls_back_immediately(self) -> None:
        transport = _SequencedTransport([
            RuntimeError("openai_compatible_http_401_authentication_error"),
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=3, backoff=1.0),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        # 4xx is not retryable; transport called once, no sleep, fallback invoked
        self.assertEqual(len(transport.calls), 1)
        mock_sleep.assert_not_called()
        assert response is not None
        reasoning = response.to_dict().get("reasoning_trace") or []
        self.assertTrue(
            any("openai_compatible_http_401" in str(r) for r in reasoning),
            f"expected 401 in fallback reason, got {reasoning}",
        )

    def test_max_retries_zero_disables_retry(self) -> None:
        transport = _SequencedTransport([
            RuntimeError("openai_compatible_http_503"),
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=0, backoff=1.0),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        # max_retries=0 means single attempt — no retry, no sleep, straight to fallback
        self.assertEqual(len(transport.calls), 1)
        mock_sleep.assert_not_called()
        assert response is not None
        reasoning = response.to_dict().get("reasoning_trace") or []
        self.assertTrue(any("live_client_fallback" in str(r) for r in reasoning))

    def test_transport_unavailable_is_retried(self) -> None:
        transport = _SequencedTransport([
            RuntimeError("openai_compatible_transport_unavailable"),
            _ok_response_payload(),
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=3, backoff=1.0),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(mock_sleep.call_count, 1)
        assert response is not None
        self.assertEqual(response.to_dict()["candidate_suggestions"], ["observe_first"])

    def test_response_parsing_error_falls_back_immediately(self) -> None:
        # Transport returns 200 but with malformed body → parsing raises
        # ``openai_compatible_response_missing_choices`` — not retryable.
        transport = _SequencedTransport([
            {"choices": []},  # empty choices list triggers parsing error
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=3, backoff=1.0),
            transport=transport,
        )
        with patch("time.sleep") as mock_sleep:
            response = client.build_working_memory_advisory(_make_test_request())
        self.assertEqual(len(transport.calls), 1)
        mock_sleep.assert_not_called()
        assert response is not None
        reasoning = response.to_dict().get("reasoning_trace") or []
        self.assertTrue(
            any("openai_compatible_response_missing_choices" in str(r) for r in reasoning),
            f"expected parsing error in fallback reason, got {reasoning}",
        )

    def test_default_fallback_uses_recognizable_provider_label(self) -> None:
        # When no fallback is supplied, the client constructs a heuristic
        # one with provider="openai-compatible-fallback" so audit logs
        # make the fallback path identifiable in the reasoning trace.
        transport = _SequencedTransport([
            RuntimeError("openai_compatible_http_503"),
        ])
        client = OpenAICompatibleWorkingMemoryModelClient(
            _make_config(max_retries=0),
            transport=transport,
        )
        with patch("time.sleep"):
            response = client.build_working_memory_advisory(_make_test_request())
        assert response is not None
        reasoning = response.to_dict().get("reasoning_trace") or []
        self.assertTrue(
            any("openai-compatible-fallback" in str(r) for r in reasoning),
            f"expected fallback provider label in reasoning_trace, got {reasoning}",
        )


if __name__ == "__main__":
    unittest.main()
