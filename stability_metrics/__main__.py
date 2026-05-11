"""CLI entrypoint for architecture-neutral stability metrics."""

from __future__ import annotations

import argparse
from pathlib import Path

from .metrics import write_stability_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute a stability profile from runtime trace files")
    subparsers = parser.add_subparsers(dest="command", required=True)
    calculate = subparsers.add_parser("calculate")
    calculate.add_argument("runtime_dir")
    calculate.add_argument("--output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "calculate":
        output_path = write_stability_profile(args.runtime_dir, output_path=args.output)
        print(f"wrote_stability_profile={Path(output_path)}")


if __name__ == "__main__":
    main()
