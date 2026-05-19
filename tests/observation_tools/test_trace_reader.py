"""trace_reader 单元测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from observation_tools.core.trace_reader import read_jsonl, read_jsonl_count


class ReadJsonlTests(unittest.TestCase):
    def test_missing_file_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(read_jsonl(Path(temp_dir) / "no-such-file.jsonl"), [])

    def test_empty_file_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            self.assertEqual(read_jsonl(path), [])

    def test_three_valid_lines_parses_to_three_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "three.jsonl"
            path.write_text(
                '{"turn_idx":0,"label":"a"}\n'
                '{"turn_idx":1,"label":"b"}\n'
                '{"turn_idx":2,"label":"c"}\n',
                encoding="utf-8",
            )
            entries = read_jsonl(path)
            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[0]["label"], "a")
            self.assertEqual(entries[2]["turn_idx"], 2)

    def test_partial_last_line_is_skipped(self) -> None:
        # 运行时 append-only：末行可能未完整写入（无换行符 + 不闭合的 JSON）。
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "partial.jsonl"
            path.write_text(
                '{"turn_idx":0,"label":"a"}\n'
                '{"turn_idx":1,"label":"b"}\n'
                '{"turn_idx":2,"lab',  # 未闭合
                encoding="utf-8",
            )
            entries = read_jsonl(path)
            self.assertEqual(len(entries), 2)
            self.assertEqual([e["turn_idx"] for e in entries], [0, 1])

    def test_invalid_json_line_in_middle_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mixed.jsonl"
            path.write_text(
                '{"ok":1}\n'
                "not even json\n"
                '{"ok":2}\n',
                encoding="utf-8",
            )
            entries = read_jsonl(path)
            self.assertEqual(len(entries), 2)
            self.assertEqual([e["ok"] for e in entries], [1, 2])

    def test_non_dict_top_level_is_skipped(self) -> None:
        # 顶层是 list 或 number 的"合法 JSON"不算 ChainView 数据；跳过。
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mixed_types.jsonl"
            path.write_text(
                '{"ok":1}\n'
                "[1, 2, 3]\n"
                "42\n"
                '{"ok":2}\n',
                encoding="utf-8",
            )
            entries = read_jsonl(path)
            self.assertEqual([e["ok"] for e in entries], [1, 2])

    def test_blank_lines_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "blanks.jsonl"
            path.write_text(
                '{"ok":1}\n'
                "\n"
                "   \n"
                '{"ok":2}\n',
                encoding="utf-8",
            )
            self.assertEqual(len(read_jsonl(path)), 2)


class ReadJsonlCountTests(unittest.TestCase):
    def test_missing_file_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(read_jsonl_count(Path(temp_dir) / "absent.jsonl"), 0)

    def test_counts_non_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "lines.jsonl"
            path.write_text(
                "line1\n"
                "\n"
                "line2\n"
                "   \n"
                "line3",  # 末行无换行也算一行
                encoding="utf-8",
            )
            self.assertEqual(read_jsonl_count(path), 3)


if __name__ == "__main__":
    unittest.main()
