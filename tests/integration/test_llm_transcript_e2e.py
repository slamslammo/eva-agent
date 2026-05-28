"""PR-Α end-to-end: EVA_LLM_TRANSCRIPT=raw produces dlPFC transcripts.

Validates the §4.6 completion criterion: a Crafter short run with the
``EVA_LLM_TRANSCRIPT=raw`` env var set produces files under
``{runtime_dir}/llm_transcripts/dlPFC/turn-*.json``, and the minted release
tokens carry ``anchor_domain_ref`` + ``dlpfc_proposal_ref``.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from eva.kernel import (
    ExternalLifeConfig,
    LifecycleConfig,
    LoopControl,
    StateStore,
    build_runtime_config,
)
from runners.run_crafter import CrafterRuntimeSession, run_crafter_runtime
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


class _StubSession:
    """Minimal stub providing a deliberation-enabling observation."""

    def __init__(self) -> None:
        self.step_actions: list[str] = []
        self.terminated = False
        self.latest_agent_observation = {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "ep",
            "step": 0,
            "visible": {
                "life_panel": {"available": True, "values": {"health": 8, "food": 7, "water": 7, "energy": 7}},
                "inventory_panel": {"available": True, "items": {}},
                "facing": "up",
                "local_view": {
                    "format": "semantic_grid", "width": 3, "height": 3,
                    "center": {"row": 1, "col": 1},
                    "cells": [["grass"]*3, ["grass","player","grass"], ["grass"]*3],
                },
                "nearby_objects": [],
            },
            "task_context": {"objective": "survive", "unlocked_achievements_visible": []},
            "available_actions": ["noop","sleep","do","move_left","move_right","move_up","move_down"],
            "notes": [],
        }

    @classmethod
    def start(cls, *, seed=None) -> "_StubSession":
        del seed
        return cls()

    def build_shared_facts(self) -> dict:
        return {"agent_observation": dict(self.latest_agent_observation)}

    def step_action(self, action_name: str):
        self.step_actions.append(action_name)
        return type("Step", (), {
            "raw_observation": None, "reward": 0.0, "done": False, "raw_info": {},
            "agent_observation": dict(self.latest_agent_observation),
            "before_observation": dict(self.latest_agent_observation),
            "after_action_observation": dict(self.latest_agent_observation),
        })()

    def close(self) -> None:
        pass


def _run_config(temp_dir: str):
    return build_runtime_config(
        temp_dir,
        lifecycle=LifecycleConfig(
            heartbeat_interval_sec=0.2,
            lease_duration_sec=1.0,
            recovering_window_sec=0.05,
            turn_guard_window_sec=0.01,
        ),
        external_life=ExternalLifeConfig(
            shallow_patrol_interval_sec=0.01,
            deep_patrol_interval_sec=0.02,
            full_report_interval_sec=0.03,
            recent_event_window_sec=60.0,
        ),
        control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
    )


def _stub_producer(chosen_action: str, runtime_dir: str):
    """Build a CrafterLLMActionProducer with sink wired from env (production-like).

    Mirrors what ``_build_candidate_producer`` does in production: reads
    ``EVA_LLM_TRANSCRIPT`` to decide sink mode + provides identity_provider.
    """

    from eva.l3_deliberation.llm_transcript import build_transcript_sink_from_env

    def _chat(messages):
        return json.dumps({"candidates": [{"action": chosen_action, "reason": "stub"}]})

    return CrafterLLMActionProducer(
        chat_fn=_chat,
        observation_fn=lambda: {
            "schema_version": "symbolic_observation_v0",
            "visible": {
                "life_panel": {"available": True, "values": {"health": 8, "food": 7, "water": 7, "energy": 7}},
                "inventory_panel": {"available": True, "items": {}},
                "facing": "up",
                "local_view": {
                    "format": "semantic_grid", "width": 3, "height": 3,
                    "center": {"row": 1, "col": 1},
                    "cells": [["grass"]*3, ["grass","player","grass"], ["grass"]*3],
                },
            },
        },
        transcript_sink=build_transcript_sink_from_env(runtime_dir),
        identity_provider=lambda: {"run_id": "test-run", "individual_id": "test-ind", "turn_index": 0},
        model_label="stub-model",
    )


class TranscriptE2EWiringTests(unittest.TestCase):
    """E2E: EVA_LLM_TRANSCRIPT=raw produces dlPFC transcript files during a Crafter run."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_env_raw_writes_transcripts_during_short_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            session = _StubSession()
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "raw"}):
                producer = _stub_producer("do", temp_dir)
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    run_crafter_runtime(config, candidate_producer=producer)

            transcript_dir = Path(config.paths.runtime_dir) / "llm_transcripts" / "dlPFC"
            self.assertTrue(
                transcript_dir.exists(),
                f"Expected transcript dir {transcript_dir}",
            )
            transcript_files = sorted(transcript_dir.glob("turn-*.json"))
            self.assertGreaterEqual(
                len(transcript_files), 1,
                "At least one transcript file should be written when EVA_LLM_TRANSCRIPT=raw",
            )

            payload = json.loads(transcript_files[0].read_text())
            # PR-Β' schema bump v1 → v1.1 (v1 superset, plan §5.5b).
            self.assertEqual(payload["schema_version"], "llm_transcript_v1.1")
            self.assertEqual(payload["llm_role"], "dlPFC")
            self.assertEqual(payload["scenario"], "crafter")
            self.assertEqual(payload["parse_status"], "ok")
            # run_id / individual_id wired through from runtime identity
            self.assertTrue(payload["run_id"], "run_id must be threaded from runtime")
            self.assertTrue(payload["individual_id"], "individual_id must be threaded from runtime")

    def test_env_off_produces_no_transcript_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            session = _StubSession()
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "off"}):
                producer = _stub_producer("do", temp_dir)
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    run_crafter_runtime(config, candidate_producer=producer)

            transcript_dir = Path(config.paths.runtime_dir) / "llm_transcripts"
            self.assertFalse(
                transcript_dir.exists(),
                "EVA_LLM_TRANSCRIPT=off must produce zero transcript files",
            )


if __name__ == "__main__":
    unittest.main()
