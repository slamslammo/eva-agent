"""observation_tools.plugins — 场景特定渲染插件。

每个场景一个子目录（例 ``crafter/``、``linux_runtime/``），提供
该场景独有的观察数据提取（后端 extractor）与渲染（前端 JS）。
核心展示组件来自 ``observation_tools.core``。

后端 hook：``apply_plugins_to_chain(chain_dict)`` —— 由 ``chain_builder``
在组装 ChainView 时调用；每个 plugin 检查该 turn 是否包含本场景的关键
字段，能识别就把提取结果 inject 进 chain_dict（前端按字段名渲染）。
"""

from __future__ import annotations

from typing import Any


def apply_plugins_to_chain(chain_dict: dict[str, Any]) -> dict[str, Any]:
    """依次运行所有已知 plugin 的 extractor。

    V1：硬编码已知 plugin 列表（Crafter）。V2 可改为基于 entry-point /
    显式注册的 discovery 机制，并接受未知场景的"无 plugin"降级。
    """

    try:
        from .crafter.extractor import extract_crafter_view

        crafter_view = extract_crafter_view(
            chain_dict.get("deliberation"),
            chain_dict.get("response"),
        )
        if crafter_view:
            chain_dict["crafter"] = crafter_view
    except ImportError:
        # crafter plugin 缺失或场景不是 Crafter，跳过
        pass

    return chain_dict
