"""Candidate-domain restriction composed from structural and dynamic anchors."""

from __future__ import annotations

from ..l3_deliberation.contracts import Candidate, DeliberationInput
from .dynamic import apply_dynamic_anchor
from .structural import apply_structural_anchor


def restrict_candidate_domain(candidate: Candidate, deliberation_input: DeliberationInput) -> Candidate:
    """Restrict one candidate domain through the current anchor stack."""

    anchored = apply_structural_anchor(candidate, deliberation_input)
    return apply_dynamic_anchor(anchored, deliberation_input)


__all__ = ["restrict_candidate_domain"]
