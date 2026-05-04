from __future__ import annotations

import unittest

from eva.l3_deliberation import Candidate, apply_structural_anchors, build_action_domain, build_deliberation_input
from eva.l3_deliberation.reasoning.candidate_generation import build_candidates


class StructuralAnchorMirrorTests(unittest.TestCase):
    def test_structural_anchor_remains_parameter_domain_mirror_after_pre_generation(self) -> None:
        deliberation_input = build_deliberation_input(
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
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": False,
                "critical_blocked": True,
                "conservative_mode": True,
                "life_state": "CRITICAL",
                "seconds_to_heartbeat": 0.4,
            },
        )

        candidate = Candidate(
            candidate_id="candidate-1",
            capability="compatibility_response",
            action="compatibility_release",
            parameter_domain={"candidate_profile": "observe_first", "top_drive": "curiosity"},
            justification=("candidate_profile=observe_first",),
        )

        anchored = apply_structural_anchors([candidate], deliberation_input)

        self.assertEqual(len(anchored), 1)
        self.assertEqual(anchored[0].candidate_id, "candidate-1")
        self.assertEqual(anchored[0].parameter_domain["instance_valid"], True)
        self.assertEqual(anchored[0].parameter_domain["turn_allowed"], False)
        self.assertEqual(anchored[0].parameter_domain["critical_blocked"], True)
        self.assertEqual(anchored[0].parameter_domain["conservative_mode"], True)
        self.assertEqual(anchored[0].parameter_domain["life_state"], "CRITICAL")
        self.assertEqual(candidate.parameter_domain, {"candidate_profile": "observe_first", "top_drive": "curiosity"})

    def test_generated_candidates_from_action_domain_still_require_anchor_mirror_for_runtime_fields(self) -> None:
        deliberation_input = build_deliberation_input(
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
                "top_drive": "curiosity",
                "drive_levels": {"curiosity": 0.8},
                "drive_trends": {"curiosity": "improving"},
            },
            runtime_gate_context={
                "instance_valid": True,
                "turn_allowed": True,
                "critical_blocked": False,
                "conservative_mode": False,
                "life_state": "STABLE",
                "seconds_to_heartbeat": 10.0,
            },
        )

        candidates = build_candidates(build_action_domain(deliberation_input))
        anchored = apply_structural_anchors(candidates, deliberation_input)

        self.assertEqual(len(candidates), 2)
        self.assertNotIn("instance_valid", candidates[0].parameter_domain)
        self.assertEqual(anchored[0].parameter_domain["instance_valid"], True)
        self.assertEqual(anchored[0].parameter_domain["turn_allowed"], True)
        self.assertEqual(anchored[0].parameter_domain["life_state"], "STABLE")


if __name__ == "__main__":
    unittest.main()
