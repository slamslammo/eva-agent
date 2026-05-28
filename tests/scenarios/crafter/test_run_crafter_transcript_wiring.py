"""PR-Α: ``_build_candidate_producer`` wires transcript_sink from env.

Ensures production wiring picks up ``EVA_LLM_TRANSCRIPT`` automatically when
building the live CrafterLLMActionProducer.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from eva.kernel import build_runtime_config
from eva.kernel.config import RuntimeConfig
from eva.l3_deliberation.llm_transcript import FileBasedTranscriptSink, NoOpTranscriptSink
from scenarios.crafter import activate_crafter_scenario


def _live_llm_config(temp_dir: str) -> RuntimeConfig:
    return build_runtime_config(
        temp_dir,
        working_memory_backend="llm_assisted",
        working_memory_model_client_mode="live",
    )


class _FakeSession:
    latest_agent_observation: dict = {}


class BuildCandidateProducerSinkWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        activate_crafter_scenario()

    def test_env_raw_wires_file_based_sink(self) -> None:
        from runners.run_crafter import _build_candidate_producer

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _live_llm_config(temp_dir)
            # Mock build_live_chat_fn to return a stub (avoids needing real env keys).
            with patch("runners.run_crafter.build_live_chat_fn", return_value=lambda m: "{}"):
                with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "raw"}):
                    producer = _build_candidate_producer(config, _FakeSession())
            self.assertIsNotNone(producer)
            self.assertIsInstance(producer._sink, FileBasedTranscriptSink)

    def test_env_off_wires_noop_sink(self) -> None:
        from runners.run_crafter import _build_candidate_producer

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _live_llm_config(temp_dir)
            with patch("runners.run_crafter.build_live_chat_fn", return_value=lambda m: "{}"):
                with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "off"}):
                    producer = _build_candidate_producer(config, _FakeSession())
            self.assertIsNotNone(producer)
            self.assertIsInstance(producer._sink, NoOpTranscriptSink)

    def test_chat_fn_none_returns_none_producer(self) -> None:
        """No live chat_fn → no producer (unchanged behavior)."""
        from runners.run_crafter import _build_candidate_producer

        with tempfile.TemporaryDirectory() as temp_dir:
            config = _live_llm_config(temp_dir)
            with patch("runners.run_crafter.build_live_chat_fn", return_value=None):
                with patch.dict(os.environ, {"EVA_LLM_TRANSCRIPT": "raw"}):
                    producer = _build_candidate_producer(config, _FakeSession())
            self.assertIsNone(producer)


if __name__ == "__main__":
    unittest.main()
