"""PR-Α: CrafterLLMActionProducer transcript_sink integration.

Producer records each LLM call to the sink before/after ``chat_fn`` and
threads the returned ref through each emitted Candidate's parameter_domain
as ``dlpfc_proposal_ref`` so the mediator can pick it up at release time.

Red lines:
- R2: sink=None or NoOp must keep zero overhead (no extra args required)
- R3: sink record failure must NOT break candidate emission
- backward compat: existing constructions (no sink, no identity_provider)
  must work unchanged
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from eva.l3_deliberation.contracts import build_deliberation_input
from eva.l3_deliberation.llm_transcript import (
    FileBasedTranscriptSink,
    LLMTranscriptSink,
    NoOpTranscriptSink,
)
from eva.anchor import build_action_domain
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.reasoning import CrafterLLMActionProducer


def _deliberation_input(top_drive: str = "acquisition") -> object:
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": top_drive,
            "drive_levels": {
                "acquisition": 0.8,
                "metabolic": 0.4,
                "safety": 0.3,
                "recovery": 0.3,
                "capability": 0.4,
                "exploration": 0.2,
            },
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
        },
    )


def _observation() -> dict:
    return {
        "schema_version": "symbolic_observation_v0",
        "episode_id": "ep",
        "step": 1,
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


class _RecordingSink:
    """Test sink that captures every record() call."""

    def __init__(self, *, ref: str | None = "test_ref/turn-000001.json") -> None:
        self.calls: list[dict] = []
        self._ref = ref

    def record(self, **kwargs) -> str | None:
        self.calls.append(kwargs)
        return self._ref


class CrafterLLMActionProducerSinkAcceptsTests(unittest.TestCase):
    """Producer accepts transcript_sink + identity_provider as optional kwargs."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_constructor_without_sink_works_unchanged(self) -> None:
        # Backward compat: existing usage (no sink) must not error.
        p = CrafterLLMActionProducer(chat_fn=lambda m: '{"candidates":[]}')
        self.assertIsNotNone(p)

    def test_constructor_accepts_transcript_sink(self) -> None:
        sink = NoOpTranscriptSink()
        p = CrafterLLMActionProducer(
            chat_fn=lambda m: '{"candidates":[]}',
            transcript_sink=sink,
        )
        self.assertIsNotNone(p)

    def test_constructor_accepts_identity_provider(self) -> None:
        p = CrafterLLMActionProducer(
            chat_fn=lambda m: '{"candidates":[]}',
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
        )
        self.assertIsNotNone(p)


class CrafterLLMActionProducerSinkRecordingTests(unittest.TestCase):
    """Producer records transcript before/after chat_fn call."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_successful_call_records_transcript_with_ok_status(self) -> None:
        sink = _RecordingSink()
        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: '{"candidates":[{"action":"do","reason":"acquire"}]}',
            observation_fn=_observation,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "run-A", "individual_id": "ind-B", "turn_index": 42},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        candidates = producer.produce(ad, di)

        self.assertEqual(len(sink.calls), 1)
        call = sink.calls[0]
        self.assertEqual(call["run_id"], "run-A")
        self.assertEqual(call["individual_id"], "ind-B")
        self.assertEqual(call["turn_index"], 42)
        self.assertEqual(call["llm_role"], "dlPFC")
        self.assertEqual(call["scenario"], "crafter")
        self.assertEqual(call["parse_status"], "ok")
        self.assertEqual(call["errors"], [])
        self.assertEqual(call["raw_response"], '{"candidates":[{"action":"do","reason":"acquire"}]}')
        self.assertEqual(call["parsed_response"], {"candidates": [{"action": "do", "reason": "acquire"}]})
        # messages contain at least system + user
        self.assertGreaterEqual(len(call["messages"]), 2)
        self.assertIsInstance(call["prompt_sections_present"], dict)
        self.assertEqual(len(candidates), 1)

    def test_returned_ref_attached_to_candidates_parameter_domain(self) -> None:
        sink = _RecordingSink(ref="llm_transcripts/dlPFC/turn-000042.json")
        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: '{"candidates":[{"action":"do","reason":"r"}]}',
            observation_fn=_observation,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 42},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        candidates = producer.produce(ad, di)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0].parameter_domain.get("dlpfc_proposal_ref"),
            "llm_transcripts/dlPFC/turn-000042.json",
        )

    def test_noop_sink_returns_none_ref_no_field_on_candidates(self) -> None:
        """When sink is NoOp (returns None), candidates carry no dlpfc_proposal_ref."""
        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: '{"candidates":[{"action":"do","reason":"r"}]}',
            observation_fn=_observation,
            transcript_sink=NoOpTranscriptSink(),
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        candidates = producer.produce(ad, di)
        self.assertEqual(len(candidates), 1)
        # dlpfc_proposal_ref should be absent or None
        self.assertIsNone(candidates[0].parameter_domain.get("dlpfc_proposal_ref"))

    def test_parse_error_records_parse_error_status(self) -> None:
        """When chat_fn returns invalid JSON, sink records parse_error status."""
        sink = _RecordingSink()
        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: "this is not json",
            observation_fn=_observation,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 5},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        producer.produce(ad, di)

        self.assertEqual(len(sink.calls), 1)
        call = sink.calls[0]
        self.assertEqual(call["parse_status"], "parse_error")
        self.assertEqual(call["raw_response"], "this is not json")
        # errors list should have at least one entry describing the failure
        self.assertGreaterEqual(len(call["errors"]), 1)

    def test_transport_error_records_transport_error_status(self) -> None:
        """When chat_fn raises, sink records transport_error and producer returns []."""
        sink = _RecordingSink()

        def _raising(_messages):
            raise RuntimeError("network unreachable")

        producer = CrafterLLMActionProducer(
            chat_fn=_raising,
            observation_fn=_observation,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 7},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        candidates = producer.produce(ad, di)

        self.assertEqual(candidates, [])
        self.assertEqual(len(sink.calls), 1)
        call = sink.calls[0]
        self.assertEqual(call["parse_status"], "transport_error")
        self.assertTrue(any("network unreachable" in e for e in call["errors"]))

    def test_sink_record_failure_does_not_break_candidate_emission(self) -> None:
        """R3: if sink itself raises, producer must still return candidates."""

        class _FailingSink:
            def record(self, **kwargs):
                raise IOError("disk full")

        producer = CrafterLLMActionProducer(
            chat_fn=lambda m: '{"candidates":[{"action":"do","reason":"r"}]}',
            observation_fn=_observation,
            transcript_sink=_FailingSink(),
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        candidates = producer.produce(ad, di)
        # Sink failure must not propagate; candidates still produced.
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].action, "do")


class CrafterLLMActionProducerNoChatFnTests(unittest.TestCase):
    """When chat_fn is None, transcript sink must NOT be called."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_chat_fn_none_does_not_record_transcript(self) -> None:
        sink = _RecordingSink()
        producer = CrafterLLMActionProducer(
            chat_fn=None,
            observation_fn=_observation,
            transcript_sink=sink,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
        )
        di = _deliberation_input()
        ad = build_action_domain(di)
        result = producer.produce(ad, di)
        self.assertEqual(result, [])
        self.assertEqual(sink.calls, [], "No transcript when chat_fn is None (no call made)")


if __name__ == "__main__":
    unittest.main()
