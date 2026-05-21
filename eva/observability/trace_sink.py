"""Round 1.H — opt-in cognitive telemetry sink (Viz P1 instrumentation).

Per `telemetry-schema.md` (P0 frozen v1): an append-only JSONL trace of the L1→L3
chain that a viewer can replay offline. Emission is **purely additive observation**
— it never reads back into or changes any decision. Tracing is **opt-in** via the
`EVA_TRACE` flag; when off, `build_trace_sink` returns a `NullTraceSink` whose
methods are no-ops, so a non-traced run is byte-identical to one with this module
absent (red-line #1).

Files written under the runtime dir, alongside existing traces (schema §0):
- `run_meta.json` — one metadata header per run (§1).
- `cognitive_trace.jsonl` — all transform + snapshot events, aligned by `turn_index` (§2–4).
- `raw_observations/` — `l1.raw_observation` payloads (§5; populated in H-2).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

__all__ = [
    "TRACE_ENV_FLAG",
    "RunIdentity",
    "TraceSink",
    "NullTraceSink",
    "JsonlTraceSink",
    "build_trace_sink",
    "trace_enabled",
    "write_run_meta",
]

TRACE_ENV_FLAG = "EVA_TRACE"

# Continuity states (schema §2). ``done=True`` ⇒ ``terminated`` closes the
# individual; the next launch starts a new individual_id with ``new_individual``.
CONTINUITY_ALIVE = "alive"
CONTINUITY_TERMINATED = "terminated"
CONTINUITY_NEW_INDIVIDUAL = "new_individual"
CONTINUITY_INHERITED = "inherited"


def trace_enabled() -> bool:
    """True iff the opt-in trace flag is set to a truthy value (default off)."""

    raw = os.environ.get(TRACE_ENV_FLAG)
    return bool(raw) and raw.strip().lower() not in {"", "0", "false", "no", "off"}


@dataclass
class RunIdentity:
    """Per-run identity context shared by every trace envelope (schema §2)."""

    run_id: str
    individual_id: str
    individual_boundary: str = ""
    continuity_state: str = CONTINUITY_ALIVE
    inherited_from: str | None = None


class TraceSink(Protocol):
    """Append-only cognitive-trace emitter. All methods are observation-only."""

    def emit_transform(
        self,
        *,
        layer: str,
        transform_id: str,
        code_anchor: str,
        turn_index: int,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        decision: Any = None,
        parents: list[dict[str, str]] | None = None,
        episode_step: int | None = None,
    ) -> None: ...

    def emit_snapshot(
        self,
        *,
        snapshot_type: str,
        values: dict[str, Any],
        turn_index: int,
        episode_step: int | None = None,
    ) -> None: ...

    def emit_raw_observation(
        self,
        *,
        turn_index: int,
        payload: dict[str, Any],
        episode_step: int | None = None,
    ) -> None: ...

    def set_continuity_state(self, state: str) -> None: ...

    @property
    def enabled(self) -> bool: ...

    def close(self) -> None: ...


class NullTraceSink:
    """No-op sink — the default when ``EVA_TRACE`` is off. Byte-equivalent to no tracing."""

    enabled = False

    def emit_transform(self, **_kwargs: Any) -> None:
        return None

    def emit_snapshot(self, **_kwargs: Any) -> None:
        return None

    def emit_raw_observation(self, **_kwargs: Any) -> None:
        return None

    def set_continuity_state(self, state: str) -> None:
        return None

    def close(self) -> None:
        return None


class JsonlTraceSink:
    """Append-only JSONL sink writing the schema §2–5 streams into the runtime dir."""

    enabled = True

    def __init__(self, runtime_dir: str | os.PathLike[str], identity: RunIdentity) -> None:
        self._dir = Path(runtime_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._identity = identity
        self._trace_path = self._dir / "cognitive_trace.jsonl"
        self._raw_dir = self._dir / "raw_observations"

    def _envelope(self, event_type: str, turn_index: int, episode_step: int | None) -> dict[str, Any]:
        return {
            "run_id": self._identity.run_id,
            "individual_id": self._identity.individual_id,
            "individual_boundary": self._identity.individual_boundary,
            "continuity_state": self._identity.continuity_state,
            "inherited_from": self._identity.inherited_from,
            "episode_step": episode_step,
            "turn_index": turn_index,
            "event_type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    def _append(self, record: dict[str, Any]) -> None:
        with self._trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def emit_transform(
        self,
        *,
        layer: str,
        transform_id: str,
        code_anchor: str,
        turn_index: int,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        decision: Any = None,
        parents: list[dict[str, str]] | None = None,
        episode_step: int | None = None,
    ) -> None:
        record = self._envelope("transform", turn_index, episode_step)
        record.update(
            {
                "layer": layer,
                "transform_id": transform_id,
                "code_anchor": code_anchor,
                "parents": parents or [],
                "inputs": inputs or {},
                "outputs": outputs or {},
                "decision": decision,
            }
        )
        self._append(record)

    def emit_snapshot(
        self,
        *,
        snapshot_type: str,
        values: dict[str, Any],
        turn_index: int,
        episode_step: int | None = None,
    ) -> None:
        record = self._envelope("snapshot", turn_index, episode_step)
        record.update({"snapshot_type": snapshot_type, "values": dict(values)})
        self._append(record)

    def emit_raw_observation(
        self,
        *,
        turn_index: int,
        payload: dict[str, Any],
        episode_step: int | None = None,
    ) -> None:
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        name = f"turn-{turn_index:08d}.json"
        record = self._envelope("transform", turn_index, episode_step)
        record.update(
            {
                "layer": "L1",
                "transform_id": "l1.raw_observation",
                "code_anchor": "scenarios/crafter/wrapper:CrafterEnvWrapper",
                "parents": [],
                "inputs": {},
                "outputs": payload,
                "decision": None,
            }
        )
        with (self._raw_dir / name).open("w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, sort_keys=True)
        # Also index it in the main trace so replay sees it inline.
        self._append({**record, "outputs": {"raw_observation_ref": f"raw_observations/{name}"}})

    def set_continuity_state(self, state: str) -> None:
        self._identity.continuity_state = state

    def close(self) -> None:
        return None


def write_run_meta(runtime_dir: str | os.PathLike[str], meta: dict[str, Any]) -> None:
    """Write the per-run metadata header (schema §1). Overwrites; one per run."""

    path = Path(runtime_dir)
    path.mkdir(parents=True, exist_ok=True)
    with (path / "run_meta.json").open("w", encoding="utf-8") as handle:
        json.dump(meta, handle, ensure_ascii=False, sort_keys=True, indent=2)


def build_trace_sink(
    runtime_dir: str | os.PathLike[str],
    *,
    enabled: bool | None = None,
    identity: RunIdentity | None = None,
) -> TraceSink:
    """Return a `JsonlTraceSink` when tracing is enabled, else a `NullTraceSink`.

    `enabled` defaults to `trace_enabled()` (the `EVA_TRACE` flag). A real sink
    requires `identity`; without it (or when disabled) the no-op sink is returned.
    """

    if enabled is None:
        enabled = trace_enabled()
    if not enabled or identity is None:
        return NullTraceSink()
    return JsonlTraceSink(runtime_dir, identity)
