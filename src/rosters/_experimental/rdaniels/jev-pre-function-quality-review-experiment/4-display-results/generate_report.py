#!/usr/bin/env python3
"""Command-line entry point for the code-quality report generator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quality_report.generator import build_report
from quality_report.model import ScoreFileError, ScoreInput


def parse_input(value: str) -> ScoreInput:
    if "=" in value:
        name, raw_path = value.split("=", 1)
        if name and raw_path:
            return ScoreInput(Path(raw_path), name)
    return ScoreInput(Path(value))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one interactive HTML report from one or more scores.yaml files."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=parse_input,
        metavar="[NAME=]SCORES_YAML",
        help="score file, optionally prefixed with a display name",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("quality-report.html"),
        help="output HTML path (default: quality-report.html)",
    )
    parser.add_argument(
        "--title",
        default="Code quality atlas",
        help="title shown in the report",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build_report(args.inputs, args.output, args.title)
    except (ScoreFileError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"Generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
