"""CLI entrypoint for inherited-prior distillation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bundle_writer import write_distilled_prior_bundle
from .pipeline import DEFAULT_OUTPUT_FILE, distill_runtime_dirs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Distill same-scenario inherited priors from runtime traces")
    subparsers = parser.add_subparsers(dest="command", required=True)
    distill = subparsers.add_parser("distill")
    distill.add_argument("runtime_dirs", nargs="+")
    distill.add_argument("--output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "distill":
        payload = distill_runtime_dirs(args.runtime_dirs)
        output_path = args.output or str(Path(args.runtime_dirs[0]).expanduser().resolve() / DEFAULT_OUTPUT_FILE)
        written = write_distilled_prior_bundle(payload, output_path)
        print(f"wrote_distilled_prior_bundle={written}")


if __name__ == "__main__":
    main()
