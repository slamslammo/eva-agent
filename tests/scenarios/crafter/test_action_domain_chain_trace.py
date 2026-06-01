"""anchor-domain-chain-trace — structured anchor-chain trace fields.

B3 found the viewer mislabels 'in-domain candidates' as pure A'(s) because the
3 intermediate stages computed in build_crafter_action_domain — feasible set,
pressure-gate branch, final A'(s) — never reach the trace (only the final
action_set + restriction_reasons strings do).

This adds structured trace fields (feasible_actions + gate_branch) to
CrafterActionDomain, derived from the SAME already-computed intermediate state.

★ Red line: PURE trace instrumentation — the anchor DECISION must not change.
action_set is byte-identical to before for every gate branch.
"""

from __future__ import annotations

import json
import unittest

from scenarios.crafter.anchors.policy import (
    CrafterActionDomain,
    build_crafter_action_domain,
)


class _FakeAgentState:
    def __init__(self, *, primary_pressure_reason="none", top_drive="exploration"):
        self.primary_pressure_reason = primary_pressure_reason
        self.top_drive = top_drive
        self.drive_levels = {}
        self.working_memory_context = None


# A minimal observation that yields a broad feasible set (no special pressure).
def _obs():
    return {"local_view": {}, "life": {}, "inventory": {}}


class ActionDomainNewFieldShapeTests(unittest.TestCase):
    def test_dataclass_has_trace_fields_with_defaults(self) -> None:
        import dataclasses

        names = {f.name for f in dataclasses.fields(CrafterActionDomain)}
        self.assertIn("feasible_actions", names)
        self.assertIn("gate_branch", names)
        # defaults so any existing direct construction still works
        d = CrafterActionDomain(action_set=frozenset({"do"}), restriction_reasons=())
        self.assertEqual(d.feasible_actions, ())
        self.assertEqual(d.gate_branch, {})

    def test_to_dict_includes_new_fields_json_serializable(self) -> None:
        domain = build_crafter_action_domain(_FakeAgentState(), _obs())
        d = domain.to_dict()
        self.assertIn("feasible_actions", d)
        self.assertIn("gate_branch", d)
        # must round-trip through json (trace serialization)
        json.dumps(d)
        self.assertIsInstance(d["feasible_actions"], list)
        self.assertIsInstance(d["gate_branch"], dict)


class GateBranchReflectsComputationTests(unittest.TestCase):
    def test_normal_branch(self) -> None:
        domain = build_crafter_action_domain(_FakeAgentState(), _obs())
        self.assertEqual(domain.gate_branch.get("branch"), "normal")
        # feasible_actions is the pre-gate feasible set: the raw-feasible actions
        # intersected with the Crafter action registry, sorted (A G2 fix: was a
        # self-comparison tautology; assert against the independently-recomputed set).
        from scenarios.crafter.actions.feasibility import feasible_raw_actions
        from scenarios.crafter.anchors import policy as P

        expected_feasible = sorted(
            a for a in feasible_raw_actions(_obs()) if a in P.CRAFTER_ACTIONS
        )
        self.assertEqual(sorted(domain.feasible_actions), expected_feasible)
        # in the normal branch nothing is narrowed: action_set ⊆ feasible
        self.assertTrue(set(domain.action_set) <= set(domain.feasible_actions))

    def test_water_critical_branch_labeled(self) -> None:
        st = _FakeAgentState(primary_pressure_reason="water_low")
        # patch WATER_REASONS membership via the real reason set
        from scenarios.crafter.anchors import policy as P

        reason = next(iter(P.WATER_REASONS))
        domain = build_crafter_action_domain(
            _FakeAgentState(primary_pressure_reason=reason), _obs()
        )
        self.assertEqual(domain.gate_branch.get("branch"), "water_critical")
        self.assertEqual(domain.gate_branch.get("primary_pressure_reason"), reason)

    def test_threat_branch_labeled(self) -> None:
        from scenarios.crafter.anchors import policy as P

        reason = next(iter(P.THREAT_REASONS))
        domain = build_crafter_action_domain(
            _FakeAgentState(primary_pressure_reason=reason), _obs()
        )
        self.assertEqual(domain.gate_branch.get("branch"), "threat_response")
        self.assertIn("threat_visible", domain.gate_branch)


class DecisionInvarianceRedLineTests(unittest.TestCase):
    """★ The anchor decision (action_set) must be unchanged by the new fields."""

    def _action_set_for(self, reason):
        return build_crafter_action_domain(
            _FakeAgentState(primary_pressure_reason=reason), _obs()
        ).action_set

    def test_action_set_matches_recomputed_admitted_for_all_branches(self) -> None:
        # Recompute admitted the OLD way (mirror policy logic) and assert the
        # instrumented build still yields the identical action_set per branch.
        from scenarios.crafter.actions.feasibility import feasible_raw_actions
        from scenarios.crafter.actions import (
            ALL_ACTIONS as _ALL,
        )
        from scenarios.crafter.anchors import policy as P

        feasible = frozenset(a for a in feasible_raw_actions(_obs()) if a in P.CRAFTER_ACTIONS)

        # normal
        self.assertEqual(self._action_set_for("none"), feasible)
        # water-critical → feasible & MOVE_ACTIONS
        wr = next(iter(P.WATER_REASONS))
        self.assertEqual(self._action_set_for(wr), frozenset(feasible & P.MOVE_ACTIONS))
        # threat → feasible & (MOVE | {do})
        tr = next(iter(P.THREAT_REASONS))
        self.assertEqual(
            self._action_set_for(tr), frozenset(feasible & (P.MOVE_ACTIONS | {P.DO_ACTION}))
        )
        # energy → feasible & {sleep}
        er = next(iter(P.ENERGY_REASONS))
        self.assertEqual(self._action_set_for(er), frozenset(feasible & {P.SLEEP_ACTION}))

    def test_restriction_reasons_strings_preserved(self) -> None:
        # Back-compat: the existing reason strings stay (not removed by structuring).
        from scenarios.crafter.anchors import policy as P

        wr = next(iter(P.WATER_REASONS))
        domain = build_crafter_action_domain(_FakeAgentState(primary_pressure_reason=wr), _obs())
        self.assertIn("water_critical_move_set", domain.restriction_reasons)
        self.assertIn("crafter_raw_action_domain", domain.restriction_reasons)


if __name__ == "__main__":
    unittest.main()
