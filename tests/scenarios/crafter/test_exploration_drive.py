"""Round 1.B-2: pin Crafter exploration drive — recovery / suppression
semantics and candidate-scoring impact.

Pre-fix: Crafter's drive_preset declared 5 drives and explicitly opted out of
the framework's curiosity-style update path (``curiosity_drive_type=None``
plus ``curiosity_recovery=0.0 / curiosity_suppression=0.0``). The agent had
no internal pull toward exploration in healthy / no-threat moments.

Post-fix: a sixth drive "exploration" is registered, the framework's
``_curiosity_delta`` recovery/suppression path is engaged for it, and
candidate scoring's ``COMPATIBILITY_RELEASE_IMPACT`` table assigns a
strong positive observe-first impact (and negative stabilize impact) so
that high exploration drive actually shifts L3 selection toward exploration.
"""

from __future__ import annotations

import unittest
from datetime import timedelta

from eva.kernel import DimensionSnapshot, DriveState, DriveStateTable, ExternalLifeSnapshot, utc_now
from eva.l1_sensing.signal_bus import SignalRecord
from eva.l2_drive.drive_state import update_drive_state
from eva.l3_deliberation.contracts import Candidate, DeliberationInput
from eva.l3_deliberation.reasoning.value_judgment import assess_candidates
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.anchors.policy import COMPATIBILITY_RELEASE_IMPACT
from scenarios.crafter.drive_preset import CRAFTER_DRIVE_PRESET, DRIVE_TYPES


def _make_healthy_snapshot(now) -> ExternalLifeSnapshot:
    rate_unknown = {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}
    return ExternalLifeSnapshot(
        captured_at=now,
        source_patrol="deep",
        dimensions={
            "avatar_safety": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "safety_ok", "rate_context": rate_unknown},
            ),
            "avatar_metabolic": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "metabolic_ok", "rate_context": rate_unknown},
            ),
            "avatar_recovery": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "recovery_ok", "rate_context": rate_unknown},
            ),
            "inventory_acquisition": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "inventory_ok", "rate_context": rate_unknown},
            ),
            "inventory_capability": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "tooling_ok", "rate_context": rate_unknown},
            ),
            "local_view_threat": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "no_threat", "rate_context": rate_unknown},
            ),
            "local_view_resource": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "resource_ok", "rate_context": rate_unknown},
            ),
            "local_view_utility": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "utility_ok", "rate_context": rate_unknown},
            ),
        },
        overall_status="healthy",
        primary_gap={"type": "none", "reason": "none"},
        trend="stable",
        updated_at=now,
    )


def _make_degraded_snapshot(now) -> ExternalLifeSnapshot:
    rate_unknown = {"available": False, "direction": "unknown", "magnitude": None, "acceleration": None}
    return ExternalLifeSnapshot(
        captured_at=now,
        source_patrol="deep",
        dimensions={
            "avatar_safety": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "safety_ok", "rate_context": rate_unknown},
            ),
            "avatar_metabolic": DimensionSnapshot(
                status="degraded",
                evidence={"reason": "food_low", "rate_context": rate_unknown},
            ),
            "avatar_recovery": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "recovery_ok", "rate_context": rate_unknown},
            ),
            "inventory_acquisition": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "inventory_ok", "rate_context": rate_unknown},
            ),
            "inventory_capability": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "tooling_ok", "rate_context": rate_unknown},
            ),
            "local_view_threat": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "no_threat", "rate_context": rate_unknown},
            ),
            "local_view_resource": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "resource_ok", "rate_context": rate_unknown},
            ),
            "local_view_utility": DimensionSnapshot(
                status="healthy",
                evidence={"reason": "utility_ok", "rate_context": rate_unknown},
            ),
        },
        overall_status="degraded",
        primary_gap={"type": "avatar_metabolic", "reason": "food_low"},
        trend="worsening",
        updated_at=now,
    )


def _make_previous_drive_table(now, *, exploration_level: float = 0.5) -> DriveStateTable:
    """Build a previous drive table that includes exploration at the given level."""

    drives = []
    for drive_type in CRAFTER_DRIVE_PRESET.drive_types:
        if drive_type == "exploration":
            drives.append(DriveState(drive_type="exploration", level=exploration_level, updated_at=now - timedelta(seconds=10)))
        else:
            drives.append(DriveState(drive_type=drive_type, level=0.0, updated_at=now - timedelta(seconds=10)))
    return DriveStateTable(
        captured_at=now - timedelta(seconds=10),
        drives=drives,
        updated_at=now - timedelta(seconds=10),
    )


def _make_threat_signal(now) -> SignalRecord:
    return SignalRecord(
        source="local_view_threat",
        signal_class="threat",
        payload={"reason": "threat_visible"},
        captured_at=now,
        rate_context={"available": False, "direction": "unknown", "magnitude": None, "acceleration": None},
    )


class CrafterExplorationDriveRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_exploration_drive_registered_in_crafter_preset(self) -> None:
        """Pin that exploration is part of Crafter's drive family and is
        flagged as the curiosity-style drive so the framework's
        recovery/suppression path engages."""

        self.assertIn(
            "exploration",
            CRAFTER_DRIVE_PRESET.drive_types,
            f"Round 1.B-2 must register 'exploration' as a Crafter drive type. Got: {CRAFTER_DRIVE_PRESET.drive_types}",
        )
        self.assertEqual(
            CRAFTER_DRIVE_PRESET.curiosity_drive_type,
            "exploration",
            "Crafter must opt the exploration drive into the framework curiosity-style update path "
            f"(curiosity_drive_type). Got: {CRAFTER_DRIVE_PRESET.curiosity_drive_type!r}",
        )

    def test_exploration_has_no_dimension_mapping(self) -> None:
        """Exploration is an internal drive — not driven by any sensor
        dimension. The curiosity-style path updates it via overall context
        (recovery in healthy, suppression in threat/degraded), not via
        dimension severity accumulation."""

        for dim, drive in CRAFTER_DRIVE_PRESET.drive_type_by_dimension.items():
            self.assertNotEqual(
                drive,
                "exploration",
                f"Dimension {dim} must not map to exploration drive; exploration is internal.",
            )


class CrafterExplorationDriveUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_exploration_recovers_under_healthy_snapshot_no_threat(self) -> None:
        """Healthy overall + no threat → exploration drive rises by
        curiosity_recovery (per framework _curiosity_delta logic)."""

        now = utc_now()
        previous = _make_previous_drive_table(now, exploration_level=0.0)
        snapshot = _make_healthy_snapshot(now)

        table, summary = update_drive_state(previous, snapshot, [])
        by_type = {drive.drive_type: drive for drive in table.drives}

        recovery = CRAFTER_DRIVE_PRESET.default_policy.curiosity_recovery
        self.assertGreater(
            recovery,
            0.0,
            f"Crafter curiosity_recovery must be positive; got {recovery}",
        )
        self.assertAlmostEqual(
            by_type["exploration"].level,
            recovery,
            places=4,
            msg=(
                f"Exploration drive must recover by curiosity_recovery in healthy state. "
                f"Got level {by_type['exploration'].level}, expected {recovery}"
            ),
        )

    def test_exploration_suppressed_under_threat_signal(self) -> None:
        """Threat signal present → exploration drive falls by
        curiosity_suppression (per framework _curiosity_delta logic)."""

        now = utc_now()
        starting_level = 0.5
        previous = _make_previous_drive_table(now, exploration_level=starting_level)
        snapshot = _make_healthy_snapshot(now)
        signals = [_make_threat_signal(now)]

        table, summary = update_drive_state(previous, snapshot, signals)
        by_type = {drive.drive_type: drive for drive in table.drives}

        suppression = CRAFTER_DRIVE_PRESET.default_policy.curiosity_suppression
        self.assertGreater(
            suppression,
            0.0,
            f"Crafter curiosity_suppression must be positive; got {suppression}",
        )
        self.assertAlmostEqual(
            by_type["exploration"].level,
            starting_level - suppression,
            places=4,
            msg=(
                f"Exploration drive must fall by curiosity_suppression under threat. "
                f"Got level {by_type['exploration'].level}, expected {starting_level - suppression}"
            ),
        )

    def test_exploration_suppressed_under_degraded_overall_status(self) -> None:
        """Overall status 'degraded' (no threat) → exploration drive falls
        by curiosity_suppression."""

        now = utc_now()
        starting_level = 0.5
        previous = _make_previous_drive_table(now, exploration_level=starting_level)
        snapshot = _make_degraded_snapshot(now)

        table, summary = update_drive_state(previous, snapshot, [])
        by_type = {drive.drive_type: drive for drive in table.drives}

        suppression = CRAFTER_DRIVE_PRESET.default_policy.curiosity_suppression
        self.assertAlmostEqual(
            by_type["exploration"].level,
            starting_level - suppression,
            places=4,
            msg=(
                f"Exploration must suppress under degraded overall status. "
                f"Got {by_type['exploration'].level}, expected {starting_level - suppression}"
            ),
        )


class CrafterExplorationDriveScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_compatibility_release_impact_includes_exploration_per_profile(self) -> None:
        """Pin that exploration impact is wired into the
        COMPATIBILITY_RELEASE_IMPACT table — required for exploration drive
        to actually shift candidate scoring."""

        for profile_name, profile_impact in COMPATIBILITY_RELEASE_IMPACT.items():
            self.assertIn(
                "exploration",
                profile_impact,
                f"COMPATIBILITY_RELEASE_IMPACT[{profile_name!r}] must include 'exploration' key; got keys {list(profile_impact)}",
            )

    def test_observe_first_scores_higher_than_stabilize_when_exploration_high(self) -> None:
        """Integration test: high exploration drive + low everything else
        must cause observe_first to outscore stabilize_first via the
        scenario-neutral drive-weighted scoring landed in Round 1.B-1-a +
        the exploration impact landed here."""

        drive_levels = {
            "metabolic": 0.1,
            "safety": 0.1,
            "recovery": 0.1,
            "acquisition": 0.1,
            "capability": 0.1,
            "exploration": 0.8,
        }
        drive_trends = {drive: "stable" for drive in drive_levels}

        def _candidate(candidate_id: str, candidate_profile: str) -> Candidate:
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
                    "primary_pressure_reason": "exploration_pull",
                },
                drive_impact_schema=dict(COMPATIBILITY_RELEASE_IMPACT[candidate_profile]),
            )

        deliberation_input = DeliberationInput(
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
                "top_drive": "exploration",
                "drive_levels": drive_levels,
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
                        "type": "exploration",
                        "severity": "degraded",
                        "evidence": {"reason": "exploration_pull"},
                    }
                ]
            },
            working_memory_context=None,
        )

        observe = _candidate("c-observe", "observe_first")
        stabilize = _candidate("c-stabilize", "stabilize_first")
        escalate = _candidate("c-escalate", "escalate_first")

        assessments = assess_candidates([observe, stabilize, escalate], deliberation_input)
        scores = {a.action: a.score for a in assessments}
        by_id = {a.candidate_id: a for a in assessments}

        # All three should pass the release gate because exploration is well
        # above DRIVE_LEVEL_RELEASE_THRESHOLD (0.3).
        for assessment in assessments:
            self.assertEqual(
                assessment.disposition,
                "allow",
                f"Candidate {assessment.candidate_id} should pass release gate with exploration=0.8; "
                f"got {assessment.disposition} with reasons {assessment.reasons}",
            )

        self.assertGreater(
            by_id["c-observe"].score,
            by_id["c-stabilize"].score,
            f"With high exploration drive, observe_first must outscore stabilize_first. "
            f"Got observe={by_id['c-observe'].score}, stabilize={by_id['c-stabilize'].score}",
        )
        self.assertGreater(
            by_id["c-observe"].score,
            by_id["c-escalate"].score,
            f"With high exploration drive, observe_first must outscore escalate_first. "
            f"Got observe={by_id['c-observe'].score}, escalate={by_id['c-escalate'].score}",
        )


if __name__ == "__main__":
    unittest.main()
