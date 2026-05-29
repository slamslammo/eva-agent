"""PR-Α: LLMTranscriptSink unit tests (test-first).

Covers §4 PR-Α acceptance:
- TranscriptMode three-tier switch (off/redacted/raw)
- NoOpTranscriptSink zero-overhead
- FileBasedTranscriptSink schema v1 + write-error swallowing
- build_transcript_sink_from_env factory
- prompt_sections_present metadata

Red lines:
- off mode must be zero-overhead (no string concat, no file io)
- write failure must NOT propagate
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class NoOpTranscriptSinkTests(unittest.TestCase):
    """off mode: record() returns None, performs zero io."""

    def test_noop_sink_record_returns_none(self) -> None:
        from eva.l3_deliberation.llm_transcript import NoOpTranscriptSink
        sink = NoOpTranscriptSink()
        result = sink.record(
            run_id="r1",
            individual_id="ind1",
            turn_index=0,
            llm_role="dlPFC",
            scenario="crafter",
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
            raw_response="ok",
            parsed_response={"candidates": []},
            parse_status="ok",
            errors=[],
            prompt_sections_present={"state_packet": True},
        )
        self.assertIsNone(result)

    def test_noop_sink_does_not_write_to_disk(self) -> None:
        from eva.l3_deliberation.llm_transcript import NoOpTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = NoOpTranscriptSink()
            sink.record(
                run_id="r1", individual_id="ind1", turn_index=0,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            # No transcript files should be created anywhere under temp_dir
            files = list(Path(temp_dir).rglob("*.json"))
            self.assertEqual(files, [], "NoOpSink must not write any files")


class FileBasedTranscriptSinkTests(unittest.TestCase):
    """raw mode: writes schema v1 json to {runtime_dir}/llm_transcripts/{llm_role}/turn-{idx:06d}.json."""

    def test_raw_mode_writes_schema_v1_json(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            ref = sink.record(
                run_id="r1", individual_id="ind1", turn_index=42,
                llm_role="dlPFC", scenario="crafter",
                model="deepseek-v4-pro",
                messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}],
                raw_response="raw text",
                parsed_response={"candidates": [{"action": "do"}]},
                parse_status="ok", errors=[],
                prompt_sections_present={"world_facts": True, "drive_ontology": False},
            )
            expected = Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000042.json"
            self.assertTrue(expected.exists(), f"Expected file at {expected}")
            payload = json.loads(expected.read_text())
            # PR-Β' schema bump v1 → v1.1 (v1 superset, plan §5.5b).
            self.assertEqual(payload["schema_version"], "llm_transcript_v1.2")
            self.assertEqual(payload["run_id"], "r1")
            self.assertEqual(payload["individual_id"], "ind1")
            self.assertEqual(payload["turn_index"], 42)
            self.assertEqual(payload["llm_role"], "dlPFC")
            self.assertEqual(payload["scenario"], "crafter")
            self.assertEqual(payload["model"], "deepseek-v4-pro")
            self.assertEqual(payload["raw_response"], "raw text")
            self.assertEqual(payload["parsed_response"], {"candidates": [{"action": "do"}]})
            self.assertEqual(payload["parse_status"], "ok")
            self.assertEqual(payload["errors"], [])
            self.assertEqual(payload["prompt_sections_present"],
                             {"world_facts": True, "drive_ontology": False})
            self.assertIn("timestamp", payload)
            self.assertIsNotNone(ref, "Sink must return ref string on success")

    def test_raw_mode_ref_is_relative_path(self) -> None:
        """Returned ref should be useful as anchor_domain_ref/dlpfc_proposal_ref — relative path."""
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            ref = sink.record(
                run_id="r1", individual_id="ind1", turn_index=7,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            self.assertEqual(ref, "llm_transcripts/dlPFC/turn-000007.json")

    def test_write_error_swallowed_returns_none_does_not_raise(self) -> None:
        """Red line R3: transcript write failure must NOT break the deliberation."""
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        # Construct against a path that cannot be created (a regular file used as parent).
        with tempfile.TemporaryDirectory() as temp_dir:
            blocking_file = Path(temp_dir) / "blocker"
            blocking_file.write_text("not a dir")
            # Use the blocking file path as runtime_dir → cannot mkdir under it.
            sink = FileBasedTranscriptSink(runtime_dir=str(blocking_file), mode="raw")
            # Must not raise; must return None to signal failure.
            ref = sink.record(
                run_id="r1", individual_id="ind1", turn_index=0,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[], raw_response="", parsed_response=None,
                parse_status="ok", errors=[], prompt_sections_present={},
            )
            self.assertIsNone(ref)

    def test_parse_error_status_persisted(self) -> None:
        """Schema must record parse_status and errors for downstream debugging."""
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            sink.record(
                run_id="r1", individual_id="ind1", turn_index=3,
                llm_role="dlPFC", scenario="crafter", model="m",
                messages=[{"role": "user", "content": "x"}],
                raw_response="not valid json",
                parsed_response=None,
                parse_status="parse_error",
                errors=["json.decoder.JSONDecodeError: Expecting value"],
                prompt_sections_present={"state_packet": True},
            )
            payload = json.loads((Path(temp_dir) / "llm_transcripts" / "dlPFC" / "turn-000003.json").read_text())
            self.assertEqual(payload["parse_status"], "parse_error")
            self.assertEqual(payload["errors"], ["json.decoder.JSONDecodeError: Expecting value"])
            self.assertIsNone(payload["parsed_response"])


class TranscriptSinkFactoryTests(unittest.TestCase):
    """build_transcript_sink_from_env: env-driven mode selection."""

    def test_env_unset_returns_noop_sink(self) -> None:
        from eva.l3_deliberation.llm_transcript import build_transcript_sink_from_env, NoOpTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("EVA_LLM_TRANSCRIPT", None)
                sink = build_transcript_sink_from_env(temp_dir)
                self.assertIsInstance(sink, NoOpTranscriptSink)

    def test_env_off_returns_noop_sink(self) -> None:
        from eva.l3_deliberation.llm_transcript import build_transcript_sink_from_env, NoOpTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "off"}):
                sink = build_transcript_sink_from_env(temp_dir)
                self.assertIsInstance(sink, NoOpTranscriptSink)

    def test_env_raw_returns_file_based_sink(self) -> None:
        from eva.l3_deliberation.llm_transcript import build_transcript_sink_from_env, FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "raw"}):
                sink = build_transcript_sink_from_env(temp_dir)
                self.assertIsInstance(sink, FileBasedTranscriptSink)

    def test_env_redacted_returns_file_based_sink(self) -> None:
        from eva.l3_deliberation.llm_transcript import build_transcript_sink_from_env, FileBasedTranscriptSink
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "redacted"}):
                sink = build_transcript_sink_from_env(temp_dir)
                self.assertIsInstance(sink, FileBasedTranscriptSink)


class TranscriptSinkProtocolTests(unittest.TestCase):
    """Both sinks satisfy the LLMTranscriptSink Protocol surface."""

    def test_both_implementations_have_record_method(self) -> None:
        from eva.l3_deliberation.llm_transcript import NoOpTranscriptSink, FileBasedTranscriptSink
        for cls in (NoOpTranscriptSink, lambda: FileBasedTranscriptSink(runtime_dir="/tmp", mode="raw")):
            sink = cls() if cls is NoOpTranscriptSink else cls()
            self.assertTrue(callable(getattr(sink, "record", None)))


if __name__ == "__main__":
    unittest.main()
