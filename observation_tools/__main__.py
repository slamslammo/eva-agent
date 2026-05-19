"""``python -m observation_tools`` 入口。

最简 CLI：必填 ``--runtime-dir``，可选 ``--host`` / ``--port``。
默认绑定 ``127.0.0.1:8080`` —— 仅本机访问，不开放外网。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .server import serve


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="observation_tools",
        description="EVA observation_tools —— runtime 黑盒子查看器（V0）",
    )
    parser.add_argument(
        "--runtime-dir",
        required=True,
        help="EVA 运行时输出目录（含 deliberation_audit.jsonl 等 JSONL）",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="绑定地址，默认 127.0.0.1（仅本机）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP 端口，默认 8080",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    runtime_dir = Path(args.runtime_dir)
    if not runtime_dir.exists():
        raise SystemExit(f"runtime_dir 不存在: {runtime_dir}")
    if not runtime_dir.is_dir():
        raise SystemExit(f"runtime_dir 不是目录: {runtime_dir}")
    serve(runtime_dir, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
