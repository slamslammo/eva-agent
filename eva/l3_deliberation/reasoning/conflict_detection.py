"""Read-only drive/candidate tension detection and structural conflict surfacing."""

from __future__ import annotations

from dataclasses import dataclass

from .candidate_generation import current_anchor_profiles
from ..contracts import Candidate

DRIVE_CONFLICT_THRESHOLD = 0.5
SIGNIFICANT_IMPACT_THRESHOLD = 0.15

# Round 1.B-1: scenario-neutral release / projection thresholds. These replace
# the previous ``top_drive == "integrity"`` magic-string checks with
# drive-level semantics that work for any scenario's drive vocabulary.
#
# ``DRIVE_LEVEL_RELEASE_THRESHOLD`` — minimum top-drive level that constitutes
# "release pressure". Below this, in the absence of threats, the candidate is
# withheld for lack of pressure. 0.3 chosen as the value that keeps existing
# Linux tests bit-equivalent: any realistic Linux state with
# ``top_drive == "integrity"`` has integrity level above 0.3 (otherwise some
# other drive would have become top).
#
# ``HIGH_DRIVE_PROJECTION_THRESHOLD`` — above this, a candidate's profile-
# specific projection boost is engaged (stabilize_first +0.75, escalate_first
# +1.0). Below this, observe_first gets its "low-pressure exploration"
# +0.25 boost instead. 0.5 chosen to match the implicit Linux semantic that
# ``top_drive == "integrity"`` meant "drive is meaningfully engaged."
DRIVE_LEVEL_RELEASE_THRESHOLD = 0.3
HIGH_DRIVE_PROJECTION_THRESHOLD = 0.5

__all__ = [
    "CandidateConflictContext",
    "build_candidate_conflict_context",
]


@dataclass(frozen=True)
class CandidateConflictContext:
    """Normalized conflict/tension view for one candidate under current reasoning input."""

    candidate_profile: str
    disposition: str
    reasons: tuple[str, ...]
    score_delta: float = 0.0


def build_candidate_conflict_context(
    candidate: Candidate,
    *,
    top_drive: str,
    threat_count: int,
    drive_levels: dict[str, float] | None = None,
) -> CandidateConflictContext:
    """Return structural conflict and pressure-tension context for one candidate."""

    if candidate.action != "compatibility_release":
        return CandidateConflictContext(
            candidate_profile="unknown",
            disposition="withhold",
            reasons=("unknown_candidate_action",),
        )

    anchor_profiles = current_anchor_profiles()
    candidate_profile = str(candidate.parameter_domain.get("candidate_profile") or "unknown")
    if candidate_profile not in {
        anchor_profiles.observe_first_profile,
        anchor_profiles.stabilize_first_profile,
        anchor_profiles.escalate_first_profile,
    }:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=(f"candidate_profile={candidate_profile}", "unknown_candidate_profile"),
        )

    reasons = [f"candidate_profile={candidate_profile}"]
    turn_allowed = bool(candidate.parameter_domain.get("turn_allowed", False))
    instance_valid = bool(candidate.parameter_domain.get("instance_valid", False))
    critical_blocked = bool(candidate.parameter_domain.get("critical_blocked", False))
    life_state = str(candidate.parameter_domain.get("life_state") or "unknown")
    conservative_mode = bool(candidate.parameter_domain.get("conservative_mode", False))

    if not instance_valid:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "instance_not_valid"]),
        )
    if not turn_allowed:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "turn_not_allowed"]),
        )
    if critical_blocked:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="defer",
            reasons=tuple([*reasons, "critical_runtime_boundary"]),
        )
    if life_state == "CRITICAL":
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="defer",
            reasons=tuple([*reasons, "critical_life_state"]),
        )
    if conservative_mode:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="defer",
            reasons=tuple([*reasons, "conservative_mode_active"]),
        )

    compatibility_pressure_count = int(candidate.parameter_domain.get("compatibility_pressure_count", 0))
    primary_pressure_reason = str(candidate.parameter_domain.get("primary_pressure_reason") or "none")
    top_drive_level = _coerce_drive_level((drive_levels or {}).get(top_drive))
    if top_drive_level < DRIVE_LEVEL_RELEASE_THRESHOLD and threat_count <= 0:
        return CandidateConflictContext(
            candidate_profile=candidate_profile,
            disposition="withhold",
            reasons=tuple([*reasons, "no_release_pressure"]),
        )

    pressure_reasons = [*reasons, "compatibility_projection_present"]
    score_delta = float(threat_count)
    if candidate_profile == anchor_profiles.stabilize_first_profile:
        if top_drive_level >= HIGH_DRIVE_PROJECTION_THRESHOLD:
            score_delta += 0.75
            pressure_reasons.append("high_drive_projection_for_stabilize_first")
        if compatibility_pressure_count > 0:
            score_delta += 0.5
            pressure_reasons.append("pressure_projection_for_stabilize_first")
    elif candidate_profile == anchor_profiles.observe_first_profile:
        if top_drive_level < HIGH_DRIVE_PROJECTION_THRESHOLD:
            score_delta += 0.25
            pressure_reasons.append("low_drive_projection_for_observe_first")
        if compatibility_pressure_count == 0:
            score_delta += 0.25
            pressure_reasons.append("low_pressure_projection_for_observe_first")
    elif candidate_profile == anchor_profiles.escalate_first_profile:
        if top_drive_level >= HIGH_DRIVE_PROJECTION_THRESHOLD:
            score_delta += 1.0
            pressure_reasons.append("high_drive_projection_for_escalate_first")
        if primary_pressure_reason in anchor_profiles.high_risk_escalation_reasons:
            score_delta += 1.0
            pressure_reasons.append("high_risk_projection_for_escalate_first")
        if compatibility_pressure_count > 0:
            score_delta += 0.25
            pressure_reasons.append("pressure_projection_for_escalate_first")

    drive_tension_reasons = _drive_tension_reasons(
        candidate.drive_impact_schema,
        drive_levels=drive_levels or {},
    )
    for reason in drive_tension_reasons:
        if reason not in pressure_reasons:
            pressure_reasons.append(reason)

    return CandidateConflictContext(
        candidate_profile=candidate_profile,
        disposition="allow",
        reasons=tuple(pressure_reasons),
        score_delta=score_delta,
    )


def _drive_tension_reasons(
    drive_impact_schema: dict[str, float],
    *,
    drive_levels: dict[str, float],
) -> list[str]:
    """Return compact reasons when a candidate helps one high drive while harming another."""

    if not drive_impact_schema or not drive_levels:
        return []
    supported = [
        drive_name
        for drive_name, impact in drive_impact_schema.items()
        if impact >= SIGNIFICANT_IMPACT_THRESHOLD and float(drive_levels.get(drive_name, 0.0)) >= DRIVE_CONFLICT_THRESHOLD
    ]
    harmed = [
        drive_name
        for drive_name, impact in drive_impact_schema.items()
        if impact <= -SIGNIFICANT_IMPACT_THRESHOLD and float(drive_levels.get(drive_name, 0.0)) >= DRIVE_CONFLICT_THRESHOLD
    ]
    if not supported or not harmed:
        return []
    reasons = ["drive_tension_detected"]
    reasons.extend(f"supports_high_drive:{drive_name}" for drive_name in sorted(supported))
    reasons.extend(f"harms_high_drive:{drive_name}" for drive_name in sorted(harmed))
    return reasons


def _coerce_drive_level(value: object) -> float:
    """Clamp a drive-level payload value to [0.0, 1.0]; non-numeric -> 0.0.

    Defensive helper for scenario-neutral release / projection thresholding.
    The drive broadcast nominally carries floats, but we coerce here to avoid
    crashing if a deliberation_input arrives with malformed level data."""

    try:
        return max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
