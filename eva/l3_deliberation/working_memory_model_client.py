"""Bounded model-client shell for future C-4 working-memory advisory backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

MODEL_CLIENT_MODE_INERT = "inert"
MODEL_CLIENT_MODE_HEURISTIC = "heuristic"


@dataclass(frozen=True)
class WorkingMemoryModelClientConfig:
    """Bounded placeholder config for future model-client implementations."""

    provider: str = "placeholder"
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
    """Protocol for future external or local model-backed advisory providers."""

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
        provider = base_config.provider if base_config.provider != "placeholder" else "heuristic"
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
        elif conservative_mode or top_drive == "integrity":
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


def build_builtin_working_memory_model_client(
    mode: str,
    config: WorkingMemoryModelClientConfig | None = None,
) -> WorkingMemoryModelClient:
    """Build one local model-client placeholder without any external requests."""

    normalized = str(mode or MODEL_CLIENT_MODE_INERT)
    if normalized == MODEL_CLIENT_MODE_HEURISTIC:
        return HeuristicWorkingMemoryModelClient(config)
    return NullWorkingMemoryModelClient()


def _as_dict(value: Any) -> dict[str, Any]:
    """Return one shallow dict view for placeholder request handling."""

    if isinstance(value, dict):
        return value
    return {}
