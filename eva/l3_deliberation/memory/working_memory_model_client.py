"""Bounded model-client implementations for working-memory advisory backends."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib import error, request

MODEL_CLIENT_MODE_INERT = "inert"
MODEL_CLIENT_MODE_HEURISTIC = "heuristic"
# Vendor-neutral live mode — speaks OpenAI Chat Completions against any
# base_url resolved from env. Vendor-private body fields travel opaquely
# through EVA_LLM_EXTRA_PARAMS_JSON. Round 1.7-c removed the legacy
# anthropic / deepseek mode strings; the live mode now covers any
# OpenAI-compatible endpoint (DeepSeek, OpenAI, Moonshot, Qwen, Ollama,
# vLLM, OpenRouter, Together, ...). Re-introducing Anthropic native
# Messages API would be a separate, deliberate slice.
MODEL_CLIENT_MODE_LIVE = "live"
EVA_LLM_API_BASE_URL_ENV = "EVA_LLM_API_BASE_URL"
EVA_LLM_API_KEY_ENV = "EVA_LLM_API_KEY"
EVA_LLM_MODEL_ENV = "EVA_LLM_MODEL"
EVA_LLM_EXTRA_PARAMS_JSON_ENV = "EVA_LLM_EXTRA_PARAMS_JSON"
OPENAI_COMPATIBLE_CHAT_COMPLETIONS_PATH = "/chat/completions"
ALLOWED_CANDIDATE_SUGGESTIONS = frozenset({"observe_first", "stabilize_first", "escalate_first"})

# Transport signature for the OpenAI-compatible live client.
# Takes ``(payload, api_key, timeout_sec, base_url)`` — base_url is per-client
# so the same transport function serves any OpenAI-compatible endpoint.
OpenAICompatibleTransport = Callable[[dict[str, Any], str, float, str], dict[str, Any]]


@dataclass(frozen=True)
class WorkingMemoryModelClientConfig:
    """Bounded config for working-memory advisory model clients.

    Provider / model fields are used by the heuristic client for its
    reasoning trace and for ``request_timeout_sec`` passthrough into the
    live client. The live client otherwise reads its real model name and
    base URL from ``EVA_LLM_*`` env vars at construction time.
    """

    provider: str = "heuristic"
    model: str = "bounded-local-placeholder"
    request_timeout_sec: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the client config for local debugging or future transport."""

        return {
            "provider": self.provider,
            "model": self.model,
            "request_timeout_sec": max(0.1, float(self.request_timeout_sec)),
        }


@dataclass(frozen=True)
class OpenAICompatibleWorkingMemoryModelClientConfig:
    """Resolved config for one OpenAI Chat Completions endpoint.

    Built by ``_load_live_config_from_env`` from ``EVA_LLM_*`` environment
    variables; the framework knows nothing about which vendor backs the
    base_url. Vendor-private body fields (e.g. DeepSeek ``thinking.disabled``)
    travel opaquely through ``extra_params``.

    Round 1.7-a: ``max_retries`` and ``retry_backoff_base_sec`` fields are
    declared now for forward stability; the actual retry wrapper is added
    in 1.7-b. Defaults (``max_retries=0``) keep 1.7-a single-shot.
    """

    base_url: str
    api_key: str
    model: str
    extra_params: dict[str, Any]
    timeout_sec: float = 5.0
    max_retries: int = 0
    retry_backoff_base_sec: float = 1.0


@dataclass(frozen=True)
class WorkingMemoryModelClientRequest:
    """Structured bounded payload sent from the adapter shell to a model client."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the request payload for transport or debugging."""

        return dict(self.payload)


@dataclass(frozen=True)
class WorkingMemoryModelClientResponse:
    """Structured bounded payload returned by a model client shell."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the response payload for adapter-side normalization."""

        return dict(self.payload)


class WorkingMemoryModelClient(Protocol):
    """Protocol for external or local model-backed advisory providers."""

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None:
        """Return a bounded advisory payload without any release authority."""


class NullWorkingMemoryModelClient:
    """Default inert client shell that never emits advisory payload."""

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None:
        """Return no advisory payload while keeping the model-client seam explicit."""

        del request
        return None


class HeuristicWorkingMemoryModelClient:
    """Local placeholder client that emits bounded advisory payload without external calls."""

    def __init__(self, config: WorkingMemoryModelClientConfig | None = None) -> None:
        base_config = config or WorkingMemoryModelClientConfig(
            provider="heuristic",
            model="bounded-local-placeholder",
        )
        # Normalize legacy / placeholder provider labels onto "heuristic" so
        # audit logs are consistent regardless of how the config was built.
        provider = base_config.provider
        if provider in {"placeholder", "anthropic", "deepseek"}:
            provider = "heuristic"
        self.config = WorkingMemoryModelClientConfig(
            provider=provider,
            model=base_config.model,
            request_timeout_sec=base_config.request_timeout_sec,
        )

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None:
        """Return a bounded placeholder payload from the local request surface only."""

        payload = request.to_dict()
        drive_broadcast = _as_dict(payload.get("drive_broadcast"))
        runtime_gate_context = _as_dict(payload.get("runtime_gate_context"))
        top_drive = str(drive_broadcast.get("top_drive") or "unknown")
        drive_levels = drive_broadcast.get("drive_levels")
        top_drive_level = _coerce_drive_level((drive_levels or {}).get(top_drive))
        turn_allowed = bool(runtime_gate_context.get("turn_allowed", False))
        conservative_mode = bool(runtime_gate_context.get("conservative_mode", False))
        local_confidence = max(0.0, min(1.0, float(payload.get("local_confidence", 0.0))))

        candidate_suggestions: list[str] = []
        prediction_hints: list[str] = []
        reasoning_trace = [
            f"model_client_provider_{self.config.provider}",
            f"model_client_{self.config.model}",
        ]

        if not turn_allowed:
            prediction_hints.append("client_turn_blocked_no_release")
            reasoning_trace.append("model_client_turn_blocked")
        elif conservative_mode or top_drive_level >= _HIGH_DRIVE_CLIENT_THRESHOLD:
            # Round 1.B-1-d: was ``top_drive == "integrity"`` — scenario-neutral
            # generalization. Conservative mode keeps the OR semantic from the
            # prior code.
            candidate_suggestions.append("stabilize_first")
            prediction_hints.append("client_prefers_stabilize_first")
            reasoning_trace.append("model_client_prefers_stabilization")
        else:
            candidate_suggestions.append("observe_first")
            prediction_hints.append("client_prefers_observation")
            reasoning_trace.append(f"model_client_top_drive_{top_drive}")

        confidence = max(0.25, min(0.75, local_confidence + 0.1))
        return WorkingMemoryModelClientResponse(
            payload={
                "candidate_suggestions": candidate_suggestions,
                "prediction_hints": prediction_hints,
                "reasoning_trace": reasoning_trace,
                "confidence": round(confidence, 3),
            }
        )


class OpenAICompatibleWorkingMemoryModelClient:
    """OpenAI Chat Completions advisory client driven by env-resolved config.

    Vendor-neutral: speaks the OpenAI Chat Completions protocol against any
    base URL provided via ``EVA_LLM_API_BASE_URL`` (DeepSeek, OpenAI,
    Moonshot, Qwen, Ollama, vLLM, OpenRouter, ...). Vendor-private body
    fields travel opaquely through
    ``OpenAICompatibleWorkingMemoryModelClientConfig.extra_params`` —
    the framework does not validate, interpret, or rewrite those fields.

    Round 1.7-b adds transparent retry with exponential backoff for
    transient transport errors (HTTP 5xx, transport_unavailable) and a
    fallback to ``HeuristicWorkingMemoryModelClient`` on exhaustion or
    non-retryable failure. Long-run scenarios must not crash on a flaky
    upstream; the fallback keeps advisory available with degraded quality.
    """

    def __init__(
        self,
        config: OpenAICompatibleWorkingMemoryModelClientConfig,
        *,
        fallback: WorkingMemoryModelClient | None = None,
        transport: OpenAICompatibleTransport | None = None,
    ) -> None:
        self.config = config
        # Round 1.7-b: when no fallback is supplied, construct a heuristic
        # one with a recognizable provider label so audit logs make the
        # fallback path visible in ``reasoning_trace``.
        if fallback is None:
            fallback = HeuristicWorkingMemoryModelClient(
                WorkingMemoryModelClientConfig(
                    provider="openai-compatible-fallback",
                    model=config.model,
                    request_timeout_sec=config.timeout_sec,
                )
            )
        self.fallback = fallback
        self.transport = transport or _post_openai_compatible_chat

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None:
        """Call the configured endpoint with retry + fallback discipline.

        Retry path: HTTP 5xx and ``openai_compatible_transport_unavailable``
        are retried up to ``config.max_retries`` times with exponential
        backoff (``retry_backoff_base_sec * 2**attempt``).

        Fallback path: on retry exhaustion or any non-retryable error
        (4xx, response-parsing errors), delegate to ``self.fallback``.
        The fallback reason is appended to the response's
        ``reasoning_trace`` so the audit log records the degraded path.
        """

        last_error_label = "unknown"
        for attempt in range(self.config.max_retries + 1):
            try:
                response_payload = self.transport(
                    _openai_compatible_request_payload(
                        request,
                        model=self.config.model,
                        extra_params=self.config.extra_params,
                    ),
                    self.config.api_key,
                    self.config.timeout_sec,
                    self.config.base_url,
                )
                response_text = _openai_compatible_text_response(response_payload)
                advisory_payload = _extract_advisory_payload(response_text)
                return WorkingMemoryModelClientResponse(payload=advisory_payload)
            except RuntimeError as exc:
                last_error_label = str(exc)
                if not _is_retryable_openai_compatible_error(last_error_label):
                    # Non-retryable (4xx / response-parsing / config). Skip
                    # remaining attempts; go straight to fallback.
                    break
                if attempt < self.config.max_retries:
                    time.sleep(
                        max(0.0, self.config.retry_backoff_base_sec * (2 ** attempt))
                    )
                # Otherwise: this was the last attempt; the for-loop will
                # exit naturally and fall through to the fallback below.

        fallback_response = self.fallback.build_working_memory_advisory(request)
        return _attach_fallback_reason(fallback_response, last_error_label)



def build_builtin_working_memory_model_client(
    mode: str,
    config: WorkingMemoryModelClientConfig | None = None,
) -> WorkingMemoryModelClient:
    """Build one built-in working-memory model client.

    Three modes are supported:
    - ``inert`` — never emits advisory (default; safe for any deployment)
    - ``heuristic`` — local rule-based client; no external calls
    - ``live`` — OpenAI Chat Completions client driven by ``EVA_LLM_*`` env
      vars; retries on 5xx / transport errors, falls back to heuristic on
      exhaustion. Vendor identity (DeepSeek / OpenAI / Moonshot / Ollama
      / etc.) is determined entirely by the configured ``base_url``.
    """

    normalized = str(mode or MODEL_CLIENT_MODE_INERT)
    if normalized == MODEL_CLIENT_MODE_HEURISTIC:
        return HeuristicWorkingMemoryModelClient(config)
    if normalized == MODEL_CLIENT_MODE_LIVE:
        return OpenAICompatibleWorkingMemoryModelClient(
            _load_live_config_from_env(config),
        )
    return NullWorkingMemoryModelClient()


# Round 1.B-1-d: scenario-neutral routing threshold. Mirrors
# ``HIGH_DRIVE_PROJECTION_THRESHOLD`` in conflict_detection — kept local to
# avoid cross-module coupling.
_HIGH_DRIVE_CLIENT_THRESHOLD = 0.5


def _coerce_drive_level(value: Any) -> float:
    """Clamp a drive-level payload value to [0.0, 1.0]; non-numeric -> 0.0."""

    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0



def _extract_advisory_payload(response_text: str) -> dict[str, Any]:
    """Extract one bounded JSON advisory payload from a model text response."""

    stripped = response_text.strip()
    for candidate_text in (_json_code_block(stripped), stripped, _json_object_window(stripped)):
        if not candidate_text:
            continue
        try:
            payload = json.loads(candidate_text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return _sanitize_advisory_payload(payload)
    raise RuntimeError("openai_compatible_response_not_json")



def _json_code_block(text: str) -> str | None:
    """Return the contents of a fenced JSON block when present."""

    fence = "```json"
    if fence not in text:
        return None
    _, _, tail = text.partition(fence)
    block, _, _ = tail.partition("```")
    stripped = block.strip()
    return stripped or None



def _json_object_window(text: str) -> str | None:
    """Return the first outermost JSON object window from free text."""

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]



def _sanitize_advisory_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only bounded advisory fields from one raw model payload."""

    advisory_payload: dict[str, Any] = {}
    candidate_suggestions = _sanitize_candidate_suggestions(payload.get("candidate_suggestions"))
    if candidate_suggestions:
        advisory_payload["candidate_suggestions"] = candidate_suggestions
    prediction_hints = _sanitize_string_list(payload.get("prediction_hints"))
    if prediction_hints:
        advisory_payload["prediction_hints"] = prediction_hints
    reasoning_trace = _sanitize_string_list(payload.get("reasoning_trace"))
    if reasoning_trace:
        advisory_payload["reasoning_trace"] = reasoning_trace
    if "confidence" in payload:
        advisory_payload["confidence"] = round(max(0.0, min(1.0, float(payload.get("confidence", 0.0)))), 3)
    return advisory_payload



def _sanitize_candidate_suggestions(values: Any) -> list[str]:
    """Return only admitted candidate-profile suggestions from one payload."""

    return [value for value in _sanitize_string_list(values) if value in ALLOWED_CANDIDATE_SUGGESTIONS]



def _sanitize_string_list(values: Any) -> list[str]:
    """Return only non-empty string entries from one advisory field."""

    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and value]



def _as_dict(value: Any) -> dict[str, Any]:
    """Return one shallow dict view for placeholder request handling."""

    if isinstance(value, dict):
        return value
    return {}


# ---------------------------------------------------------------------------
# OpenAI-compatible live client helpers — the only HTTP / payload / response
# code path in the module after Round 1.7-c removed the legacy Anthropic /
# DeepSeek vendor helpers.
# ---------------------------------------------------------------------------


def _load_live_config_from_env(
    config: WorkingMemoryModelClientConfig | None,
) -> OpenAICompatibleWorkingMemoryModelClientConfig:
    """Resolve ``OpenAICompatibleWorkingMemoryModelClientConfig`` from env vars.

    Required env: ``EVA_LLM_API_BASE_URL``, ``EVA_LLM_API_KEY``, ``EVA_LLM_MODEL``.
    Optional env: ``EVA_LLM_EXTRA_PARAMS_JSON`` (JSON object merged into the
    request body — carries vendor-private fields opaquely).

    ``timeout_sec`` is sourced from the passed ``WorkingMemoryModelClientConfig``
    (i.e. the ``--working-memory-model-client-timeout-sec`` CLI flag) so the
    runtime configuration plumbing remains consistent with the legacy vendor
    modes.

    Fail-fast on missing or invalid values — silently falling back to a
    heuristic client would mask config errors in long-run scenarios.
    """

    base_url = os.environ.get(EVA_LLM_API_BASE_URL_ENV)
    if not base_url:
        raise RuntimeError(f"eva_llm_env_missing:{EVA_LLM_API_BASE_URL_ENV}")
    api_key = os.environ.get(EVA_LLM_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"eva_llm_env_missing:{EVA_LLM_API_KEY_ENV}")
    model = os.environ.get(EVA_LLM_MODEL_ENV)
    if not model:
        raise RuntimeError(f"eva_llm_env_missing:{EVA_LLM_MODEL_ENV}")

    extra_params_raw = os.environ.get(EVA_LLM_EXTRA_PARAMS_JSON_ENV)
    if extra_params_raw is None or extra_params_raw.strip() == "":
        extra_params: dict[str, Any] = {}
    else:
        try:
            parsed = json.loads(extra_params_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("eva_llm_extra_params_json_invalid:not_json") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("eva_llm_extra_params_json_invalid:not_object")
        extra_params = parsed

    timeout_sec = 5.0
    if config is not None:
        timeout_sec = max(0.1, float(config.request_timeout_sec))

    return OpenAICompatibleWorkingMemoryModelClientConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
        extra_params=extra_params,
        timeout_sec=timeout_sec,
        # Round 1.7-b: default to 3 retries with 1s base backoff (sleeps
        # 1s, 2s, 4s between attempts) for transient HTTP 5xx / transport
        # errors. Sub-second timeouts on the long-run path can override
        # these by constructing the config directly.
        max_retries=3,
        retry_backoff_base_sec=1.0,
    )


def _resolve_openai_compatible_chat_url(base_url: str) -> str:
    """Resolve the chat-completions URL from a base URL.

    The base URL is expected to include the API version segment (e.g. ``/v1``);
    only ``/chat/completions`` is appended. Trailing slash on the base URL is
    tolerated. If the base URL already ends with ``/chat/completions``
    (some relays expose it that way), no path is appended.
    """

    base = base_url.rstrip("/")
    if base.endswith(OPENAI_COMPATIBLE_CHAT_COMPLETIONS_PATH):
        return base
    return base + OPENAI_COMPATIBLE_CHAT_COMPLETIONS_PATH


def _openai_compatible_request_payload(
    request_payload: WorkingMemoryModelClientRequest,
    *,
    model: str,
    extra_params: dict[str, Any],
) -> dict[str, Any]:
    """Build the OpenAI-compatible chat-completions request body.

    Standard shape: system + user message, bounded token cap, deterministic
    temperature. Any vendor-private fields from ``extra_params`` are merged
    into the body — the framework has no understanding of what those fields
    mean (e.g. DeepSeek ``thinking.disabled``); they pass through opaquely.
    """

    user_prompt = (
        "Return only a JSON object with these optional keys: "
        "candidate_suggestions, prediction_hints, reasoning_trace, confidence. "
        "candidate_suggestions, if present, must contain only these strings: "
        '"observe_first", "stabilize_first", "escalate_first". '
        "Do not propose actions outside those candidate profiles. "
        "prediction_hints and reasoning_trace must be short string lists. "
        "confidence must be a number between 0 and 1. "
        "If uncertain, return empty lists and a low confidence. "
        "Request payload:\n"
        f"{json.dumps(request_payload.to_dict(), ensure_ascii=False, sort_keys=True)}"
    )
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": 220,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a bounded EVA working-memory advisory model. "
                    "You are not allowed to release actions, choose external side effects, or invent new action domains. "
                    "Respond with JSON only."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
    }
    # Merge extra_params LAST. The framework does not validate which keys are
    # passed through — that is intentional. Callers who configure an
    # invalid extra-params shape get the backend's error verbatim.
    if extra_params:
        body.update(extra_params)
    return body


def _openai_compatible_text_response(payload: dict[str, Any]) -> str:
    """Extract assistant content from an OpenAI-compatible response payload.

    Handles both ``choices[0].message.content`` shapes:
    - plain string (the common case)
    - list of ``{"type": "text", "text": ...}`` blocks (some OpenAI-compatible
      proxies emit this richer shape).

    Error labels use the ``openai_compatible_*`` prefix to keep framework
    logs vendor-neutral.
    """

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("openai_compatible_response_missing_choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise RuntimeError("openai_compatible_response_missing_message")
    content = message.get("content")
    if isinstance(content, str):
        if not content.strip():
            raise RuntimeError("openai_compatible_response_empty_content")
        return content
    if isinstance(content, list):
        parts = [
            str(block.get("text") or "")
            for block in content
            if isinstance(block, dict) and str(block.get("type") or "") in {"text", ""}
        ]
        joined = "\n".join(p for p in parts if p)
        if joined:
            return joined
    raise RuntimeError("openai_compatible_response_missing_content")


def _post_openai_compatible_chat(
    payload: dict[str, Any],
    api_key: str,
    timeout_sec: float,
    base_url: str,
) -> dict[str, Any]:
    """Post one OpenAI-compatible chat-completions request via stdlib HTTP.

    ``base_url`` should already include the API version segment (e.g. ``/v1``);
    ``/chat/completions`` is appended. Auth uses Bearer header — the de facto
    standard for OpenAI-compatible endpoints (DeepSeek, OpenAI, Moonshot,
    Qwen, Together, Fireworks, Ollama, vLLM, OpenRouter).
    """

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        _resolve_openai_compatible_chat_url(base_url),
        data=body,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=max(0.1, float(timeout_sec))) as response:
            raw_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise RuntimeError(_openai_compatible_http_error_label(exc)) from exc
    except error.URLError as exc:
        raise RuntimeError("openai_compatible_transport_unavailable") from exc
    payload_dict = json.loads(raw_body)
    if not isinstance(payload_dict, dict):
        raise RuntimeError("openai_compatible_response_not_object")
    return payload_dict


def _openai_compatible_http_error_label(exc: error.HTTPError) -> str:
    """Return a compact, audit-safe OpenAI-compatible HTTP error label."""

    try:
        body = exc.read().decode("utf-8", errors="ignore")
        payload = json.loads(body)
    except Exception:
        payload = {}
    error_payload = payload.get("error") if isinstance(payload, dict) else {}
    if isinstance(error_payload, dict):
        error_type = str(error_payload.get("type") or error_payload.get("code") or "").strip()
        if error_type:
            return f"openai_compatible_http_{exc.code}_{error_type}"
    return f"openai_compatible_http_{exc.code}"


def _is_retryable_openai_compatible_error(label: str) -> bool:
    """Return True iff the error label denotes a transient failure worth retrying.

    Retryable:
    - ``openai_compatible_http_5*`` — server error, often transient
    - ``openai_compatible_transport_unavailable`` — URLError (connection refused,
      DNS failure, etc.)

    Not retryable (fall back immediately):
    - HTTP 4xx — config / auth / quota errors that won't fix on retry
    - Response-parsing errors (``openai_compatible_response_*``) — the backend
      returned 200 but the payload was malformed; retrying yields the same
      malformed payload
    """

    if label == "openai_compatible_transport_unavailable":
        return True
    if label.startswith("openai_compatible_http_5"):
        return True
    return False


def _attach_fallback_reason(
    response: WorkingMemoryModelClientResponse | None,
    reason: str,
) -> WorkingMemoryModelClientResponse | None:
    """Append a fallback-reason marker to the response's ``reasoning_trace``.

    Audit visibility: when the live client falls back to the heuristic, the
    reason (last error label) is recorded so post-run analysis can
    distinguish "agent advisory was bounded heuristic by design" from
    "agent advisory was bounded heuristic because the upstream API failed".
    """

    if response is None:
        return None
    payload = response.to_dict()
    reasoning = list(payload.get("reasoning_trace") or [])
    reasoning.append(f"live_client_fallback:{reason}")
    payload["reasoning_trace"] = reasoning
    return WorkingMemoryModelClientResponse(payload=payload)
