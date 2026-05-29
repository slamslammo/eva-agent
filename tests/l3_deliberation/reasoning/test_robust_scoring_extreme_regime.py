"""PR-O3 slice 1: extreme-regime validation of the robust OFC aggregation.

review §3 caveat: T3 was a 温和 run (STABLE, never water-critical), so the
calibrated factor ranges (drive in [-0.25, 0.55]) do NOT cover the extreme high
end. Beyond the range tanh saturates (safe), but discrimination WITHIN the
extreme band is compressed. These tests PIN the *designed* extreme-regime
behavior (plan §3.0 层级 + §9 验证):

  - drive gates at the CATEGORY layer (water-critical → water-class wins),
  - dlPFC rank passes through DIRECTION within a category,
  - the OFC drive term still vetoes an anomalous dlPFC rank,
  - the experience group is capped (no collusion / single-factor 作妖),

and they EXPLICITLY document the saturation caveat: in the extreme band the
drive micro-gap is dominated by the dlpfc rank gap, i.e. direction within a
saturated category is dlPFC's call (intended, not a regression). Pinned so any
future re-calibration (review §3: when a water-critical run lands) is conscious.

Pure-function level (zero Linux risk): exercises _robust_aggregate directly.
"""

from __future__ import annotations

import math
import unittest

from eva.l3_deliberation.reasoning.value_judgment import (
    _robust_aggregate,
    DRIVE_SCALE,
    W_DRIVE,
    W_DLPFC,
    EXPERIENCE_GROUP_CAP,
)


def _agg(drive: float = 0.0, rank: int | None = None, learn: float = 0.0, habit: float = 0.0) -> float:
    return _robust_aggregate(
        drive_score=drive,
        projection_score=0.0,
        learning_bias=learn,
        habit_priority_bonus=habit,
        dlpfc_rank=rank,
    )


class ExtremeRegimeCategoryGatingTests(unittest.TestCase):
    """drive gates at the CATEGORY layer even in the extreme (super-calibration) band."""

    def test_water_critical_category_wins(self) -> None:
        # 朝水 (high drive_impact, extreme) beats 非水 (low) with no dlpfc either side.
        self.assertGreater(_agg(drive=0.9), _agg(drive=0.2))

    def test_extreme_drive_monotonic_and_bounded(self) -> None:
        # Beyond the [-0.25,0.55] calibration the drive contribution stays MONOTONIC
        # (no inversion) and BOUNDED by W_DRIVE — this is exactly what tanh saturation
        # buys: extreme inputs are safe, never explode or flip.
        self.assertLess(_agg(drive=0.55), _agg(drive=0.9))
        self.assertLess(_agg(drive=0.9), _agg(drive=1.2))
        self.assertLessEqual(_agg(drive=1.2), W_DRIVE + 1e-9)  # no dlpfc/proj/exp → term ≤ W_DRIVE

    def test_ofc_vetoes_anomalous_dlpfc_rank0(self) -> None:
        # dlPFC mis-ranks an anti-drive candidate rank0; a positive-drive rank2
        # candidate must still win — the OFC drive term vetoes the anomalous rank.
        self.assertGreater(_agg(drive=0.5, rank=2), _agg(drive=-0.3, rank=0))


class ExtremeRegimeDirectionPassthroughTests(unittest.TestCase):
    """Within one category (similar high drive), dlPFC rank decides DIRECTION."""

    def test_same_category_rank_passthrough(self) -> None:
        self.assertGreater(_agg(drive=0.85, rank=0), _agg(drive=0.85, rank=1))

    def test_saturation_caveat_dlpfc_dominates_drive_microgap(self) -> None:
        # CAVEAT (review §3), pinned: in the extreme band the drive micro-gap
        # (0.9 vs 0.7 → term gap ~0.018) is SMALLER than the dlpfc rank gap (~0.12),
        # so a lower-drive rank0 candidate beats a higher-drive rank1 one. This is
        # the INTENDED 层级 (direction within a saturated category = dlPFC's call),
        # NOT a regression. If a future water-critical run shows extreme drive must
        # discriminate harder, re-calibrate DRIVE_SCALE (review §3) — pinning it
        # here makes any such change a conscious decision.
        drive_gap = W_DRIVE * (math.tanh(0.9 / DRIVE_SCALE) - math.tanh(0.7 / DRIVE_SCALE))
        rank_gap = W_DLPFC * (1.0 - 0.6)
        self.assertLess(drive_gap, rank_gap)  # documents the compression magnitude
        self.assertGreater(_agg(drive=0.7, rank=0), _agg(drive=0.9, rank=1))


class ExtremeRegimeExperienceCapTests(unittest.TestCase):
    """Experience group capped even under colluding / single-factor extreme spikes."""

    def test_colluding_experience_capped_below_strong_drive(self) -> None:
        # habit+learning 同向尖峰 (collusion) cannot overturn a strong drive.
        self.assertGreater(_agg(drive=0.5), _agg(drive=0.0, learn=10.0, habit=10.0))

    def test_single_factor_spike_does_not_drown_drive_aligned(self) -> None:
        # 单因子作妖 (plan §9): a habit spike alone must not beat a drive-aligned
        # candidate (the experience group is weighted-then-capped).
        self.assertGreater(_agg(drive=0.4), _agg(drive=0.0, habit=10.0))

    def test_experience_group_never_exceeds_cap(self) -> None:
        self.assertLessEqual(_agg(drive=0.0, learn=100.0, habit=100.0), EXPERIENCE_GROUP_CAP + 1e-9)


if __name__ == "__main__":
    unittest.main()
