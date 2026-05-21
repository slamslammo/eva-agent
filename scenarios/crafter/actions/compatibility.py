"""Crafter bounded action policy for Stage H H-2."""

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

ACTION_TO_POSTURE = {action: "crafter_candidate" for action in ALL_ACTIONS}
ACTION_TO_STATE_MODE = {action: "normal" for action in ALL_ACTIONS}
ALL_LIFE_STATES = ("RECOVERING", "STABLE", "DEGRADED", "CRITICAL")
ACTION_TO_ALLOWED_STATES = {action: ALL_LIFE_STATES for action in ALL_ACTIONS}


# Round 1.A: map each framework-level candidate_profile to the concrete Crafter
# actions that are semantically eligible under it.
#
# Rationale per profile:
#   - ``observe_first``: low-cost, exploratory, or wait-and-see actions. Movement
#     counts here because it primarily surfaces information rather than changing
#     world state. ``noop`` is the canonical passive fallback.
#   - ``stabilize_first``: maintenance and recovery. ``sleep`` is the canonical
#     case. ``noop`` is allowed when doing nothing is preferable to acting under
#     risk.
#   - ``escalate_first``: actions that change world state. ``do`` is the generic
#     direct-action verb (which Crafter resolves to attack/chop/mine/collect
#     based on the tile in front). ``place_*`` and ``make_*`` are explicit
#     construction / crafting actions that change inventory and unlock
#     achievements.
#
# This table is the canonical seam for Round 1.A action-resolution widening. It
# is consumed by ``build_integrity_response_candidates`` (slice A-3) to enumerate
# context-eligible candidates per profile, and by ``select_response_action``
# (slice A-4) when weighting habit / prior bias against candidates.
PROFILE_ELIGIBLE_ACTIONS: dict[str, tuple[str, ...]] = {
    "observe_first": (
        NOOP_ACTION,
        MOVE_LEFT_ACTION,
        MOVE_RIGHT_ACTION,
        MOVE_UP_ACTION,
        MOVE_DOWN_ACTION,
    ),
    "stabilize_first": (
        SLEEP_ACTION,
        NOOP_ACTION,
    ),
    "escalate_first": (
        DO_ACTION,
        # Fix-B: escalate can also *approach* a target (move toward it, then ``do``).
        # "Actively pursue the resource/threat" includes walking up to it; without
        # this the dominant escalate profile could only ``do`` whatever it happened
        # to already face, so it stalled doing nothing in place.
        MOVE_LEFT_ACTION,
        MOVE_RIGHT_ACTION,
        MOVE_UP_ACTION,
        MOVE_DOWN_ACTION,
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
    ),
}

# Default fallback action per profile, used when no context-specific resolution
# yields a candidate. This preserves pre-Round-1.A behavior as a strict fallback:
# every profile still resolves to its legacy single action when context is
# insufficient.
PROFILE_DEFAULT_ACTION: dict[str, str] = {
    "observe_first": NOOP_ACTION,
    "stabilize_first": SLEEP_ACTION,
    "escalate_first": DO_ACTION,
}

# Round 1.A: profile-aware posture tokens. ``ResponseCandidate`` does not expose
# a ``parameter_domain`` field, so candidate-profile provenance is encoded in
# the scenario-owned ``posture`` field. Framework code does not interpret
# posture — it propagates it into traces — so this overload is safe.
PROFILE_TO_POSTURE: dict[str, str] = {
    "observe_first": "crafter_candidate_observe",
    "stabilize_first": "crafter_candidate_stabilize",
    "escalate_first": "crafter_candidate_escalate",
}

_CANDIDATE_PROFILES: tuple[str, ...] = ("observe_first", "stabilize_first", "escalate_first")


def build_integrity_response_candidates(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    *,
    candidate_context: dict[str, Any] | None = None,
) -> list[ResponseCandidate]:
    """Build a context-resolved candidate set for one integrity pressure.

    Round 1.A widening: the previous Stage H implementation discarded ``pressure``
    and ``runtime_state`` and emitted a fixed 3-candidate set. After Round 1.A
    this function reads:

    - ``pressure.evidence["reason"]`` — drives which concrete actions are
      contextually appropriate for ``escalate_first`` and ``observe_first``.
    - ``runtime_state.life_state`` — used for fallback ordering only.
    - ``candidate_context`` (optional) — payload carrying ``inherited_priors``,
      ``top_drive``, ``agent_observation``, and ``pressure_reason`` overrides.

    For each profile in ``_CANDIDATE_PROFILES``, the function resolves one or
    more concrete actions via:
      1. Inherited prior preferred_action (if profile matches and action is
         eligible under the new ``PROFILE_ELIGIBLE_ACTIONS`` mapping).
      2. Pressure-driven resolution against the eligible action set.
      3. Profile-default fallback if neither yielded anything.

    The function never returns zero candidates; each profile always contributes
    at least its default action. Candidate-profile provenance is carried via
    ``posture`` per ``PROFILE_TO_POSTURE``.
    """

    from eva.l3_deliberation.tool_edge.tool_registry import ResponseCandidate

    context = candidate_context if isinstance(candidate_context, dict) else {}
    pressure_reason = str(pressure.evidence.get("reason") or context.get("pressure_reason") or "")
    top_drive = str(context.get("top_drive") or "")
    life_state = str(
        getattr(runtime_state, "life_state", None)
        or context.get("life_state")
        or "STABLE"
    )
    agent_observation = context.get("agent_observation") if isinstance(context.get("agent_observation"), dict) else {}
    inherited_priors = context.get("inherited_priors") if isinstance(context.get("inherited_priors"), list) else []

    del life_state, top_drive  # reserved for future heuristics

    # When L3 has already selected a candidate_profile (delivered to the bridge
    # via release_context), restrict widening to that profile so the bridge's
    # selection respects the upstream mediator choice. Without an L3-supplied
    # profile, widen across all three profiles (the direct-test path).
    requested_profile = context.get("candidate_profile")
    if isinstance(requested_profile, str) and requested_profile in _CANDIDATE_PROFILES:
        active_profiles: tuple[str, ...] = (requested_profile,)
    else:
        active_profiles = _CANDIDATE_PROFILES

    # Round 1.G phase 2 (a): the live-LLM producer's concrete-action lever for the
    # drive-selected posture. Only honored when it names an action eligible under
    # that profile; otherwise ignored (heuristic resolution stands).
    action_hint = context.get("action_hint")
    action_hint = action_hint if isinstance(action_hint, str) and action_hint else None

    candidates: list[ResponseCandidate] = []
    for profile in active_profiles:
        resolved = _resolve_actions_for_profile(
            profile,
            pressure_reason=pressure_reason,
            inherited_priors=inherited_priors,
            agent_observation=agent_observation,
        )
        if not resolved:
            resolved = [PROFILE_DEFAULT_ACTION[profile]]
        # Ensure a valid LLM action_hint is available as a candidate for this
        # posture (prepended) so selection can honor it; eligibility is checked
        # against this profile's action set.
        if action_hint and action_hint in PROFILE_ELIGIBLE_ACTIONS.get(profile, ()):
            resolved = [action_hint] + [a for a in resolved if a != action_hint]
        posture = PROFILE_TO_POSTURE[profile]
        for action_name in resolved:
            candidates.append(
                ResponseCandidate(
                    action=action_name,
                    posture=posture,
                    allowed_in_states=ALL_LIFE_STATES,
                )
            )
    return candidates


def _resolve_actions_for_profile(
    profile: str,
    *,
    pressure_reason: str,
    inherited_priors: list[Any],
    agent_observation: dict[str, Any] | None = None,
) -> list[str]:
    """Resolve concrete actions for one profile under current context.

    Order of resolution (first hit wins per action; duplicates suppressed):
      1. Fix-B: observation-directed approach/interact (pursue the nearest
         useful target) — first so the situationally-correct action wins the
         un-biased ``candidates[0]`` tie-break.
      2. Prior with matching profile + eligible preferred_action.
      3. Pressure-driven heuristic for the profile.
      4. Profile default (handled by caller if list is empty).
    """

    eligible: tuple[str, ...] = PROFILE_ELIGIBLE_ACTIONS.get(profile, ())
    if not eligible:
        return []
    resolved: list[str] = []

    # 1. Fix-B: observation-directed action (approach the nearest useful target,
    # or ``do`` it when already facing it).
    for action_name in _obs_directed_actions(pressure_reason, eligible, agent_observation):
        if action_name not in resolved:
            resolved.append(action_name)

    # 2. Inherited priors whose profile matches and whose preferred_action is
    # eligible under this profile's mapping.
    for prior in inherited_priors:
        if not isinstance(prior, dict):
            continue
        if str(prior.get("candidate_profile") or "") != profile:
            continue
        preferred = str(prior.get("preferred_action") or "")
        if preferred and preferred in eligible and preferred not in resolved:
            resolved.append(preferred)

    # 3. Pressure-driven resolution.
    for action_name in _pressure_driven_actions_for_profile(profile, pressure_reason, eligible):
        if action_name not in resolved:
            resolved.append(action_name)

    return resolved


# Fix-B: cell names the agent can usefully approach + interact with, grouped by need.
_WATER_TARGETS = ("water",)
_FOOD_TARGETS = ("cow", "plant")
_RESOURCE_TARGETS = ("tree", "stone", "coal", "iron", "diamond")
_THREAT_TARGETS = ("zombie", "skeleton")

# facing string -> (col_delta, row_delta) in the local-view grid (col->x, row->y),
# matching Crafter's verified facing tuples (down=(0,1), left=(-1,0), up=(0,-1), right=(1,0)).
_FACING_DELTA = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, -1),
    "down": (0, 1),
}


def _useful_targets_for(pressure_reason: str) -> tuple[str, ...]:
    """Order target cell-types by the active pressure (most relevant first)."""

    if pressure_reason in {"health_critical", "threat_visible", "threat_nearby"}:
        return _THREAT_TARGETS + _FOOD_TARGETS + _WATER_TARGETS
    if pressure_reason in {"metabolic_degraded", "food_critical", "water_critical"}:
        return _WATER_TARGETS + _FOOD_TARGETS + _RESOURCE_TARGETS
    if pressure_reason in {"inventory_sparse", "tooling_missing", "resource_visible"}:
        return _RESOURCE_TARGETS + _FOOD_TARGETS + _WATER_TARGETS
    return _FOOD_TARGETS + _WATER_TARGETS + _RESOURCE_TARGETS + _THREAT_TARGETS


def _local_view_from_observation(agent_observation: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(agent_observation, dict):
        return None
    visible = agent_observation.get("visible")
    local_view = visible.get("local_view") if isinstance(visible, dict) else None
    if not isinstance(local_view, dict):
        return None
    if not isinstance(local_view.get("cells"), list) or not local_view["cells"]:
        return None
    if not isinstance(local_view.get("center"), dict):
        return None
    return local_view


def _cell_at(cells: list[Any], row: int, col: int) -> str | None:
    if 0 <= row < len(cells):
        cell_row = cells[row]
        if isinstance(cell_row, list) and 0 <= col < len(cell_row):
            return cell_row[col]
    return None


def _facing_cell_is_target(local_view: dict[str, Any], facing: str, targets: tuple[str, ...]) -> bool:
    delta = _FACING_DELTA.get(str(facing))
    if delta is None:
        return False
    center = local_view["center"]
    crow, ccol = center.get("row"), center.get("col")
    if crow is None or ccol is None:
        return False
    col_d, row_d = delta
    return _cell_at(local_view["cells"], crow + row_d, ccol + col_d) in set(targets)


def _nearest_target_offset(local_view: dict[str, Any], targets: tuple[str, ...]) -> tuple[int, int] | None:
    """Return (row_diff, col_diff) from player center to the nearest target cell."""

    center = local_view["center"]
    crow, ccol = center.get("row"), center.get("col")
    if crow is None or ccol is None:
        return None
    target_set = set(targets)
    best: tuple[int, int] | None = None
    best_dist: int | None = None
    for r, cell_row in enumerate(local_view["cells"]):
        if not isinstance(cell_row, list):
            continue
        for c, name in enumerate(cell_row):
            if name in target_set:
                dist = abs(r - crow) + abs(c - ccol)
                if dist > 0 and (best_dist is None or dist < best_dist):
                    best_dist, best = dist, (r - crow, c - ccol)
    return best


def _move_toward(row_diff: int, col_diff: int) -> str:
    """Greedy beeline: step along the larger-magnitude axis first."""

    if abs(col_diff) >= abs(row_diff):
        return MOVE_RIGHT_ACTION if col_diff > 0 else MOVE_LEFT_ACTION
    return MOVE_DOWN_ACTION if row_diff > 0 else MOVE_UP_ACTION


def _obs_directed_actions(
    pressure_reason: str,
    eligible: tuple[str, ...],
    agent_observation: dict[str, Any] | None,
) -> list[str]:
    """Fix-B: pursue the nearest useful target using the local view + facing.

    Facing a useful target -> ``do`` (Crafter interacts with the faced tile).
    Otherwise step toward the nearest target (which also turns the agent to
    face it, enabling ``do`` next turn). Only eligible actions are returned, so
    a profile that cannot move/interact (e.g. ``stabilize_first``) yields [].
    """

    local_view = _local_view_from_observation(agent_observation)
    if local_view is None:
        return []
    targets = _useful_targets_for(pressure_reason)
    visible = agent_observation.get("visible") if isinstance(agent_observation, dict) else {}
    facing = visible.get("facing", "unknown") if isinstance(visible, dict) else "unknown"
    actions: list[str] = []
    if DO_ACTION in eligible and _facing_cell_is_target(local_view, facing, targets):
        actions.append(DO_ACTION)
    offset = _nearest_target_offset(local_view, targets)
    if offset is not None:
        move = _move_toward(offset[0], offset[1])
        if move in eligible and move not in actions:
            actions.append(move)
    return actions


def _pressure_driven_actions_for_profile(
    profile: str,
    pressure_reason: str,
    eligible: tuple[str, ...],
) -> list[str]:
    """Return the additional context-eligible actions for one profile.

    Heuristics are conservative on purpose: they widen the candidate set
    enough to enable meaningful Crafter behavior, without flooding selection
    with every possible action. Habit and prior bias (handled in
    ``select_response_action``) do the finer-grained picking.
    """

    actions: list[str] = []

    def _add(action_name: str) -> None:
        if action_name in eligible and action_name not in actions:
            actions.append(action_name)

    if profile == "observe_first":
        # Fix-2A ordering note: under exploration-relevant pressures, list
        # movement before NOOP so the un-biased ``candidates[0]`` default
        # picks an actually-exploratory action instead of stagnating at
        # noop. Under other pressures (e.g. threat) keep NOOP first so the
        # default stays cautious.
        if pressure_reason in {"inventory_sparse", "tooling_missing", "resource_visible", ""}:
            # Movement surfaces new tiles for resource / utility discovery.
            _add(MOVE_LEFT_ACTION)
            _add(MOVE_RIGHT_ACTION)
            _add(MOVE_UP_ACTION)
            _add(MOVE_DOWN_ACTION)
            _add(NOOP_ACTION)
        else:
            _add(NOOP_ACTION)
        return actions

    if profile == "stabilize_first":
        # Sleep is the canonical stabilize action across all pressures. The
        # legacy fallback (noop) is implicit through PROFILE_DEFAULT_ACTION.
        _add(SLEEP_ACTION)
        return actions

    if profile == "escalate_first":
        _add(DO_ACTION)  # always usable — Crafter resolves ``do`` to the
        # context-appropriate interaction (chop / mine / attack / collect).
        if pressure_reason in {"inventory_sparse", "tooling_missing"}:
            # Resource acquisition: crafting and placement engage Crafter's
            # progression chain (wood -> pickaxe -> stone -> ...).
            _add(MAKE_WOOD_PICKAXE_ACTION)
            _add(MAKE_STONE_PICKAXE_ACTION)
            _add(PLACE_TABLE_ACTION)
            _add(PLACE_FURNACE_ACTION)
        elif pressure_reason in {"health_critical", "threat_visible"}:
            # Defensive escalation: weapons.
            _add(MAKE_WOOD_SWORD_ACTION)
            _add(MAKE_STONE_SWORD_ACTION)
        return actions

    return actions


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
    candidate_context = _candidate_context_from_release_context(release_context)
    candidates = build_integrity_response_candidates(
        pressure,
        runtime_state,
        candidate_context=candidate_context,
    )
    decisions = filter_response_candidates(pressure, runtime_state, candidates)
    return select_response_action(
        pressure,
        runtime_state,
        candidates,
        decisions,
        bridge_policy=release_context,
    )


def _candidate_context_from_release_context(
    release_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Extract ``candidate_context`` from one release context, if present.

    The runner / framework forwards ``release_context`` through
    ``select_integrity_response``. Two sources of context get folded together:

    1. ``release_context["candidate_context"]`` — explicit payload that
       callers may set with inherited priors / observation / drive info.
    2. ``release_context["candidate_profile"]`` — the L3 mediator's profile
       choice. Lifting this into candidate_context lets the bridge constrain
       widening to the profile L3 actually picked, instead of always emitting
       all three profiles.

    The explicit ``candidate_context`` payload, when present, takes precedence;
    the lifted ``candidate_profile`` only fills in when the explicit payload
    doesn't already specify one.
    """

    if not isinstance(release_context, dict):
        return None
    payload = release_context.get("candidate_context")
    base = dict(payload) if isinstance(payload, dict) else {}
    if "candidate_profile" not in base:
        l3_profile = release_context.get("candidate_profile")
        if isinstance(l3_profile, str) and l3_profile in _CANDIDATE_PROFILES:
            base["candidate_profile"] = l3_profile
    # Round 1.G phase 2 (a): lift the selected candidate's LLM ``action_hint``
    # (threaded into release_context by ``run_deliberation``) so the concrete
    # action it names becomes available to candidate widening and selection.
    if "action_hint" not in base:
        l3_action_hint = release_context.get("action_hint")
        if isinstance(l3_action_hint, str) and l3_action_hint:
            base["action_hint"] = l3_action_hint
    return base if base else None


def select_response_action(
    pressure: ActivePressure,
    runtime_state: RuntimeState,
    candidates: list[ResponseCandidate],
    decisions: list[ResponseFilterDecision],
    *,
    bridge_policy: dict[str, Any] | None = None,
) -> ResponseSelection:
    """Pick one Crafter action from the candidate set under bounded bias.

    Round 1.A widening: previously this function returned ``candidates[0]`` and
    discarded its inputs. After Round 1.A it consults a ``selection_context``
    payload (delivered via ``bridge_policy["selection_context"]``) to apply:

    - **Habit bias**: matching ``(situation_key, candidate.action)`` from
      ``selection_context["habit_summaries"]``. Habit is the dominant signal
      because it represents crystallized experience under the same situation.
    - **Inherited-prior bias**: matching ``(candidate_profile, candidate.action)``
      from ``selection_context["inherited_priors"]``. Profile is recovered from
      the candidate's posture token.

    When no bias applies, the function falls back to the original "first
    eligible candidate" behavior (which under the new candidate order is the
    first ``observe_first`` action, typically ``noop``).
    """

    from eva.l3_deliberation.tool_edge.tool_registry import ResponseSelection

    del runtime_state
    if not candidates:
        fallback_candidate = ResponseCandidate(
            action=NOOP_ACTION,
            posture=ACTION_TO_POSTURE[NOOP_ACTION],
            allowed_in_states=ALL_LIFE_STATES,
        )
        return ResponseSelection(
            pressure_id=pressure.pressure_id,
            selected_action=fallback_candidate.action,
            selected_posture=fallback_candidate.posture,
            selected_action_reason="crafter_minimal_selection_fallback",
            filter_result="allow",
            candidate_actions=(),
            denied_actions=(),
            discouraged_actions=(),
            filter_reasons=(),
            state_mode=ACTION_TO_STATE_MODE[fallback_candidate.action],
        )

    # Round 1.G phase 2 (a): a valid LLM action_hint for the drive-selected
    # posture is authoritative for the concrete action — it takes priority over
    # PROFILE_DEFAULT_ACTION, inherited prior, and habit bias (within the posture,
    # the live reasoning core picks the action; RPE feeds learning back). It is
    # honored only when it matches a candidate already admitted for this posture
    # (so eligibility is enforced upstream); otherwise the heuristic path stands
    # → model-off / no-hint is byte-identical.
    action_hint = bridge_policy.get("action_hint") if isinstance(bridge_policy, dict) else None
    if isinstance(action_hint, str) and action_hint:
        for candidate in candidates:
            if candidate.action == action_hint:
                return ResponseSelection(
                    pressure_id=pressure.pressure_id,
                    selected_action=candidate.action,
                    selected_posture=candidate.posture,
                    selected_action_reason="crafter_llm_action_hint_selection",
                    filter_result="allow",
                    candidate_actions=tuple(c.action for c in candidates),
                    denied_actions=(),
                    discouraged_actions=(),
                    filter_reasons=tuple(reason for decision in decisions for reason in decision.reasons),
                    state_mode=ACTION_TO_STATE_MODE[candidate.action],
                )

    selection_context = _selection_context_from_bridge_policy(bridge_policy)
    situation_key = str(selection_context.get("situation_key") or "")
    habit_summaries = selection_context.get("habit_summaries")
    if not isinstance(habit_summaries, list):
        habit_summaries = []
    inherited_priors = selection_context.get("inherited_priors")
    if not isinstance(inherited_priors, list):
        inherited_priors = []

    best_index = 0
    best_score = float("-inf")
    best_reasons: tuple[str, ...] = ()
    for index, candidate in enumerate(candidates):
        score, reasons = _score_candidate_for_selection(
            candidate,
            situation_key=situation_key,
            habit_summaries=habit_summaries,
            inherited_priors=inherited_priors,
        )
        # Strict greater-than keeps original ``candidates[0]`` tie-break order
        # (first candidate wins among equal scores).
        if score > best_score:
            best_score = score
            best_index = index
            best_reasons = reasons

    selected_candidate = candidates[best_index]
    selected_action = selected_candidate.action
    if best_reasons:
        selected_action_reason = "crafter_" + "_".join(best_reasons) + "_selection"
    else:
        selected_action_reason = "crafter_minimal_selection"
    return ResponseSelection(
        pressure_id=pressure.pressure_id,
        selected_action=selected_action,
        selected_posture=selected_candidate.posture,
        selected_action_reason=selected_action_reason,
        filter_result="allow",
        candidate_actions=tuple(candidate.action for candidate in candidates),
        denied_actions=(),
        discouraged_actions=(),
        filter_reasons=tuple(reason for decision in decisions for reason in decision.reasons),
        state_mode=ACTION_TO_STATE_MODE[selected_action],
    )


def _selection_context_from_bridge_policy(
    bridge_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    """Extract ``selection_context`` from one bridge_policy payload, if present."""

    if not isinstance(bridge_policy, dict):
        return {}
    payload = bridge_policy.get("selection_context")
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _profile_from_posture(posture: str) -> str:
    """Recover the candidate_profile from the scenario-internal posture token."""

    for profile, token in PROFILE_TO_POSTURE.items():
        if posture == token:
            return profile
    return "unknown"


def _score_candidate_for_selection(
    candidate: ResponseCandidate,
    *,
    situation_key: str,
    habit_summaries: list[Any],
    inherited_priors: list[Any],
) -> tuple[float, tuple[str, ...]]:
    """Return a bounded selection score plus provenance tags for one candidate.

    Score composition:
      - Habit bias for matching ``(situation_key, candidate.action)``:
        contributes ``1.0 + confidence * stability * |bias_strength|`` so that
        any matched habit reliably outranks any zero-bias candidate.
      - Inherited-prior bias for matching ``(candidate_profile, candidate.action)``:
        contributes ``0.5 * confidence * |bias_strength|``, smaller than habit
        because inherited priors are weaker evidence than first-hand habit.

    Both components are added rather than max'd so that a habit-and-prior
    aligned candidate naturally outranks one with only one signal.
    """

    score = 0.0
    reasons: list[str] = []

    if situation_key and habit_summaries:
        for habit in habit_summaries:
            if not isinstance(habit, dict):
                continue
            if str(habit.get("situation_key") or "") != situation_key:
                continue
            if str(habit.get("preferred_action") or "") != candidate.action:
                continue
            confidence = _coerce_unit(habit.get("confidence"))
            stability = _coerce_unit(habit.get("stability_score"))
            bias_strength = _coerce_bias(habit.get("bias_strength"))
            habit_score = confidence * stability * abs(bias_strength)
            if habit_score > 0.0:
                score += 1.0 + habit_score
                reasons.append("habit_bias")
            break

    if inherited_priors:
        candidate_profile = _profile_from_posture(candidate.posture)
        for prior in inherited_priors:
            if not isinstance(prior, dict):
                continue
            if str(prior.get("candidate_profile") or "") != candidate_profile:
                continue
            if str(prior.get("preferred_action") or "") != candidate.action:
                continue
            confidence = _coerce_unit(prior.get("confidence"))
            bias_strength = _coerce_bias(prior.get("bias_strength"))
            prior_score = 0.5 * confidence * abs(bias_strength)
            if prior_score > 0.0:
                score += prior_score
                reasons.append("inherited_prior_bias")
            break

    return score, tuple(reasons)


def _coerce_unit(value: Any) -> float:
    """Clamp one payload field to [0.0, 1.0]; non-numeric -> 0.0."""

    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _coerce_bias(value: Any) -> float:
    """Clamp one bias-strength payload field to [-1.0, 1.0]; non-numeric -> 0.0."""

    try:
        return max(-1.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


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
    "PROFILE_DEFAULT_ACTION",
    "PROFILE_ELIGIBLE_ACTIONS",
    "PROFILE_TO_POSTURE",
    "RECHECK_ACTION",
    "REPAIR_ACTION",
    "SLEEP_ACTION",
    "build_integrity_response_candidates",
    "execute_crafter_action",
    "filter_response_candidates",
    "select_integrity_response",
    "select_response_action",
]
