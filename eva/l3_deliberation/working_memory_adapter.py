"""Bounded Phase C-4 working-memory adapter protocol and placeholder implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .working_memory_model_client import (
    MODEL_CLIENT_MODE_INERT,
    WorkingMemoryModelClient,
    WorkingMemoryModelClientConfig,
    WorkingMemoryModelClientRequest,
    build_builtin_working_memory_model_client,
)

ADAPTER_MODE_INERT = "inert"
ADAPTER_MODE_HEURISTIC = "heuristic"


@dataclass(frozen=True)
class WorkingMemoryAdapterRequest:
    """Structured advisory request sent to the optional C-4 adapter."""

    situation_key: str
    drive_broadcast: dict[str, Any]
    runtime_gate_context: dict[str, Any]
    bias_summaries: list[dict[str, Any]] = field(default_factory=list)
    habit_skills: list[dict[str, Any]] = field(default_factory=list)
    recent_relevant_outcomes: list[dict[str, Any]] = field(default_factory=list)
    local_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the adapter request for debugging or transport boundaries."""

        return {
            "situation_key": self.situation_key,
            "drive_broadcast": dict(self.drive_broadcast),
            "runtime_gate_context": dict(self.runtime_gate_context),
            "bias_summaries": [dict(summary) for summary in self.bias_summaries],
            "habit_skills": [dict(skill) for skill in self.habit_skills],
            "recent_relevant_outcomes": [dict(outcome) for outcome in self.recent_relevant_outcomes],
            "local_confidence": round(max(0.0, min(1.0, float(self.local_confidence))), 3),
        }


@dataclass(frozen=True)
class WorkingMemoryAdapterResponse:
    """Bounded advisory-only response returned by the optional C-4 adapter."""

    candidate_suggestions: tuple[str, ...] = ()
    prediction_hints: tuple[str, ...] = ()
    reasoning_trace: tuple[str, ...] = ()
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the bounded advisory response."""

        advisory_context: dict[str, Any] = {}
        candidate_suggestions = _sanitize_string_sequence(self.candidate_suggestions)
        if candidate_suggestions:
            advisory_context["candidate_suggestions"] = candidate_suggestions
        prediction_hints = _sanitize_string_sequence(self.prediction_hints)
        if prediction_hints:
            advisory_context["prediction_hints"] = prediction_hints
        reasoning_trace = _sanitize_string_sequence(self.reasoning_trace)
        if reasoning_trace:
            advisory_context["reasoning_trace"] = reasoning_trace
        if self.confidence is not None:
            advisory_context["confidence"] = round(max(0.0, min(1.0, float(self.confidence))), 3)
        return advisory_context


class WorkingMemoryAdapter(Protocol):
    """Protocol for optional C-4 advisory builders."""

    def build_advisory_context(self, request: WorkingMemoryAdapterRequest) -> WorkingMemoryAdapterResponse | None:
        """Return bounded advisory-only context for one working-memory assembly."""


class NullWorkingMemoryAdapter:
    """Placeholder adapter that keeps the C-4 seam explicit but behaviorally inert."""

    def build_advisory_context(self, request: WorkingMemoryAdapterRequest) -> WorkingMemoryAdapterResponse | None:
        """Return no advisory payload while preserving the formal adapter seam."""

        del request
        return None


class HeuristicWorkingMemoryAdapter:
    """Local bounded placeholder that emits advisory hints without any external model call."""

    def build_advisory_context(self, request: WorkingMemoryAdapterRequest) -> WorkingMemoryAdapterResponse | None:
        """Return simple advisory hints from the local request surface only."""

        top_drive = str(request.drive_broadcast.get("top_drive") or "unknown")
        turn_allowed = bool(request.runtime_gate_context.get("turn_allowed", False))
        conservative_mode = bool(request.runtime_gate_context.get("conservative_mode", False))
        candidate_suggestions: list[str] = []
        prediction_hints: list[str] = []
        reasoning_trace: list[str] = []

        if not turn_allowed:
            prediction_hints.append("turn_blocked_no_release")
            reasoning_trace.append("runtime_gate_turn_blocked")
        elif conservative_mode:
            candidate_suggestions.append("stabilize_first")
            prediction_hints.append("prefer_conservative_compatibility_path")
            reasoning_trace.append("conservative_mode_active")
        elif top_drive == "integrity":
            candidate_suggestions.append("stabilize_first")
            prediction_hints.append("integrity_pressure_prefers_stabilization")
            reasoning_trace.append("top_drive_integrity")
        else:
            candidate_suggestions.append("observe_first")
            prediction_hints.append("low_constraint_context_prefers_observation")
            reasoning_trace.append(f"top_drive_{top_drive}")

        if request.habit_skills:
            reasoning_trace.append("habit_skills_present")
        if request.bias_summaries:
            reasoning_trace.append("bias_summaries_present")
        if request.recent_relevant_outcomes:
            reasoning_trace.append("recent_outcomes_present")

        confidence = max(0.2, min(0.7, request.local_confidence + 0.1))
        return WorkingMemoryAdapterResponse(
            candidate_suggestions=tuple(candidate_suggestions),
            prediction_hints=tuple(prediction_hints),
            reasoning_trace=tuple(reasoning_trace),
            confidence=confidence,
        )


class ClientBackedWorkingMemoryAdapter:
    """Adapter shell that delegates bounded advisory generation to a model-client seam."""

    def __init__(
        self,
        client: WorkingMemoryModelClient | None = None,
        *,
        client_mode: str = MODEL_CLIENT_MODE_INERT,
        client_config: WorkingMemoryModelClientConfig | None = None,
    ) -> None:
        if client is not None:
            self.client = client
        else:
            self.client = build_builtin_working_memory_model_client(client_mode, client_config)

    def build_advisory_context(self, request: WorkingMemoryAdapterRequest) -> WorkingMemoryAdapterResponse | None:
        """Build advisory context through the model-client shell and normalize the result."""

        client_response = self.client.build_working_memory_advisory(
            WorkingMemoryModelClientRequest(payload=request.to_dict())
        )
        if client_response is None:
            return None
        payload = client_response.to_dict()
        return WorkingMemoryAdapterResponse(
            candidate_suggestions=tuple(_sanitize_string_sequence(payload.get("candidate_suggestions"))),
            prediction_hints=tuple(_sanitize_string_sequence(payload.get("prediction_hints"))),
            reasoning_trace=tuple(_sanitize_string_sequence(payload.get("reasoning_trace"))),
            confidence=_sanitize_optional_confidence(payload.get("confidence")),
        )


def build_builtin_working_memory_adapter(mode: str) -> WorkingMemoryAdapter:
    """Build one built-in placeholder adapter mode without external dependencies."""

    normalized = str(mode or ADAPTER_MODE_INERT)
    if normalized == ADAPTER_MODE_HEURISTIC:
        return HeuristicWorkingMemoryAdapter()
    return NullWorkingMemoryAdapter()


def _sanitize_optional_confidence(value: Any) -> float | None:
    """Return one bounded optional confidence value."""

    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def _sanitize_string_sequence(values: Any) -> list[str]:
    """Return only non-empty string entries from one advisory sequence."""

    if not isinstance(values, (list, tuple)):
        return []
    return [value for value in values if isinstance(value, str) and value]
