"""Round 1.G — L3 dlPFC candidate-producer seam.

Per theory (v0.5 §8.6.3 / blueprint §7.4) the reasoning core (dlPFC) *forms the
candidate set* within the anchor-bounded domain; selection (peer-circuit) and
release (mediator) authority downstream are unchanged — a producer never selects
or releases.

Phase 1 ships the deterministic ``HeuristicCandidateProducer`` (= the anchor-admitted
schemas materialized = pre-1.G behavior), establishing the seam without any LLM. The
live-LLM producer (phase 2) plugs into the same ``CandidateProducer`` protocol and
degrades to the heuristic on error/timeout, so ``local_rule_based`` / model-off stays
behavior-preserving.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..contracts import Candidate, DeliberationInput
from .candidate_generation import build_candidates

if TYPE_CHECKING:
    from ...anchor.domain_restriction import ActionDomain

__all__ = ["CandidateProducer", "HeuristicCandidateProducer"]


@runtime_checkable
class CandidateProducer(Protocol):
    """Form the candidate set within the anchor-bounded domain (dlPFC role)."""

    def produce(
        self, action_domain: "ActionDomain", deliberation_input: DeliberationInput
    ) -> list[Candidate]:
        ...


class HeuristicCandidateProducer:
    """Deterministic producer = anchor-admitted schemas materialized (pre-1.G behavior).

    The ``local_rule_based`` / model-off default, and the fallback the live-LLM
    producer degrades to. Behavior-preserving: ``produce`` equals
    ``build_candidates(action_domain)``.
    """

    def produce(
        self, action_domain: "ActionDomain", deliberation_input: DeliberationInput
    ) -> list[Candidate]:
        del deliberation_input  # heuristic uses only the anchor-bounded domain
        return build_candidates(action_domain)
