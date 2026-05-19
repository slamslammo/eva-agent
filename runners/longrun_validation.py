"""Round 1.D-3: long-run validation hook factory.

Builds the periodic hook used by ``eva.kernel.main.run_runtime`` during
extended validation runs. The hook performs two jobs each time it fires:

1. Compute the current ``stability_metrics`` profile via
   ``calculate_stability_profile`` and write it to
   ``snapshot_dir / profile-{seq:05d}.json``.
2. Check the configured ``LongrunTripwire`` thresholds against the
   computed profile. If any threshold is violated, return
   ``(True, "tripwire:<metric_name>")`` so the loop stops cleanly with
   a recorded exit_reason; otherwise return ``(False, None)``.

Hook errors are caught by ``run_runtime`` itself; this module only
declares the surface and delegates calculation to ``stability_metrics``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from stability_metrics.metrics import calculate_stability_profile


__all__ = [
    "LongrunTripwire",
    "build_longrun_validation_hook",
    "longrun_hook_from_args",
    "tripwire_from_args",
]


@dataclass(frozen=True)
class LongrunTripwire:
    """Threshold configuration for long-run invariant validation.

    Each field is the bound that, when violated, triggers an early stop.
    ``None`` disables that particular check. Defaults reflect the
    blueprint §13.2 invariant set: no constraint violations, viability
    preservation above 0.5, and at least some useful progress emerging.
    """

    max_constraint_violation_rate: float | None = 0.0
    min_continuity_preservation_score: float | None = 0.5
    # ``min_useful_progress`` left as None by default because Crafter at
    # current capability levels produces minimal task_progress; turning
    # this on requires post-Round-1.B-2 parameter tuning data first.
    min_useful_progress_under_constraint: float | None = None


def build_longrun_validation_hook(
    *,
    snapshot_dir: Path | str,
    tripwire: LongrunTripwire | None = None,
) -> Callable[..., tuple[bool, str | None]]:
    """Return a periodic hook that writes snapshots and checks tripwires.

    Parameters
    ----------
    snapshot_dir
        Directory where numbered profile snapshots will be written. Will
        be created if it does not exist.
    tripwire
        Threshold configuration. If ``None``, no tripwire checks are
        performed — the hook becomes snapshot-only.

    Returns
    -------
    Callable matching the signature required by
    ``run_runtime(periodic_hook=...)``.
    """

    snapshots_path = Path(snapshot_dir)
    snapshots_path.mkdir(parents=True, exist_ok=True)
    sequence = {"n": 0}

    def hook(*, runtime_dir: Path, elapsed_since_start: float, ticks: int, turns: int) -> tuple[bool, str | None]:
        sequence["n"] += 1
        profile = calculate_stability_profile(runtime_dir)
        # Augment with the elapsed / loop counters so report consumers can
        # plot metric trajectory over time without re-deriving them.
        annotated = {
            "sequence": sequence["n"],
            "elapsed_since_start_sec": round(float(elapsed_since_start), 3),
            "ticks": int(ticks),
            "turns": int(turns),
            **profile,
        }
        target = snapshots_path / f"profile-{sequence['n']:05d}.json"
        target.write_text(json.dumps(annotated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if tripwire is not None:
            violation = _check_tripwire(profile.get("metrics") or {}, tripwire)
            if violation is not None:
                return True, f"tripwire:{violation}"
        return False, None

    return hook


def tripwire_from_args(args: Any) -> LongrunTripwire:
    """Translate parsed CLI args into a ``LongrunTripwire`` configuration.

    Negative values disable a threshold; otherwise the value is honored as
    the threshold to enforce.
    """

    def _opt(value: float | None, *, disable_if_negative: bool = True) -> float | None:
        if value is None:
            return None
        numeric = float(value)
        if disable_if_negative and numeric < 0.0:
            return None
        return numeric

    return LongrunTripwire(
        max_constraint_violation_rate=_opt(getattr(args, "longrun_tripwire_max_constraint_violation_rate", 0.0)),
        min_continuity_preservation_score=_opt(getattr(args, "longrun_tripwire_min_continuity_score", 0.5)),
        # ``min_useful_progress_under_constraint`` not yet exposed to CLI;
        # leave default (None) until Round 1.B-2 tuning produces a value.
    )


def longrun_hook_from_args(args: Any) -> Callable[..., tuple[bool, str | None]] | None:
    """Translate parsed CLI args into a periodic hook, or ``None`` if disabled.

    Returns ``None`` when ``--longrun-snapshot-dir`` was not supplied, so
    callers can pass the result directly to ``run_runtime(periodic_hook=...)``
    without conditional wiring.
    """

    snapshot_dir = getattr(args, "longrun_snapshot_dir", None)
    if not snapshot_dir:
        return None
    return build_longrun_validation_hook(
        snapshot_dir=Path(snapshot_dir),
        tripwire=tripwire_from_args(args),
    )


def _check_tripwire(metrics: dict[str, Any], tripwire: LongrunTripwire) -> str | None:
    """Return the name of the first violated threshold, or ``None``."""

    if tripwire.max_constraint_violation_rate is not None:
        value = metrics.get("constraint_violation_rate")
        if value is not None and float(value) > tripwire.max_constraint_violation_rate:
            return "constraint_violation_rate"
    if tripwire.min_continuity_preservation_score is not None:
        value = metrics.get("continuity_preservation_score")
        if value is not None and float(value) < tripwire.min_continuity_preservation_score:
            return "continuity_preservation_score"
    if tripwire.min_useful_progress_under_constraint is not None:
        value = metrics.get("useful_progress_under_constraint")
        if value is not None and float(value) < tripwire.min_useful_progress_under_constraint:
            return "useful_progress_under_constraint"
    return None
