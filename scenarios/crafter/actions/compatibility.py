"""Crafter bridge executor (PR-4): raw-action execution path.

PR-4 removes the profile-based pathfinding AI and candidate-scoring machinery.
The bridge now only executes the raw action already decided by the mediator:

1. Read the mediator-released raw action from release_context["action_hint"]
   (threaded by runtime._thread_selected_action_hint for raw-action candidates).
2. Validate it is a known Crafter action.
3. Return ResponseSelection.
4. Fallback: defer with noop + "crafter_bridge_defer_no_raw_action" reason when
   no valid action is found in release_context (LLM unavailable → mediator
   withheld → bridge never called; this path only fires for edge cases).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eva.kernel import ActivePressure, RuntimeState, StateStore

if TYPE_CHECKING:
    from scenarios.crafter.wrapper import StepResult
    from eva.l3_deliberation.tool_edge.tool_registry import ResponseCandidate, ResponseFilterDecision, ResponseSelection

NOOP_ACTION = "noop"
MOVE_LEFT_ACTION = "move_left"
MOVE_RIGHT_ACTION = "move_right"
MOVE_UP_ACTION = "move_up"
MOVE_DOWN_ACTION = "move_down"
DO_ACTION = "do"
SLEEP_ACTION = "sleep"
PLACE_STONE_ACTION = "place_stone"
PLACE_TABLE_ACTION = "place_table"
PLACE_FURNACE_ACTION = "place_furnace"
PLACE_PLANT_ACTION = "place_plant"
MAKE_WOOD_PICKAXE_ACTION = "make_wood_pickaxe"
MAKE_STONE_PICKAXE_ACTION = "make_stone_pickaxe"
MAKE_IRON_PICKAXE_ACTION = "make_iron_pickaxe"
MAKE_WOOD_SWORD_ACTION = "make_wood_sword"
MAKE_STONE_SWORD_ACTION = "make_stone_sword"
MAKE_IRON_SWORD_ACTION = "make_iron_sword"

RECHECK_ACTION = NOOP_ACTION
REPAIR_ACTION = SLEEP_ACTION
ESCALATE_ACTION = DO_ACTION
DEFAULT_RESPONSE_MODE = "crafter_bounded_compatibility"

ALL_ACTIONS = (
    NOOP_ACTION,
    MOVE_LEFT_ACTION,
    MOVE_RIGHT_ACTION,
    MOVE_UP_ACTION,
    MOVE_DOWN_ACTION,
    DO_ACTION,
    SLEEP_ACTION,
    PLACE_STONE_ACTION,
    PLACE_TABLE_ACTION,
    PLACE_FURNACE_ACTION,
    PLACE_PLANT_ACTION,
    MAKE_WOOD_PICKAXE_ACTION,
    MAKE_STONE_PICKAXE_ACTION,
    MAKE_IRON_PICKAXE_ACTION,
    MAKE_WOOD_SWORD_ACTION,
    MAKE_STONE_SWORD_ACTION,
    MAKE_IRON_SWORD_ACTION,
)

_ALL_ACTIONS_SET = frozenset(ALL_ACTIONS)

ACTION_TO_POSTURE = {action: "crafter_candidate" for action in ALL_ACTIONS}
ACTION_TO_STATE_MODE = {action: "normal" for action in ALL_ACTIONS}
ALL_LIFE_STATES = ("RECOVERING", "STABLE", "DEGRADED", "CRITICAL")
ACTION_TO_ALLOWED_STATES = {action: ALL_LIFE_STATES for action in ALL_ACTIONS}


def build_integrity_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    *,
    candidate_context: dict[str, Any] | None = None,
) -> list[ResponseCandidate]:
    """Stub — candidate set is now built by CrafterLLMActionProducer upstream."""

    del pressure, runtime_state, candidate_context
    return []


def filter_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
) -> list[ResponseFilterDecision]:
    from eva.l3_deliberation.tool_edge.tool_registry import ResponseFilterDecision

    del pressure, runtime_state
    return [ResponseFilterDecision(action=candidate.action, result="allow") for candidate in candidates]


def select_integrity_response(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    *,
    release_context: dict[str, Any] | None = None,
) -> ResponseSelection:
    return select_response_action(
        pressure,
        runtime_state,
        [],
        [],
        bridge_policy=release_context,
    )


def select_response_action(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
    decisions: list[ResponseFilterDecision],
    *,
    bridge_policy: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Execute the mediator-released raw action.

    bridge_policy IS release_context (passed as-is by select_integrity_response).
    The raw action is threaded into release_context["action_hint"] by
    runtime._thread_selected_action_hint for raw-action candidates.
    """

    from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection

    del runtime_state, candidates, decisions

    raw_action = bridge_policy.get("action_hint") if isinstance(bridge_policy, dict) else None
    if isinstance(raw_action, str) and raw_action and raw_action in _ALL_ACTIONS_SET:
        return ResponseSelection(
            pressure_id=pressure.pressure_id,
            selected_action=raw_action,
            selected_posture=ACTION_TO_POSTURE[raw_action],
            selected_action_reason="crafter_raw_action_execution",
            filter_result="allow",
            candidate_actions=(raw_action,),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode=ACTION_TO_STATE_MODE[raw_action],
        )

    # Fallback: no valid raw action in release_context (edge case only).
    # Per rev1 §6.3: fallback = defer, not baseline controller.
    return ResponseSelection(
        pressure_id=pressure.pressure_id,
        selected_action=NOOP_ACTION,
        selected_posture=ACTION_TO_POSTURE[NOOP_ACTION],
        selected_action_reason="crafter_bridge_defer_no_raw_action",
        filter_result="allow",
        candidate_actions=(),
        denied_actions=(),
        discouraged_actions=(),
        filter_reasons=(),
        state_mode=ACTION_TO_STATE_MODE[NOOP_ACTION],
    )


def execute_crafter_action(
    store: StateStore,
    pressure: ActivePressure,
    selection: ResponseSelection,
    runtime: Any = None,
    *,
    allow_repair_side_effects: bool = True,
) -> dict[str, Any]:
    del store, allow_repair_side_effects
    selected_action = selection.selected_action
    if runtime is None or not hasattr(runtime, "step_external_action"):
        return _fallback_execution_payload(selected_action)
    step_result = runtime.step_external_action(selected_action)
    if step_result is None:
        return _fallback_execution_payload(selected_action)
    return _build_execution_payload(pressure, selected_action, step_result)


def _fallback_execution_payload(selected_action: str) -> dict[str, Any]:
    return {
        "execution_status": "completed",
        "pressure_outcome": "unknown",
        "selected_action": selected_action,
        "followup_needed": selected_action not in {NOOP_ACTION, SLEEP_ACTION},
        "side_effects": [],
        "integration_hint": "worth_review",
        "inventory_delta": {},
        "achievement_delta": 0.0,
        "life_delta": {},
        "visible_threat_count": 0,
        "uncertainty_after_action": "cannot_determine_safely",
    }


def _build_execution_payload(
    pressure: ActivePressure,
    selected_action: str,
    step_result: StepResult,
) -> dict[str, Any]:
    before = _observation_panels(getattr(step_result, "before_observation", {}) or {})
    after = _observation_panels(getattr(step_result, "after_action_observation", step_result.agent_observation))
    inventory_delta = _numeric_delta(before["inventory"], after["inventory"])
    life_delta = _numeric_delta(before["life"], after["life"])
    achievement_delta = _achievement_delta(before["achievements"], after["achievements"])
    visible_threat_count = int(after["threat_count"])
    pressure_outcome = _pressure_outcome(pressure, before, after, step_result.done)
    side_effects = ["episode_reset"] if step_result.done else []
    followup_needed = pressure_outcome != "relieved"
    uncertainty_after_action = "resolved_enough" if pressure_outcome == "relieved" else "still_needs_confirmation"
    return {
        "execution_status": "completed",
        "pressure_outcome": pressure_outcome,
        "selected_action": selected_action,
        "followup_needed": followup_needed,
        "side_effects": side_effects,
        "integration_hint": "worth_review" if followup_needed else "none",
        "inventory_delta": inventory_delta,
        "achievement_delta": achievement_delta,
        "life_delta": life_delta,
        "visible_threat_count": visible_threat_count,
        "uncertainty_after_action": uncertainty_after_action,
    }


def _observation_panels(observation: dict[str, Any]) -> dict[str, Any]:
    visible = observation.get("visible") if isinstance(observation, dict) else {}
    visible = visible if isinstance(visible, dict) else {}
    task_context = observation.get("task_context") if isinstance(observation, dict) else {}
    task_context = task_context if isinstance(task_context, dict) else {}
    local_view = visible.get("local_view") if isinstance(visible.get("local_view"), dict) else {}
    threat_counts = local_view.get("nearby_objects") if isinstance(local_view, dict) else {}
    threat_total = 0
    if isinstance(threat_counts, dict):
        threat_total = sum(int(value or 0) for value in threat_counts.values())
    elif isinstance(visible.get("nearby_objects"), list):
        threat_total = len(visible.get("nearby_objects") or [])
    return {
        "life": _numeric_mapping(((visible.get("life_panel") or {}).get("values")) if isinstance(visible.get("life_panel"), dict) else {}),
        "inventory": _numeric_mapping(((visible.get("inventory_panel") or {}).get("items")) if isinstance(visible.get("inventory_panel"), dict) else {}),
        "nearby_objects": tuple(visible.get("nearby_objects") or ()),
        "threat_count": threat_total,
        "achievements": tuple(task_context.get("unlocked_achievements_visible") or ()),
    }


def _numeric_mapping(values: Any) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    numeric: dict[str, float] = {}
    for key, value in values.items():
        if isinstance(value, (int, float)):
            numeric[str(key)] = float(value)
    return numeric


def _numeric_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    delta: dict[str, float] = {}
    for key in sorted(set(before) | set(after)):
        change = round(after.get(key, 0.0) - before.get(key, 0.0), 3)
        if change != 0.0:
            delta[key] = change
    return delta


def _achievement_delta(before: tuple[Any, ...], after: tuple[Any, ...]) -> float:
    return float(max(len(after) - len(before), 0))


def _pressure_outcome(
    pressure: ActivePressure,
    before: dict[str, Any],
    after: dict[str, Any],
    done: bool,
) -> str:
    reason = str(pressure.evidence.get("reason") or "unknown")
    if done:
        return "unknown"
    if reason == "health_critical":
        if after["life"].get("health", 0.0) > before["life"].get("health", 0.0):
            return "relieved"
    if reason in {"food_critical", "water_critical", "energy_critical"}:
        key = reason.removesuffix("_critical")
        if after["life"].get(key, 0.0) > before["life"].get(key, 0.0):
            return "relieved"
    if reason == "threat_visible":
        if int(after["threat_count"]) < int(before["threat_count"]):
            return "relieved"
    if reason in {"tooling_missing", "inventory_sparse"}:
        if any(change > 0 for change in _numeric_delta(before["inventory"], after["inventory"]).values()):
            return "relieved"
    return "unchanged"


__all__ = [
    "ACTION_TO_ALLOWED_STATES",
    "ACTION_TO_POSTURE",
    "ACTION_TO_STATE_MODE",
    "ALL_ACTIONS",
    "ALL_LIFE_STATES",
    "DEFAULT_RESPONSE_MODE",
    "DO_ACTION",
    "ESCALATE_ACTION",
    "NOOP_ACTION",
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "SLEEP_ACTION",
    "build_integrity_response_candidates",
    "execute_crafter_action",
    "filter_response_candidates",
    "select_integrity_response",
    "select_response_action",
]
