"""PR-Γ §6.2/§6.3: OFC assessment → transcript + mediator ofc_assessment_ref.

After PR-Γ, ``run_deliberation``:
1. Accepts optional ``ofc_transcript_sink`` + ``ofc_identity_provider``.
2. After ``assess_candidates``, records an OFC_classical transcript with
   ``llm_role="OFC_classical"``, ``model="drive_weighted_formula_v1"``,
   ``messages=[]``, ``raw_response=""``, ``parsed_response={"assessments": [...]}``,
   ``prompt_sections_present={drive_levels, drive_impact_schema, candidates}``.
3. Threads the returned ref into ``decide_release`` so the minted
   ``ReleaseToken.ofc_assessment_ref`` is populated (no longer None).

Red lines:
- ofc_transcript_sink=None → no OFC recording (Linux byte-compat)
- Sink failure must NOT propagate (R3 — same swallow contract as dlPFC)
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from eva.l3_deliberation.contracts import Candidate, build_deliberation_input
from eva.l3_deliberation.runtime import run_deliberation
from scenarios.crafter import activate_crafter_scenario


def _di() -> object:
    return build_deliberation_input(
        {"signals": [], "summary": {"signal_count": 0, "status_signal_count": 0}},
        {
            "top_drive": "acquisition",
            "drive_levels": {
                "acquisition": 0.8, "metabolic": 0.5, "safety": 0.4,
                "recovery": 0.3, "capability": 0.6, "exploration": 0.1,
            },
            "drive_trends": {"acquisition": "stable"},
        },
        {
            "instance_valid": True, "turn_allowed": True,
            "critical_blocked": False, "conservative_mode": False,
            "life_state": "STABLE",
        },
    )


class _CapturingSink:
    def __init__(self, *, ref: str = "captured/turn-0.json") -> None:
        self.calls: list[dict] = []
        self._ref = ref

    def record(self, **kwargs) -> str | None:
        self.calls.append(kwargs)
        return self._ref


class OfcSinkOptionalLinuxCompatTests(unittest.TestCase):
    """ofc_transcript_sink=None must not change run_deliberation semantics."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 29, tzinfo=timezone.utc)

    def test_no_sink_no_ofc_recording(self) -> None:
        di = _di()
        # No ofc_transcript_sink → produced audit and release_decision should be
        # unchanged compared to before PR-Γ.
        audit, _ = run_deliberation(self.now, di)
        # Token (if any) has ofc_assessment_ref None when no sink.
        if audit.release_token is not None:
            self.assertIsNone(audit.release_token.ofc_assessment_ref)


class OfcTranscriptRecordingTests(unittest.TestCase):
    """When sink is provided, OFC assessment is recorded with the expected schema."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 29, tzinfo=timezone.utc)

    def test_sink_receives_ofc_classical_record_with_canonical_fields(self) -> None:
        sink = _CapturingSink()
        di = _di()
        run_deliberation(
            self.now, di,
            ofc_transcript_sink=sink,
            ofc_identity_provider=lambda: {"run_id": "rid", "individual_id": "iid", "turn_index": 9},
        )
        self.assertEqual(len(sink.calls), 1, "OFC sink must be called once per run_deliberation")
        call = sink.calls[0]
        self.assertEqual(call["llm_role"], "OFC_classical")
        self.assertEqual(call["model"], "drive_weighted_formula_v1")
        self.assertEqual(call["messages"], [])
        self.assertEqual(call["raw_response"], "")
        self.assertEqual(call["parse_status"], "ok")
        self.assertEqual(call["errors"], [])
        self.assertEqual(call["run_id"], "rid")
        self.assertEqual(call["individual_id"], "iid")
        self.assertEqual(call["turn_index"], 9)
        # parsed_response contains assessments
        parsed = call["parsed_response"]
        self.assertIn("assessments", parsed)
        self.assertGreaterEqual(len(parsed["assessments"]), 1)
        # Each item carries score_decomposition + disposition
        for item in parsed["assessments"]:
            self.assertIn("candidate_id", item)
            self.assertIn("score_decomposition", item)
            self.assertIn("disposition", item)
        # prompt_sections_present uses OFC canonical keys
        sections = call["prompt_sections_present"]
        self.assertTrue(sections.get("drive_levels"))
        self.assertTrue(sections.get("drive_impact_schema"))
        self.assertTrue(sections.get("candidates"))

    def test_release_token_ofc_assessment_ref_filled_from_sink_returned_ref(self) -> None:
        sink = _CapturingSink(ref="llm_transcripts/OFC_classical/turn-000009.json")
        di = _di()
        audit, _ = run_deliberation(
            self.now, di,
            ofc_transcript_sink=sink,
            ofc_identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 9},
        )
        if audit.release_token is not None:
            self.assertEqual(
                audit.release_token.ofc_assessment_ref,
                "llm_transcripts/OFC_classical/turn-000009.json",
            )


class OfcSinkFailureSwallowedTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 29, tzinfo=timezone.utc)

    def test_sink_record_failure_does_not_break_run_deliberation(self) -> None:
        """R3: sink raising must NOT propagate; release_decision still produced."""

        class _FailingSink:
            def record(self, **kwargs):
                raise IOError("disk full")

        di = _di()
        # Should not raise.
        try:
            audit, _ = run_deliberation(
                self.now, di,
                ofc_transcript_sink=_FailingSink(),
                ofc_identity_provider=lambda: {"run_id": "r", "individual_id": "i", "turn_index": 0},
            )
        except Exception as exc:
            self.fail(f"OFC sink failure must not propagate; got {type(exc).__name__}: {exc}")
        # Token must still exist (chain not broken).
        self.assertIsNotNone(audit.release_decision)


class OfcTranscriptE2EFileWriteTests(unittest.TestCase):
    """E2E: with FileBasedTranscriptSink, OFC transcript file appears under
    llm_transcripts/OFC_classical/turn-N.json with the v1.1 schema."""

    def setUp(self) -> None:
        activate_crafter_scenario()
        self.now = datetime(2026, 5, 29, tzinfo=timezone.utc)

    def test_file_based_sink_writes_ofc_classical_turn_file(self) -> None:
        from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink

        with tempfile.TemporaryDirectory() as temp_dir:
            sink = FileBasedTranscriptSink(runtime_dir=temp_dir, mode="raw")
            di = _di()
            run_deliberation(
                self.now, di,
                ofc_transcript_sink=sink,
                ofc_identity_provider=lambda: {"run_id": "rid", "individual_id": "iid", "turn_index": 11},
            )
            expected = Path(temp_dir) / "llm_transcripts" / "OFC_classical" / "turn-000011.json"
            self.assertTrue(expected.exists(), f"OFC transcript missing at {expected}")
            payload = json.loads(expected.read_text())
            self.assertEqual(payload["schema_version"], "llm_transcript_v1.1")
            self.assertEqual(payload["llm_role"], "OFC_classical")
            self.assertEqual(payload["model"], "drive_weighted_formula_v1")
            self.assertIn("assessments", payload["parsed_response"])


if __name__ == "__main__":
    unittest.main()
