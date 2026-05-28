"""Tests for PR-3 CrafterLLMActionProducer."""

from __future__ import annotations

import json
import unittest
from typing import Any

from eva.anchor.domain_restriction import build_action_domain
from eva.l3_deliberation import build_deliberation_input
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


def _observation(
    *,
    health: int = 9,
    food: int = 7,
    water: int = 7,
    energy: int = 8,
    cells: list[list[str]] | None = None,
    facing: str = "left",
    inventory: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "symbolic_observation_v0",
        "episode_id": "ep",
        "step": 1,
        "visible": {
            "life_panel": {
                "values": {
                    "health": health,
                    "food": food,
                    "water": water,
                    "energy": energy,
                }
            },
            "inventory_panel": {"items": inventory or {}},
            "facing": facing,
            "local_view": {
                "format": "semantic_grid",
                "width": 3,
                "height": 3,
                "center": {"row": 1, "col": 1},
                "cells": cells
                or [
                    ["grass", "grass", "grass"],
                    ["grass", "player", "grass"],
                    ["grass", "grass", "grass"],
                ],
            },
        },
    }


def _deliberation_input(
    *,
    top_drive: str = "metabolic",
    drive_levels: dict[str, float] | None = None,
    pressure_reason: str = "none",
    working_memory: dict[str, Any] | None = None,
) -> Any:
    levels = drive_levels or {
        "metabolic": 0.3,
        "safety": 0.1,
        "recovery": 0.1,
        "acquisition": 0.2,
        "capability": 0.1,
        "exploration": 0.1,
    }
    return build_deliberation_input(
        signal_batch={
            "signals": [{"class": "status"}],
            "summary": {
                "signal_count": 1,
                "status_signal_count": 1,
                "threat_signal_count": 0,
                "background_signal_count": 0,
                "has_threat_signal": False,
            },
        },
        drive_broadcast={
            "top_drive": top_drive,
            "drive_levels": levels,
            "drive_trends": {name: "unknown" for name in levels},
        },
        runtime_gate_context={
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
        },
        pressure_table={
            "pressures": [
                {
                    "type": "integrity",
                    "severity": "normal",
                    "evidence": {"reason": pressure_reason},
                }
            ]
        },
        working_memory_context=working_memory,
    )


def _stub_chat(response_json: dict[str, Any]) -> Any:
    """Return a chat_fn stub that always returns the given JSON."""
    text = json.dumps(response_json)

    def chat_fn(messages: list[dict[str, str]]) -> str:
        return text

    return chat_fn


class TestCrafterLLMActionProducerNoLLM(unittest.TestCase):
    """Producer with chat_fn=None returns empty list."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_no_chat_fn_returns_empty(self) -> None:
        producer = CrafterLLMActionProducer(chat_fn=None)
        di = _deliberation_input()
        domain = build_action_domain(di)
        result = producer.produce(domain, di)
        self.assertEqual(result, [])


class TestCrafterLLMActionProducerCandidateFormat(unittest.TestCase):
    """Produced candidates carry raw actions and correct structure."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_candidate_has_raw_action(self) -> None:
        chat_fn = _stub_chat(
            {"candidates": [{"action": "move_left", "reason": "water nearby"}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.5,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.2,
                "capability": 0.1,
                "exploration": 0.1,
            },
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)
        c = candidates[0]
        self.assertEqual(c.action, "move_left")
        self.assertEqual(c.capability, "raw_action")
        self.assertEqual(c.side_effect_class, "crafter_raw_action")

    def test_candidate_id_format(self) -> None:
        chat_fn = _stub_chat(
            {"candidates": [{"action": "move_right", "reason": "explore"}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            top_drive="acquisition",
            drive_levels={
                "metabolic": 0.1,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.6,
                "capability": 0.1,
                "exploration": 0.1,
            },
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)
        # candidate_id uses hyphens, not underscores
        self.assertEqual(candidates[0].candidate_id, "candidate-crafter-move-right")

    def test_candidate_parameter_domain_has_gate_fields(self) -> None:
        chat_fn = _stub_chat(
            {"candidates": [{"action": "move_up", "reason": "explore"}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)
        pd = candidates[0].parameter_domain
        # Gate fields must be present for conflict_detection to process the candidate
        self.assertIn("turn_allowed", pd)
        self.assertIn("instance_valid", pd)
        self.assertIn("critical_blocked", pd)
        self.assertIn("life_state", pd)
        self.assertIn("conservative_mode", pd)
        # Marked as raw_action for conflict_detection._is_raw_action_candidate
        self.assertTrue(pd.get("raw_action_candidate") is True)
        self.assertEqual(pd.get("candidate_kind"), "raw_action")

    def test_justification_includes_llm_reason(self) -> None:
        """LLM reason should be carried in justification for audit replay."""
        chat_fn = _stub_chat(
            {"candidates": [{"action": "move_left", "reason": "water visible to the left"}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.5,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.2,
                "capability": 0.1,
                "exploration": 0.1,
            },
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)
        justification_text = " ".join(candidates[0].justification)
        self.assertIn("water visible to the left", justification_text)

    def test_justification_truncates_long_reason(self) -> None:
        long_reason = "x" * 200
        chat_fn = _stub_chat(
            {"candidates": [{"action": "move_left", "reason": long_reason}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)
        # Reason in justification capped at 80 chars
        reason_entry = next(
            (j for j in candidates[0].justification if j.startswith("reason=")), ""
        )
        self.assertTrue(reason_entry)
        # Strip "reason=" prefix → check truncation
        self.assertLessEqual(len(reason_entry) - len("reason="), 80)

    def test_justification_omits_empty_reason(self) -> None:
        chat_fn = _stub_chat({"candidates": [{"action": "move_left", "reason": ""}]})
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)
        # No "reason=" entry when LLM provided no reason
        for entry in candidates[0].justification:
            self.assertFalse(entry.startswith("reason="))

    def test_candidate_has_no_compatibility_release_shell(self) -> None:
        chat_fn = _stub_chat(
            {"candidates": [{"action": "do", "reason": "collect resource"}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            top_drive="acquisition",
            drive_levels={
                "metabolic": 0.1,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.7,
                "capability": 0.1,
                "exploration": 0.1,
            },
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        for c in candidates:
            self.assertNotEqual(c.action, "compatibility_release")
            self.assertNotIn("action_hint", c.parameter_domain)


class TestCrafterLLMActionProducerDomainFiltering(unittest.TestCase):
    """Candidates outside A'(s) are discarded."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_out_of_domain_action_discarded(self) -> None:
        # When water is critical, A'(s) is restricted to move_* only.
        # An LLM-returned "sleep" or "do" must be discarded.
        chat_fn = _stub_chat(
            {
                "candidates": [
                    {"action": "sleep", "reason": "rest"},         # outside A'(s)
                    {"action": "move_left", "reason": "find water"},  # inside
                ]
            }
        )
        obs = _observation(water=1)
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        # water_critical pressure triggers anchor to restrict A'(s) to move_*
        di = _deliberation_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.9,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
                "exploration": 0.1,
            },
            pressure_reason="water_critical",
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        actions = {c.action for c in candidates}
        # "sleep" must be absent (not in A'(s) under water_critical)
        self.assertNotIn("sleep", actions)
        # "move_left" should be present
        self.assertIn("move_left", actions)

    def test_all_invalid_actions_returns_empty(self) -> None:
        # LLM returns only actions outside A'(s).
        chat_fn = _stub_chat(
            {
                "candidates": [
                    {"action": "fly", "reason": "invented"},
                    {"action": "teleport", "reason": "invented"},
                ]
            }
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertEqual(candidates, [])

    def test_duplicate_actions_deduplicated(self) -> None:
        chat_fn = _stub_chat(
            {
                "candidates": [
                    {"action": "move_left", "reason": "first"},
                    {"action": "move_left", "reason": "duplicate"},
                    {"action": "move_right", "reason": "second"},
                ]
            }
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        actions = [c.action for c in candidates]
        self.assertEqual(len(actions), len(set(actions)), "duplicate actions should be removed")

    def test_max_three_candidates(self) -> None:
        chat_fn = _stub_chat(
            {
                "candidates": [
                    {"action": "move_left", "reason": "a"},
                    {"action": "move_right", "reason": "b"},
                    {"action": "move_up", "reason": "c"},
                    {"action": "move_down", "reason": "d"},  # 4th → capped
                ]
            }
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertLessEqual(len(candidates), 3)


class TestCrafterLLMActionProducerFallback(unittest.TestCase):
    """Producer falls back to empty list on LLM errors."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_exception_in_chat_fn_returns_empty(self) -> None:
        def bad_chat(messages: list[dict[str, str]]) -> str:
            raise RuntimeError("transport error")

        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=bad_chat,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertEqual(candidates, [])

    def test_unparseable_response_returns_empty(self) -> None:
        def garbage_chat(messages: list[dict[str, str]]) -> str:
            return "not valid json at all"

        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=garbage_chat,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertEqual(candidates, [])

    def test_empty_candidates_in_response(self) -> None:
        chat_fn = _stub_chat({"candidates": []})
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertEqual(candidates, [])


class TestCrafterLLMActionProducerPromptContent(unittest.TestCase):
    """Prompt includes state packet, A'(s), and world facts."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_prompt_contains_admitted_actions(self) -> None:
        captured: list[list[dict[str, str]]] = []

        def capturing_chat(messages: list[dict[str, str]]) -> str:
            captured.append(messages)
            return json.dumps({"candidates": [{"action": "move_left", "reason": "test"}]})

        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=capturing_chat,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        producer.produce(domain, di)
        self.assertEqual(len(captured), 1)
        user_msg = next(m["content"] for m in captured[0] if m["role"] == "user")
        self.assertIn("admitted_actions", user_msg)

    def test_prompt_contains_state_packet(self) -> None:
        captured: list[list[dict[str, str]]] = []

        def capturing_chat(messages: list[dict[str, str]]) -> str:
            captured.append(messages)
            return json.dumps({"candidates": [{"action": "move_left", "reason": "test"}]})

        obs = _observation(water=3, health=5)
        producer = CrafterLLMActionProducer(
            chat_fn=capturing_chat,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        producer.produce(domain, di)
        user_msg = next(m["content"] for m in captured[0] if m["role"] == "user")
        self.assertIn("state_packet", user_msg)

    def test_world_facts_injected_into_system_prompt(self) -> None:
        captured: list[list[dict[str, str]]] = []

        def capturing_chat(messages: list[dict[str, str]]) -> str:
            captured.append(messages)
            return json.dumps({"candidates": [{"action": "move_left", "reason": "test"}]})

        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=capturing_chat,
            world_facts_fn=lambda: "CRAFTER_WORLD_FACTS_BLOCK",
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        producer.produce(domain, di)
        sys_msg = next(m["content"] for m in captured[0] if m["role"] == "system")
        self.assertIn("CRAFTER_WORLD_FACTS_BLOCK", sys_msg)

    def test_no_world_facts_fn_no_block(self) -> None:
        captured: list[list[dict[str, str]]] = []

        def capturing_chat(messages: list[dict[str, str]]) -> str:
            captured.append(messages)
            return json.dumps({"candidates": [{"action": "move_left", "reason": "test"}]})

        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=capturing_chat,
            world_facts_fn=None,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        producer.produce(domain, di)
        sys_msg = next(m["content"] for m in captured[0] if m["role"] == "system")
        self.assertNotIn("Background world facts", sys_msg)

    def test_recent_memory_included_when_present(self) -> None:
        captured: list[list[dict[str, str]]] = []

        def capturing_chat(messages: list[dict[str, str]]) -> str:
            captured.append(messages)
            return json.dumps({"candidates": [{"action": "move_left", "reason": "test"}]})

        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=capturing_chat,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            working_memory={"summary": "recent_memory_sentinel_value"}
        )
        domain = build_action_domain(di)
        producer.produce(domain, di)
        user_msg = next(m["content"] for m in captured[0] if m["role"] == "user")
        self.assertIn("recent_memory_sentinel_value", user_msg)


class TestCrafterLLMActionProducerAssessmentPath(unittest.TestCase):
    """Produced candidates can be assessed by PR-0's value_judgment path."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_raw_action_candidates_can_be_assessed(self) -> None:
        chat_fn = _stub_chat(
            {
                "candidates": [
                    {"action": "move_left", "reason": "water nearby"},
                    {"action": "move_right", "reason": "alternate path"},
                ]
            }
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.6,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
                "exploration": 0.1,
            },
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        self.assertTrue(len(candidates) >= 1)

        # PR-0 ensured raw-action candidates can be assessed.
        assessments = assess_candidates(candidates, di)
        self.assertEqual(len(assessments), len(candidates))
        for assessment in assessments:
            self.assertIn(assessment.disposition, {"allow", "defer", "withhold"})

    def test_assess_allows_valid_raw_action_candidate(self) -> None:
        """With instance_valid + turn_allowed and drive pressure, disposition == allow."""
        chat_fn = _stub_chat(
            {"candidates": [{"action": "move_left", "reason": "find water"}]}
        )
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.8,  # high enough to pass DRIVE_LEVEL_RELEASE_THRESHOLD
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
                "exploration": 0.1,
            },
        )
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        assessments = assess_candidates(candidates, di)
        # At least one candidate should be allowed
        dispositions = {a.disposition for a in assessments}
        self.assertIn("allow", dispositions)


class TestCrafterLLMActionProducerDriveImpact(unittest.TestCase):
    """drive_impact_schema is set based on action category."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def _get_candidate_for_action(self, action: str) -> Any:
        chat_fn = _stub_chat({"candidates": [{"action": action, "reason": "test"}]})
        obs = _observation()
        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            observation_fn=lambda: obs,
        )
        di = _deliberation_input()
        domain = build_action_domain(di)
        candidates = producer.produce(domain, di)
        return candidates[0] if candidates else None

    def test_move_action_has_metabolic_impact(self) -> None:
        c = self._get_candidate_for_action("move_left")
        if c is None:
            self.skipTest("move_left not in A'(s) for default state")
        self.assertIn("metabolic", c.drive_impact_schema)
        self.assertGreater(c.drive_impact_schema["metabolic"], 0.0)

    def test_sleep_has_recovery_impact(self) -> None:
        c = self._get_candidate_for_action("sleep")
        if c is None:
            self.skipTest("sleep not in A'(s) for default state")
        self.assertIn("recovery", c.drive_impact_schema)
        self.assertGreater(c.drive_impact_schema["recovery"], 0.0)


if __name__ == "__main__":
    unittest.main()
