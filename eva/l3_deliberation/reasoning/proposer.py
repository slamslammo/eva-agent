"""Round 1.E — L3 reasoning proposal seam.

A ``Proposer`` turns the anchor-admitted candidate domain + working-memory context
into a ranked set of ``ReasoningProposal``s; ``normalize_proposals`` maps them back
into the existing ``Candidate`` vocabulary, dropping anything outside the admitted
domain. The proposer shapes *which candidates are considered and in what order* —
peer-circuit selection and mediator release authority are unchanged (red-lines §6).

DP1 = (a): ``ModelBackedProposer`` reuses the upstream ``advisory_context`` (no new
LLM call). The ``Proposer`` protocol leaves room for a future schema-bound-JSON
proposer (option b) to drop in without touching the seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ..contracts import Candidate, ReasoningProposal

if TYPE_CHECKING:
    from ...anchor.domain_restriction import ActionDomain, CandidateSchema

__all__ = [
    "HeuristicProposer",
    "ModelBackedProposer",
    "NormalizationResult",
    "Proposer",
    "ReasoningProposal",
    "normalize_proposals",
]


@runtime_checkable
class Proposer(Protocol):
    """Produce ranked reasoning proposals within the anchor-admitted domain only."""

    def propose(
        self, working_memory_context: dict[str, Any], action_domain: "ActionDomain"
    ) -> list[ReasoningProposal]:
        ...


class HeuristicProposer:
    """Deterministic default proposer: every admitted schema, in admitted order.

    Behavior-preserving — ``normalize_proposals(propose(...))`` reproduces
    ``build_candidates(action_domain)``. This is the ``local_rule_based`` proposer.
    """

    def propose(
        self, working_memory_context: dict[str, Any], action_domain: "ActionDomain"
    ) -> list[ReasoningProposal]:
        del working_memory_context  # heuristic ignores the advisory signal
        return [
            ReasoningProposal(
                proposal_id=f"prop-heuristic-{index}",
                candidate_profile=schema.candidate_profile,
                action_hint=schema.action,
                rationale=("heuristic_admitted_order",),
                confidence=0.0,
                provenance="heuristic",
            )
            for index, schema in enumerate(action_domain.admitted_candidate_schemas)
        ]


class ModelBackedProposer:
    """Rank admitted schemas using the upstream ``advisory_context`` (DP1 = a).

    Profiles the model suggested are ranked first (in suggestion order); the rest
    keep admitted order. **No candidate is dropped** — bounded shaping is re-ranking
    only, so the peer-circuit/mediator still see the full admitted set, and the
    model can never starve the agent of a viable option. With no advisory present
    (model off / ``local_rule_based``) it degrades to admitted order (heuristic).
    """

    def propose(
        self, working_memory_context: dict[str, Any], action_domain: "ActionDomain"
    ) -> list[ReasoningProposal]:
        schemas = list(action_domain.admitted_candidate_schemas)
        suggestions, confidence = _advisory_signal(working_memory_context)
        if not suggestions:
            return HeuristicProposer().propose(working_memory_context, action_domain)

        def rank_key(item: tuple[int, "CandidateSchema"]) -> tuple[int, int]:
            order, schema = item
            profile = schema.candidate_profile
            primary = suggestions.index(profile) if profile in suggestions else len(suggestions)
            return (primary, order)

        ordered = sorted(enumerate(schemas), key=rank_key)
        proposals: list[ReasoningProposal] = []
        for new_index, (_original_index, schema) in enumerate(ordered):
            suggested = schema.candidate_profile in suggestions
            proposals.append(
                ReasoningProposal(
                    proposal_id=f"prop-model-{new_index}",
                    candidate_profile=schema.candidate_profile,
                    action_hint=schema.action,
                    rationale=("model_advisory_suggested",) if suggested else ("model_advisory_residual",),
                    confidence=confidence if suggested else 0.0,
                    provenance="model_advisory",
                )
            )
        return proposals


def _advisory_signal(working_memory_context: dict[str, Any] | None) -> tuple[list[str], float]:
    """Extract (candidate_suggestions, confidence) from the upstream advisory_context."""

    advisory = (working_memory_context or {}).get("advisory_context")
    if not isinstance(advisory, dict):
        return [], 0.0
    raw = advisory.get("candidate_suggestions")
    suggestions = [str(item) for item in raw] if isinstance(raw, list) else []
    try:
        confidence = float(advisory.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return suggestions, confidence


@dataclass(frozen=True)
class NormalizationResult:
    """Outcome of mapping proposals into the admitted candidate vocabulary.

    ``linkage`` maps each materialized ``candidate_id`` to the ``proposal_id`` that
    produced it — the basis for the E-6 reasoning-contribution signal (which
    proposal, if any, the mediator's selected candidate came from).
    """

    candidates: list[Candidate]
    rejections: list[dict[str, Any]]
    linkage: dict[str, str] = field(default_factory=dict)


def normalize_proposals(
    proposals: list[ReasoningProposal], action_domain: "ActionDomain"
) -> NormalizationResult:
    """Map proposals to admitted candidates; drop + log anything out-of-domain.

    A proposal is rejected when its ``candidate_profile`` is not in the admitted
    domain, or its ``action_hint`` names an action outside the admitted set. Each
    admitted schema materializes at most once (first proposal wins its slot); the
    resulting candidate order follows proposal order (the considered-set ordering).
    """

    schemas_by_profile: dict[str, list["CandidateSchema"]] = {}
    for schema in action_domain.admitted_candidate_schemas:
        schemas_by_profile.setdefault(schema.candidate_profile, []).append(schema)
    admitted_actions = {schema.action for schema in action_domain.admitted_candidate_schemas}

    candidates: list[Candidate] = []
    rejections: list[dict[str, Any]] = []
    linkage: dict[str, str] = {}
    used_candidate_ids: set[str] = set()
    for proposal in proposals:
        if proposal.candidate_profile not in schemas_by_profile:
            rejections.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "candidate_profile": proposal.candidate_profile,
                    "reason": "profile_not_admitted",
                }
            )
            continue
        if proposal.action_hint is not None and proposal.action_hint not in admitted_actions:
            rejections.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "action_hint": proposal.action_hint,
                    "reason": "action_not_admitted",
                }
            )
            continue
        schema = _match_schema(schemas_by_profile[proposal.candidate_profile], proposal.action_hint)
        if schema.candidate_id in used_candidate_ids:
            continue
        used_candidate_ids.add(schema.candidate_id)
        candidates.append(schema.to_candidate())
        linkage[schema.candidate_id] = proposal.proposal_id
    return NormalizationResult(candidates=candidates, rejections=rejections, linkage=linkage)


def _match_schema(schemas: list["CandidateSchema"], action_hint: str | None) -> "CandidateSchema":
    """Pick the schema matching ``action_hint`` within a profile, else the first."""

    if action_hint is not None:
        for schema in schemas:
            if schema.action == action_hint:
                return schema
    return schemas[0]
