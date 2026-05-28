"""Crafter action × drive effect schema — text per plan §5.4.5 (1:1 transcription).

17 actions × 6 drives = 102 cells. Wildcards in plan §5.4.5 (``move_*``,
``make_*``, ``place_*``) are expanded to all variants uniformly, per
plan's row-template semantics: each conditional label (e.g.
``improves_if_sword``) is self-explanatory and evaluates per-action.

Red line (§5.4.5): cells contain world-rule + drive-definition derivations
only. No graded adverbs ("slightly improves"), no episodic memory ("usually
water is southeast"). Fact statements live in world_facts (single source of
truth); this schema only projects them onto drive dimensions.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import ActionEffectSchema

__all__ = ["CRAFTER_ACTION_EFFECT_SCHEMA"]


# Per plan §5.4.5: row templates by action family.
_MOVE_ROW = {
    "metabolic": "context_dependent (improves if approaches water/food/cow)",
    "safety": "context_dependent (worsens if approaches threat)",
    "recovery": "neutral",
    "acquisition": "context_dependent (improves if approaches resource)",
    "capability": "neutral",
    "exploration": "improves (reveals new area or confirms current)",
}

_DO_ROW = {
    "metabolic": "context_dependent (NOTE: do does NOT 补 water/food, must walk into tile)",
    "safety": "context_dependent (improves if attacking threat with sword)",
    "recovery": "neutral",
    "acquisition": "context_dependent (improves if facing collectible with right tool)",
    "capability": "neutral",
    "exploration": "neutral",
}

_SLEEP_ROW = {
    "metabolic": "neutral (does NOT restore food/water/health)",
    "safety": "worsens_if_threat_visible (vulnerable during sleep)",
    "recovery": "improves (restores energy)",
    "acquisition": "neutral",
    "capability": "neutral",
    "exploration": "neutral",
}

_MAKE_ROW = {
    "metabolic": "neutral",
    "safety": "improves_if_sword (sword enables threat handling)",
    "recovery": "neutral",
    "acquisition": "worsens (consumes inventory materials)",
    "capability": "improves (gains new tool)",
    "exploration": "neutral",
}

_PLACE_ROW = {
    "metabolic": "neutral",
    "safety": "neutral",
    "recovery": "neutral",
    "acquisition": "worsens (consumes inventory)",
    "capability": "improves (table/furnace enables crafting; place_plant for future food)",
    "exploration": "neutral",
}

_NOOP_ROW = {
    "metabolic": "time_passes (no action effect; drive 按 L2 update policy 自然演化)",
    "safety": "time_passes (no action effect)",
    "recovery": "time_passes (no action effect)",
    "acquisition": "time_passes (no action effect)",
    "capability": "time_passes (no action effect)",
    "exploration": "time_passes (no action effect)",
}


def _build_matrix() -> dict[str, dict[str, str]]:
    matrix: dict[str, dict[str, str]] = {}
    for action in ("move_left", "move_right", "move_up", "move_down"):
        matrix[action] = dict(_MOVE_ROW)
    matrix["do"] = dict(_DO_ROW)
    matrix["sleep"] = dict(_SLEEP_ROW)
    for action in ("place_stone", "place_table", "place_furnace", "place_plant"):
        matrix[action] = dict(_PLACE_ROW)
    for action in (
        "make_wood_pickaxe", "make_stone_pickaxe", "make_iron_pickaxe",
        "make_wood_sword", "make_stone_sword", "make_iron_sword",
    ):
        matrix[action] = dict(_MAKE_ROW)
    matrix["noop"] = dict(_NOOP_ROW)
    return matrix


CRAFTER_ACTION_EFFECT_SCHEMA = ActionEffectSchema(matrix=_build_matrix())
