"""round-1j: unit tests for world_facts_fn injection in LLMCandidateProducer.

Two invariants:
1. world_facts_fn=None  → LLM prompt unchanged (backward-compat, no sentinel in prompt)
2. world_facts_fn=<fn>  → LLM prompt contains the world facts returned by fn

Both tests stub chat_fn so no real LLM is called.
"""

from __future__ import annotations

import unittest

from eva.anchor import build_action_domain
from eva.l3_deliberation.contracts import build_deliberation_input
from eva.l3_deliberation.reasoning.llm_candidate_producer import LLMCandidateProducer
from scenarios.crafter import activate_crafter_scenario


_VOCAB = {
    "escalate_first": ("do", "make_wood_pickaxe"),
    "stabilize_first": ("sleep", "noop"),
    "observe_first": ("noop", "move_left"),
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


class _CapturingChat:
    """Stub chat_fn that records every messages list it receives."""

    def __init__(self) -> None:
        self.captured: list[list[dict]] = []

    def __call__(self, messages: list[dict]) -> str:
        self.captured.append(messages)
        # Return a valid but empty response so the producer degrades gracefully.
        return "{}"


class WorldFactsInjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()
        self.di = _deliberation_input()
        self.domain = build_action_domain(self.di)

    def _all_message_content(self, messages: list[dict]) -> str:
        return "\n".join(m.get("content", "") for m in messages)

    def test_no_world_facts_when_fn_is_none(self) -> None:
        """world_facts_fn=None: the LLM prompt must NOT contain 'Background world facts'."""
        chat = _CapturingChat()
        producer = LLMCandidateProducer(
            chat_fn=chat,
            profile_action_vocab=_VOCAB,
            world_facts_fn=None,
        )
        producer.produce(self.domain, self.di)
        self.assertEqual(len(chat.captured), 1, "Expected exactly one LLM call")
        content = self._all_message_content(chat.captured[0])
        self.assertNotIn(
            "Background world facts",
            content,
            "world_facts_fn=None must not inject any world-facts header into the prompt",
        )

    def test_world_facts_sentinel_present_when_fn_provided(self) -> None:
        """world_facts_fn=<fn>: the LLM prompt must contain the sentinel string."""
        sentinel = "WORLD_FACT_SENTINEL"
        chat = _CapturingChat()
        producer = LLMCandidateProducer(
            chat_fn=chat,
            profile_action_vocab=_VOCAB,
            world_facts_fn=lambda: sentinel,
        )
        producer.produce(self.domain, self.di)
        self.assertEqual(len(chat.captured), 1, "Expected exactly one LLM call")
        content = self._all_message_content(chat.captured[0])
        self.assertIn(
            sentinel,
            content,
            "world_facts_fn result must appear in the LLM prompt",
        )


if __name__ == "__main__":
    unittest.main()
