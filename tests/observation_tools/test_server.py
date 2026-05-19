"""HTTP server 集成测试。

启动真实 server 实例到随机端口（127.0.0.1:0），用 urllib 触发各端点。
不依赖第三方测试客户端。
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from observation_tools.server import build_server


class ServerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.runtime_dir = Path(self._temp.name)
        # 端口 0 让系统分配未占用端口，避免并发测试冲突
        self.server = build_server(self.runtime_dir, host="127.0.0.1", port=0)
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self._temp.cleanup()

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _fetch_json(self, path: str) -> tuple[int, dict]:
        url = f"http://{self.host}:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _expect_status(self, path: str, expected: int) -> None:
        url = f"http://{self.host}:{self.port}{path}"
        try:
            urllib.request.urlopen(url, timeout=2)
            self.fail(f"expected HTTPError {expected}")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, expected)

    # ------------------------------------------------------------------
    # 测试
    # ------------------------------------------------------------------

    def test_run_info_endpoint_empty_runtime(self) -> None:
        status, body = self._fetch_json("/api/run_info")
        self.assertEqual(status, 200)
        self.assertIn("runtime_dir", body)
        self.assertIn("counts", body)
        # 空 runtime_dir：所有 counts 都是 0
        for value in body["counts"].values():
            self.assertEqual(value, 0)

    def test_turns_endpoint_empty(self) -> None:
        status, body = self._fetch_json("/api/turns")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"turns": []})

    def test_timeline_endpoint_empty(self) -> None:
        status, body = self._fetch_json("/api/timeline")
        self.assertEqual(status, 200)
        self.assertEqual(body["n_turns"], 0)
        self.assertEqual(body["life_state"], [])

    def test_unknown_path_returns_404(self) -> None:
        self._expect_status("/nonexistent", 404)

    def test_single_turn_out_of_range_returns_404(self) -> None:
        self._expect_status("/api/turn/0", 404)  # 空 runtime，0 越界

    def test_single_turn_invalid_index_returns_400(self) -> None:
        self._expect_status("/api/turn/abc", 400)

    def test_static_missing_file_returns_404(self) -> None:
        self._expect_status("/static/does-not-exist.css", 404)

    def test_static_path_traversal_blocked(self) -> None:
        # 任何 .. 段都不应该把请求带出 STATIC_DIR
        self._expect_status("/static/../../etc/passwd", 404)


class ServerWithDataTests(unittest.TestCase):
    """用真实合成数据测试 server 端到端 wiring。"""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.runtime_dir = Path(self._temp.name)
        # 写两条 deliberation_audit + 两条 response_history
        with (self.runtime_dir / "deliberation_audit.jsonl").open("w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "recorded_at": "2026-05-19T17:00:00Z",
                        "deliberation_input": {
                            "drive_broadcast": {
                                "top_drive": "acquisition",
                                "drive_levels": {"metabolic": 0.1, "acquisition": 0.5},
                            },
                        },
                        "release_decision": {"outcome": "released"},
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "recorded_at": "2026-05-19T17:00:01Z",
                        "deliberation_input": {
                            "drive_broadcast": {
                                "top_drive": "acquisition",
                                "drive_levels": {"metabolic": 0.2, "acquisition": 0.6},
                            },
                        },
                        "release_decision": {"outcome": "released"},
                    }
                )
                + "\n"
            )
        with (self.runtime_dir / "response_history.jsonl").open("w", encoding="utf-8") as f:
            f.write(json.dumps({"recorded_at": "2026-05-19T17:00:00Z", "selected_action": "move_left", "life_state": "STABLE"}) + "\n")
            f.write(json.dumps({"recorded_at": "2026-05-19T17:00:01Z", "selected_action": "move_up", "life_state": "STABLE"}) + "\n")

        self.server = build_server(self.runtime_dir, host="127.0.0.1", port=0)
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self._temp.cleanup()

    def _fetch_json(self, path: str) -> dict:
        url = f"http://{self.host}:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=2) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_turns_endpoint_returns_aligned_chains(self) -> None:
        body = self._fetch_json("/api/turns")
        self.assertEqual(len(body["turns"]), 2)
        self.assertEqual(body["turns"][0]["turn_idx"], 0)
        self.assertEqual(body["turns"][0]["response"]["selected_action"], "move_left")
        self.assertEqual(body["turns"][1]["response"]["selected_action"], "move_up")

    def test_single_turn_endpoint(self) -> None:
        body = self._fetch_json("/api/turn/1")
        self.assertEqual(body["turn_idx"], 1)
        self.assertEqual(body["response"]["selected_action"], "move_up")

    def test_timeline_endpoint_aggregates_data(self) -> None:
        body = self._fetch_json("/api/timeline")
        self.assertEqual(body["n_turns"], 2)
        self.assertEqual(body["life_state"], ["STABLE", "STABLE"])
        self.assertEqual(body["drive_levels"]["acquisition"], [0.5, 0.6])
        self.assertEqual(body["drive_levels"]["metabolic"], [0.1, 0.2])

    def test_run_info_endpoint_reports_counts(self) -> None:
        body = self._fetch_json("/api/run_info")
        self.assertEqual(body["counts"]["deliberation_audit"], 2)
        self.assertEqual(body["counts"]["response_history"], 2)


if __name__ == "__main__":
    unittest.main()
