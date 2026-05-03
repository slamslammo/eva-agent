"""Cross-layer anchor composition entry for the current minimal L3 path."""

from __future__ import annotations

from ..l3_deliberation.contracts import Candidate, DeliberationInput
from .domain_restriction import restrict_candidate_domain

__all__ = ["apply_structural_anchors", "restrict_candidate_domain"]


def apply_structural_anchors(candidates: list[Candidate], deliberation_input: DeliberationInput) -> list[Candidate]:
    """Apply the current anchor restriction stack to all candidates."""

    return [restrict_candidate_domain(candidate, deliberation_input) for candidate in candidates]
