"""Round 1.G phase 2 (a) — LLMCandidateProducer unit tests (stub chat_fn, token-free).

Pins the action_hint lever invariants: a valid in-vocab hint is attached to the
matching posture; an ineligible hint is dropped; the producer never adds/removes
candidates or changes profiles (drive-locked posture preserved); and any
transport / parse failure or missing vocab degrades to the heuristic base
(behavior-preserving).
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from eva.anchor import build_action_domain
from eva.l3_deliberation.contracts import build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_producer import (
    CandidateProducer,
    HeuristicCandidateProducer,
)
from eva.l3_deliberation.reasoning.llm_candidate_producer import LLMCandidateProducer
from scenarios.crafter import activate_crafter_scenario


_VOCAB = {
    "escalate_first": ("do", "make_wood_pickaxe", "place_table"),
    "stabilize_first": ("sleep", "noop"),
    "observe_first": ("noop", "move_left", "move_right"),
}


def _deliberation_input():
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {
                "acquisition": 0.8,
                "metabolic": 0.5,
                "safety": 0.4,
                "recovery": 0.3,
                "capability": 0.6,
                "exploration": 0.1,
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


class _StubChat:
    """Stub chat_fn: records calls, returns canned text (or raises)."""

    def __init__(self, text: str | None = None, *, raises: Exception | None = None) -> None:
        self.text = text
        self.raises = raises
        self.calls = 0

    def __call__(self, messages):
        self.calls += 1
        self.last_messages = messages
        if self.raises is not None:
            raise self.raises
        return self.text


class LLMCandidateProducerTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 21, tzinfo=timezone.utc)
        self.di = _deliberation_input()
        self.domain = build_action_domain(self.di)
        self.base_ids = [c.candidate_id for c in HeuristicCandidateProducer().produce(self.domain, self.di)]
        self.base_profiles = {
            c.candidate_id: c.parameter_domain.get("candidate_profile")
            for c in HeuristicCandidateProducer().produce(self.domain, self.di)
        }

    def _produce(self, chat) -> list:
        producer = LLMCandidateProducer(chat_fn=chat, profile_action_vocab=_VOCAB)
        return producer.produce(self.domain, self.di)

    def test_satisfies_candidate_producer_protocol(self) -> None:
        self.assertIsInstance(LLMCandidateProducer(), CandidateProducer)

    def test_valid_in_vocab_hint_is_attached(self) -> None:
        chat = _StubChat(
            '{"action_hints": {"escalate_first": "make_wood_pickaxe", '
            '"stabilize_first": "sleep", "observe_first": "move_left"}}'
        )
        produced = self._produce(chat)
        self.assertEqual(chat.calls, 1)
        expected = {
            "escalate_first": "make_wood_pickaxe",
            "stabilize_first": "sleep",
            "observe_first": "move_left",
        }
        for candidate in produced:
            profile = candidate.parameter_domain.get("candidate_profile")
            self.assertEqual(candidate.action_hint, expected.get(profile))

    def test_ineligible_hint_is_dropped(self) -> None:
        chat = _StubChat('{"action_hints": {"escalate_first": "fly_to_moon"}}')
        produced = self._produce(chat)
        for candidate in produced:
            self.assertIsNone(candidate.action_hint)

    def test_membership_and_profiles_are_preserved(self) -> None:
        chat = _StubChat('{"action_hints": {"escalate_first": "do"}}')
        produced = self._produce(chat)
        # Never adds / removes candidates …
        self.assertEqual([c.candidate_id for c in produced], self.base_ids)
        # … and never changes a candidate's profile (drive-locked posture).
        self.assertEqual(
            {c.candidate_id: c.parameter_domain.get("candidate_profile") for c in produced},
            self.base_profiles,
        )

    def test_transport_failure_degrades_to_heuristic(self) -> None:
        chat = _StubChat(raises=RuntimeError("openai_compatible_transport_unavailable"))
        produced = self._produce(chat)
        self.assertEqual([c.candidate_id for c in produced], self.base_ids)
        self.assertTrue(all(c.action_hint is None for c in produced))

    def test_unparseable_output_degrades_to_heuristic(self) -> None:
        produced = self._produce(_StubChat("sorry, I cannot help with that"))
        self.assertTrue(all(c.action_hint is None for c in produced))

    def test_missing_vocab_skips_llm_call(self) -> None:
        chat = _StubChat('{"action_hints": {"escalate_first": "do"}}')
        producer = LLMCandidateProducer(chat_fn=chat, profile_action_vocab=None)
        produced = producer.produce(self.domain, self.di)
        self.assertEqual(chat.calls, 0)  # no vocab -> no call, pure heuristic
        self.assertTrue(all(c.action_hint is None for c in produced))

    def test_no_chat_fn_is_pure_heuristic(self) -> None:
        producer = LLMCandidateProducer(profile_action_vocab=_VOCAB)
        produced = producer.produce(self.domain, self.di)
        self.assertEqual([c.candidate_id for c in produced], self.base_ids)
        self.assertTrue(all(c.action_hint is None for c in produced))

    def test_callable_vocab_resolved_per_produce_filters_infeasible_hint(self) -> None:
        # round-1i (a2): a per-turn callable vocab that omits make_iron_sword from
        # escalate (infeasible) -> the LLM's escalate hint is dropped; stabilize's
        # sleep (in vocab) is attached. Proves the producer honors the dynamic vocab.
        calls = {"n": 0}

        def vocab_fn():
            calls["n"] += 1
            return {
                "escalate_first": ("do", "move_left"),  # make_iron_sword NOT feasible
                "stabilize_first": ("sleep", "noop"),
                "observe_first": ("noop", "move_right"),
            }

        chat = _StubChat('{"action_hints": {"escalate_first": "make_iron_sword", "stabilize_first": "sleep"}}')
        producer = LLMCandidateProducer(chat_fn=chat, profile_action_vocab=vocab_fn)
        produced = producer.produce(self.domain, self.di)
        self.assertEqual(calls["n"], 1)  # callable resolved exactly once this produce
        by_profile = {c.parameter_domain.get("candidate_profile"): c.action_hint for c in produced}
        self.assertIsNone(by_profile.get("escalate_first"))  # infeasible hint dropped
        self.assertEqual(by_profile.get("stabilize_first"), "sleep")  # feasible hint kept


if __name__ == "__main__":
    unittest.main()
