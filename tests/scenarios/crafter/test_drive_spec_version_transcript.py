"""single-source-scenario-drive-metadata slice 3 — drive_spec_version emission.

The transcript schema v1.1 reserved a ``drive_spec_version`` field (previously
always null, a placeholder for this task). Now that CRAFTER_DRIVE_SPEC is the
single authority, its ``version`` flows through ScenarioOntology into the
dlPFC transcript so a 100-turn replay can pin which drive-spec snapshot a run
used. The framework field stays optional (None default) so non-Crafter / bare
runs are unaffected.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class ScenarioOntologyCarriesDriveSpecVersionTests(unittest.TestCase):
    def test_scenario_ontology_has_drive_spec_version_field_default_none(self) -> None:
        from eva.l3_deliberation.ontology import (
            ActionEffectSchema,
            ActionOntology,
            DlpfcRoleContract,
            DriveOntology,
            SalienceSpec,
            ScenarioOntology,
        )

        ont = ScenarioOntology(
            scenario_name="x",
            dlpfc_role_contract=DlpfcRoleContract(body="b"),
            drive_ontology=DriveOntology(entries=()),
            salience_spec=SalienceSpec(body="s"),
            action_ontology=ActionOntology(entries=()),
            action_effect_schema=ActionEffectSchema(matrix={}),
        )
        # additive optional field — default None keeps existing constructions valid
        self.assertIsNone(ont.drive_spec_version)

    def test_crafter_scenario_ontology_carries_spec_version(self) -> None:
        from scenarios.crafter.drive_spec import CRAFTER_DRIVE_SPEC
        from scenarios.crafter.ontology import CRAFTER_SCENARIO_ONTOLOGY

        self.assertEqual(
            CRAFTER_SCENARIO_ONTOLOGY.drive_spec_version, CRAFTER_DRIVE_SPEC.version
        )
        self.assertEqual(CRAFTER_SCENARIO_ONTOLOGY.drive_spec_version, "crafter-drive-spec-v1")


class ProducerThreadsDriveSpecVersionTests(unittest.TestCase):
    """The dlPFC producer must emit the active scenario's drive_spec_version."""

    def _run_one_turn(self, temp_dir: str):
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        from scenarios.crafter.ontology import CRAFTER_SCENARIO_ONTOLOGY
        from scenarios.crafter.reasoning.llm_action_producer import CrafterLLMActionProducer

        sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")

        def chat_fn(messages):
            return '{"candidates": [{"action": "noop", "reason": "r"}]}'

        producer = CrafterLLMActionProducer(
            chat_fn=chat_fn,
            world_facts_fn=lambda: "",
            observation_fn=lambda: {},
            transcript_sink=sink,
            model_label="test-model",
            scenario_ontology=CRAFTER_SCENARIO_ONTOLOGY,
            identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
        )
        return producer

    def test_transcript_carries_crafter_drive_spec_version(self) -> None:
        from scenarios.crafter import activate_crafter_scenario
        from scenarios.crafter.drive_spec import CRAFTER_DRIVE_SPEC

        activate_crafter_scenario()
        with tempfile.TemporaryDirectory() as temp_dir:
            producer = self._run_one_turn(temp_dir)
            # Drive one record via the producer's own safe recorder, mirroring
            # how generate() calls it (avoids standing up a full env turn).
            ref = producer._record_transcript_safely(
                messages=[{"role": "system", "content": "s"}],
                raw_response='{"candidates": []}',
                parsed_response={"candidates": []},
                parse_status="ok",
                errors=[],
                prompt_sections_present={"drive_ontology": True},
                ontology_hash=None,
                world_facts_hash=None,
                action_effect_schema_hash=None,
            )
            self.assertIsNotNone(ref)
            payload = json.loads((Path(temp_dir) / ref).read_text())
            self.assertEqual(
                payload["drive_spec_version"], CRAFTER_DRIVE_SPEC.version
            )


if __name__ == "__main__":
    unittest.main()
