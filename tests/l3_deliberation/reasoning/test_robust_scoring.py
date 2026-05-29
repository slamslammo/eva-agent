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


if __name__ == "__main__":
    unittest.main()
