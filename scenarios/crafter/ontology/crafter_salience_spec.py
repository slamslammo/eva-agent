"""Crafter salience spec — text per plan §5.4.2 (1:1 transcription).

Red line: text is A-authored per plan §5.4.2. B does NOT free-form.

dlpfc-prompt-all-english: LLM-facing prose translated zh→en (faithful, no
add/drop). Field names (top_drive / drive_levels / drive_trends) and threshold
numbers unchanged; only the natural-language wording changed.
"""

from __future__ import annotations

from eva.l3_deliberation.ontology import SalienceSpec

__all__ = ["CRAFTER_SALIENCE_SPEC"]


_BODY = """salience is the "attention annotation" that L2 provides to the dlPFC — it is context, not a command:

- top_drive: the name of the drive with the highest current value. This reminds you "which need is most urgent",
            but does not force you to handle it first.
- drive_levels: the current strength of each drive (0-1).
- drive_trends: the trend of each drive (worsening / stable / improving).

Key thresholds (reference, not absolute):
- > 0.7: usually classed as critical (needs urgent attention)
- 0.4-0.7: degraded (noticeable but not urgent)
- < 0.4: stable

Important: a high drive_level does not mean "must handle immediately" — you need to combine state_packet,
local_view, and the action effect schema to judge the most reasonable candidate action right now. A high drive
only makes you "keep an eye on that dimension"; the final action is decided by you (the dlPFC) within admitted_actions."""


CRAFTER_SALIENCE_SPEC = SalienceSpec(body=_BODY)
