"""Round 1.G phase 2 (a) — live-LLM dlPFC candidate producer (action_hint lever).

Per the phase-2 (a) contract: drive decides the posture/profile (the mediator's
frozen OFC-max selection); within that posture the live reasoning core (dlPFC =
LLM) chooses the *concrete* action. This producer's only causal lever is the
``action_hint`` it annotates onto each candidate — it **never adds or removes
candidates and never changes a candidate's profile**, so the drive-locked posture
(and the round-1f anti-passivity guarantee) is structurally preserved.

The producer wraps a deterministic ``base_producer`` (the heuristic seam). For each
base candidate it asks the model, in one bounded schema-bound JSON call, for the
single most useful concrete action within that profile's eligible-action set. A
returned action is attached as ``action_hint`` only when it is eligible for that
profile (the scenario bridge enforces eligibility a second time at consumption).
On any error / timeout / unparseable output the base candidates are returned
unchanged → degrades to heuristic, so ``local_rule_based`` / model-off and a
flaky upstream are both behavior-preserving.
"""

from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING, Any, Callable, Mapping, Sequence

from ..contracts import Candidate, DeliberationInput
from .candidate_producer import CandidateProducer, HeuristicCandidateProducer

if TYPE_CHECKING:
    from ...anchor.domain_restriction import ActionDomain

__all__ = ["LLMCandidateProducer", "ChatFn", "VocabSource"]

# Injected transport seam: takes OpenAI-style ``messages`` and returns the
# assistant's text. The framework stays vendor-neutral; the live wiring builds
# this from the existing working-memory model-client transport, and tests inject
# a stub. ``None`` disables the LLM (→ pure heuristic).
ChatFn = Callable[[list[dict[str, str]]], str]

# Scenario-owned per-posture action vocabulary. Either a static mapping or a
# zero-arg callable resolved per ``produce()`` (round-1i a2: lets the scenario
# return only the actions feasible *this turn*, e.g. filtered by current inventory).
# The producer treats it opaquely and never imports the scenario.
VocabSource = Mapping[str, Sequence[str]] | Callable[[], Mapping[str, Sequence[str]]]

_PROFILE_KEY = "candidate_profile"
_MAX_VOCAB_IN_PROMPT = 16


class LLMCandidateProducer:
    """Annotate heuristic candidates with a live-LLM ``action_hint`` per posture."""

    def __init__(
        self,
        base_producer: CandidateProducer | None = None,
        *,
        chat_fn: ChatFn | None = None,
        profile_action_vocab: VocabSource | None = None,
        world_facts_fn: "Callable[[], str] | None" = None,
    ) -> None:
        self.base_producer = base_producer or HeuristicCandidateProducer()
        self.chat_fn = chat_fn
        # Scenario-owned vocabulary (profile -> eligible concrete actions), injected
        # by the runtime so the framework producer stays generic (no scenario import).
        # round-1i (a2): may be a **callable** resolved per ``produce()`` so the scenario
        # can return only the actions feasible *this turn* (e.g. filtered by current
        # inventory) — the producer treats it opaquely. A static mapping still works.
        self._vocab_source: VocabSource | None = profile_action_vocab
        # round-1j: optional zero-arg callable that returns a world-facts string block.
        # When non-None, its output is prepended to the system message so the LLM has
        # background knowledge (tech tree, crafting recipes, survival facts) before
        # choosing an action hint. None = complete backward-compat (no prompt change).
        self._world_facts_fn: "Callable[[], str] | None" = world_facts_fn

    def _resolve_vocab(self) -> dict[str, tuple[str, ...]]:
        """Resolve the per-turn vocabulary (call the source if it is a callable)."""

        source = self._vocab_source
        if callable(source):
            source = source()
        if not isinstance(source, Mapping):
            return {}
        return {str(profile): tuple(str(a) for a in actions) for profile, actions in source.items()}

    def produce(
        self, action_domain: "ActionDomain", deliberation_input: DeliberationInput
    ) -> list[Candidate]:
        base = list(self.base_producer.produce(action_domain, deliberation_input))
        vocab = self._resolve_vocab()
        if self.chat_fn is None or not base or not vocab:
            return base
        try:
            text = self.chat_fn(self._build_messages(base, deliberation_input, vocab))
            hints = _parse_action_hints(text)
        except Exception:
            # Any failure (transport, timeout, parse) degrades to heuristic.
            return base
        if not hints:
            return base
        return [self._maybe_attach_hint(candidate, hints, vocab) for candidate in base]

    # -- internal -----------------------------------------------------------

    def _maybe_attach_hint(
        self, candidate: Candidate, hints: dict[str, str], vocab: dict[str, tuple[str, ...]]
    ) -> Candidate:
        """Attach a hint only when it is eligible (feasible) for the candidate's profile."""

        profile = str(candidate.parameter_domain.get(_PROFILE_KEY) or "")
        if not profile:
            return candidate
        action = hints.get(profile)
        if not action:
            return candidate
        if action not in vocab.get(profile, ()):  # ineligible / infeasible this turn
            return candidate
        return dataclasses.replace(candidate, action_hint=action)

    def _build_messages(
        self,
        base: list[Candidate],
        deliberation_input: DeliberationInput,
        vocab: dict[str, tuple[str, ...]],
    ) -> list[dict[str, str]]:
        """Build a compact, bounded chat request enumerating per-posture options."""

        profiles = [
            str(c.parameter_domain.get(_PROFILE_KEY) or "")
            for c in base
            if c.parameter_domain.get(_PROFILE_KEY)
        ]
        options = {
            profile: list(vocab.get(profile, ())[:_MAX_VOCAB_IN_PROMPT])
            for profile in profiles
            if profile in vocab
        }
        drive = deliberation_input.drive_broadcast
        situation = {
            "top_drive": drive.get("top_drive"),
            "drive_levels": drive.get("drive_levels"),
            "options_per_posture": options,
        }
        wm = deliberation_input.working_memory_context or {}
        if isinstance(wm.get("situation_key"), str) and wm["situation_key"]:
            situation["situation_key"] = wm["situation_key"]
        user_prompt = (
            "For each posture key, choose the single most useful concrete action "
            "STRICTLY from that posture's options list. Return only a JSON object "
            '{"action_hints": {<posture>: <action>}}. Use only listed actions; omit '
            "a posture if unsure. You cannot release actions or invent new ones.\n"
            f"{json.dumps(situation, ensure_ascii=False, sort_keys=True)}"
        )
        system_content = (
            "You are a bounded EVA reasoning core (dlPFC). The posture is "
            "already chosen by drive; you only pick the concrete action within "
            "it. Respond with JSON only."
        )
        # round-1j: prepend world facts (tech tree, crafting recipes, survival
        # parameters) to the system message when provided. When world_facts_fn
        # is None this block is skipped entirely → backward-compatible.
        if self._world_facts_fn is not None:
            world_facts = self._world_facts_fn()
            if world_facts:
                system_content = (
                    f"Background world facts:\n{world_facts}\n\n{system_content}"
                )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]


def _parse_action_hints(text: str) -> dict[str, str]:
    """Extract a bounded ``{profile: action}`` map from a model text response."""

    payload = _first_json_object(text)
    if not isinstance(payload, dict):
        return {}
    raw = payload.get("action_hints")
    if not isinstance(raw, dict):
        return {}
    hints: dict[str, str] = {}
    for profile, action in raw.items():
        if isinstance(profile, str) and isinstance(action, str) and profile and action:
            hints[profile] = action
    return hints


def _first_json_object(text: str) -> Any:
    """Parse the first outermost JSON object found in free text; None on failure."""

    if not isinstance(text, str):
        return None
    stripped = text.strip()
    candidates: list[str] = [stripped]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        candidates.append(stripped[start : end + 1])
    for candidate_text in candidates:
        try:
            return json.loads(candidate_text)
        except json.JSONDecodeError:
            continue
    return None
