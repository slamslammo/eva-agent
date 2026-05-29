"""PR-S1 Slice 9: dlPFC role contract carries clock_source="step" semantic.

Plan §3.6 + R11: the role contract injected into the dlPFC system prompt
must inform the LLM that under Crafter (clock_source="step"), failed
decisions do NOT advance scenario time — so it should not invent a noop
candidate just to "keep things moving".
"""

from __future__ import annotations

import unittest

from scenarios.crafter import activate_crafter_scenario


class RoleContractClockSourceSegmentTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_role_contract_mentions_clock_source_step(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        self.assertIn("clock_source", body)
        self.assertIn("step", body)

    def test_role_contract_explains_failure_does_not_advance_time(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        # Must convey: failure → env.step not called, same observation next.
        self.assertIn("env.step", body)
        # Crafter time advances on successful release; the contract must say so.
        self.assertIn("+1", body)

    def test_role_contract_discourages_noop_placeholder(self) -> None:
        """Plan §3.6 line: do NOT emit low-quality action just to advance time."""
        from scenarios.crafter.ontology import CRAFTER_DLPFC_ROLE_CONTRACT
        body = CRAFTER_DLPFC_ROLE_CONTRACT.format_text()
        self.assertIn("noop 占位", body)


if __name__ == "__main__":
    unittest.main()
