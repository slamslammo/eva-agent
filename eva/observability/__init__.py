"""Observability surfaces (opt-in cognitive telemetry for offline viz replay)."""

from .trace_sink import (
    CONTINUITY_ALIVE,
    CONTINUITY_INHERITED,
    CONTINUITY_NEW_INDIVIDUAL,
    CONTINUITY_TERMINATED,
    TRACE_ENV_FLAG,
    JsonlTraceSink,
    NullTraceSink,
    RunIdentity,
    TraceSink,
    build_trace_sink,
    current_trace_sink,
    current_trace_turn_index,
    reset_current_trace,
    set_current_trace,
    trace_enabled,
    write_run_meta,
)

__all__ = [
    "CONTINUITY_ALIVE",
    "CONTINUITY_INHERITED",
    "CONTINUITY_NEW_INDIVIDUAL",
    "CONTINUITY_TERMINATED",
    "TRACE_ENV_FLAG",
    "JsonlTraceSink",
    "NullTraceSink",
    "RunIdentity",
    "TraceSink",
    "build_trace_sink",
    "current_trace_sink",
    "current_trace_turn_index",
    "reset_current_trace",
    "set_current_trace",
    "trace_enabled",
    "write_run_meta",
]
