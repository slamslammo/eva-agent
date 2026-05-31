"""Observer-only world-map trace channel (crafter-world-map-observer-trace).

The Crafter env's raw ``info`` carries a full semantic world map + global
player_pos. These are deliberately hidden from the agent (fairness) and not
persisted on the agent path. This module records them on an OBSERVER-ONLY sink so
a viz can reconstruct the world at any turn — WITHOUT ever touching the agent's
observation (the sink reads the raw ``info`` at the cropping source; it never sees
or mutates ``agent_observation``, so the fairness invariant is untouched).

Schema (``runtime/world_trace.jsonl``):
- line 0: ``{"record":"base_map","seed":S,"shape":[W,H],"semantic":[[...]]}``
- per step: ``{"record":"step","step":N,"player_pos":[x,y],"facing":F,
  "tile_diffs":[[x,y,material_id], ...]}`` — only cells that changed vs the
  running world (base + prior diffs).

reconstruct world@turn = base + accumulated diffs up to and including ``turn``.

Pure-additive: when no sink is wired (``None``), the wrapper path is byte-for-byte
unchanged; this file adds a new artifact only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

__all__ = [
    "JsonlWorldTraceSink",
    "compute_tile_diffs",
    "reconstruct_world",
    "reconstruct_from_trace",
]

_WORLD_TRACE_FILE = "world_trace.jsonl"


def compute_tile_diffs(previous: np.ndarray, current: np.ndarray) -> list[list[int]]:
    """Return ``[[x, y, material_id], ...]`` for cells that changed prev→current.

    Both arrays must have the same 2D shape (the Crafter world does not resize).
    """

    prev = np.asarray(previous, dtype=int)
    cur = np.asarray(current, dtype=int)
    if prev.shape != cur.shape:
        raise ValueError(f"world shape changed {prev.shape} -> {cur.shape}; cannot diff")
    xs, ys = np.where(prev != cur)
    return [[int(x), int(y), int(cur[x, y])] for x, y in zip(xs, ys)]


def reconstruct_world(
    base: np.ndarray, step_diffs: Sequence[Sequence[Sequence[int]]], *, turn: int
) -> np.ndarray:
    """Rebuild the world array at ``turn`` = base + diffs[0:turn] applied in order.

    ``step_diffs[i]`` is the diff list recorded for step ``i+1`` (turn 0 is base).
    """

    world = np.array(base, dtype=int, copy=True)
    for i in range(min(turn, len(step_diffs))):
        for cell in step_diffs[i]:
            x, y, material_id = int(cell[0]), int(cell[1]), int(cell[2])
            world[x, y] = material_id
    return world


def reconstruct_from_trace(path: str | Path, *, turn: int) -> np.ndarray:
    """Reconstruct world@turn from a written ``world_trace.jsonl`` file."""

    lines = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    base_rec = next(r for r in lines if r.get("record") == "base_map")
    base = np.array(base_rec["semantic"], dtype=int)
    step_recs = sorted(
        (r for r in lines if r.get("record") == "step"), key=lambda r: r["step"]
    )
    step_diffs = [r.get("tile_diffs", []) for r in step_recs]
    return reconstruct_world(base, step_diffs, turn=turn)


def _as_int_array(semantic: Any) -> np.ndarray | None:
    """Coerce a semantic map to a 2D int array, or None if not usable."""

    if semantic is None:
        return None
    try:
        arr = np.asarray(semantic, dtype=int)
    except (TypeError, ValueError):
        return None
    if arr.ndim != 2:
        return None
    return arr


class JsonlWorldTraceSink:
    """Observer-only sink writing ``runtime/world_trace.jsonl``.

    ``write_base`` records the reset world (+ seed). ``write_step`` records the
    per-step player_pos/facing + the cells that changed vs the running world.
    All methods are defensive no-ops when the semantic map is unavailable (e.g.
    crafter internals changed) so they can never crash a run.
    """

    def __init__(self, *, runtime_dir: str | Path) -> None:
        self._path = Path(runtime_dir) / _WORLD_TRACE_FILE
        self._running: np.ndarray | None = None

    def _append(self, record: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def write_base(self, *, semantic: Any, seed: int | None) -> None:
        arr = _as_int_array(semantic)
        if arr is None:
            return  # no usable base map → record nothing (graceful)
        self._running = arr.copy()
        self._append(
            {
                "record": "base_map",
                "seed": seed,
                "shape": [int(arr.shape[0]), int(arr.shape[1])],
                "semantic": arr.tolist(),
            }
        )

    def write_step(
        self, *, step: int, player_pos: Any, facing: str, semantic: Any
    ) -> None:
        arr = _as_int_array(semantic)
        if arr is None or self._running is None:
            return  # no usable map / no base yet → skip this step (graceful)
        try:
            diffs = compute_tile_diffs(self._running, arr)
        except ValueError:
            return  # shape changed unexpectedly → skip rather than crash
        self._running = arr.copy()
        pos: list[int] | None = None
        if player_pos is not None:
            try:
                p = np.asarray(player_pos, dtype=int)
                if p.shape[0] >= 2:
                    pos = [int(p[0]), int(p[1])]
            except (TypeError, ValueError, IndexError):
                pos = None
        self._append(
            {
                "record": "step",
                "step": int(step),
                "player_pos": pos,
                "facing": facing,
                "tile_diffs": diffs,
            }
        )
