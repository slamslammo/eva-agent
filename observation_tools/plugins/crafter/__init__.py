"""Crafter 场景特定可视化 plugin。

从 EVA 运行时 trace 中提取 Crafter 场景的关键观察数据，注入到 ChainView
里供前端渲染。提取范围：

- 生命体征（health / food / water / energy / threat_count）
- 库存（items / tools / available_tools）
- 视野感知（threat / resource / utility / capability_gap）
- 本 turn 变化（life_delta / inventory_delta / achievement_delta /
  visible_threat_count）

9×7 local_view 格子在 V1 不可用：EVA 运行时当前没有把 agent observation
持久化到 trace（只在 deliberation 内部使用）。要恢复需要 runtime 增加
observation 持久化 hook，留 V2。
"""

from .extractor import extract_crafter_view

__all__ = ["extract_crafter_view"]
