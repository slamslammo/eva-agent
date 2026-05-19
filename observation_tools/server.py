"""HTTP 服务端 —— 用 stdlib ``http.server.ThreadingHTTPServer``。

不引入任何第三方 Web 框架。路由集中在 ``ObservationToolsHandler.do_GET``。

API 端点：

| Path | 作用 |
|---|---|
| ``GET /`` | 返回 ``static/index.html`` |
| ``GET /static/<file>`` | 返回静态资源（CSS / JS / JSON） |
| ``GET /api/run_info`` | 运行时元信息 + 各 JSONL 文件行数 |
| ``GET /api/turns`` | 全部 ChainView 列表（V0 全量返回） |
| ``GET /api/turn/<idx>`` | 单个 turn 的 ChainView |
| ``GET /api/timeline`` | 顶部迷你时间轴 + drive 折线 |

服务启动时 ``runtime_dir`` 注入到 ``server.runtime_dir``，所有 handler 共享。
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .core.chain_builder import (
    build_chains,
    build_timeline_summary,
    runtime_counts,
)


# 静态文件根目录 —— 与本模块同 package 的 ``core/static/``。
STATIC_DIR = Path(__file__).parent / "core" / "static"


_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class ObservationToolsHandler(BaseHTTPRequestHandler):
    """请求处理。``server.runtime_dir`` 由启动时注入。"""

    # 默认 BaseHTTPRequestHandler 会把每个请求 print 到 stderr —— 太吵。
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:  # noqa: N802  (BaseHTTPRequestHandler 接口名)
        path = urlparse(self.path).path
        try:
            if path == "/":
                self._serve_static("index.html")
            elif path.startswith("/static/"):
                self._serve_static(path[len("/static/"):])
            elif path == "/api/run_info":
                self._serve_run_info()
            elif path == "/api/turns":
                self._serve_turns()
            elif path.startswith("/api/turn/"):
                self._serve_single_turn(path[len("/api/turn/"):])
            elif path == "/api/timeline":
                self._serve_timeline()
            else:
                self._send_text(404, "Not Found")
        except Exception as exc:  # 网络服务的最后一道防线 —— 任何错误返回 500，不让进程崩
            self._send_json(500, {"error": str(exc)})

    # ------------------------------------------------------------------
    # 路由实现
    # ------------------------------------------------------------------

    def _serve_static(self, name: str) -> None:
        # 防止目录遍历：去掉 ``..`` 段、限制在 STATIC_DIR 内
        safe_name = name.replace("..", "").lstrip("/")
        if not safe_name:
            self._send_text(404, "Not Found")
            return
        path = STATIC_DIR / safe_name
        try:
            resolved = path.resolve()
            resolved.relative_to(STATIC_DIR.resolve())
        except (OSError, ValueError):
            self._send_text(404, "Not Found")
            return
        if not resolved.is_file():
            self._send_text(404, "Not Found")
            return
        content_type = _CONTENT_TYPES.get(resolved.suffix, "application/octet-stream")
        body = resolved.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_run_info(self) -> None:
        runtime_dir = Path(self.server.runtime_dir)  # type: ignore[attr-defined]
        counts = runtime_counts(runtime_dir)
        run_name = runtime_dir.parent.name or runtime_dir.name
        self._send_json(
            200,
            {
                "run_name": run_name,
                "runtime_dir": str(runtime_dir),
                "counts": counts,
            },
        )

    def _serve_turns(self) -> None:
        chains = build_chains(self.server.runtime_dir)  # type: ignore[attr-defined]
        self._send_json(200, {"turns": [c.to_dict() for c in chains]})

    def _serve_single_turn(self, idx_str: str) -> None:
        try:
            idx = int(idx_str)
        except ValueError:
            self._send_text(400, "invalid turn index")
            return
        chains = build_chains(self.server.runtime_dir)  # type: ignore[attr-defined]
        if 0 <= idx < len(chains):
            self._send_json(200, chains[idx].to_dict())
        else:
            self._send_text(404, "turn not found")

    def _serve_timeline(self) -> None:
        summary = build_timeline_summary(self.server.runtime_dir)  # type: ignore[attr-defined]
        self._send_json(200, summary)

    # ------------------------------------------------------------------
    # 通用响应辅助
    # ------------------------------------------------------------------

    def _send_json(self, status: int, obj: Any) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(
    runtime_dir: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> ThreadingHTTPServer:
    """构建一个 server 实例（不启动循环；测试可用此 fixture）。"""

    server = ThreadingHTTPServer((host, port), ObservationToolsHandler)
    server.runtime_dir = str(runtime_dir)  # type: ignore[attr-defined]
    return server


def serve(
    runtime_dir: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    """启动 server 并阻塞循环（Ctrl-C 退出）。"""

    server = build_server(runtime_dir, host=host, port=port)
    print(f"observation_tools running at http://{host}:{port}")
    print(f"runtime_dir: {runtime_dir}")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.shutdown()
        server.server_close()
