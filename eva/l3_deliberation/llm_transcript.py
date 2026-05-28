"""LLM transcript instrumentation (PR-Α).

Records LLM call payloads (messages, raw response, parsed response, metadata)
to disk for analysis. The sink is driven by ``EVA_LLM_TRANSCRIPT`` env var
(``off`` / ``redacted`` / ``raw``); ``off`` (default) uses a no-op sink with
zero overhead.

Red lines (plan §9 + §4.5):
- ``off`` mode must be zero-overhead (no string concat, no io)
- Write failures must NOT propagate — sink swallows + returns ``None``
- Sink is decoupled from anchor / dlPFC reasoning / OFC scoring logic
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol

__all__ = [
    "ENV_VAR",
    "FileBasedTranscriptSink",
    "LLMTranscriptSink",
    "NoOpTranscriptSink",
    "SCHEMA_VERSION",
    "TranscriptMode",
    "build_transcript_sink_from_env",
]

TranscriptMode = Literal["off", "redacted", "raw"]
ENV_VAR = "EVA_LLM_TRANSCRIPT"
SCHEMA_VERSION = "llm_transcript_v1"

_TRANSCRIPT_SUBDIR = "llm_transcripts"

_logger = logging.getLogger(__name__)


class LLMTranscriptSink(Protocol):
    """Protocol for recording an LLM call's full transcript.

    Returns a reference string (relative path or id) on success, or ``None``
    when the sink is no-op or recording failed silently.
    """

    def record(
        self,
        *,
        run_id: str,
        individual_id: str,
        turn_index: int,
        llm_role: str,
        scenario: str,
        model: str,
        messages: list[dict[str, str]],
        raw_response: str,
        parsed_response: dict[str, Any] | None,
        parse_status: Literal["ok", "parse_error", "transport_error"],
        errors: list[str],
        prompt_sections_present: dict[str, bool],
    ) -> str | None: ...


class NoOpTranscriptSink:
    """``off`` mode sink: returns ``None`` immediately, no work."""

    def record(self, **_kwargs: Any) -> None:
        return None


class FileBasedTranscriptSink:
    """``raw`` / ``redacted`` mode sink.

    Writes ``{runtime_dir}/llm_transcripts/{llm_role}/turn-{index:06d}.json``
    in schema ``llm_transcript_v1``. Returns the relative path on success.

    Write failures (permission, disk full, parent-is-file) are logged and
    swallowed; sink returns ``None`` so the deliberation loop is never broken.
    """

    def __init__(self, *, runtime_dir: str | os.PathLike[str], mode: TranscriptMode) -> None:
        self._runtime_dir = Path(runtime_dir)
        self._mode: TranscriptMode = mode

    def record(
        self,
        *,
        run_id: str,
        individual_id: str,
        turn_index: int,
        llm_role: str,
        scenario: str,
        model: str,
        messages: list[dict[str, str]],
        raw_response: str,
        parsed_response: dict[str, Any] | None,
        parse_status: Literal["ok", "parse_error", "transport_error"],
        errors: list[str],
        prompt_sections_present: dict[str, bool],
    ) -> str | None:
        try:
            relative_path = (
                f"{_TRANSCRIPT_SUBDIR}/{llm_role}/turn-{int(turn_index):06d}.json"
            )
            absolute_path = self._runtime_dir / relative_path
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "individual_id": individual_id,
                "turn_index": int(turn_index),
                "llm_role": llm_role,
                "scenario": scenario,
                "model": model,
                "messages": list(messages),
                "raw_response": raw_response,
                "parsed_response": parsed_response,
                "parse_status": parse_status,
                "errors": list(errors),
                "prompt_sections_present": dict(prompt_sections_present),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            absolute_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return relative_path
        except Exception as exc:  # noqa: BLE001 — R3: swallow all errors
            _logger.warning(
                "llm_transcript_write_failed run_id=%s turn=%s role=%s err=%s",
                run_id, turn_index, llm_role, exc,
            )
            return None


def build_transcript_sink_from_env(runtime_dir: str | os.PathLike[str]) -> LLMTranscriptSink:
    """Construct the appropriate sink from ``EVA_LLM_TRANSCRIPT`` env var.

    ``off`` (or unset) → ``NoOpTranscriptSink`` (zero overhead).
    ``raw`` / ``redacted`` → ``FileBasedTranscriptSink``.
    Any other value defaults to ``NoOpTranscriptSink`` (safe default).
    """

    mode = os.environ.get(ENV_VAR, "off").strip().lower()
    if mode in ("raw", "redacted"):
        return FileBasedTranscriptSink(runtime_dir=runtime_dir, mode=mode)  # type: ignore[arg-type]
    return NoOpTranscriptSink()
