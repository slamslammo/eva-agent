"""crafter-world-map-observer-trace slice 2 — wrapper wiring + fairness invariant.

The wrapper accepts an optional observer-only world_trace_sink (default None =
off, byte-for-byte unchanged agent path). When wired, reset writes the base map
and each step writes a diff record — all from the RAW info at the cropping
source, never from the agent observation. The fairness red line holds:
validate_agent_local_view still passes with the trace on.

These tests use a fake env (no real Crafter install needed) so they run in CI.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scenarios.crafter.wrapper.semantic_local_view import validate_agent_local_view


class _FakeCrafterEnv:
    """Minimal Crafter-shaped env: 4x4 semantic world, player at (1,1)."""

    def __init__(self, *, seed=None):
        self._seed = seed
        self.action_space = type("A", (), {"n": 17})()
        self._world = np.array(
            [[1, 1, 1, 1], [1, 2, 1, 1], [1, 1, 3, 1], [1, 1, 1, 1]], dtype=int
        )
        self._pos = [1, 1]

    def reset(self, seed=None):
        return ("rawobs", {"semantic": self._world.copy(), "player_pos": list(self._pos)})

    def step(self, action_id):
        # mutate one world cell each step so diffs are non-empty
        self._world[2, 2] = 5
        info = {"semantic": self._world.copy(), "player_pos": list(self._pos)}
        return ("rawobs", 0.0, False, info)

    def close(self):
        pass


def _wrapper_with(temp_dir, *, trace_on):
    from scenarios.crafter.wrapper.env_wrapper import CrafterEnvWrapper
    from scenarios.crafter.wrapper.world_trace import JsonlWorldTraceSink

    sink = JsonlWorldTraceSink(runtime_dir=temp_dir) if trace_on else None
    # Inject the fake env + optional sink without touching real Crafter.
    w = CrafterEnvWrapper.__new__(CrafterEnvWrapper)
    from scenarios.crafter.actions import ActionAdapter
    from uuid import uuid4

    w._seed = 42
    w._env = _FakeCrafterEnv(seed=42)
    w._adapter = ActionAdapter()
    w._episode_id = uuid4().hex
    w._step = 0
    w._facing = "down"
    w._last_raw_observation = None
    w._last_info = {}
    w._world_trace_sink = sink
    return w


class WorldTraceWiringTests(unittest.TestCase):
    def test_default_sink_is_none_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            w = _wrapper_with(temp_dir, trace_on=False)
            w.reset(seed=42)
            w.step("noop")
            self.assertFalse((Path(temp_dir) / "world_trace.jsonl").exists())

    def test_trace_on_writes_base_and_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            w = _wrapper_with(temp_dir, trace_on=True)
            w.reset(seed=42)
            w.step("do")
            path = Path(temp_dir) / "world_trace.jsonl"
            self.assertTrue(path.exists())
            lines = [json.loads(l) for l in path.read_text().splitlines()]
            self.assertEqual(lines[0]["record"], "base_map")
            self.assertEqual(lines[0]["seed"], 42)
            self.assertEqual(lines[1]["record"], "step")
            self.assertEqual(lines[1]["tile_diffs"], [[2, 2, 5]])

    def test_fairness_invariant_holds_with_trace_on(self) -> None:
        # THE red line: agent observation must still pass the fairness check
        # (no semantic/raw_info/player_pos/position) when world-trace is on.
        with tempfile.TemporaryDirectory() as temp_dir:
            w = _wrapper_with(temp_dir, trace_on=True)
            agent_obs_reset = w.reset(seed=42)
            self.assertTrue(validate_agent_local_view(agent_obs_reset)["passed"])
            result = w.step("do")
            self.assertTrue(validate_agent_local_view(result.agent_observation)["passed"])

    def test_agent_observation_byte_identical_regardless_of_trace(self) -> None:
        # Pure-additive: the agent observation must be identical whether or not
        # the world-trace sink is wired (the sink only reads raw info).
        with tempfile.TemporaryDirectory() as td_off, tempfile.TemporaryDirectory() as td_on:
            w_off = _wrapper_with(td_off, trace_on=False)
            w_on = _wrapper_with(td_on, trace_on=True)
            obs_off = w_off.reset(seed=42)
            obs_on = w_on.reset(seed=42)
            # episode_id differs (random uuid) — compare the visible payload only
            self.assertEqual(obs_off["visible"], obs_on["visible"])
            r_off = w_off.step("do")
            r_on = w_on.step("do")
            self.assertEqual(r_off.agent_observation["visible"], r_on.agent_observation["visible"])


if __name__ == "__main__":
    unittest.main()
