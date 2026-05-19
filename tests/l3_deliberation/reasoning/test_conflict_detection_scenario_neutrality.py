"""Round 1.B-1-b/c: pin that conflict_detection's withhold gate and score
adjustments are scenario-neutral.

Pre-fix behavior: framework code treated ``"integrity"`` as a magic-string
top-drive name. Specifically:
- Withhold gate: ``top_drive != "integrity" and threat_count <= 0 → withhold``.
  This silently blocks Crafter agents from acting in any low-pressure
  no-threat state, because Crafter top_drive is never literally ``"integrity"``.
- Score adjustments: stabilize_first / observe_first / escalate_first profile
  branches all used ``top_drive == "integrity"`` to decide whether the
  candidate gets a contextual score_delta boost.

Post-fix behavior: both decision points use the **top_drive's level** instead
of its specific name. Linux's ``"integrity"`` being top drive implies its
level is high in any meaningful pressure state; the level-based check is
operationally equivalent for Linux while making Crafter drives first-class.

This file pins both layers (gate behavior + score adjustment) so the design
intent is recorded in tests, not just in code comments.
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation import Candidate
from eva.l3_deliberation.reasoning import build_candidate_conflict_context
from scenarios.crafter import activate_crafter_scenario


# Profile names — Crafter and Linux share the same vocabulary at framework level.
OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"
ESCALATE_FIRST_PROFILE = "escalate_first"


def _well_formed_parameter_domain(
    *,
    candidate_profile: str,
    compatibility_pressure_count: int = 1,
    primary_pressure_reason: str = "test_pressure",
) -> dict[str, object]:
    """Return a parameter_domain with all runtime-gate fields populated so the
    only thing being tested is the drive / pressure logic in conflict_detection."""

    return {
        "candidate_profile": candidate_profile,
        "instance_valid": True,
        "turn_allowed": True,
        "critical_blocked": False,
        "conservative_mode": False,
        "life_state": "STABLE",
        "seconds_to_heartbeat": 10.0,
        "compatibility_pressure_count": compatibility_pressure_count,
        "primary_pressure_reason": primary_pressure_reason,
    }


class WithholdGateScenarioNeutralityTests(unittest.TestCase):
    """Cover 1.B-1-b: the withhold gate must accept any high-level top_drive,
    not only the Linux ``"integrity"`` name."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_crafter_acquisition_high_drive_no_threat_passes_gate(self) -> None:
        """Pre-fix: Crafter's top_drive='acquisition' fails ``!= "integrity"``,
        so the gate withholds even when the acquisition drive is high.
        Post-fix: top_drive's level >= 0.3 passes the gate, regardless of name."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-escalate-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=ESCALATE_FIRST_PROFILE,
                ),
                drive_impact_schema={"acquisition": 0.5},
            ),
            top_drive="acquisition",
            threat_count=0,
            drive_levels={"acquisition": 0.8, "safety": 0.2, "metabolic": 0.2},
        )
        self.assertEqual(
            conflict.disposition,
            "allow",
            f"Crafter high-acquisition top_drive must pass the withhold gate even "
            f"without threat. Got disposition={conflict.disposition}, reasons={conflict.reasons}",
        )

    def test_crafter_all_low_drives_no_threat_still_withholds(self) -> None:
        """Post-fix: when no drive is above the release threshold and no
        threat is present, withhold is still the right outcome. The new logic
        does not over-permit."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=OBSERVE_FIRST_PROFILE,
                    compatibility_pressure_count=0,
                ),
                drive_impact_schema={"metabolic": 0.1},
            ),
            top_drive="metabolic",
            threat_count=0,
            drive_levels={"metabolic": 0.1, "safety": 0.1, "acquisition": 0.05},
        )
        self.assertEqual(conflict.disposition, "withhold")
        self.assertIn("no_release_pressure", conflict.reasons)

    def test_linux_integrity_high_passes_gate_equivalently(self) -> None:
        """Linux equivalence: when top_drive='integrity' with level 0.9, the
        gate must let the candidate through — exactly the same as before."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-stabilize-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=STABILIZE_FIRST_PROFILE,
                ),
                drive_impact_schema={"integrity": 0.5},
            ),
            top_drive="integrity",
            threat_count=0,
            drive_levels={"integrity": 0.9, "curiosity": 0.3},
        )
        self.assertEqual(conflict.disposition, "allow")
        self.assertNotIn("no_release_pressure", conflict.reasons)

    def test_linux_low_integrity_no_threat_now_correctly_withholds(self) -> None:
        """Linux equivalence (corner): the OLD code passed the gate whenever
        top_drive='integrity' regardless of level. The NEW code requires
        level >= threshold. For Linux integrity-low-no-threat, this is a
        behavior change. Document the new (more principled) behavior here.

        Justification for accepting this corner-case change: a real Linux
        runtime with top_drive='integrity' but level near 0 is essentially in
        a degenerate state (all drives near 0). In practice this doesn't
        occur because if integrity were near 0, some other drive would be
        higher and become top_drive. The check is operationally equivalent
        for any realistic Linux state."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=OBSERVE_FIRST_PROFILE,
                    compatibility_pressure_count=0,
                ),
                drive_impact_schema={"integrity": 0.0},
            ),
            top_drive="integrity",
            threat_count=0,
            drive_levels={"integrity": 0.05},
        )
        self.assertEqual(conflict.disposition, "withhold")
        self.assertIn("no_release_pressure", conflict.reasons)

    def test_threat_alone_passes_gate(self) -> None:
        """Threat alone (no high drive) is still sufficient — preserves
        existing semantics that threats always merit a response."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-escalate-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=ESCALATE_FIRST_PROFILE,
                ),
                drive_impact_schema={"safety": 0.5},
            ),
            top_drive="safety",
            threat_count=2,
            drive_levels={"safety": 0.1, "metabolic": 0.1},  # all low
        )
        self.assertEqual(conflict.disposition, "allow")

    def test_drive_levels_none_treated_as_zero(self) -> None:
        """Defensive: drive_levels=None must not crash and should fall back
        to the no-release-pressure withhold (since level defaults to 0)."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=OBSERVE_FIRST_PROFILE,
                    compatibility_pressure_count=0,
                ),
            ),
            top_drive="metabolic",
            threat_count=0,
            drive_levels=None,
        )
        self.assertEqual(conflict.disposition, "withhold")
        self.assertIn("no_release_pressure", conflict.reasons)


class ScoreAdjustmentScenarioNeutralityTests(unittest.TestCase):
    """Cover 1.B-1-c: profile-specific score_delta boosts must trigger on
    top_drive's level (scenario-neutral), not its specific name."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_high_crafter_drive_boosts_stabilize_first(self) -> None:
        """Pre-fix: stabilize_first +0.75 only when top_drive='integrity'.
        Post-fix: stabilize_first +0.75 when top_drive_level >= HIGH."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-stabilize-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=STABILIZE_FIRST_PROFILE,
                ),
                drive_impact_schema={"metabolic": 0.5},
            ),
            top_drive="metabolic",
            threat_count=1,
            drive_levels={"metabolic": 0.9, "safety": 0.2},
        )
        self.assertEqual(conflict.disposition, "allow")
        self.assertIn("high_drive_projection_for_stabilize_first", conflict.reasons)
        self.assertIn("pressure_projection_for_stabilize_first", conflict.reasons)
        # The total score_delta should match the Linux test_conflict_detection
        # pattern when stabilize gets both boosts (0.75 + 0.5) plus threat (1.0).
        self.assertGreaterEqual(conflict.score_delta, 2.0)

    def test_low_crafter_drive_boosts_observe_first(self) -> None:
        """Pre-fix: observe_first +0.25 when top_drive != "integrity".
        Post-fix: observe_first +0.25 when top_drive_level < HIGH."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-observe-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=OBSERVE_FIRST_PROFILE,
                    compatibility_pressure_count=0,
                ),
                drive_impact_schema={"metabolic": 0.1},
            ),
            top_drive="metabolic",
            threat_count=1,
            drive_levels={"metabolic": 0.35, "safety": 0.1},  # above release thresh, below high thresh
        )
        self.assertEqual(conflict.disposition, "allow")
        self.assertIn("low_drive_projection_for_observe_first", conflict.reasons)
        self.assertIn("low_pressure_projection_for_observe_first", conflict.reasons)

    def test_high_crafter_drive_boosts_escalate_first(self) -> None:
        """Pre-fix: escalate_first +1.0 when top_drive == "integrity".
        Post-fix: escalate_first +1.0 when top_drive_level >= HIGH."""

        conflict = build_candidate_conflict_context(
            Candidate(
                candidate_id="candidate-compatibility-escalate-first",
                capability="compatibility_response",
                action="compatibility_release",
                parameter_domain=_well_formed_parameter_domain(
                    candidate_profile=ESCALATE_FIRST_PROFILE,
                    primary_pressure_reason="threat_visible",
                ),
                drive_impact_schema={"safety": 0.7},
            ),
            top_drive="safety",
            threat_count=1,
            drive_levels={"safety": 0.85, "metabolic": 0.2},
        )
        self.assertEqual(conflict.disposition, "allow")
        self.assertIn("high_drive_projection_for_escalate_first", conflict.reasons)


if __name__ == "__main__":
    unittest.main()
