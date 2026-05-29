"""PR-Β': transcript schema v1.1 backward-compatible extension.

Plan §5.5b: schema bump v1 → v1.1 with 6 new optional fields:
- ontology_hash / world_facts_hash / action_effect_schema_hash (sha256:hex16)
- drive_spec_version (null placeholder for future task)
- drive_rendering (null placeholder for future task)
- drive_rendering_enabled (False placeholder for future task)

Red lines:
- v1.1 is a v1 SUPERSET — v1 clients can still read v1.1 payloads (new
  fields are additive optional)
- hash computation failure must NOT break decisions (R3)
- schema_version field becomes "llm_transcript_v1.2"
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class SchemaVersionV11Tests(unittest.TestCase):
    def test_schema_version_constant_bumped_to_v1_1(self) -> None:
        from eva.l3_deliberation.llm_transcript import SCHEMA_VERSION
        self.assertEqual(SCHEMA_VERSION, "llm_transcript_v1.2")

    def test_persisted_payload_records_v1_1_schema_version(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=0,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000000.json").read_text())
            self.assertEqual(payload["schema_version"], "llm_transcript_v1.2")


class V11OptionalHashFieldsTests(unittest.TestCase):
    """Sink accepts and persists the 3 hash fields when provided."""

    def test_record_accepts_three_hash_fields_and_persists_them(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=1,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
                ontology_hash="sha256:abcd1234",
                world_facts_hash="sha256:beef5678",
                action_effect_schema_hash="sha256:cafe9999",
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000001.json").read_text())
            self.assertEqual(payload["ontology_hash"], "sha256:abcd1234")
            self.assertEqual(payload["world_facts_hash"], "sha256:beef5678")
            self.assertEqual(payload["action_effect_schema_hash"], "sha256:cafe9999")

    def test_hash_fields_absent_in_payload_when_not_provided(self) -> None:
        """Backward compat: when caller doesn't pass hashes, payload still parseable as v1."""
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=2,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000002.json").read_text())
            # All v1 fields still present
            for v1_field in ("run_id", "individual_id", "turn_index", "llm_role",
                             "scenario", "model", "messages", "raw_response",
                             "parsed_response", "parse_status", "errors",
                             "prompt_sections_present", "timestamp", "schema_version"):
                self.assertIn(v1_field, payload, f"v1 field {v1_field} missing")


class V11DriveRenderingPlaceholderFieldsTests(unittest.TestCase):
    """drive_spec_version / drive_rendering / drive_rendering_enabled are placeholders.

    Plan §5.5b: these are reserved interface slots for future tasks
    (single-source-scenario-drive-metadata + drive-rendering-layer). They must
    be present in the schema with safe defaults so future code can populate
    them without re-shipping a schema bump.
    """

    def test_placeholder_fields_have_default_values_when_omitted(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=3,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000003.json").read_text())
            self.assertIsNone(payload.get("drive_spec_version"))
            self.assertIsNone(payload.get("drive_rendering"))
            self.assertEqual(payload.get("drive_rendering_enabled"), False)


class V11BackwardCompatTests(unittest.TestCase):
    """A v1 client reading a v1.1 payload should find all v1 fields unchanged."""

    def test_v1_field_names_unchanged_in_v1_1_payload(self) -> None:
        """All original v1 keys must still appear with original shapes."""
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="rid", individual_id="iid", turn_index=7,
                llm_role="dlPFC", scenario="crafter",
                model="deepseek-v4-pro",
                messages=[{"role": "system", "content": "s"}],
                raw_response="ok",
                parsed_response={"candidates": []},
                parse_status="ok", errors=[],
                prompt_sections_present={"state_packet": True},
                ontology_hash="sha256:aaaa",
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000007.json").read_text())
            # v1 fields keep their original types
            self.assertIsInstance(payload["messages"], list)
            self.assertIsInstance(payload["prompt_sections_present"], dict)
            self.assertEqual(payload["parse_status"], "ok")
            self.assertEqual(payload["model"], "deepseek-v4-pro")


class V11NoOpSinkUnaffectedTests(unittest.TestCase):
    """R4: off mode (NoOpSink) must still be zero-overhead with v1.1 fields."""

    def test_noop_sink_ignores_v1_1_fields(self) -> None:
        from eva.l3_deliberation.llm_transcript import NoOpTranscriptSink
        sink = NoOpTranscriptSink()
        result = sink.record(
            run_id="r", individual_id="i", turn_index=0,
            llm_role="dlPFC", scenario="crafter", model="m",
            messages=[], raw_response="", parsed_response=None,
            parse_status="ok", errors=[], prompt_sections_present={},
            ontology_hash="sha256:x",
            world_facts_hash="sha256:y",
            action_effect_schema_hash="sha256:z",
            drive_spec_version=None,
            drive_rendering=None,
            drive_rendering_enabled=False,
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
