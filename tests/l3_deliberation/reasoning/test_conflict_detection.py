from __future__ import annotations

import unittest

from eva.l3_deliberation import Candidate
from eva.l3_deliberation.reasoning import (
    OBSERVE_FIRST_PROFILE,
    STABILIZE_FIRST_PROFILE,
    build_candidate_conflict_context,
)


class ConflictDetectionTests(unittest.TestCase):
    def test_unknown_candidate_action_is_withheld(self) -> None:
        conflict = build_candidate_conflict_context(
            Candidate(candidate_id="candidate-unknown", capability="unknown", action="unknown_action"),
            top_drive="curiosity",
            threat_count=0,
        )

        self.assertEqual(conflict.disposition, "withhold")
        self.assertEqual(conflict.reasons, ("unknown_candidate_action",))

    def test_runtime_boundary_conflict_surfaces_from_candidate_domain(self) -> None:
        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={
                    "candidate_profile": OBSERVE_FIRST_PROFILE,
                    "instance_valid": True,
                    "turn_allowed": False,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                    "seconds_to_heartbeat": 10.0,
                },
            ),
            top_drive="integrity",
            threat_count=1,
        )

        self.assertEqual(conflict.candidate_profile, OBSERVE_FIRST_PROFILE)
        self.assertEqual(conflict.disposition, "withhold")
        self.assertIn("turn_not_allowed", conflict.reasons)

    def test_integrity_pressure_builds_stabilize_first_tension_bias(self) -> None:
        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-stabilize-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain={
                    "candidate_profile": STABILIZE_FIRST_PROFILE,
                    "instance_valid": True,
                    "turn_allowed": True,
                    "critical_blocked": False,
                    "conservative_mode": False,
                    "life_state": "STABLE",
                    "seconds_to_heartbeat": 10.0,
                    "compatibility_pressure_count": 1,
                },
                drive_impact_schema={
                    "integrity": 0.5,
                    "curiosity": -0.2,
                },
            ),
            top_drive="integrity",
            threat_count=1,
            drive_levels={"integrity": 0.9, "curiosity": 0.7},
        )

        self.assertEqual(conflict.disposition, "allow")
        self.assertIn("integrity_or_threat_pressure_present", conflict.reasons)
        self.assertIn("integrity_bias_for_stabilize_first", conflict.reasons)
        self.assertIn("pressure_bias_for_stabilize_first", conflict.reasons)
        self.assertIn("drive_tension_detected", conflict.reasons)
        self.assertIn("supports_high_drive:integrity", conflict.reasons)
        self.assertIn("harms_high_drive:curiosity", conflict.reasons)
        self.assertEqual(conflict.score_delta, 2.25)


if __name__ == "__main__":
    unittest.main()
