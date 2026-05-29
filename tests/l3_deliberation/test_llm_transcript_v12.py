"""PR-S1 Slice 7: transcript schema v1.1 → v1.2 with env_step_invoked + counters.

Plan §3.5 R12: extends schema additively with three fields so the transcript
self-documents whether the deliberation that produced the LLM call ended in
an actual env.step (env_step_invoked) and which decision attempt / scenario
step it corresponds to.

Red lines:
- v1.2 is a v1.1 superset — v1.1 clients can still read v1.2 payloads.
- Sink record() accepts the new kwargs as optional; legacy call sites unchanged.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class SchemaVersionV12Tests(unittest.TestCase):
    def test_schema_version_bumped_to_v1_2(self) -> None:
        from eva.l3_deliberation.llm_transcript import SCHEMA_VERSION
        self.assertEqual(SCHEMA_VERSION, "llm_transcript_v1.2")

    def test_persisted_payload_records_v1_2(self) -> None:
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


class V12OptionalScenarioTimeFieldsTests(unittest.TestCase):
    def test_record_accepts_env_step_invoked_and_counters(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=5,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
                env_step_invoked=True,
                attempt_index=7,
                scenario_step_index=5,
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000005.json").read_text())
            self.assertTrue(payload.get("env_step_invoked"))
            self.assertEqual(payload.get("attempt_index"), 7)
            self.assertEqual(payload.get("scenario_step_index"), 5)

    def test_env_step_invoked_false_persisted(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=3,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
                env_step_invoked=False,
                attempt_index=10,
                scenario_step_index=4,
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000003.json").read_text())
            self.assertFalse(payload.get("env_step_invoked"))
            self.assertEqual(payload.get("attempt_index"), 10)
            self.assertEqual(payload.get("scenario_step_index"), 4)

    def test_legacy_call_without_new_fields_still_works(self) -> None:
        """v1.1 callers don't pass env_step_invoked / counters; sink defaults gracefully."""
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r", individual_id="i", turn_index=1,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000001.json").read_text())
            # When not provided: omit env_step_invoked + attempt_index +
            # scenario_step_index from payload (back-compat: v1.1 clients see
            # the same fields they expect).
            self.assertNotIn("env_step_invoked", payload)
            self.assertNotIn("attempt_index", payload)
            self.assertNotIn("scenario_step_index", payload)


class V12NoOpSinkTests(unittest.TestCase):
    def test_noop_sink_accepts_v1_2_kwargs(self) -> None:
        from eva.l3_deliberation.llm_transcript import NoOpTranscriptSink
        sink = NoOpTranscriptSink()
        result = sink.record(
            run_id="r", individual_id="i", turn_index=0,
            llm_role="dlPFC", scenario="crafter", model="m",
            messages=[], raw_response="", parsed_response=None,
            parse_status="ok", errors=[], prompt_sections_present={},
            env_step_invoked=True, attempt_index=1, scenario_step_index=1,
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
