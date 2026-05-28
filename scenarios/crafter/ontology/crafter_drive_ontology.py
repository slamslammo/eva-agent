"""Crafter drive ontology — text per plan §5.4.1 (1:1 transcription).

Red line: text is A-authored per plan §5.4.1. B does NOT free-form. Any
revision must update the plan first and then sync this file.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import DriveOntology, DriveOntologyEntry

__all__ = ["CRAFTER_DRIVE_ONTOLOGY"]


CRAFTER_DRIVE_ONTOLOGY = DriveOntology(
    entries=(
        DriveOntologyEntry(
            name="metabolic",
            meaning="生理资源压强——身体维持运转所需的基本能量物质处于短缺压力下",
            low_means="生理资源充足，无短缺压力",
            high_means="生理资源严重短缺，个体正在承受生理代谢压力",
            typical_causes=(
                "food 数值下降（饥饿）",
                "water 数值下降（渴）",
                "energy 数值下降（疲劳）",
                "health 数值下降（受伤）",
            ),
            relief_directions=(
                "走进 water tile 补 water",
                "走进 cow / plant tile 补 food",
                "sleep 补 energy（注意：不补 food/water）",
            ),
        ),
        DriveOntologyEntry(
            name="safety",
            meaning="安全压强——个体生存受外部威胁直接威胁的程度",
            low_means="当前无可见威胁，安全",
            high_means="可见威胁正在接近或已造成伤害",
            typical_causes=(
                "可见 zombie / skeleton",
                "threat 距离接近",
                "夜晚（zombies 高发）",
            ),
            relief_directions=(
                "远离威胁（move away from threat）",
                "攻击威胁（do facing threat tile，需要 sword）",
                "进入安全区域",
            ),
        ),
        DriveOntologyEntry(
            name="recovery",
            meaning="恢复需求压强——个体能量储备处于需要主动恢复的状态",
            low_means="能量充沛，无需休息",
            high_means="能量耗尽，必须休息恢复",
            typical_causes=(
                "energy 数值下降",
                "长期未 sleep",
            ),
            relief_directions=(
                "sleep 动作（但仅在安全环境）",
            ),
        ),
        DriveOntologyEntry(
            name="acquisition",
            meaning="资源获取压强——个体当前缺少推进所需的基础资源",
            low_means="资源充足，无获取需求",
            high_means="关键资源缺失，需要主动获取",
            typical_causes=(
                "inventory 空 / 关键资源（wood/stone/coal/iron）缺失",
                "看到附近有可采集资源",
            ),
            relief_directions=(
                "朝可见资源移动 + do 采集",
                "探索未知区域寻找资源",
            ),
        ),
        DriveOntologyEntry(
            name="capability",
            meaning="能力建设压强——个体当前缺少推进所需的能力工具",
            low_means="工具齐备，能力满足当前任务",
            high_means="缺少关键工具，制约后续动作",
            typical_causes=(
                "缺少 pickaxe（无法采矿）",
                "缺少 sword（无法攻击威胁）",
                "缺少 table / furnace（无法制作）",
            ),
            relief_directions=(
                "收集材料后 make_* / place_*",
                "优先制作前置工具（table → pickaxe → sword）",
            ),
        ),
        DriveOntologyEntry(
            name="exploration",
            meaning="探索驱动力——个体在健康状态下扩展认知边界的内在拉力",
            low_means="探索意愿低（通常因威胁或资源压力）",
            high_means="健康状态下的认知扩展驱动",
            typical_causes=(
                "当前安全 + 资源充足时自然上升",
                "在威胁 / 资源压力下自动抑制",
            ),
            relief_directions=(
                "走向未探索区域",
                "注意：exploration 是 growth-driver，不像其他 drive 那样必须解决",
            ),
        ),
    ),
)
