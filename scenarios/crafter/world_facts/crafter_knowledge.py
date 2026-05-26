"""Crafter world facts: tech tree, crafting recipes, and survival priority facts.

This module contains only physical world facts (crafting rules, resource locations,
game mechanics). It does NOT contain behavioral advice or strategic recommendations
— those are the LLM's domain.
"""

from __future__ import annotations

__all__ = ["get_crafter_world_facts_context"]

_WORLD_FACTS = """\
=== Crafter World Facts ===

TECH TREE (crafting dependencies):
- wood -> place_table (requires: wood x2, no nearby needed)
- wood -> make_wood_pickaxe (requires: wood x1, nearby: table)
- wood -> make_wood_sword (requires: wood x1, nearby: table)
- wood + stone -> make_stone_pickaxe (requires: wood x1, stone x1, nearby: table)
- wood + stone -> make_stone_sword (requires: wood x1, stone x1, nearby: table)
- stone x4 -> place_furnace (requires: stone x4, no nearby needed)
- wood + coal + iron -> make_iron_pickaxe (requires: wood x1, coal x1, iron x1, nearby: table + furnace)
- wood + coal + iron -> make_iron_sword (requires: wood x1, coal x1, iron x1, nearby: table + furnace)

PROGRESSION PATH (resource unlock chain):
1. Collect wood (surface, always available)
2. Place table (enables all crafting)
3. Make wood_pickaxe -> collect stone
4. Make stone_pickaxe -> mine coal and iron (underground)
5. Place furnace (needs stone x4) -> enables iron crafting
6. Make iron_pickaxe / iron_sword (need coal + iron)

WORLD STRUCTURE:
- Surface: grass, trees (wood), saplings, water, cows, zombies at night
- Underground (dig down): stone, coal, iron, deeper: diamond (rare)
- Night: zombies spawn; staying on surface at night is dangerous
- do action: context-sensitive — attacks nearby enemies, collects adjacent resources, or interacts

SURVIVAL PARAMETERS:
- health: reduced by zombie attacks or fall damage
- food: reduced over time; eat by walking into cows or plants
- water: reduced over time; drink by walking into water tiles
- energy: restored by sleep action; if critical, must sleep
- All four parameters matter for survival; any reaching zero causes death
"""


def get_crafter_world_facts_context() -> str:
    """Return a compact world facts block for injection into LLM prompts.

    Contains only physical facts (crafting rules, resource locations, game
    mechanics). No behavioral recommendations — those belong to the LLM and
    value_judgment layers, not here.
    """
    return _WORLD_FACTS
