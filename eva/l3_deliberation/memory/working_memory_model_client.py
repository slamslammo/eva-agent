"""Bounded model-client implementations for working-memory advisory backends."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Protocol
from urllib import error, request

MODEL_CLIENT_MODE_INERT = "inert"
MODEL_CLIENT_MODE_HEURISTIC = "heuristic"
MODEL_CLIENT_MODE_ANTHROPIC = "anthropic"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
ANTHROPIC_API_BASE_URL_ENV = "ANTHROPIC_API_BASE_URL"
DEFAULT_ANTHROPIC_API_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_MESSAGES_API_PATH = "/v1/messages"


def _resolve_anthropic_messages_url() -> str:
    """Resolve the Anthropic Messages API URL, honoring the env override.

    When ``ANTHROPIC_API_BASE_URL`` is set, it replaces the production base
    (``https://api.anthropic.com``). This supports validation runs through
    an enterprise relay / proxy without committing endpoint config. The
    ``/v1/messages`` path is appended unless the env value already targets
    that path explicitly.
    """

    base = os.environ.get(ANTHROPIC_API_BASE_URL_ENV) or DEFAULT_ANTHROPIC_API_BASE_URL
    base = base.rstrip("/")
    if base.endswith(ANTHROPIC_MESSAGES_API_PATH):
        return base
    return base + ANTHROPIC_MESSAGES_API_PATH
ALLOWED_CANDIDATE_SUGGESTIONS = frozenset({"observe_first", "stabilize_first", "escalate_first"})

AnthropicTransport = Callable[[dict[str, Any], str, float], dict[str, Any]]


@dataclass(frozen=True)
class WorkingMemoryModelClientConfig:
    """Bounded config for working-memory advisory model clients."""

    provider: str = "anthropic"
    model: str = DEFAULT_ANTHROPIC_MODEL
    request_timeout_sec: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the client config for local debugging or future transport."""

        return {
            "provider": self.provider,
            "model": self.model,
            "request_timeout_sec": max(0.1, float(self.request_timeout_sec)),
        }


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
        provider = base_config.provider
        if provider in {"placeholder", "anthropic"}:
            provider = "heuristic"
        model = base_config.model
        if model == DEFAULT_ANTHROPIC_MODEL:
            model = "bounded-local-placeholder"
        self.config = WorkingMemoryModelClientConfig(
            provider=provider,
            model=model,
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


class AnthropicWorkingMemoryModelClient:
    """Anthropic-backed bounded advisory client for Stage E working memory."""

    def __init__(
        self,
        config: WorkingMemoryModelClientConfig | None = None,
        *,
        transport: AnthropicTransport | None = None,
    ) -> None:
        base_config = config or WorkingMemoryModelClientConfig(
            provider="anthropic",
            model=DEFAULT_ANTHROPIC_MODEL,
        )
        provider = base_config.provider if base_config.provider not in {"placeholder", "heuristic"} else "anthropic"
        model = str(base_config.model or DEFAULT_ANTHROPIC_MODEL)
        self.config = WorkingMemoryModelClientConfig(
            provider=provider,
            model=model,
            request_timeout_sec=base_config.request_timeout_sec,
        )
        self.transport = transport or _post_anthropic_messages

    def build_working_memory_advisory(
        self,
        request: WorkingMemoryModelClientRequest,
    ) -> WorkingMemoryModelClientResponse | None:
        """Call Anthropic Messages API and return one bounded advisory payload."""

        api_key = os.environ.get(ANTHROPIC_API_KEY_ENV)
        if not api_key:
            raise RuntimeError("anthropic_api_key_missing")
        response_payload = self.transport(
            _anthropic_request_payload(request, model=self.config.model),
            api_key,
            self.config.request_timeout_sec,
        )
        response_text = _anthropic_text_response(response_payload)
        advisory_payload = _extract_advisory_payload(response_text)
        return WorkingMemoryModelClientResponse(payload=advisory_payload)



def build_builtin_working_memory_model_client(
    mode: str,
    config: WorkingMemoryModelClientConfig | None = None,
) -> WorkingMemoryModelClient:
    """Build one built-in working-memory model client."""

    normalized = str(mode or MODEL_CLIENT_MODE_INERT)
    if normalized == MODEL_CLIENT_MODE_HEURISTIC:
        return HeuristicWorkingMemoryModelClient(config)
    if normalized == MODEL_CLIENT_MODE_ANTHROPIC:
        return AnthropicWorkingMemoryModelClient(config)
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



def _anthropic_request_payload(
    request_payload: WorkingMemoryModelClientRequest,
    *,
    model: str,
) -> dict[str, Any]:
    """Build the bounded Anthropic request payload for one advisory turn."""

    prompt = (
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
    return {
        "model": model,
        "max_tokens": 220,
        "temperature": 0,
        "system": (
            "You are a bounded EVA working-memory advisory model. "
            "You are not allowed to release actions, choose external side effects, or invent new action domains. "
            "Respond with JSON only."
        ),
        "messages": [{"role": "user", "content": prompt}],
    }



def _post_anthropic_messages(payload: dict[str, Any], api_key: str, timeout_sec: float) -> dict[str, Any]:
    """Post one Anthropic Messages request through the stdlib HTTP client."""

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        _resolve_anthropic_messages_url(),
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=max(0.1, float(timeout_sec))) as response:
            raw_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise RuntimeError(_anthropic_http_error_label(exc)) from exc
    except error.URLError as exc:
        raise RuntimeError("anthropic_transport_unavailable") from exc
    payload_dict = json.loads(raw_body)
    if not isinstance(payload_dict, dict):
        raise RuntimeError("anthropic_response_not_object")
    return payload_dict



def _anthropic_http_error_label(exc: error.HTTPError) -> str:
    """Return a compact, audit-safe HTTP error label."""

    try:
        body = exc.read().decode("utf-8", errors="ignore")
        payload = json.loads(body)
    except Exception:
        payload = {}
    error_payload = payload.get("error") if isinstance(payload, dict) else {}
    if isinstance(error_payload, dict):
        error_type = str(error_payload.get("type") or "").strip()
        if error_type:
            return f"anthropic_http_{exc.code}_{error_type}"
    return f"anthropic_http_{exc.code}"



def _anthropic_text_response(payload: dict[str, Any]) -> str:
    """Extract the concatenated text response from one Anthropic payload."""

    content = payload.get("content")
    if not isinstance(content, list):
        raise RuntimeError("anthropic_response_missing_content")
    text_blocks = [
        str(block.get("text") or "")
        for block in content
        if isinstance(block, dict) and str(block.get("type") or "") == "text"
    ]
    response_text = "\n".join(block for block in text_blocks if block)
    if not response_text:
        raise RuntimeError("anthropic_response_missing_text")
    return response_text



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
    raise RuntimeError("anthropic_response_not_json")



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
