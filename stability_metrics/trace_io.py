"""Trace-file readers for architecture-neutral stability metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRACE_FILES = (
    "deliberation_audit.jsonl",
    "learning_outcomes.jsonl",
    "habit_bias.jsonl",
    "response_history.jsonl",
    "events.jsonl",
    "llm_advisory_audit.jsonl",
)


def load_trace_bundle(runtime_dir: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Load all supported trace files that exist in one runtime directory."""

    root = Path(runtime_dir)
    bundle: dict[str, list[dict[str, Any]]] = {}
    for file_name in TRACE_FILES:
        path = root / file_name
        if path.exists():
            bundle[file_name] = _read_jsonl(path)
    return bundle


def trace_metadata(runtime_dir: str | Path, bundle: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Build basic metadata about the trace bundle."""

    start = None
    end = None
    counts = {file_name: len(entries) for file_name, entries in bundle.items()}
    for entries in bundle.values():
        for entry in entries:
            timestamp = best_effort_timestamp(entry)
            if timestamp is None:
                continue
            start = timestamp if start is None or timestamp < start else start
            end = timestamp if end is None or timestamp > end else end
    return {
        "runtime_dir": str(Path(runtime_dir)),
        "source_files": sorted(bundle.keys()),
        "record_counts": counts,
        "time_range": {
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
        },
    }


def best_effort_timestamp(entry: dict[str, Any]) -> datetime | None:
    """Return the first parseable timestamp found in a trace record."""

    for key in ("recorded_at", "captured_at", "timestamp"):
        value = entry.get(key)
        if not isinstance(value, str) or not value:
            continue
        parsed = parse_iso8601(value)
        if parsed is not None:
            return parsed
    return None


def parse_iso8601(value: str | None) -> datetime | None:
    """Parse a trace timestamp into a timezone-aware UTC datetime."""

    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            entries.append(json.loads(stripped))
    return entries
