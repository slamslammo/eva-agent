"""PR-Β': §5.4.3 plausibility annotation + producer wires v1.1 hashes.

Two pieces:
1. Crafter dlPFC role contract gains a "plausibility 标注" section per
   plan §5.4.3 (line 401-407): dlPFC may annotate each candidate reason
   with plausibility / confidence / primary_reason.
2. CrafterLLMActionProducer computes ontology_hash / world_facts_hash /
   action_effect_schema_hash from CRAFTER_SCENARIO_ONTOLOGY and passes them
   to the transcript sink. Hash failures must NOT break candidate emission.
"""

from __future__ import annotations

import json
import unittest

from eva.l3_deliberation.contracts import build_deliberation_input
from eva.anchor import build_action_domain
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


def _di() -> object:
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {"acquisition": 0.8, "metabolic": 0.4, "safety": 0.3,
                             "recovery": 0.3, "capability": 0.4, "exploration": 0.2},
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True, "turn_allowed": True,
            "critical_blocked": False, "conservative_mode": False, "life_state": "STABLE",
        },
    )


def _obs() -> dict:
    return {
        "schema_version": "symbolic_observation_v0",
        "episode_id": "ep", "step": 1,
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


class _CapturingSink:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record(self, **kwargs) -> str | None:
        self.calls.append(kwargs)
        return "captured/turn-000.json"


class CrafterRoleContractPlausibilityTests(unittest.TestCase):
    """Plan §5.4.3 plausibility 标注 section must be present in role contract."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_role_contract_mentions_plausibility_annotation_allowed(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        self.assertIn("plausibility", body)

    def test_role_contract_mentions_confidence_and_primary_reason(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        self.assertIn("confidence", body)
        self.assertIn("primary_reason", body)

    def test_role_contract_states_ofc_does_not_consume_plausibility_yet(self) -> None:
        """Plan §5.4.3 line 406: OFC currently does not consume; transcript preserves."""
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        # Body should make clear OFC doesn't yet consume this annotation, but transcript keeps it.
        self.assertIn("OFC", body)
        self.assertIn("transcript", body)


class CrafterProducerOntologyHashTests(unittest.TestCase):
    """Producer computes 3 sha256:hex16 hashes from scenario_ontology + passes to sink."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def _producer(self, sink) -> CrafterLLMActionProducer:
        from scenarios.crafter.ontology import CRAFTER_SCENARIO_ONTOLOGY
        return CrafterLLMActionProducer(
            chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "r"}]}),
            observation_fn=_obs,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
            scenario_ontology=CRAFTER_SCENARIO_ONTOLOGY,
        )

    def test_producer_passes_three_hash_fields_to_sink(self) -> None:
        sink = _CapturingSink()
        producer = self._producer(sink)
        di = _di()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        self.assertEqual(len(sink.calls), 1)
        call = sink.calls[0]
        for field in ("ontology_hash", "world_facts_hash", "action_effect_schema_hash"):
            self.assertIn(field, call)
            value = call[field]
            self.assertIsInstance(value, str)
            self.assertTrue(value.startswith("sha256:"), f"{field}={value!r} should start with sha256:")
            # hex16 after the prefix
            self.assertEqual(len(value), len("sha256:") + 16, f"{field}={value!r} expected 16 hex chars")

    def test_hashes_deterministic_for_same_ontology(self) -> None:
        """Same ontology → same hash on every call (no time/randomness in computation)."""
        sink = _CapturingSink()
        producer = self._producer(sink)
        di = _di()
        ad = build_action_domain(di)
        producer.produce(ad, di)
        producer.produce(ad, di)

        self.assertEqual(len(sink.calls), 2)
        for field in ("ontology_hash", "world_facts_hash", "action_effect_schema_hash"):
            self.assertEqual(sink.calls[0][field], sink.calls[1][field],
                             f"{field} should be deterministic")

    def test_no_scenario_ontology_omits_hash_fields(self) -> None:
        """Producer without scenario_ontology must NOT pass hash fields to sink."""
        sink = _CapturingSink()
        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: json.dumps({"candidates": [{"action": "do", "reason": "r"}]}),
            observation_fn=_obs,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
            # scenario_ontology omitted → no hashes available
        )
        di = _di()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        # The call may omit the keys entirely, or pass them as None — both OK.
        call = sink.calls[0]
        for field in ("ontology_hash", "world_facts_hash", "action_effect_schema_hash"):
            self.assertIsNone(call.get(field), f"{field} should be None when no scenario_ontology")

    def test_hash_compute_failure_does_not_break_candidate_emission(self) -> None:
        """R3 §5.5b: even if hash computation specifically fails, candidates still emit.

        Patches one of the ontology component's ``format_text`` to raise — the
        prompt assembly path uses these too, so to isolate the hash failure we
        target the hash-only path by patching the producer's compute helper.
        """
        from unittest.mock import patch

        sink = _CapturingSink()
        producer = self._producer(sink)
        di = _di()
        ad = build_action_domain(di)

        # Force the hash compute method to raise; producer must swallow and still emit.
        with patch.object(
            producer, "_compute_ontology_hashes_safely",
            side_effect=RuntimeError("hash backend offline"),
        ):
            try:
                candidates = producer.produce(ad, di)
            except Exception as exc:
                self.fail(f"hash failure must not propagate; got {type(exc).__name__}: {exc}")
        self.assertEqual(len(candidates), 1, "candidate emission survives hash failure")
        self.assertEqual(candidates[0].action, "do")


if __name__ == "__main__":
    unittest.main()
