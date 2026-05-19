"""chain_builder 单元测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from observation_tools.core.chain_builder import (
    ChainView,
    DELIBERATION_AUDIT_FILE,
    HABIT_BIAS_FILE,
    LEARNING_OUTCOMES_FILE,
    LLM_ADVISORY_AUDIT_FILE,
    RESPONSE_HISTORY_FILE,
    build_chains,
    build_timeline_summary,
    runtime_counts,
)


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _synth_deliberation(idx: int, drives: dict[str, float] | None = None) -> dict:
    return {
        "recorded_at": f"2026-05-19T17:47:{30 + idx:02d}Z",
        "deliberation_input": {
            "signal_batch": {"signals": []},
            "drive_broadcast": {
                "top_drive": "acquisition",
                "drive_levels": drives or {"metabolic": 0.1 * idx, "safety": 0.0},
            },
            "working_memory_context": {},
        },
        "candidates": [],
        "assessments": [],
        "release_decision": {"outcome": "released"},
    }


def _synth_response(idx: int, life_state: str = "STABLE") -> dict:
    return {
        "recorded_at": f"2026-05-19T17:47:{30 + idx:02d}Z",
        "selected_action": f"action_{idx}",
        "life_state": life_state,
    }


def _synth_advisory(idx: int) -> dict:
    return {
        "recorded_at": f"2026-05-19T17:47:{30 + idx:02d}Z",
        "outcome": "advisory_attached",
        "model": "deepseek-v4-flash",
    }


class BuildChainsTests(unittest.TestCase):
    def test_empty_runtime_dir_yields_empty_chain_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(build_chains(temp_dir), [])

    def test_three_turns_aligned_one_to_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_jsonl(root / DELIBERATION_AUDIT_FILE, [_synth_deliberation(i) for i in range(3)])
            _write_jsonl(root / RESPONSE_HISTORY_FILE, [_synth_response(i) for i in range(3)])
            _write_jsonl(root / LLM_ADVISORY_AUDIT_FILE, [_synth_advisory(i) for i in range(3)])

            chains = build_chains(root)

            self.assertEqual(len(chains), 3)
            for i, chain in enumerate(chains):
                self.assertEqual(chain.turn_idx, i)
                self.assertIsNotNone(chain.deliberation)
                self.assertIsNotNone(chain.response)
                self.assertIsNotNone(chain.advisory)
                self.assertEqual(chain.response["selected_action"], f"action_{i}")

    def test_off_by_one_at_end_handled_gracefully(self) -> None:
        # 3 个 deliberation + 2 个 response —— 末 turn 缺 response（运行末尾常态）
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_jsonl(root / DELIBERATION_AUDIT_FILE, [_synth_deliberation(i) for i in range(3)])
            _write_jsonl(root / RESPONSE_HISTORY_FILE, [_synth_response(i) for i in range(2)])

            chains = build_chains(root)

            self.assertEqual(len(chains), 3)
            self.assertIsNotNone(chains[2].deliberation)
            self.assertIsNone(chains[2].response)

    def test_missing_llm_advisory_file_yields_none_advisory(self) -> None:
        # advisory 未启用（heuristic / inert mode）时 llm_advisory_audit.jsonl 不存在
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_jsonl(root / DELIBERATION_AUDIT_FILE, [_synth_deliberation(i) for i in range(2)])
            _write_jsonl(root / RESPONSE_HISTORY_FILE, [_synth_response(i) for i in range(2)])

            chains = build_chains(root)

            self.assertEqual(len(chains), 2)
            self.assertIsNone(chains[0].advisory)
            self.assertIsNone(chains[1].advisory)

    def test_chain_to_dict_round_trips(self) -> None:
        view = ChainView(
            turn_idx=5,
            recorded_at="2026-05-19T17:47:35Z",
            deliberation={"x": 1},
            response={"y": 2},
            advisory=None,
            outcome=None,
            habit=None,
        )
        data = view.to_dict()
        self.assertEqual(data["turn_idx"], 5)
        self.assertEqual(data["deliberation"], {"x": 1})
        self.assertIsNone(data["advisory"])


class BuildTimelineSummaryTests(unittest.TestCase):
    def test_empty_runtime_dir_yields_zero_turn_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = build_timeline_summary(temp_dir)
            self.assertEqual(summary["n_turns"], 0)
            self.assertEqual(summary["life_state"], [])
            self.assertEqual(summary["drive_levels"], {})

    def test_three_turns_emit_drive_series(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deliberations = [
                _synth_deliberation(0, {"metabolic": 0.1, "safety": 0.0}),
                _synth_deliberation(1, {"metabolic": 0.2, "safety": 0.0}),
                _synth_deliberation(2, {"metabolic": 0.3, "safety": 0.1}),
            ]
            _write_jsonl(root / DELIBERATION_AUDIT_FILE, deliberations)
            _write_jsonl(
                root / RESPONSE_HISTORY_FILE,
                [
                    _synth_response(0, "STABLE"),
                    _synth_response(1, "RECOVERING"),
                    _synth_response(2, "STABLE"),
                ],
            )

            summary = build_timeline_summary(root)
            self.assertEqual(summary["n_turns"], 3)
            self.assertEqual(summary["life_state"], ["STABLE", "RECOVERING", "STABLE"])
            self.assertEqual(summary["drive_levels"]["metabolic"], [0.1, 0.2, 0.3])
            self.assertEqual(summary["drive_levels"]["safety"], [0.0, 0.0, 0.1])

    def test_drive_appearing_late_is_padded_with_zeros(self) -> None:
        # turn 0 只有 metabolic；turn 1 又出现 exploration —— exploration 历史补 0
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            deliberations = [
                _synth_deliberation(0, {"metabolic": 0.1}),
                _synth_deliberation(1, {"metabolic": 0.2, "exploration": 0.5}),
            ]
            _write_jsonl(root / DELIBERATION_AUDIT_FILE, deliberations)
            _write_jsonl(root / RESPONSE_HISTORY_FILE, [_synth_response(0), _synth_response(1)])

            summary = build_timeline_summary(root)
            self.assertEqual(summary["drive_levels"]["metabolic"], [0.1, 0.2])
            self.assertEqual(summary["drive_levels"]["exploration"], [0.0, 0.5])


class RuntimeCountsTests(unittest.TestCase):
    def test_returns_zero_for_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            counts = runtime_counts(temp_dir)
            for value in counts.values():
                self.assertEqual(value, 0)

    def test_returns_actual_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_jsonl(root / DELIBERATION_AUDIT_FILE, [_synth_deliberation(i) for i in range(3)])
            _write_jsonl(root / RESPONSE_HISTORY_FILE, [_synth_response(i) for i in range(2)])
            counts = runtime_counts(root)
            self.assertEqual(counts["deliberation_audit"], 3)
            self.assertEqual(counts["response_history"], 2)
            self.assertEqual(counts["llm_advisory_audit"], 0)


if __name__ == "__main__":
    unittest.main()
