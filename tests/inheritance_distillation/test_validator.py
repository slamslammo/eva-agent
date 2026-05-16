from __future__ import annotations

import unittest

from inheritance_distillation.validators import validate_structural_invariants


class StructuralInvariantValidatorTests(unittest.TestCase):
    def test_validator_rejects_framework_authority_claims(self) -> None:
        records = [
            {
                "scope": {"scenario": "crafter", "anchor_mutation": True},
                "content": {
                    "situation_key": "acquisition|STABLE|inventory_sparse",
                    "candidate_profile": "observe_first",
                },
            }
        ]
        with self.assertRaisesRegex(ValueError, "structural invariants"):
            validate_structural_invariants(records)

    def test_validator_allows_advisory_prior_records(self) -> None:
        records = [
            {
                "scope": {"scenario": "crafter", "situation_key": "acquisition|STABLE|inventory_sparse"},
                "content": {
                    "situation_key": "acquisition|STABLE|inventory_sparse",
                    "candidate_profile": "observe_first",
                    "preferred_action": "noop",
                    "evidence_count": 3,
                    "stability_score": 0.75,
                    "bias_strength": 0.4,
                },
            }
        ]
        validate_structural_invariants(records)


if __name__ == "__main__":
    unittest.main()
