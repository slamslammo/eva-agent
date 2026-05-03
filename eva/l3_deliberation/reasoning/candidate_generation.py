"""Candidate generation for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from typing import Any

from ..contracts import Candidate, DeliberationInput
from ..peer_circuit.habit_track import shape_candidates_with_habit_track

OBSERVE_FIRST_PROFILE = "observe_first"
STABILIZE_FIRST_PROFILE = "stabilize_first"


def build_candidates(deliberation_input: DeliberationInput) -> list[Candidate]:
    """Build the minimal internal candidate set from B0 input surfaces."""

    signal_summary = deliberation_input.signal_batch.get("summary", {})
    drive_broadcast = deliberation_input.drive_broadcast
    threat_count = int(signal_summary.get("threat_signal_count", 0))
    top_drive = str(drive_broadcast.get("top_drive") or "unknown")
    compatibility_pressure_count = 0
    if deliberation_input.compatibility_pressure_table is not None:
        pressures = deliberation_input.compatibility_pressure_table.get("pressures", [])
        if isinstance(pressures, list):
            compatibility_pressure_count = len(pressures)

    common_domain = {
        "top_drive": top_drive,
        "threat_signal_count": threat_count,
        "compatibility_pressure_count": compatibility_pressure_count,
    }
    common_justification = (
        f"top_drive={top_drive}",
        f"threat_signal_count={threat_count}",
    )
    candidates = [
        _build_candidate(
            candidate_id="candidate-compatibility-observe-first",
            candidate_profile=OBSERVE_FIRST_PROFILE,
            common_domain=common_domain,
            common_justification=common_justification,
        ),
        _build_candidate(
            candidate_id="candidate-compatibility-stabilize-first",
            candidate_profile=STABILIZE_FIRST_PROFILE,
            common_domain=common_domain,
            common_justification=common_justification,
        ),
    ]
    return shape_candidates_with_habit_track(candidates, deliberation_input)


def _build_candidate(
    *,
    candidate_id: str,
    candidate_profile: str,
    common_domain: dict[str, Any],
    common_justification: tuple[str, ...],
) -> Candidate:
    """Build one base candidate before habit-path shaping."""

    return Candidate(
        candidate_id=candidate_id,
        capability="compatibility_response",
        action="compatibility_release",
        parameter_domain={
            **common_domain,
            "candidate_profile": candidate_profile,
        },
        justification=(
            f"candidate_profile={candidate_profile}",
            *common_justification,
        ),
    )
