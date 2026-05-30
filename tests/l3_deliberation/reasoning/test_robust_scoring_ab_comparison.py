"""PR-O3 slice 2: A/B comparison of robust aggregation vs the pre-PR-O1 直接相加.

plan §9 "Linux 评分前后对照：排序结论不变，或变化可解释" + "尺度不可比" row.

The old unbounded direct-sum (score = drive + projection + learning + habit) was
REPLACED by the robust aggregation in PR-O1, so it no longer exists in the code —
the only way to do a true "前/后" comparison is to reproduce the old formula here
as a reference oracle and compare ORDERING:

  - Normal regime (factors in calibration range, no collusion): robust preserves
    the old ordering → "排序结论不变" (this is the A/B-equivalence guarantee the
    Linux scenario relies on; shared value_judgment.py).
  - Collusion regime: the old sum lets an experience spike overturn drive; robust
    caps the experience group so drive stays dominant → "变化可解释" (improvement,
    not a regression — exactly failure-mode B / §1.3 the plan set out to fix).
  - Scale comparability (problem 2): under direct-sum an inflated drive_score
    (e.g. raw-action summing 5 Crafter drives) runs away and crushes everything;
    calibrated tanh normalization saturates it so an inflated magnitude no longer
    manufactures a false gap.

Pure-function level (the oracle + _robust_aggregate), zero Linux risk. Class /
test names deliberately avoid the substring 'linux' so `pytest -k linux` keeps
reporting exactly the real Linux-scenario regression count (A's A/B baseline).
"""

from __future__ import annotations

import unittest

from eva.l3_deliberation.reasoning.value_judgment import (
    _robust_aggregate,
    EXPERIENCE_GROUP_CAP,
)


def _robust(drive: float = 0.0, proj: float = 0.0, learn: float = 0.0, habit: float = 0.0) -> float:
    return _robust_aggregate(
        drive_score=drive,
        projection_score=proj,
        learning_bias=learn,
        habit_priority_bonus=habit,
        dlpfc_rank=None,  # A/B oracle compares non-LLM (Linux-equivalent) candidates
    )


def _old_direct_sum(drive: float = 0.0, proj: float = 0.0, learn: float = 0.0, habit: float = 0.0) -> float:
    """Pre-PR-O1 unbounded aggregation: equal-weight direct sum of the raw factors.

    Reference oracle ONLY (the production code no longer contains this). This is the
    'before' side of the 评分前后对照.
    """

    return drive + proj + learn + habit


def _ordering(score_fn, candidates: list[dict]) -> list[int]:
    """Return candidate indices sorted best→worst under score_fn (stable)."""

    return sorted(range(len(candidates)), key=lambda i: score_fn(**candidates[i]), reverse=True)


class DirectSumABComparisonTests(unittest.TestCase):
    """robust aggregation vs the reproduced pre-PR-O1 direct-sum oracle."""

    def test_normal_regime_preserves_ordering(self) -> None:
        # Factors within the calibrated range, no experience collusion: the robust
        # ordering must equal the old direct-sum ordering —排序结论不变 (A/B equiv).
        candidates = [
            {"drive": 0.50, "learn": 0.10},
            {"drive": 0.30, "learn": 0.20},
            {"drive": 0.10, "learn": 0.05},
            {"drive": 0.40, "learn": 0.00},
        ]
        self.assertEqual(
            _ordering(_old_direct_sum, candidates),
            _ordering(_robust, candidates),
            "normal-regime robust ordering must match the pre-PR-O1 direct-sum ordering",
        )

    def test_normal_regime_preserves_ordering_with_negative_drive(self) -> None:
        # Sign preserved: an anti-drive candidate ranks last under both.
        candidates = [
            {"drive": 0.45, "learn": 0.05},
            {"drive": 0.20, "learn": 0.10},
            {"drive": -0.20, "learn": 0.15},
        ]
        self.assertEqual(_ordering(_old_direct_sum, candidates), _ordering(_robust, candidates))

    def test_collusion_regime_diverges_explicably(self) -> None:
        # Failure-mode B / §1.3: weak-drive candidate with a colluding experience
        # spike. OLD direct-sum lets it overturn a strong-drive candidate; robust
        # caps the experience group so drive stays on top. The divergence is the
        # intended fix (变化可解释), not a regression.
        strong_drive = {"drive": 0.5}
        exp_spike = {"drive": 0.1, "learn": 5.0, "habit": 5.0}
        # before: experience spike wins (the bug)
        self.assertGreater(_old_direct_sum(**exp_spike), _old_direct_sum(**strong_drive))
        # after: drive wins (the fix)
        self.assertGreater(_robust(**strong_drive), _robust(**exp_spike))


class ScaleComparabilityTests(unittest.TestCase):
    """problem 2: calibrated normalization makes differently-scaled drives comparable."""

    def test_inflated_drive_does_not_create_false_gap(self) -> None:
        # A raw-action drive_score can inflate (sum over 5 Crafter drives). Under
        # direct-sum, 2.0 vs 0.9 is a 1.1 chasm that crushes a calibrated rival;
        # under robust both saturate near the ceiling → tiny gap, no false区分.
        old_gap = _old_direct_sum(drive=2.0) - _old_direct_sum(drive=0.9)
        new_gap = _robust(drive=2.0) - _robust(drive=0.9)
        self.assertGreater(old_gap, 1.0)
        self.assertLess(new_gap, 0.05)

    def test_calibrated_normalization_keeps_drive_bounded(self) -> None:
        # However inflated the raw magnitude, the normalized contribution stays
        # bounded (so cross-source candidates are scored on one absolute ruler).
        for drive in (0.3, 0.9, 2.0, 50.0):
            self.assertLessEqual(_robust(drive=drive), 0.5 + EXPERIENCE_GROUP_CAP + 1e-9)


if __name__ == "__main__":
    unittest.main()
