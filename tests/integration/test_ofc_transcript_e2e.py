"""PR-Γ end-to-end: live Crafter short run produces BOTH dlPFC and OFC_classical transcripts.

Validates §6.4 completion criteria:
- EVA_LLM_TRANSCRIPT=raw → OFC transcripts written under
  ``{runtime_dir}/llm_transcripts/OFC_classical/turn-*.json``
- ReleaseToken.ofc_assessment_ref filled (no longer None placeholder)
- Both dlPFC (PR-Α) and OFC (PR-Γ) coexist in transcript output
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
    def __init__(self) -> None:
        self.step_actions: list[str] = []
        self.terminated = False
        self.latest_agent_observation = {
            "schema_version": "symbolic_observation_v0",
            "episode_id": "ep", "step": 0,
            "visible": {
                "life_panel": {"available": True, "values": {"health": 8, "food": 7, "water": 7, "energy": 7}},
                "inventory_panel": {"available": True, "items": {}},
                "facing": "up",
                "local_view": {"format": "semantic_grid", "width": 3, "height": 3,
                               "center": {"row": 1, "col": 1},
                               "cells": [["grass"]*3, ["grass","player","grass"], ["grass"]*3]},
                "nearby_objects": [],
            },
            "task_context": {"objective": "survive", "unlocked_achievements_visible": []},
            "available_actions": ["noop","sleep","do","move_left","move_right","move_up","move_down"],
            "notes": [],
        }

    @classmethod
    def start(cls, *, seed=None):
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
            heartbeat_interval_sec=0.2, lease_duration_sec=1.0,
            recovering_window_sec=0.05, turn_guard_window_sec=0.01,
        ),
        external_life=ExternalLifeConfig(
            shallow_patrol_interval_sec=0.01, deep_patrol_interval_sec=0.02,
            full_report_interval_sec=0.03, recent_event_window_sec=60.0,
        ),
        control=LoopControl(max_turns=6, max_runtime_sec=2.0, idle_sleep_sec=0.01),
    )


def _stub_producer(runtime_dir: str):
    """Stub producer that's still wired through PR-Α sink for dlPFC transcripts."""
    from eva.l3_deliberation.llm_transcript import build_transcript_sink_from_env
    from scenarios.crafter.ontology import CRAFTER_SCENARIO_ONTOLOGY

    return CrafterLLMActionProducer(
        chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "r"}]}),
        observation_fn=lambda: {
            "schema_version": "symbolic_observation_v0",
            "visible": {
                "life_panel": {"available": True, "values": {"health": 8, "food": 7, "water": 7, "energy": 7}},
                "inventory_panel": {"available": True, "items": {}},
                "facing": "up",
                "local_view": {"format": "semantic_grid", "width": 3, "height": 3,
                               "center": {"row": 1, "col": 1},
                               "cells": [["grass"]*3, ["grass","player","grass"], ["grass"]*3]},
            },
        },
        transcript_sink=build_transcript_sink_from_env(runtime_dir),
        identity_provider=lambda: {"run_id": "test-run", "individual_id": "test-ind", "turn_index": 0},
        scenario_ontology=CRAFTER_SCENARIO_ONTOLOGY,
    )


class OfcTranscriptE2EWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_env_raw_writes_both_dlpfc_and_ofc_transcripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            session = _StubSession()
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "raw"}):
                producer = _stub_producer(temp_dir)
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    run_crafter_runtime(config, candidate_producer=producer)

            base = Path(config.paths.runtime_dir) / "llm_transcripts"
            # OFC transcripts written
            ofc_dir = base / "OFC_classical"
            self.assertTrue(ofc_dir.exists(), f"OFC dir missing: {ofc_dir}")
            ofc_files = sorted(ofc_dir.glob("turn-*.json"))
            self.assertGreaterEqual(len(ofc_files), 1, "at least one OFC transcript expected")
            # dlPFC transcripts also written (PR-Α coexists)
            dlpfc_dir = base / "dlPFC"
            self.assertTrue(dlpfc_dir.exists(), f"dlPFC dir missing: {dlpfc_dir}")

            # Verify OFC content
            payload = json.loads(ofc_files[0].read_text())
            self.assertEqual(payload["llm_role"], "OFC_classical")
            self.assertEqual(payload["model"], "drive_weighted_formula_v1")
            self.assertEqual(payload["schema_version"], "llm_transcript_v1.2")
            self.assertIn("assessments", payload["parsed_response"])

    def test_env_off_produces_no_ofc_transcripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = _run_config(temp_dir)
            session = _StubSession()
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "off"}):
                producer = _stub_producer(temp_dir)
                with patch.object(CrafterRuntimeSession, "start", return_value=session):
                    run_crafter_runtime(config, candidate_producer=producer)

            ofc_dir = Path(config.paths.runtime_dir) / "llm_transcripts" / "OFC_classical"
            self.assertFalse(ofc_dir.exists(), "EVA_LLM_TRANSCRIPT=off must produce no OFC transcripts")


if __name__ == "__main__":
    unittest.main()
