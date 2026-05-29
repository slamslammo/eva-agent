"""PR-T2 slice 1: substrate-level bounded retry for the LLM transport.

Plan rev3 §3 / A G1 review: LLM transport failures (IncompleteRead / timeout /
socket close) are INFRASTRUCTURE, not cognition. They must be retried a bounded
number of times at the transport boundary — NOT surfaced into the cognitive path
as an empty-candidate "withhold". This tests the substrate retry helper in
isolation (北极星: substrate stays boring, separate from the dlPFC producer's
candidate logic).
"""

from __future__ import annotations

import json
import unittest

from scenarios.crafter.reasoning.llm_action_producer import _call_chat_with_bounded_retry


class BoundedTransportRetryTests(unittest.TestCase):
    def test_retries_transport_error_up_to_max_then_gives_up(self) -> None:
        calls = {"n": 0}

        def always_failing(messages):
            calls["n"] += 1
            raise OSError("IncompleteRead(0 bytes read)")

        raw, parsed, status, errors, attempts = _call_chat_with_bounded_retry(
            always_failing, [], max_retries=2
        )
        self.assertEqual(status, "transport_error")
        self.assertIsNone(parsed)
        # 1 initial attempt + 2 retries = 3 transport calls (bounded).
        self.assertEqual(attempts, 3)
        self.assertEqual(calls["n"], 3)

    def test_recovers_within_retry_budget(self) -> None:
        calls = {"n": 0}

        def flaky(messages):
            calls["n"] += 1
            if calls["n"] < 2:
                raise OSError("transient socket close")
            return json.dumps({"candidates": [{"action": "do", "reason": "ok"}]})

        raw, parsed, status, errors, attempts = _call_chat_with_bounded_retry(
            flaky, [], max_retries=2
        )
        self.assertEqual(status, "ok")
        self.assertIsInstance(parsed, dict)
        self.assertEqual(attempts, 2)  # failed once, succeeded on retry

    def test_no_retry_when_max_retries_zero(self) -> None:
        calls = {"n": 0}

        def failing(messages):
            calls["n"] += 1
            raise OSError("down")

        _, _, status, _, attempts = _call_chat_with_bounded_retry(failing, [], max_retries=0)
        self.assertEqual(status, "transport_error")
        self.assertEqual(attempts, 1)  # no retry — single attempt
        self.assertEqual(calls["n"], 1)

    def test_parse_error_not_retried(self) -> None:
        """Only transport errors retry; a parse error is not an infra hiccup."""
        calls = {"n": 0}

        def bad_json(messages):
            calls["n"] += 1
            return "not json at all"

        _, _, status, _, attempts = _call_chat_with_bounded_retry(bad_json, [], max_retries=3)
        self.assertEqual(status, "parse_error")
        self.assertEqual(attempts, 1)  # parse error does not trigger transport retry
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
