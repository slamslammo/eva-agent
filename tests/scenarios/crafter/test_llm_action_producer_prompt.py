"""PR-Β Slice 5: CrafterLLMActionProducer system prompt now injects 6 ontology sections.

After PR-Β, the system prompt assembled by ``_build_messages`` must contain
the 6 sections from ``CRAFTER_SCENARIO_ONTOLOGY`` (role / drive / salience /
action / effect / world facts) in canonical order, and the producer's
``prompt_sections_present`` metadata recorded to the transcript sink must
reflect each section's actual presence (not a hard-coded stub).

Red lines:
- Body text must match the §5.4 草稿 verbatim (the ontology modules are the
  source of truth; tests verify producer wires them through, not what they say)
- ``prompt_sections_present`` keys are: world_facts / drive_ontology /
  salience_spec / action_ontology / action_effect_schema / dlpfc_role_contract
"""

from __future__ import annotations

import json
import unittest

from eva.l3_deliberation.contracts import build_deliberation_input
from eva.anchor import build_action_domain
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


def _deliberation_input() -> object:
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {
                "acquisition": 0.8, "metabolic": 0.4, "safety": 0.3,
                "recovery": 0.3, "capability": 0.4, "exploration": 0.2,
            },
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True, "turn_allowed": True,
            "critical_blocked": False, "conservative_mode": False,
            "life_state": "STABLE",
        },
    )


def _observation() -> dict:
    return {
        "schema_version": "symbolic_observation_v0",
        "episode_id": "ep", "step": 1,
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


class _CapturingSink:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record(self, **kwargs) -> str | None:
        self.calls.append(kwargs)
        return "captured/turn-001.json"


def _producer_with_ontology(capture_sink: _CapturingSink) -> CrafterLLMActionProducer:
    from scenarios.crafter.ontology import CRAFTER_SCENARIO_ONTOLOGY
    return CrafterLLMActionProducer(
        chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "r"}]}),
        observation_fn=_observation,
        transcript_sink=capture_sink,
        identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
        scenario_ontology=CRAFTER_SCENARIO_ONTOLOGY,
    )


class PromptInjectsSixOntologySectionsTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_system_prompt_contains_six_canonical_section_headers(self) -> None:
        sink = _CapturingSink()
        producer = _producer_with_ontology(sink)
        di = _deliberation_input()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        self.assertEqual(len(sink.calls), 1)
        messages = sink.calls[0]["messages"]
        system_content = messages[0]["content"]
        for header in (
            "=== EVA dlPFC Role ===",
            "=== Drive Ontology ===",
            "=== Salience Spec ===",
            "=== Action Ontology ===",
            "=== Action Effect Schema ===",
            "=== Crafter World Facts ===",
        ):
            self.assertIn(header, system_content, f"missing section {header}")

    def test_system_prompt_contains_drive_names_and_action_names(self) -> None:
        """The injected ontology must carry real drive + action names from CRAFTER_SCENARIO_ONTOLOGY."""
        sink = _CapturingSink()
        producer = _producer_with_ontology(sink)
        di = _deliberation_input()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        system_content = sink.calls[0]["messages"][0]["content"]
        # All 6 drives must appear by name
        for drive in ("metabolic", "safety", "recovery", "acquisition", "capability", "exploration"):
            self.assertIn(drive, system_content)
        # All raw action names should appear in either action ontology or effect schema
        for action in ("noop", "do", "sleep", "move_left", "move_right", "move_up", "move_down",
                       "make_wood_pickaxe", "place_table"):
            self.assertIn(action, system_content)


class PromptSectionsPresentMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_prompt_sections_present_reflects_all_six_sections_true(self) -> None:
        sink = _CapturingSink()
        producer = _producer_with_ontology(sink)
        di = _deliberation_input()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        sections = sink.calls[0]["prompt_sections_present"]
        # All 6 ontology sections must be True (wired via CRAFTER_SCENARIO_ONTOLOGY)
        self.assertTrue(sections.get("dlpfc_role_contract"))
        self.assertTrue(sections.get("drive_ontology"))
        self.assertTrue(sections.get("salience_spec"))
        self.assertTrue(sections.get("action_ontology"))
        self.assertTrue(sections.get("action_effect_schema"))
        self.assertTrue(sections.get("world_facts"))
        # state_packet and admitted_actions remain true (user-prompt scope)
        self.assertTrue(sections.get("state_packet"))
        self.assertTrue(sections.get("admitted_actions"))


class UserPromptStillCarriesStateAndAdmittedActionsTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_user_prompt_contains_state_packet_and_admitted_actions(self) -> None:
        sink = _CapturingSink()
        producer = _producer_with_ontology(sink)
        di = _deliberation_input()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        messages = sink.calls[0]["messages"]
        user_content = messages[-1]["content"]
        self.assertIn("state_packet", user_content)
        self.assertIn("admitted_actions", user_content)


if __name__ == "__main__":
    unittest.main()
