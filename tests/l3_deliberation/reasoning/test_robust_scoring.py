"""PR-O1 slice 1: robust-scoring primitives (pure functions).

Plan ofc-robust-scoring §3 + A G1 review Q1/Q3:
- normalize signed factors via tanh (sign-preserving, saturating) — NOT clip[0,1]
  (clipping to [0,1] would drop the negative = the "anti-drive should be penalized"
  signal, which is the core of OFC's veto role).
- cap the EXPERIENCE GROUP's summed contribution (Q3: cap the sum, not each), so
  experience factors can't collude (§1.3) to overturn drive+dlpfc.

These are pure functions — tested in isolation before any aggregation rewrite
(zero Linux risk until wired in by a later slice).
"""

from __future__ import annotations

import math
import unittest

from eva.l3_deliberation.reasoning.value_judgment import (
    robust_normalize,
    cap_group_contribution,
    _robust_aggregate,
    EXPERIENCE_GROUP_CAP,
    W_DRIVE,
)


class RobustNormalizeTests(unittest.TestCase):
    def test_zero_maps_to_zero(self) -> None:
        self.assertEqual(robust_normalize(0.0, scale=0.3), 0.0)

    def test_sign_preserved(self) -> None:
        self.assertGreater(robust_normalize(0.2, scale=0.3), 0.0)
        self.assertLess(robust_normalize(-0.2, scale=0.3), 0.0)

    def test_bounded_in_minus1_1(self) -> None:
        # tanh saturates within [-1, 1] (float tanh reaches exactly ±1.0 at extremes).
        self.assertLessEqual(robust_normalize(1000.0, scale=0.3), 1.0)
        self.assertGreater(robust_normalize(1000.0, scale=0.3), 0.99)
        self.assertGreaterEqual(robust_normalize(-1000.0, scale=0.3), -1.0)
        self.assertLess(robust_normalize(-1000.0, scale=0.3), -0.99)

    def test_monotonic_preserves_order(self) -> None:
        a = robust_normalize(0.1, scale=0.3)
        b = robust_normalize(0.3, scale=0.3)
        c = robust_normalize(0.5, scale=0.3)
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_saturation_compresses_extremes(self) -> None:
        # 0.99 vs 0.90 raw should NOT be a huge gap after saturation (plan §3.2).
        hi = robust_normalize(0.99, scale=0.3)
        lo = robust_normalize(0.90, scale=0.3)
        self.assertLess(hi - lo, 0.05)

    def test_matches_tanh_scale(self) -> None:
        self.assertAlmostEqual(robust_normalize(0.3, scale=0.3), math.tanh(1.0), places=6)

    def test_zero_scale_is_safe(self) -> None:
        # Degenerate scale must not divide-by-zero; returns 0.0 (no signal).
        self.assertEqual(robust_normalize(0.5, scale=0.0), 0.0)


class CapGroupContributionTests(unittest.TestCase):
    def test_under_cap_unchanged(self) -> None:
        self.assertEqual(cap_group_contribution(0.1, cap=0.2), 0.1)
        self.assertEqual(cap_group_contribution(-0.1, cap=0.2), -0.1)

    def test_over_cap_clipped_both_signs(self) -> None:
        self.assertEqual(cap_group_contribution(0.5, cap=0.2), 0.2)
        self.assertEqual(cap_group_contribution(-0.5, cap=0.2), -0.2)

    def test_exactly_cap(self) -> None:
        self.assertEqual(cap_group_contribution(0.2, cap=0.2), 0.2)


class RobustAggregateTests(unittest.TestCase):
    """The robust aggregation: score = w_drive·norm(drive) + w_proj·norm(proj)
    + cap(experience). Drive dominates; experience can't overturn it; ordering
    by the dominant factor is preserved; sign is preserved."""

    def _agg(self, drive=0.0, proj=0.0, learn=0.0, habit=0.0):
        return _robust_aggregate(
            drive_score=drive, projection_score=proj,
            learning_bias=learn, habit_priority_bonus=habit,
        )

    def test_drive_ordering_preserved(self) -> None:
        # Higher drive → higher score (monotonic), other factors equal.
        self.assertLess(self._agg(drive=0.1), self._agg(drive=0.3))
        self.assertLess(self._agg(drive=0.3), self._agg(drive=0.5))

    def test_negative_drive_penalized(self) -> None:
        # Anti-drive stays a penalty (sign preserved, A Q1).
        self.assertLess(self._agg(drive=-0.2), self._agg(drive=0.0))

    def test_experience_capped(self) -> None:
        # Even huge learning+habit, the experience term cannot exceed the cap.
        huge = self._agg(learn=10.0, habit=10.0)
        self.assertLessEqual(huge, EXPERIENCE_GROUP_CAP + 1e-9)

    def test_experience_cannot_overturn_drive(self) -> None:
        # A strong-drive candidate with no experience beats a zero-drive
        # candidate maxing experience (w_dlpfc>cap invariant; here drive>cap).
        strong_drive = self._agg(drive=0.5)
        max_experience = self._agg(drive=0.0, learn=10.0, habit=10.0)
        self.assertGreater(strong_drive, max_experience)

    def test_drive_is_dominant_weight(self) -> None:
        # drive's full-saturation contribution ≈ W_DRIVE, the largest single term.
        near_full = self._agg(drive=100.0)  # tanh saturates → ~W_DRIVE
        self.assertGreater(near_full, EXPERIENCE_GROUP_CAP)
        self.assertLessEqual(near_full, W_DRIVE + 0.2)  # + small proj/exp headroom


if __name__ == "__main__":
    unittest.main()
