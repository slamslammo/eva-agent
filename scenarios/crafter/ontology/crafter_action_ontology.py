"""Crafter action ontology — text per plan §5.4.4 (1:1 transcription).

17 raw Crafter actions with world-rule semantics. B does NOT free-form.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import ActionOntology, ActionOntologyEntry

__all__ = ["CRAFTER_ACTION_ONTOLOGY"]


CRAFTER_ACTION_ONTOLOGY = ActionOntology(
    entries=(
        ActionOntologyEntry(
            action="noop",
            effect="跳过本回合，无世界状态变化",
            details=(),
            typical_use="极少使用——通常不优于探索移动",
        ),
        ActionOntologyEntry(
            action="move_left",
            effect="朝左移动 1 格",
            details=(
                "若目标 tile 可通行（grass 等）：成功移动",
                "若目标 tile 是 water：进入 tile 同时补水（water +N）",
                "若目标 tile 是 cow / plant：进入 tile 同时补食物（food +N）",
                "若目标 tile 是 zombie / skeleton：可能受到攻击",
                "若目标 tile 不可通行（stone / tree / lava）：移动失败",
                "移动会改变 facing 方向",
            ),
        ),
        ActionOntologyEntry(
            action="move_right",
            effect="朝右移动 1 格",
            details=(
                "若目标 tile 可通行（grass 等）：成功移动",
                "若目标 tile 是 water：进入 tile 同时补水（water +N）",
                "若目标 tile 是 cow / plant：进入 tile 同时补食物（food +N）",
                "若目标 tile 是 zombie / skeleton：可能受到攻击",
                "若目标 tile 不可通行（stone / tree / lava）：移动失败",
                "移动会改变 facing 方向",
            ),
        ),
        ActionOntologyEntry(
            action="move_up",
            effect="朝上移动 1 格",
            details=(
                "若目标 tile 可通行（grass 等）：成功移动",
                "若目标 tile 是 water：进入 tile 同时补水（water +N）",
                "若目标 tile 是 cow / plant：进入 tile 同时补食物（food +N）",
                "若目标 tile 是 zombie / skeleton：可能受到攻击",
                "若目标 tile 不可通行（stone / tree / lava）：移动失败",
                "移动会改变 facing 方向",
            ),
        ),
        ActionOntologyEntry(
            action="move_down",
            effect="朝下移动 1 格",
            details=(
                "若目标 tile 可通行（grass 等）：成功移动",
                "若目标 tile 是 water：进入 tile 同时补水（water +N）",
                "若目标 tile 是 cow / plant：进入 tile 同时补食物（food +N）",
                "若目标 tile 是 zombie / skeleton：可能受到攻击",
                "若目标 tile 不可通行（stone / tree / lava）：移动失败",
                "移动会改变 facing 方向",
            ),
        ),
        ActionOntologyEntry(
            action="do",
            effect="context-sensitive，取决于 facing 的 tile",
            details=(
                "facing zombie / skeleton: 攻击（需要 sword 工具更有效）",
                "facing tree: 采集 wood（无需工具）",
                "facing stone: 采集 stone（需要 wood_pickaxe 或更高）",
                "facing coal: 采集 coal（需要 wood_pickaxe 或更高）",
                "facing iron: 采集 iron（需要 stone_pickaxe 或更高）",
                "facing diamond: 采集 diamond（需要 iron_pickaxe）",
                "facing cow / plant: 通常无效（食物靠走进 tile，不靠 do）",
                "facing water: 无效（水靠走进 tile）",
                "facing grass / empty: 无效",
            ),
        ),
        ActionOntologyEntry(
            action="sleep",
            effect="恢复 energy（推进时间，可能进入夜晚）",
            details=(
                "不补 food / water / health",
                "睡眠时易受威胁攻击——有 threat 可见时不建议",
                "energy 严重低时必须 sleep",
            ),
        ),
        ActionOntologyEntry(
            action="place_stone",
            effect="在 facing tile 放置 stone",
            details=(
                "需要 inventory 中有 stone",
                "放置后 inventory -1，该 tile 变成 stone",
            ),
        ),
        ActionOntologyEntry(
            action="place_table",
            effect="在 facing tile 放置 crafting table",
            details=(
                "需要 inventory 中有 wood",
                "table 是制作工具的前置",
            ),
        ),
        ActionOntologyEntry(
            action="place_furnace",
            effect="在 facing tile 放置 furnace",
            details=(
                "需要 inventory 中有 stone",
                "furnace 是 iron 制作的前置",
            ),
        ),
        ActionOntologyEntry(
            action="place_plant",
            effect="在 facing tile 放置 plant（种子）",
            details=(
                "需要 inventory 中有对应种子",
                "种植为后续食物来源做铺垫",
            ),
        ),
        ActionOntologyEntry(
            action="make_wood_pickaxe",
            effect="制作 wood_pickaxe",
            details=(
                "需要 wood x1，nearby table",
            ),
        ),
        ActionOntologyEntry(
            action="make_stone_pickaxe",
            effect="制作 stone_pickaxe",
            details=(
                "需要 wood x1 + stone x1，nearby table",
            ),
        ),
        ActionOntologyEntry(
            action="make_iron_pickaxe",
            effect="制作 iron_pickaxe",
            details=(
                "需要 wood x1 + coal x1 + iron x1，nearby table + furnace",
            ),
        ),
        ActionOntologyEntry(
            action="make_wood_sword",
            effect="制作 wood_sword",
            details=(
                "需要 wood x1，nearby table",
                "sword 用于 do 攻击 threat（提高攻击效果）",
            ),
        ),
        ActionOntologyEntry(
            action="make_stone_sword",
            effect="制作 stone_sword",
            details=(
                "需要 wood x1 + stone x1，nearby table",
                "sword 用于 do 攻击 threat（提高攻击效果）",
            ),
        ),
        ActionOntologyEntry(
            action="make_iron_sword",
            effect="制作 iron_sword",
            details=(
                "需要 wood x1 + coal x1 + iron x1，nearby table + furnace",
                "sword 用于 do 攻击 threat（提高攻击效果）",
            ),
        ),
    ),
)
