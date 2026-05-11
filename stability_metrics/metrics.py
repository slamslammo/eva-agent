"""Metric calculators for architecture-neutral stability profiles."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .trace_io import best_effort_timestamp, load_trace_bundle, trace_metadata


def calculate_stability_profile(runtime_dir: str | Path) -> dict[str, Any]:
    """Calculate an architecture-neutral stability profile from trace files."""

    bundle = load_trace_bundle(runtime_dir)
    audits = bundle.get("deliberation_audit.jsonl", [])
    learning_outcomes = bundle.get("learning_outcomes.jsonl", [])
    response_history = bundle.get("response_history.jsonl", [])

    metrics = {
        "constraint_violation_rate": _constraint_violation_rate(audits),
        "continuity_preservation_score": _continuity_preservation_score(audits, response_history),
        "useful_progress_under_constraint": _useful_progress_under_constraint(learning_outcomes),
        "recovery_success_rate": _recovery_success_rate(response_history),
        "mean_time_to_recovery_sec": _mean_time_to_recovery(response_history),
        "recovery_path_entropy": _recovery_path_entropy(response_history),
        "cost_ratio": _cost_ratio(response_history, learning_outcomes),
    }
    return {
        "metadata": trace_metadata(runtime_dir, bundle),
        "metrics": metrics,
    }


def write_stability_profile(runtime_dir: str | Path, *, output_path: str | Path | None = None) -> Path:
    """Compute and persist one stability profile JSON file."""

    runtime_path = Path(runtime_dir)
    destination = Path(output_path) if output_path is not None else runtime_path / "stability_profile.json"
    profile = calculate_stability_profile(runtime_path)
    destination.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def _constraint_violation_rate(audits: list[dict[str, Any]]) -> float | None:
    if not audits:
        return None
    violations = 0
    for audit in audits:
        release_decision = dict(audit.get("release_decision") or {})
        if str(release_decision.get("outcome") or "withhold") == "withhold":
            continue
        runtime_gate = dict((audit.get("deliberation_input") or {}).get("runtime_gate_context") or {})
        if (
            not bool(runtime_gate.get("instance_valid", False))
            or not bool(runtime_gate.get("turn_allowed", False))
            or bool(runtime_gate.get("critical_blocked", False))
        ):
            violations += 1
    return round(violations / len(audits), 6)


def _continuity_preservation_score(
    audits: list[dict[str, Any]],
    response_history: list[dict[str, Any]],
) -> float | None:
    samples: list[tuple[bool, str, bool]] = []
    for audit in audits:
        runtime_gate = dict((audit.get("deliberation_input") or {}).get("runtime_gate_context") or {})
        if runtime_gate:
            samples.append(
                (
                    bool(runtime_gate.get("instance_valid", False)),
                    str(runtime_gate.get("life_state") or "unknown"),
                    not bool(runtime_gate.get("critical_blocked", False)),
                )
            )
    if not samples:
        for entry in response_history:
            samples.append(
                (
                    bool(entry.get("instance_valid", False)),
                    str(entry.get("life_state") or "unknown"),
                    True,
                )
            )
    if not samples:
        return None
    viable = 0
    for instance_valid, life_state, not_critically_blocked in samples:
        if instance_valid and not_critically_blocked and life_state in {"RECOVERING", "STABLE", "DEGRADED"}:
            viable += 1
    return round(viable / len(samples), 6)


def _useful_progress_under_constraint(learning_outcomes: list[dict[str, Any]]) -> float | None:
    if not learning_outcomes:
        return None
    task_progress_values = [
        _as_float((entry.get("outcome_vector") or {}).get("task_progress"))
        for entry in learning_outcomes
    ]
    task_progress_values = [value for value in task_progress_values if value is not None]
    if task_progress_values:
        return round(sum(max(value, 0.0) for value in task_progress_values) / len(learning_outcomes), 6)
    positive_value = sum(max(_as_float(entry.get("outcome_delta")) or 0.0, 0.0) for entry in learning_outcomes)
    return round(positive_value / len(learning_outcomes), 6)


def _recovery_success_rate(response_history: list[dict[str, Any]]) -> float | None:
    if not response_history:
        return None
    disturbances = {str(entry.get("pressure_id") or f"idx:{index}") for index, entry in enumerate(response_history)}
    successful = {
        str(entry.get("pressure_id") or f"idx:{index}")
        for index, entry in enumerate(response_history)
        if str(entry.get("pressure_outcome") or "unknown") == "relieved"
    }
    if not disturbances:
        return None
    return round(len(successful) / len(disturbances), 6)


def _mean_time_to_recovery(response_history: list[dict[str, Any]]) -> float | None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, entry in enumerate(response_history):
        grouped[str(entry.get("pressure_id") or f"idx:{index}")].append(entry)
    durations: list[float] = []
    for entries in grouped.values():
        ordered = sorted(
            (
                (timestamp, entry)
                for entry in entries
                for timestamp in [_entry_timestamp(entry)]
                if timestamp is not None
            ),
            key=lambda item: item[0],
        )
        if not ordered:
            continue
        start = ordered[0][0]
        end = None
        for timestamp, entry in ordered:
            if str(entry.get("pressure_outcome") or "unknown") == "relieved":
                end = timestamp
                break
        if end is not None:
            durations.append(max((end - start).total_seconds(), 0.0))
    if not durations:
        return None
    return round(sum(durations) / len(durations), 6)


def _recovery_path_entropy(response_history: list[dict[str, Any]]) -> float | None:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for index, entry in enumerate(response_history):
        reason = str(entry.get("pressure_reason") or "unknown")
        pressure_id = str(entry.get("pressure_id") or f"idx:{index}")
        grouped[reason][pressure_id].append(str(entry.get("selected_action") or "unknown"))
    entropies: list[float] = []
    for pressure_groups in grouped.values():
        if not pressure_groups:
            continue
        counter = Counter(tuple(actions) for actions in pressure_groups.values())
        total = sum(counter.values())
        if total <= 0:
            continue
        entropy = 0.0
        for count in counter.values():
            probability = count / total
            entropy -= probability * math.log2(probability)
        entropies.append(entropy)
    if not entropies:
        return None
    return round(sum(entropies) / len(entropies), 6)


def _cost_ratio(response_history: list[dict[str, Any]], learning_outcomes: list[dict[str, Any]]) -> float | None:
    if not response_history:
        return None
    value_preserved = sum(max(_as_float(entry.get("outcome_delta")) or 0.0, 0.0) for entry in learning_outcomes)
    if value_preserved <= 0.0:
        return None
    return round(len(response_history) / value_preserved, 6)


def _entry_timestamp(entry: dict[str, Any]):
    return best_effort_timestamp(entry)


def _timestamp_sort_key(entry: dict[str, Any]) -> datetime:
    return _entry_timestamp(entry) or datetime.min


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
