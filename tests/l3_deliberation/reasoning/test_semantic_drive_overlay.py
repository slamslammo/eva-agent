"""Round 1.B-3 (W5): pin that semantic memory contributes to the drive_impact
overlay via a bounded safe-path.

Pre-fix: semantic memory affected only the flat ``learning_bias`` score
contribution (via ``_semantic_pattern_bias``); it had no effect on a
candidate's ``drive_impact_schema``. The framework architecturally allowed
for a "semantic memory → L2 drive-weight" path but it was explicitly
deferred per Stage I follow-up #2 / v0.6.1 §2.5.

Post-fix: ``build_semantic_drive_impact_overlay`` produces a bounded
amplification overlay for the drive_impact_schema whenever
``working_memory_context.semantic_patterns`` includes high-confidence
patterns matching the current candidate_profile. The overlay is applied
inside ``_effective_drive_impact_schema`` after the existing learned
overlay (so semantic refinement layers on top of habit-driven shaping).
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.contracts import Candidate, DeliberationInput
from eva.l3_deliberation.reasoning.value_judgment import (
    MAX_SEMANTIC_OVERLAY_BLEND,
    MIN_SEMANTIC_OVERLAY_CONFIDENCE,
    assess_candidates,
    build_semantic_drive_impact_overlay,
)
from scenarios.crafter import activate_crafter_scenario


def _make_candidate(*, drive_impact_schema: dict[str, float]) -> Candidate:
    return Candidate(
        candidate_id="candidate-compatibility-observe-first",
        capability="compatibility",
        action="compatibility_release",
        parameter_domain={
            "candidate_profile": "observe_first",
            "habit_eligible": True,
            "instance_valid": True,
            "turn_allowed": True,
            "critical_blocked": False,
            "life_state": "STABLE",
            "conservative_mode": False,
            "compatibility_pressure_count": 1,
            "primary_pressure_reason": "test_pressure",
        },
        drive_impact_schema=dict(drive_impact_schema),
    )


def _make_input(*, working_memory_context: dict | None) -> DeliberationInput:
    return DeliberationInput(
        signal_batch={
            "signals": [{"class": "threat"}],
            "summary": {
                "signal_count": 1,
                "status_signal_count": 0,
                "threat_signal_count": 1,
                "background_signal_count": 0,
                "has_threat_signal": True,
            },
        },
        drive_broadcast={
            "top_drive": "exploration",
            "drive_levels": {
                "metabolic": 0.1,
                "safety": 0.1,
                "recovery": 0.1,
                "acquisition": 0.1,
                "capability": 0.1,
                "exploration": 0.6,
            },
            "drive_trends": {drive: "stable" for drive in (
                "metabolic", "safety", "recovery", "acquisition", "capability", "exploration",
            )},
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
                    "type": "exploration",
                    "severity": "degraded",
                    "evidence": {"reason": "test_pressure"},
                }
            ]
        },
        working_memory_context=working_memory_context,
    )


class SemanticDriveOverlayUnitTests(unittest.TestCase):
    def test_high_confidence_semantic_pattern_amplifies_positive_drive_impact(self) -> None:
        """When a high-confidence semantic pattern matches the candidate
        profile, the overlay must amplify positive entries in
        drive_impact_schema."""

        drive_impact_schema = {"exploration": 0.5, "metabolic": 0.1, "safety": -0.1}
        working_memory_context = {
            "semantic_patterns": [
                {
                    "preferred_candidate_profiles": ["observe_first"],
                    "confidence": 0.85,
                }
            ],
        }
        overlay, blend = build_semantic_drive_impact_overlay(
            working_memory_context,
            candidate_profile="observe_first",
            drive_impact_schema=drive_impact_schema,
        )
        self.assertGreater(blend, 0.0, f"blend should be positive when pattern matches; got {blend}")
        self.assertLessEqual(
            blend,
            MAX_SEMANTIC_OVERLAY_BLEND,
            f"blend must be bounded by MAX_SEMANTIC_OVERLAY_BLEND ({MAX_SEMANTIC_OVERLAY_BLEND})",
        )
        # Positive impacts get amplified upward.
        self.assertGreater(overlay.get("exploration", 0.0), 0.5)
        self.assertGreater(overlay.get("metabolic", 0.0), 0.1)
        # Negative impacts MUST NOT be weakened (overlay should not include
        # them, OR include them unchanged at most).
        if "safety" in overlay:
            self.assertLessEqual(
                overlay["safety"],
                -0.1,
                "Negative impacts must NEVER be weakened by semantic overlay (preserves safety signal)",
            )

    def test_low_confidence_semantic_pattern_does_nothing(self) -> None:
        """Patterns below MIN_SEMANTIC_OVERLAY_CONFIDENCE contribute zero."""

        working_memory_context = {
            "semantic_patterns": [
                {
                    "preferred_candidate_profiles": ["observe_first"],
                    "confidence": MIN_SEMANTIC_OVERLAY_CONFIDENCE - 0.01,  # just below
                }
            ],
        }
        overlay, blend = build_semantic_drive_impact_overlay(
            working_memory_context,
            candidate_profile="observe_first",
            drive_impact_schema={"exploration": 0.5},
        )
        self.assertEqual(blend, 0.0)
        self.assertEqual(overlay, {})

    def test_no_semantic_patterns_is_no_op(self) -> None:
        """Empty or missing semantic_patterns must short-circuit to no-op."""

        overlay_empty, blend_empty = build_semantic_drive_impact_overlay(
            {"semantic_patterns": []},
            candidate_profile="observe_first",
            drive_impact_schema={"exploration": 0.5},
        )
        self.assertEqual((overlay_empty, blend_empty), ({}, 0.0))

        overlay_absent, blend_absent = build_semantic_drive_impact_overlay(
            {},
            candidate_profile="observe_first",
            drive_impact_schema={"exploration": 0.5},
        )
        self.assertEqual((overlay_absent, blend_absent), ({}, 0.0))

        overlay_none, blend_none = build_semantic_drive_impact_overlay(
            None,
            candidate_profile="observe_first",
            drive_impact_schema={"exploration": 0.5},
        )
        self.assertEqual((overlay_none, blend_none), ({}, 0.0))

    def test_pattern_for_different_profile_does_not_apply(self) -> None:
        """A semantic pattern targeting a different candidate_profile must not
        leak into this candidate's overlay."""

        working_memory_context = {
            "semantic_patterns": [
                {
                    "preferred_candidate_profiles": ["escalate_first"],
                    "confidence": 0.9,
                }
            ],
        }
        overlay, blend = build_semantic_drive_impact_overlay(
            working_memory_context,
            candidate_profile="observe_first",
            drive_impact_schema={"exploration": 0.5},
        )
        self.assertEqual((overlay, blend), ({}, 0.0))


class SemanticDriveOverlayIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_semantic_overlay_reason_recorded_in_assessment_reasons(self) -> None:
        """End-to-end through assess_candidates: when the overlay applies,
        ``semantic_impact_overlay`` must appear in assessment reasons."""

        candidate = _make_candidate(drive_impact_schema={"exploration": 0.5, "metabolic": 0.1})
        deliberation_input = _make_input(
            working_memory_context={
                "semantic_patterns": [
                    {
                        "preferred_candidate_profiles": ["observe_first"],
                        "confidence": 0.85,
                    }
                ],
            },
        )
        assessments = assess_candidates([candidate], deliberation_input)
        self.assertEqual(len(assessments), 1)
        self.assertIn(
            "semantic_impact_overlay",
            assessments[0].reasons,
            f"Expected semantic_impact_overlay reason; got {assessments[0].reasons}",
        )

    def test_semantic_overlay_does_not_appear_without_matching_pattern(self) -> None:
        """Without matching patterns, no reason tag should be added."""

        candidate = _make_candidate(drive_impact_schema={"exploration": 0.5, "metabolic": 0.1})
        deliberation_input = _make_input(working_memory_context={"semantic_patterns": []})
        assessments = assess_candidates([candidate], deliberation_input)
        self.assertNotIn("semantic_impact_overlay", assessments[0].reasons)

    def test_semantic_overlay_strictly_smaller_max_blend_than_learned(self) -> None:
        """Bounded check: MAX_SEMANTIC_OVERLAY_BLEND must be strictly less
        than the existing MAX_LEARNED_IMPACT_BLEND in rpe.py — semantic is
        weaker evidence than direct outcome reinforcement."""

        from eva.l3_deliberation.peer_circuit.rpe import MAX_LEARNED_IMPACT_BLEND
        self.assertLess(
            MAX_SEMANTIC_OVERLAY_BLEND,
            MAX_LEARNED_IMPACT_BLEND,
            f"Semantic overlay cap ({MAX_SEMANTIC_OVERLAY_BLEND}) must be smaller than "
            f"learned overlay cap ({MAX_LEARNED_IMPACT_BLEND}) — semantic is weaker evidence.",
        )


if __name__ == "__main__":
    unittest.main()
