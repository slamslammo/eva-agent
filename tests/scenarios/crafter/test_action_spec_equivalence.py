"""single-source-crafter-action-metadata slice 2 — Crafter derivation equivalence.

CRAFTER_ACTION_SPEC becomes the single authority; ALL_ACTIONS and
CRAFTER_ACTION_ONTOLOGY are derived from it. Pins that the derived values are
byte/semantically identical to the pre-refactor hardcoded values captured in
_action_spec_oracle.json (snapshot on 402d49d, the two-source code) — per
remediation-plan §8 anti-circular red line (oracle from OLD code, not new spec).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

_ORACLE = json.loads((Path(__file__).parent / "_action_spec_oracle.json").read_text())


class CrafterActionSpecEquivalenceTests(unittest.TestCase):
    def test_spec_exists_and_is_single_source(self) -> None:
        from eva.l3_deliberation.ontology import ScenarioActionSpec
        from scenarios.crafter.action_spec import CRAFTER_ACTION_SPEC

        self.assertIsInstance(CRAFTER_ACTION_SPEC, ScenarioActionSpec)
        self.assertTrue(CRAFTER_ACTION_SPEC.version)

    def test_derived_all_actions_match_oracle(self) -> None:
        from scenarios.crafter.actions import ALL_ACTIONS

        self.assertEqual(list(ALL_ACTIONS), _ORACLE["all_actions"])

    def test_derived_ontology_format_text_byte_identical(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_ACTION_ONTOLOGY

        self.assertEqual(
            CRAFTER_ACTION_ONTOLOGY.format_text(), _ORACLE["action_ontology_format_text"]
        )

    def test_derived_ontology_entries_match_oracle(self) -> None:
        from scenarios.crafter.ontology import CRAFTER_ACTION_ONTOLOGY

        derived = [
            {
                "action": e.action,
                "effect": e.effect,
                "details": list(e.details),
                "typical_use": e.typical_use,
            }
            for e in CRAFTER_ACTION_ONTOLOGY.entries
        ]
        self.assertEqual(derived, _ORACLE["entries"])

    def test_single_source_invariant_holds(self) -> None:
        from scenarios.crafter.actions import ALL_ACTIONS
        from scenarios.crafter.ontology import CRAFTER_ACTION_ONTOLOGY

        self.assertEqual(CRAFTER_ACTION_ONTOLOGY.actions(), frozenset(ALL_ACTIONS))

    def test_bridge_name_constants_still_present(self) -> None:
        # The bridge executor constants (used by select_response_action) must
        # survive — only ALL_ACTIONS is derived, not the name constants/logic.
        from scenarios.crafter.actions import compatibility as c

        for const in ("NOOP_ACTION", "DO_ACTION", "SLEEP_ACTION", "MAKE_IRON_SWORD_ACTION"):
            self.assertTrue(hasattr(c, const), f"missing bridge constant {const}")
        self.assertEqual(c.RECHECK_ACTION, c.NOOP_ACTION)
        self.assertEqual(c.REPAIR_ACTION, c.SLEEP_ACTION)


if __name__ == "__main__":
    unittest.main()
