"""PR-3: Crafter-specific LLM producer for raw-action candidates within A'(s).

Generates 1-3 Candidate objects directly bearing raw Crafter actions
(move_left, do, sleep, etc.) chosen by the LLM from the pre-generative
action domain A'(s) built by PR-2's anchor layer.

Boundary:
- Only selects from A'(s); candidates outside A'(s) are silently discarded.
- Does NOT use compatibility_release / posture / action_hint / profile shells.
- Returns [] on any LLM failure (caller handles inhibition via default inhibition).
- Does NOT touch bridge executor / fallback (that is PR-4).
"""

from __future__ import annotations

import json
from typing import Any, Callable, TYPE_CHECKING

from eva.l3_deliberation.contracts import Candidate, DeliberationInput
from scenarios.crafter.anchors.policy import CrafterActionDomain, build_crafter_action_domain
from scenarios.crafter.state_packet import build_crafter_state_packet

if TYPE_CHECKING:
    from eva.anchor.domain_restriction import ActionDomain

__all__ = ["CrafterLLMActionProducer", "ChatFn"]

# Injected transport seam: takes OpenAI-style messages, returns assistant text.
# None = LLM unavailable → producer returns [].
ChatFn = Callable[[list[dict[str, str]]], str]

_MAX_CANDIDATES = 3

# Minimal drive-impact heuristic keyed by raw action category.
# move_* explores and may find resources; do harvests/crafts; sleep recovers;
# make_*/place_* build capability. noop and unknowns get no declared impact.
_MOVE_ACTIONS = frozenset({"move_left", "move_right", "move_up", "move_down"})


def _drive_impact_for_action(action: str) -> dict[str, float]:
    if action in _MOVE_ACTIONS:
        return {"metabolic": 0.15, "acquisition": 0.1}
    if action == "sleep":
        return {"recovery": 0.5}
    if action == "do":
        return {"acquisition": 0.35, "metabolic": 0.15}
    if action.startswith("make_"):
        return {"capability": 0.5, "acquisition": 0.2}
    if action.startswith("place_"):
        return {"capability": 0.3}
    return {}


class CrafterLLMActionProducer:
    """Crafter LLM producer: raw-action candidates within pre-generative A'(s)."""

    def __init__(
        self,
        *,
        chat_fn: ChatFn | None = None,
        world_facts_fn: Callable[[], str] | None = None,
        observation_fn: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.chat_fn = chat_fn
        self._world_facts_fn = world_facts_fn
        # Injected per-turn observation accessor (closed over live session).
        self._observation_fn = observation_fn

    def produce(
        self,
        action_domain: "ActionDomain",
        deliberation_input: DeliberationInput,
    ) -> list[Candidate]:
        """Generate raw-action candidates. Returns [] when LLM unavailable or fails."""
        if self.chat_fn is None:
            return []

        observation = self._observation_fn() if self._observation_fn is not None else {}
        agent_state = action_domain.agent_state

        crafter_domain = build_crafter_action_domain(agent_state, observation)
        if not crafter_domain.action_set:
            return []

        state_packet = build_crafter_state_packet(
            observation,
            drive_broadcast=deliberation_input.drive_broadcast,
            working_memory_context=deliberation_input.working_memory_context,
            available_actions=sorted(crafter_domain.action_set),
        )
        recent_memory = _extract_recent_memory(deliberation_input.working_memory_context)

        try:
            messages = self._build_messages(state_packet, crafter_domain, recent_memory)
            text = self.chat_fn(messages)
            raw = _parse_raw_candidates(text)
        except Exception:
            return []

        return _build_candidates(raw, crafter_domain=crafter_domain, agent_state=agent_state)

    def _build_messages(
        self,
        state_packet: dict[str, Any],
        crafter_domain: CrafterActionDomain,
        recent_memory: str,
    ) -> list[dict[str, str]]:
        admitted = sorted(crafter_domain.action_set)
        situation: dict[str, Any] = {
            "state_packet": state_packet,
            "admitted_actions": admitted,
        }
        if recent_memory:
            situation["recent_memory"] = recent_memory

        user_content = (
            "Choose 1-3 actions STRICTLY from admitted_actions. "
            "Return JSON only: "
            '{"candidates": [{"action": "<action>", "reason": "<reason>"}, ...]}\n'
            f"{json.dumps(situation, ensure_ascii=False)}"
        )
        system_content = (
            "You are the Crafter reasoning core (dlPFC). The anchor layer has "
            "pre-selected the admitted action set A'(s). Choose concrete raw actions "
            "only from admitted_actions; never invent or return an action not listed. "
            "Respond with JSON only."
        )
        if self._world_facts_fn is not None:
            world_facts = self._world_facts_fn()
            if world_facts:
                system_content = (
                    f"Background world facts:\n{world_facts}\n\n{system_content}"
                )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_recent_memory(working_memory_context: dict[str, Any] | None) -> str:
    if not isinstance(working_memory_context, dict):
        return ""
    summary = (
        working_memory_context.get("summary")
        or working_memory_context.get("situation_key")
        or ""
    )
    return str(summary).strip() if summary else ""


def _parse_raw_candidates(text: str) -> list[dict[str, str]]:
    """Parse LLM response into [{action, reason}] list, up to _MAX_CANDIDATES."""
    payload = _first_json_object(text)
    if not isinstance(payload, dict):
        return []
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, str]] = []
    for item in raw[:_MAX_CANDIDATES]:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if action:
            result.append({"action": action, "reason": reason})
    return result


def _build_candidates(
    raw_candidates: list[dict[str, str]],
    *,
    crafter_domain: CrafterActionDomain,
    agent_state: Any,
) -> list[Candidate]:
    """Materialize Candidate objects; discard any action not in A'(s)."""
    runtime_gate = getattr(agent_state, "runtime_gate_context", {}) or {}
    gate_fields: dict[str, Any] = {
        "turn_allowed": bool(runtime_gate.get("turn_allowed", False)),
        "instance_valid": bool(runtime_gate.get("instance_valid", False)),
        "critical_blocked": bool(runtime_gate.get("critical_blocked", False)),
        "life_state": str(runtime_gate.get("life_state") or "unknown"),
        "conservative_mode": bool(runtime_gate.get("conservative_mode", False)),
        "compatibility_pressure_count": int(
            getattr(agent_state, "compatibility_pressure_count", 0)
        ),
        "primary_pressure_reason": str(
            getattr(agent_state, "primary_pressure_reason", "none") or "none"
        ),
        # Marks this as a raw-action candidate for value_judgment / conflict_detection.
        "candidate_kind": "raw_action",
        "raw_action_candidate": True,
        "candidate_profile": "crafter_raw_action",
    }

    seen: set[str] = set()
    candidates: list[Candidate] = []
    for item in raw_candidates:
        action = item["action"]
        if action in seen:
            continue
        # Discard candidates outside A'(s) (pre-generative boundary enforced here).
        if action not in crafter_domain.action_set:
            continue
        seen.add(action)
        reason = item.get("reason", "")
        # Keep the LLM-given reason in justification (audit trace) so a short-run
        # replay can see *why* the model chose this action, not just *what*.
        reason_excerpt = reason[:80] if reason else ""
        justification: tuple[str, ...] = (
            "crafter_llm_action_producer",
            f"action={action}",
            "domain_restricted",
        )
        if reason_excerpt:
            justification = (*justification, f"reason={reason_excerpt}")
        candidates.append(
            Candidate(
                candidate_id=f"candidate-crafter-{action.replace('_', '-')}",
                capability="raw_action",
                action=action,
                parameter_domain={**gate_fields, "reason": reason},
                justification=justification,
                drive_impact_schema=_drive_impact_for_action(action),
                side_effect_class="crafter_raw_action",
            )
        )
    return candidates


def _first_json_object(text: str) -> Any:
    """Parse the first JSON object found in text; None on failure."""
    if not isinstance(text, str):
        return None
    stripped = text.strip()
    texts_to_try: list[str] = [stripped]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        texts_to_try.append(stripped[start: end + 1])
    for candidate_text in texts_to_try:
        try:
            return json.loads(candidate_text)
        except json.JSONDecodeError:
            continue
    return None
