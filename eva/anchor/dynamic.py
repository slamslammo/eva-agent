"""Dynamic anchor restrictions derived from the current runtime condition."""

from __future__ import annotations

from ..l3_deliberation.contracts import Candidate, DeliberationInput


def apply_dynamic_anchor(candidate: Candidate, deliberation_input: DeliberationInput) -> Candidate:
    """Inject dynamic runtime-state constraints into one candidate domain."""

    runtime_gate = deliberation_input.runtime_gate_context
    restricted_domain = dict(candidate.parameter_domain)
    restricted_domain["conservative_mode"] = bool(runtime_gate.get("conservative_mode", False))
    restricted_domain["life_state"] = runtime_gate.get("life_state")
    return Candidate(
        candidate_id=candidate.candidate_id,
        capability=candidate.capability,
        action=candidate.action,
        parameter_domain=restricted_domain,
        justification=candidate.justification,
        drive_impact_schema=dict(candidate.drive_impact_schema),
        side_effect_class=candidate.side_effect_class,
    )


__all__ = ["apply_dynamic_anchor"]
