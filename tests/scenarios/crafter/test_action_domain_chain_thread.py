"""anchor-domain-chain-trace slices 2-3 — producer threads chain onto candidates.

The producer threads the anchor's chain stages (feasible_actions + gate_branch)
onto each Candidate's parameter_domain (reusing the single gate_fields dict, no
second parallel set), so the deliberation_audit carries them and the kernel
anchor.admit trace can read them back. Trace-only — the candidate set / actions
are unchanged.
"""

from __future__ import annotations

import unittest

from scenarios.crafter.anchors.policy import CrafterActionDomain
from scenarios.crafter.reasoning.llm_action_producer import _build_candidates


class _FakeAgentState:
    runtime_gate_context = {"turn_allowed": True, "instance_valid": True,
                            "life_state": "STABLE"}
    compatibility_pressure_count = 0
    primary_pressure_reason = "water_critical"


class ProducerThreadsChainTests(unittest.TestCase):
    def _domain(self):
        return CrafterActionDomain(
            action_set=frozenset({"move_left", "move_right"}),
            restriction_reasons=("crafter_raw_action_domain", "water_critical_move_set"),
            feasible_actions=("do", "move_left", "move_right", "sleep"),
            gate_branch={"branch": "water_critical", "primary_pressure_reason": "water_critical",
                         "threat_visible": False, "salience_critical": {"thirst": "critical"}},
        )

    def test_candidate_parameter_domain_carries_chain_fields(self) -> None:
        domain = self._domain()
        raw = [{"action": "move_left", "reason": "water left"}]
        cands = _build_candidates(raw, crafter_domain=domain, agent_state=_FakeAgentState())
        self.assertEqual(len(cands), 1)
        pd = cands[0].parameter_domain
        self.assertEqual(pd["anchor_feasible_actions"], ["do", "move_left", "move_right", "sleep"])
        self.assertEqual(pd["anchor_gate_branch"]["branch"], "water_critical")
        self.assertEqual(
            pd["anchor_gate_branch"]["salience_critical"], {"thirst": "critical"}
        )

    def test_chain_fields_do_not_change_admitted_candidates(self) -> None:
        # Red line: only actions in action_set survive; chain fields don't alter that.
        domain = self._domain()
        raw = [
            {"action": "move_left", "reason": "a"},
            {"action": "do", "reason": "b"},  # NOT in action_set → dropped
            {"action": "move_right", "reason": "c"},
        ]
        cands = _build_candidates(raw, crafter_domain=domain, agent_state=_FakeAgentState())
        actions = [c.action for c in cands]
        self.assertEqual(actions, ["move_left", "move_right"])  # 'do' excluded as before

    def test_lifecycle_reads_chain_from_parameter_domain_keys(self) -> None:
        # Structural: the keys the producer writes are exactly what the lifecycle
        # anchor.admit emit reads (anchor_feasible_actions / anchor_gate_branch).
        domain = self._domain()
        raw = [{"action": "move_left", "reason": "x"}]
        cands = _build_candidates(raw, crafter_domain=domain, agent_state=_FakeAgentState())
        pd = cands[0].parameter_domain
        self.assertIn("anchor_feasible_actions", pd)
        self.assertIn("anchor_gate_branch", pd)


if __name__ == "__main__":
    unittest.main()
