"""Same-scenario inherited-prior distillation pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bundle_writer import build_distilled_prior_bundle
from .extractors import (
    extract_pattern_priors,
    extract_risk_priors,
    extract_skill_template_priors,
    extract_threshold_priors,
)
from .trace_io import infer_scenario, load_trace_bundles
from .validators import validate_structural_invariants

DEFAULT_OUTPUT_FILE = "DistilledPriorBundle.json"


def distill_runtime_dirs(runtime_dirs: list[str | Path]) -> dict[str, Any]:
    """Load one or more runtime directories and distill a same-scenario prior bundle."""

    return distill_trace_bundles(load_trace_bundles(list(runtime_dirs)))


def distill_trace_bundles(trace_bundles: list[dict[str, Any]]) -> dict[str, Any]:
    """Distill one normalized inherited-prior bundle from loaded traces."""

    if not trace_bundles:
        raise ValueError("at least one runtime trace bundle is required")
    scenarios = {
        scenario
        for item in trace_bundles
        for scenario in [infer_scenario(item.get("trace_bundle", {}))]
        if scenario is not None
    }
    if len(scenarios) != 1:
        raise ValueError("distillation requires traces from exactly one scenario")
    scenario = next(iter(scenarios))
    aggregated_bundle = _merge_trace_bundles(trace_bundles)
    records = _dedupe_records(
        [
            *extract_threshold_priors(aggregated_bundle, scenario=scenario),
            *extract_pattern_priors(aggregated_bundle, scenario=scenario),
            *extract_risk_priors(aggregated_bundle, scenario=scenario),
            *extract_skill_template_priors(aggregated_bundle, scenario=scenario),
        ]
    )
    validate_structural_invariants(records)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return build_distilled_prior_bundle(
        scenario=scenario,
        records=records,
        source_runtime_dirs=[str(item.get("runtime_dir") or "") for item in trace_bundles],
        source_trace_files=sorted({file_name for item in trace_bundles for file_name in (item.get("trace_bundle") or {}).keys()}),
        generated_at=generated_at,
    )


def _merge_trace_bundles(trace_bundles: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    merged: dict[str, list[dict[str, Any]]] = {}
    for item in trace_bundles:
        trace_bundle = item.get("trace_bundle")
        if not isinstance(trace_bundle, dict):
            continue
        for file_name, entries in trace_bundle.items():
            if not isinstance(entries, list):
                continue
            merged.setdefault(file_name, []).extend(entry for entry in entries if isinstance(entry, dict))
    return merged


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str, str | None, str | None], dict[str, Any]] = {}
    for record in records:
        content = record.get("content")
        if not isinstance(content, dict):
            continue
        key = (
            str(content.get("situation_key") or ""),
            str(content.get("candidate_profile") or ""),
            str(record.get("provenance_detail") or ""),
            str(content.get("preferred_action")) if content.get("preferred_action") is not None else None,
            str(content.get("avoid_action")) if content.get("avoid_action") is not None else None,
        )
        current = by_key.get(key)
        if current is None or float(record.get("confidence", 0.0)) > float(current.get("confidence", 0.0)):
            by_key[key] = _normalized_record(record)
    return sorted(
        by_key.values(),
        key=lambda record: (
            str(((record.get("content") or {}).get("situation_key") or "")),
            str(((record.get("content") or {}).get("candidate_profile") or "")),
            -float(record.get("confidence", 0.0)),
            str(record.get("provenance_detail") or ""),
        ),
    )


def _normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    content = dict(normalized.get("content") or {})
    if content.get("avoid_action") is None:
        content.pop("avoid_action", None)
    if content.get("preferred_action") is None:
        content.pop("preferred_action", None)
    normalized["content"] = content
    normalized["scope"] = dict(normalized.get("scope") or {})
    normalized["confidence"] = round(float(normalized.get("confidence", 0.0)), 3)
    return normalized
