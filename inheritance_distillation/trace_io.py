"""Trace-file readers for architecture-neutral inherited-prior distillation."""

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


def load_trace_bundles(runtime_dirs: list[str | Path]) -> list[dict[str, Any]]:
    """Load trace bundles plus metadata for one or more runtime directories."""

    bundles: list[dict[str, Any]] = []
    for runtime_dir in runtime_dirs:
        trace_bundle = load_trace_bundle(runtime_dir)
        bundles.append(
            {
                "runtime_dir": str(Path(runtime_dir).expanduser().resolve()),
                "trace_bundle": trace_bundle,
                "metadata": trace_metadata(runtime_dir, trace_bundle),
            }
        )
    return bundles


def trace_metadata(runtime_dir: str | Path, bundle: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Build basic metadata about one trace bundle."""

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
        "runtime_dir": str(Path(runtime_dir).expanduser().resolve()),
        "source_files": sorted(bundle.keys()),
        "record_counts": counts,
        "time_range": {
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
        },
    }


def infer_scenario(bundle: dict[str, list[dict[str, Any]]]) -> str | None:
    """Infer the scenario from trace payloads without importing framework code."""

    for entry in bundle.get("learning_outcomes.jsonl", []):
        if not isinstance(entry, dict):
            continue
        content = entry.get("content")
        if isinstance(content, dict):
            scenario = content.get("scenario")
            if isinstance(scenario, str) and scenario:
                return scenario
    for entry in bundle.get("habit_bias.jsonl", []):
        if not isinstance(entry, dict):
            continue
        provenance = entry.get("provenance")
        if isinstance(provenance, dict):
            scope = provenance.get("scope")
            if isinstance(scope, dict):
                scenario = scope.get("scenario")
                if isinstance(scenario, str) and scenario:
                    return scenario
    for entry in bundle.get("deliberation_audit.jsonl", []):
        if not isinstance(entry, dict):
            continue
        deliberation_input = entry.get("deliberation_input")
        if not isinstance(deliberation_input, dict):
            continue
        working_memory_context = deliberation_input.get("working_memory_context")
        if not isinstance(working_memory_context, dict):
            continue
        for field_name in ("semantic_patterns", "episodic_memory", "inherited_priors"):
            entries = working_memory_context.get(field_name)
            if not isinstance(entries, list):
                continue
            for item in entries:
                if not isinstance(item, dict):
                    continue
                provenance = item.get("provenance")
                if not isinstance(provenance, dict):
                    continue
                scope = provenance.get("scope")
                if not isinstance(scope, dict):
                    continue
                scenario = scope.get("scenario")
                if isinstance(scenario, str) and scenario:
                    return scenario
    return None


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
