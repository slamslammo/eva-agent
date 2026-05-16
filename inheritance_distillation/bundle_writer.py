"""Bundle serialization for inherited-prior distillation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_distilled_prior_bundle(
    *,
    scenario: str,
    records: list[dict[str, Any]],
    source_runtime_dirs: list[str],
    source_trace_files: list[str],
    generated_at: str,
) -> dict[str, Any]:
    """Build the normalized same-scenario distillation payload."""

    return {
        "scenario": scenario,
        "distillation_date": generated_at,
        "source_runtime_dirs": sorted(source_runtime_dirs),
        "source_trace_files": sorted(source_trace_files),
        "record_count": len(records),
        "records": records,
    }


def write_distilled_prior_bundle(payload: dict[str, Any], output_path: str | Path) -> Path:
    """Write one distilled-prior bundle JSON file."""

    path = Path(output_path).expanduser().resolve()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
