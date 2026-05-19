"""Round 1.A failing tests pinning target behavior for Crafter action-resolution widening.

These tests are intentionally written against the post-Round-1.A signatures
of ``build_integrity_response_candidates`` / ``select_response_action``.
On current ``main`` they fail with ``TypeError`` (unexpected keyword argument)
or assertion failure. After slices A-2/A-3/A-4 land they should all pass.

What each test pins:

* ``test_widening_produces_candidates_beyond_legacy_noop_sleep_do_set`` —
  the candidate set must expand beyond the legacy 3 actions when context
  supports a wider eligible set.
* ``test_prior_preferred_action_appears_when_eligible_under_profile`` —
  when an inherited prior recommends a concrete action that is eligible for
  its candidate_profile under the new mapping, that action must appear in
  the candidate set with the matching profile.
* ``test_habit_bias_drives_selection_among_candidates_of_same_profile`` —
  when habit bias favors a specific concrete action and multiple candidates
  of the same profile are available, selection must pick the habit-favored
  action and record habit provenance in the selection reason.
"""

from __future__ import annotations

import unittest

from eva.kernel import ActivePressure, RuntimeState, utc_now
from scenarios.crafter import activate_crafter_scenario
from scenarios.crafter.actions import (
    build_integrity_response_candidates,
    filter_response_candidates,
    select_response_action,
)


class CrafterActionWideningSmokeTests(unittest.TestCase):
    """Pin Round 1.A target behavior. Failing until slices A-2/A-3/A-4 land."""

    def setUp(self) -> None:
        activate_crafter_scenario()

    def _build_acquisition_pressure(self) -> ActivePressure:
        return ActivePressure(
            pressure_id="pressure-acquisition-test",
            type="acquisition",
            severity="critical",
            evidence={"reason": "inventory_sparse"},
            first_seen_at=utc_now(),
            last_seen_at=utc_now(),
            trend="worsening",
        )

    def _build_runtime_state(self) -> RuntimeState:
        return RuntimeState(life_state="STABLE", instance_valid=True)

    def _baseline_agent_observation(self) -> dict[str, object]:
        return {
            "visible": {
                "life_panel": {
                    "values": {"health": 9, "food": 7, "water": 7, "energy": 8}
                },
                "inventory_panel": {"items": {}},
                "nearby_objects": [],
                "local_view": {"nearby_objects": {}},
            },
            "task_context": {"unlocked_achievements_visible": []},
        }

    # -- Pin 1: widening expands the candidate set beyond legacy 3 -----------

    def test_widening_produces_candidates_beyond_legacy_noop_sleep_do_set(self) -> None:
        """Under acquisition pressure with no immediate threat, widening must
        surface at least one candidate action outside the legacy
        ``{noop, sleep, do}`` set so that the agent has real choice."""

        pressure = self._build_acquisition_pressure()
        runtime_state = self._build_runtime_state()

        candidate_context = {
            "top_drive": "acquisition",
            "pressure_reason": "inventory_sparse",
            "life_state": "STABLE",
            "agent_observation": self._baseline_agent_observation(),
            "inherited_priors": [],
        }

        candidates = build_integrity_response_candidates(
            pressure,
            runtime_state,
            candidate_context=candidate_context,
        )

        actions = {candidate.action for candidate in candidates}
        legacy_set = {"noop", "sleep", "do"}
        new_actions = actions - legacy_set

        self.assertGreater(
            len(new_actions),
            0,
            "Round 1.A widening must surface at least one action beyond the "
            f"legacy {{noop, sleep, do}} set. Observed candidate actions: {sorted(actions)}.",
        )

    # -- Pin 2: prior preferred_action appears when eligible -----------------

    def test_prior_preferred_action_appears_when_eligible_under_profile(self) -> None:
        """An inherited prior recommending a concrete action that is eligible
        for its candidate_profile under the new mapping must cause that action
        to appear in the candidate set with the matching profile."""

        pressure = self._build_acquisition_pressure()
        runtime_state = self._build_runtime_state()

        # ``place_table`` is eligible for ``escalate_first`` under the new
        # PROFILE_ELIGIBLE_ACTIONS mapping. A prior recommending it should
        # cause it to surface as a candidate.
        candidate_context = {
            "top_drive": "acquisition",
            "pressure_reason": "inventory_sparse",
            "life_state": "STABLE",
            "agent_observation": self._baseline_agent_observation(),
            "inherited_priors": [
                {
                    "candidate_profile": "escalate_first",
                    "preferred_action": "place_table",
                    "evidence_count": 3,
                    "stability_score": 0.75,
                    "confidence": 0.85,
                    "bias_strength": 0.8,
                }
            ],
        }

        candidates = build_integrity_response_candidates(
            pressure,
            runtime_state,
            candidate_context=candidate_context,
        )

        actions = {candidate.action for candidate in candidates}
        self.assertIn(
            "place_table",
            actions,
            "When an inherited prior recommends ``place_table`` under "
            "``escalate_first`` (which the new mapping makes eligible), "
            f"``place_table`` must appear in the candidate set. Observed: {sorted(actions)}.",
        )

        # The candidate carrying ``place_table`` must carry escalate-profile
        # provenance via its ``posture`` field. ``ResponseCandidate`` does not
        # expose ``parameter_domain``; profile association is encoded as a
        # scenario-internal posture token consumed downstream by selection.
        matched = [c for c in candidates if c.action == "place_table"]
        self.assertTrue(matched, "Expected at least one ``place_table`` candidate.")
        self.assertIn(
            "escalate",
            matched[0].posture.lower(),
            "The ``place_table`` candidate must carry escalate-profile provenance "
            f"in its posture token. Got: {matched[0].posture!r}.",
        )

    # -- Pin 3: habit bias drives selection among same-profile candidates ----

    def test_habit_bias_drives_selection_among_candidates_of_same_profile(self) -> None:
        """When two candidates share the same profile but habit bias favors one
        concrete action, ``select_response_action`` must pick the habit-favored
        action and record habit provenance in ``selected_action_reason``."""

        pressure = self._build_acquisition_pressure()
        runtime_state = self._build_runtime_state()

        candidate_context = {
            "top_drive": "acquisition",
            "pressure_reason": "inventory_sparse",
            "life_state": "STABLE",
            "agent_observation": self._baseline_agent_observation(),
            "inherited_priors": [],
        }

        candidates = build_integrity_response_candidates(
            pressure,
            runtime_state,
            candidate_context=candidate_context,
        )
        decisions = filter_response_candidates(pressure, runtime_state, candidates)

        # Habit bias favors ``do`` under this situation_key. Selection must
        # prefer ``do`` over other equally-eligible escalate_first candidates.
        selection_context = {
            "situation_key": "acquisition|STABLE|inventory_sparse",
            "habit_summaries": [
                {
                    "situation_key": "acquisition|STABLE|inventory_sparse",
                    "candidate_profile": "escalate_first",
                    "preferred_action": "do",
                    "evidence_count": 6,
                    "stability_score": 0.85,
                    "confidence": 0.9,
                    "bias_strength": 0.75,
                }
            ],
            "inherited_priors": [],
        }

        selection = select_response_action(
            pressure,
            runtime_state,
            candidates,
            decisions,
            bridge_policy={"selection_context": selection_context},
        )

        self.assertEqual(
            selection.selected_action,
            "do",
            "Habit bias favoring ``do`` under the situation_key must drive "
            f"selection to ``do``. Got: {selection.selected_action}.",
        )
        self.assertIn(
            "habit",
            (selection.selected_action_reason or "").lower(),
            "Selection reason must record habit provenance when habit bias "
            f"drives the choice. Got: {selection.selected_action_reason!r}.",
        )


if __name__ == "__main__":
    unittest.main()
