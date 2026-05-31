"""Crafter action spec — the single authority source for Crafter action metadata.

single-source-crafter-action-metadata: merges the two previously-parallel
hardcoded sources into one declaration:
- action identity (the ``ALL_ACTIONS`` name tuple), previously hardcoded in
  ``actions/compatibility.py``
- action semantics (effect / details / typical_use), previously hardcoded as
  ``ActionOntologyEntry`` text in ``ontology/crafter_action_ontology.py``

``ALL_ACTIONS`` and ``CRAFTER_ACTION_ONTOLOGY`` are both derived from
``CRAFTER_ACTION_SPEC``, so they can no longer drift apart. The action × drive
effect-schema's action axis is pinned to this same name set by an
axis-alignment test (see tests/scenarios/crafter/test_ontology_consistency.py).

Red line (plan §5.4.4): the semantic text is A-authored — B does NOT free-form.
This is a 1:1 transcription/merge of the pre-existing ALL_ACTIONS +
crafter_action_ontology.py content (byte-equivalence pinned by
tests/scenarios/crafter/test_action_spec_equivalence.py against the
pre-refactor 402d49d oracle snapshot). Any revision updates the plan first.

The action-name literals here are the same strings the bridge executor defines
as ``*_ACTION`` constants in compatibility.py; the executor keeps those
constants + its logic, and only its ``ALL_ACTIONS`` tuple is replaced by
``CRAFTER_ACTION_SPEC.action_names()``.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import ActionSpecEntry, ScenarioActionSpec

__all__ = ["CRAFTER_ACTION_SPEC"]


_MOVE_DETAILS = (
    "if the target tile is passable (grass etc.): move succeeds",
    "if the target tile is water: enter the tile and refill water (water +N)",
    "if the target tile is cow / plant: enter the tile and refill food (food +N)",
    "if the target tile is zombie / skeleton: may take an attack",
    "if the target tile is impassable (stone / tree / lava): move fails",
    "moving changes the facing direction",
)


CRAFTER_ACTION_SPEC = ScenarioActionSpec(
    version="crafter-action-spec-v1",
    entries=(
        ActionSpecEntry(
            action="noop",
            effect="skip this turn, no world-state change",
            details=(),
            typical_use="rarely used — usually not better than an exploratory move",
        ),
        ActionSpecEntry(action="move_left", effect="move 1 tile left", details=_MOVE_DETAILS),
        ActionSpecEntry(action="move_right", effect="move 1 tile right", details=_MOVE_DETAILS),
        ActionSpecEntry(action="move_up", effect="move 1 tile up", details=_MOVE_DETAILS),
        ActionSpecEntry(action="move_down", effect="move 1 tile down", details=_MOVE_DETAILS),
        ActionSpecEntry(
            action="do",
            effect="context-sensitive, depends on the facing tile",
            details=(
                "facing zombie / skeleton: attack (more effective with a sword tool)",
                "facing tree: collect wood (no tool needed)",
                "facing stone: collect stone (needs wood_pickaxe or higher)",
                "facing coal: collect coal (needs wood_pickaxe or higher)",
                "facing iron: collect iron (needs stone_pickaxe or higher)",
                "facing diamond: collect diamond (needs iron_pickaxe)",
                "facing cow / plant: usually ineffective (food comes from walking into the tile, not do)",
                "facing water: ineffective (water comes from walking into the tile)",
                "facing grass / empty: ineffective",
            ),
        ),
        ActionSpecEntry(
            action="sleep",
            effect="recover energy (advances time, may enter night)",
            details=(
                "does NOT refill food / water / health",
                "vulnerable to threat attacks while sleeping — not advised when a threat is visible",
                "must sleep when energy is severely low",
            ),
        ),
        ActionSpecEntry(
            action="place_stone",
            effect="place stone on the facing tile",
            details=(
                "needs stone in inventory",
                "after placing, inventory -1 and the tile becomes stone",
            ),
        ),
        ActionSpecEntry(
            action="place_table",
            effect="place a crafting table on the facing tile",
            details=(
                "needs wood in inventory",
                "the table is a prerequisite for crafting tools",
            ),
        ),
        ActionSpecEntry(
            action="place_furnace",
            effect="place a furnace on the facing tile",
            details=(
                "needs stone in inventory",
                "the furnace is a prerequisite for crafting iron",
            ),
        ),
        ActionSpecEntry(
            action="place_plant",
            effect="place a plant (seed) on the facing tile",
            details=(
                "needs the corresponding seed in inventory",
                "planting paves the way for a future food source",
            ),
        ),
        ActionSpecEntry(
            action="make_wood_pickaxe",
            effect="craft a wood_pickaxe",
            details=(
                "needs wood x1, nearby table",
            ),
        ),
        ActionSpecEntry(
            action="make_stone_pickaxe",
            effect="craft a stone_pickaxe",
            details=(
                "needs wood x1 + stone x1, nearby table",
            ),
        ),
        ActionSpecEntry(
            action="make_iron_pickaxe",
            effect="craft an iron_pickaxe",
            details=(
                "needs wood x1 + coal x1 + iron x1, nearby table + furnace",
            ),
        ),
        ActionSpecEntry(
            action="make_wood_sword",
            effect="craft a wood_sword",
            details=(
                "needs wood x1, nearby table",
                "the sword is used with do to attack threats (improves attack effect)",
            ),
        ),
        ActionSpecEntry(
            action="make_stone_sword",
            effect="craft a stone_sword",
            details=(
                "needs wood x1 + stone x1, nearby table",
                "the sword is used with do to attack threats (improves attack effect)",
            ),
        ),
        ActionSpecEntry(
            action="make_iron_sword",
            effect="craft an iron_sword",
            details=(
                "needs wood x1 + coal x1 + iron x1, nearby table + furnace",
                "the sword is used with do to attack threats (improves attack effect)",
            ),
        ),
    ),
)
