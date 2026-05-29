"""Round 1.B-1-a: pin that drive-weighted scoring is scenario-neutral.

Pre-1.B-1-a behavior: ``_drive_weighted_score`` hardcoded iteration to the
Linux drive tuple ``("survival", "integrity", "continuity", "curiosity")``.
Crafter drives (``metabolic / safety / recovery / acquisition / capability``)
silently scored zero. After 1.B-1-a, scoring iterates the drives the
candidate has actually declared an impact for, so any scenario's drive
vocabulary contributes.

Two layers of tests:

1. **Unit tests** call ``_drive_weighted_score`` directly. They are the most
   precise pin for the single function being changed.
2. **Integration test** goes through ``assess_candidates`` to confirm the
   fix is wired into the assessment path correctly.
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.contracts import Candidate, DeliberationInput
from eva.l3_deliberation.reasoning.value_judgment import (
    _drive_weighted_score,
    assess_candidates,
)
from scenarios.crafter import activate_crafter_scenario


# ----------------------------------------------------------------------------
# Unit tests on the private ``_drive_weighted_score`` function.
# ----------------------------------------------------------------------------


class DriveWeightedScoreUnitTests(unittest.TestCase):
    def test_picks_up_crafter_drive_impact(self) -> None:
        """Crafter-named drive_impact_schema must contribute to the score."""

        drive_impact_schema = {
            "metabolic": 0.6,
            "safety": 0.3,
            "recovery": 0.4,
            "acquisition": 0.1,
            "capability": 0.05,
        }
        drive_levels = {
            "metabolic": 0.9,
            "safety": 0.5,
            "recovery": 0.5,
            "acquisition": 0.1,
            "capability": 0.1,
        }
        expected = (
            0.9 * 0.6
            + 0.5 * 0.3
            + 0.5 * 0.4
            + 0.1 * 0.1
            + 0.1 * 0.05
        )  # = 0.915
        score = _drive_weighted_score(drive_impact_schema, drive_levels)
        self.assertAlmostEqual(
            score,
            expected,
            places=4,
            msg=(
                "After 1.B-1-a, _drive_weighted_score must iterate "
                "drive_impact_schema.items() so Crafter drives contribute. "
                f"Got {score}, expected {expected}"
            ),
        )

    def test_linux_equivalent_for_linux_drive_vocab(self) -> None:
        """Linux equivalence: Linux drive vocabulary must produce the same
        score as the pre-fix hardcoded iteration. Tests both signs (positive
        and negative impact components) to ensure no truncation."""

        drive_impact_schema = {
            "survival": 0.5,
            "integrity": 0.7,
            "continuity": 0.2,
            "curiosity": -0.1,
        }
        drive_levels = {
            "survival": 0.4,
            "integrity": 0.85,
            "continuity": 0.3,
            "curiosity": 0.2,
        }
        expected = 0.4 * 0.5 + 0.85 * 0.7 + 0.3 * 0.2 + 0.2 * (-0.1)  # = 0.835
        score = _drive_weighted_score(drive_impact_schema, drive_levels)
        self.assertAlmostEqual(
            score,
            expected,
            places=4,
            msg=(
                "Linux equivalence: post-fix iteration must produce the same "
                f"score as the pre-fix hardcoded loop. Got {score}, expected {expected}"
            ),
        )

    def test_ignores_drive_levels_not_in_impact_schema(self) -> None:
        """A broadcast drive absent from impact_schema must not contribute."""

        drive_impact_schema = {"metabolic": 0.5}
        drive_levels = {
            "metabolic": 0.8,
            "safety": 0.9,  # high but not in impact_schema
            "recovery": 0.9,
            "acquisition": 0.9,
            "capability": 0.9,
            "survival": 0.5,  # mixed: also a Linux drive name not in schema
        }
        expected = 0.8 * 0.5  # = 0.4
        score = _drive_weighted_score(drive_impact_schema, drive_levels)
        self.assertAlmostEqual(score, expected, places=4)

    def test_treats_missing_broadcast_level_as_zero(self) -> None:
        """If impact_schema declares a drive but broadcast doesn't report it,
        the contribution is zero (matches the .get(_, 0.0) fallback)."""

        drive_impact_schema = {"metabolic": 0.7, "safety": 0.3}
        drive_levels = {"metabolic": 0.5}  # safety missing
        expected = 0.5 * 0.7  # = 0.35
        score = _drive_weighted_score(drive_impact_schema, drive_levels)
        self.assertAlmostEqual(score, expected, places=4)

    def test_empty_impact_schema_returns_zero(self) -> None:
        """Pre-fix behavior preserved: empty impact_schema means no scoring."""

        self.assertEqual(_drive_weighted_score({}, {"metabolic": 0.5}), 0.0)

    def test_empty_drive_levels_returns_zero(self) -> None:
        """Each drive in impact_schema contributes 0 if broadcast is empty."""

        self.assertAlmostEqual(
            _drive_weighted_score({"metabolic": 0.5, "safety": 0.3}, {}),
            0.0,
            places=4,
        )


# ----------------------------------------------------------------------------
# Integration test through assess_candidates.
# ----------------------------------------------------------------------------


def _make_full_candidate(*, candidate_id: str, candidate_profile: str, drive_impact_schema: dict[str, float]) -> Candidate:
    """Build one compatibility_release candidate with the runtime-gate fields
    that conflict_detection expects in parameter_domain (production code
    propagates these via build_action_domain; we set them directly here so the
    integration test can isolate scoring behavior)."""

    return Candidate(
        candidate_id=candidate_id,
        capability="compatibility",
        action="compatibility_release",
        parameter_domain={
            "candidate_profile": candidate_profile,
            "habit_eligible": True,
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "life_state": "STABLE",
            "conservative_mode": False,
            "compatibility_pressure_count": 1,
            "primary_pressure_reason": "test_pressure",
        },
        justification=(),
        drive_impact_schema=dict(drive_impact_schema),
        side_effect_class="compatibility_side_effect",
    )


def _make_deliberation_input(*, top_drive: str, drive_levels: dict[str, float], threat: bool = True) -> DeliberationInput:
    drive_trends = {drive: "stable" for drive in drive_levels}
    threat_count = 1 if threat else 0
    return DeliberationInput(
        signal_batch={
            "signals": [{"class": "threat"}] if threat else [{"class": "status"}],
            "summary": {
                "signal_count": 1,
                "status_signal_count": 0 if threat else 1,
                "threat_signal_count": threat_count,
                "background_signal_count": 0,
                "has_threat_signal": threat,
            },
        },
        drive_broadcast={
            "top_drive": top_drive,
            "drive_levels": dict(drive_levels),
            "drive_trends": drive_trends,
        },
        runtime_gate_context={
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "conservative_mode": False,
            "life_state": "STABLE",
        },
        compatibility_pressure_table={
            "pressures": [
                {
                    "type": top_drive,
                    "severity": "degraded",
                    "evidence": {"reason": "test_pressure"},
                }
            ]
        },
        working_memory_context=None,
    )


class AssessCandidatesIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_crafter_candidate_drive_score_reaches_assessment(self) -> None:
        """Through the full assess_candidates pipeline, a candidate with
        Crafter-vocabulary drive_impact_schema must end up with a non-zero
        contribution coming from the drive-weighted dimension."""

        candidate = _make_full_candidate(
            candidate_id="candidate-compatibility-stabilize-first",
            candidate_profile="stabilize_first",
            drive_impact_schema={
                "metabolic": 0.6,
                "safety": 0.3,
                "recovery": 0.4,
                "acquisition": 0.1,
                "capability": 0.05,
            },
        )
        deliberation_input = _make_deliberation_input(
            top_drive="metabolic",
            drive_levels={
                "metabolic": 0.9,
                "safety": 0.5,
                "recovery": 0.5,
                "acquisition": 0.1,
                "capability": 0.1,
            },
            threat=True,  # pass the integrity-or-threat withhold gate
        )
        assessments = assess_candidates([candidate], deliberation_input)
        self.assertEqual(len(assessments), 1)
        assessment = assessments[0]
        self.assertEqual(
            assessment.disposition,
            "allow",
            f"Expected allow disposition for non-degenerate test setup; got {assessment.disposition} with reasons {assessment.reasons}",
        )
        # The drive-weighted contribution alone is 0.915. The full score
        # includes profile-specific pressure projection score_delta added on
        # top by conflict_detection. We only assert that drive scoring is
        # contributing — exact total depends on conflict_detection details
        # which 1.B-1-b/c will refactor.
        self.assertGreater(
            assessment.score,
            0.4,
            "Drive-weighted score on Crafter vocabulary must reach assessment as "
            "the primary contributor. PR-O1 robust scheme: drive saturates toward "
            "W_DRIVE=0.5, so a drive-dominant candidate scores >0.4 (was >0.9 under "
            f"the old unbounded direct sum). Got: {assessment.score} with "
            f"reasons {assessment.reasons}",
        )


if __name__ == "__main__":
    unittest.main()
