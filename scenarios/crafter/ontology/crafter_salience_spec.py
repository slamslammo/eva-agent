"""Crafter salience spec — text per plan §5.4.2 (1:1 transcription).

Red line: text is A-authored per plan §5.4.2. B does NOT free-form.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import SalienceSpec

__all__ = ["CRAFTER_SALIENCE_SPEC"]


_BODY = """salience 是 L2 提供给 dlPFC 的"注意力标注"，是 context 不是命令：

- top_drive: 当前数值最高的 drive 的名字。这是提醒"哪个需求最迫切"，
            但不强制你必须先处理它。
- drive_levels: 每个 drive 当前强度（0-1）。
- drive_trends: 每个 drive 的趋势（worsening / stable / improving）。

关键阈值（参考，非绝对）：
- > 0.7: 通常归为 critical（迫切需要关注）
- 0.4-0.7: degraded（明显但不紧急）
- < 0.4: stable

重要：drive_level 数值高不等于"必须立刻处理"——你需要综合 state_packet、
local_view、action effect schema 判断当前最合理的候选动作。drive 高只是
让你"留意这个维度"，最终行动由你（dlPFC）在 admitted_actions 内决定。"""


CRAFTER_SALIENCE_SPEC = SalienceSpec(body=_BODY)
