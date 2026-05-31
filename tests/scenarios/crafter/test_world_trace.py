"""crafter-world-map-observer-trace — observer-only world-map trace channel.

The Crafter env's raw info carries a full semantic world map + global player_pos,
hidden from the agent for fairness. This adds an OBSERVER-ONLY sink that records
the world map so a viz can reconstruct world@turn — WITHOUT ever leaking the map
or player_pos into the agent's observation.

Schema: a base-map record (line 0: full semantic + shape + seed) followed by
per-step diff records ({step, player_pos, facing, tile_diffs}). reconstruct
world@turn = base + accumulated diffs.

slice 1 fixes the world_trace module (sink + diff + reconstruct) in isolation;
wrapper wiring + fairness regression land in slice 2.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np


class WorldTraceDiffTests(unittest.TestCase):
    def test_diff_lists_only_changed_cells(self) -> None:
        from scenarios.crafter.wrapper.world_trace import compute_tile_diffs

        base = np.array([[1, 1], [2, 2]], dtype=int)
        nxt = np.array([[1, 9], [2, 2]], dtype=int)  # one cell changed: (0,1) 1->9
        diffs = compute_tile_diffs(base, nxt)
        self.assertEqual(diffs, [[0, 1, 9]])

    def test_diff_empty_when_unchanged(self) -> None:
        from scenarios.crafter.wrapper.world_trace import compute_tile_diffs

        base = np.array([[1, 2], [3, 4]], dtype=int)
        self.assertEqual(compute_tile_diffs(base, base.copy()), [])

    def test_reconstruct_world_at_turn(self) -> None:
        from scenarios.crafter.wrapper.world_trace import reconstruct_world

        base = np.array([[1, 1], [1, 1]], dtype=int)
        # turn1 changes (0,0)->5; turn2 changes (1,1)->7
        step_diffs = [
            [[0, 0, 5]],
            [[1, 1, 7]],
        ]
        w1 = reconstruct_world(base, step_diffs, turn=1)
        self.assertEqual(w1.tolist(), [[5, 1], [1, 1]])
        w2 = reconstruct_world(base, step_diffs, turn=2)
        self.assertEqual(w2.tolist(), [[5, 1], [1, 7]])
        # turn 0 = base untouched
        w0 = reconstruct_world(base, step_diffs, turn=0)
        self.assertEqual(w0.tolist(), base.tolist())


class WorldTraceSinkTests(unittest.TestCase):
    def _sink(self, temp_dir: str):
        from scenarios.crafter.wrapper.world_trace import JsonlWorldTraceSink

        return JsonlWorldTraceSink(runtime_dir=temp_dir)

    def test_base_then_steps_written_to_world_trace_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = self._sink(temp_dir)
            base = np.array([[1, 1], [1, 1]], dtype=int)
            sink.write_base(semantic=base, seed=42)
            sink.write_step(step=1, player_pos=(0, 0), facing="down",
                            semantic=np.array([[5, 1], [1, 1]], dtype=int))
            path = Path(temp_dir) / "world_trace.jsonl"
            self.assertTrue(path.exists())
            lines = [json.loads(l) for l in path.read_text().splitlines()]
            self.assertEqual(lines[0]["record"], "base_map")
            self.assertEqual(lines[0]["seed"], 42)
            self.assertEqual(lines[0]["shape"], [2, 2])
            self.assertEqual(lines[0]["semantic"], [[1, 1], [1, 1]])
            self.assertEqual(lines[1]["record"], "step")
            self.assertEqual(lines[1]["step"], 1)
            self.assertEqual(lines[1]["player_pos"], [0, 0])
            self.assertEqual(lines[1]["facing"], "down")
            self.assertEqual(lines[1]["tile_diffs"], [[0, 0, 5]])

    def test_reconstruct_from_written_trace_roundtrips(self) -> None:
        from scenarios.crafter.wrapper.world_trace import reconstruct_from_trace

        with tempfile.TemporaryDirectory() as temp_dir:
            sink = self._sink(temp_dir)
            base = np.array([[1, 1], [1, 1]], dtype=int)
            sink.write_base(semantic=base, seed=7)
            full_t1 = np.array([[5, 1], [1, 1]], dtype=int)
            sink.write_step(step=1, player_pos=(0, 0), facing="up", semantic=full_t1)
            path = Path(temp_dir) / "world_trace.jsonl"
            world1 = reconstruct_from_trace(path, turn=1)
            self.assertEqual(world1.tolist(), full_t1.tolist())

    def test_sink_handles_missing_semantic_gracefully(self) -> None:
        # If raw info lacks semantic/player_pos (crafter internals changed),
        # the sink must no-op that step, never crash the run.
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = self._sink(temp_dir)
            sink.write_base(semantic=None, seed=1)  # no base → nothing written yet
            sink.write_step(step=1, player_pos=None, facing="down", semantic=None)
            path = Path(temp_dir) / "world_trace.jsonl"
            # graceful: either no file or no malformed lines
            if path.exists():
                for l in path.read_text().splitlines():
                    json.loads(l)  # must be valid json, no crash


if __name__ == "__main__":
    unittest.main()
