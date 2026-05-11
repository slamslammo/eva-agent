"""Candidate generation for the minimal Phase B L3 skeleton."""

from __future__ import annotations

from ..contracts import Candidate
from ...anchor.domain_restriction import ActionDomain, AnchorConstants, get_anchor_constants


def build_candidates(action_domain: ActionDomain) -> list[Candidate]:
    """Build the minimal internal candidate set from admitted pre-generative schemas."""

    return [schema.to_candidate() for schema in action_domain.admitted_candidate_schemas]


def current_anchor_profiles() -> AnchorConstants:
    """Return the current scenario-owned candidate-profile vocabulary."""

    return get_anchor_constants()
