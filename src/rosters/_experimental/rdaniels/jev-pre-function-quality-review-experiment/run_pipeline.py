#!/usr/bin/env python3
"""Run the repository quality pipeline for one or more Git snapshots."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PARSER = SCRIPT_DIR / "1-parse-repo" / "function_index.py"
REVIEWER = SCRIPT_DIR / "2-set-up-and-call-jev" / "review_functions.py"
SCORER = SCRIPT_DIR / "3-calculate-score" / "score_reviews.py"
REPORTER = SCRIPT_DIR / "4-display-results" / "generate_report.py"


@dataclass(frozen=True)
class Snapshot:
    name: str
    parsed_file: Path
    estimated_tokens: int
    estimated_cost: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run parsing, Jev review, scoring, and reporting for Git snapshots."
    )
    parser.add_argument("--repo", type=Path, required=True, help="local Git repository to analyze")
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="directory for all pipeline results"
    )
    parser.add_argument(
        "--interval",
        choices=("weekly", "monthly", "bimonthly"),
        default="monthly",
        help="time between snapshots (default: monthly)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="number of snapshots, including the current one (default: 1)",
    )
    parser.add_argument("--ref", default="HEAD", help="local branch or Git ref (default: HEAD)")
    return parser.parse_args()


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def estimate(parsed_file: Path) -> tuple[int, float]:
    result = run(
        [sys.executable, str(REVIEWER), "--input", str(parsed_file), "--estimate-only"],
        capture=True,
    )
    tokens_match = re.search(r"Estimated input tokens:\s*([\d,]+)", result.stdout)
    cost_match = re.search(r"Estimated cost:\s*\$([\d.]+)", result.stdout)
    if tokens_match is None or cost_match is None:
        raise RuntimeError(f"Could not read the cost estimate for {parsed_file}")
    return int(tokens_match.group(1).replace(",", "")), float(cost_match.group(1))


def prepare_snapshots(repo: Path, output_dir: Path, interval: str, count: int, ref: str) -> list[Snapshot]:
    with tempfile.TemporaryDirectory(prefix="quality-pipeline-") as temporary_directory:
        parsed_directory = Path(temporary_directory)
        result = run(
            [
                sys.executable,
                str(PARSER),
                str(repo),
                "--ref",
                ref,
                "--interval",
                interval,
                "--count",
                str(count),
                "--output-dir",
                str(parsed_directory),
            ],
            capture=True,
        )
        parsed_files = [Path(line) for line in result.stdout.splitlines() if line.strip()]
        snapshots: list[Snapshot] = []
        for source_file in parsed_files:
            metadata = json.loads(source_file.read_text(encoding="utf-8"))
            git = metadata["git"]
            timestamp = datetime.fromisoformat(git["cutoff"]).strftime("%Y-%m-%dT%H%M%S%z")
            snapshot_name = f"{timestamp}-{git['commit'][:12]}"
            snapshot_directory = output_dir / snapshot_name
            snapshot_directory.mkdir(parents=True, exist_ok=True)
            parsed_file = snapshot_directory / "parsed.json"
            shutil.copy2(source_file, parsed_file)
            estimated_tokens, estimated_cost = estimate(parsed_file)
            snapshots.append(
                Snapshot(snapshot_name, parsed_file, estimated_tokens, estimated_cost)
            )
        return snapshots


def approve_cost(snapshots: list[Snapshot]) -> bool:
    print("\nJev cost estimate for the complete run (no Jev calls made)")
    for snapshot in snapshots:
        print(
            f"  {snapshot.name}: {snapshot.estimated_tokens:,} input tokens, "
            f"${snapshot.estimated_cost:.8f}"
        )
    total_tokens = sum(snapshot.estimated_tokens for snapshot in snapshots)
    total_cost = sum(snapshot.estimated_cost for snapshot in snapshots)
    print(f"  TOTAL: {total_tokens:,} input tokens, ${total_cost:.8f}")
    if not sys.stdin.isatty():
        print("Cost approval requires an interactive terminal.", file=sys.stderr)
        return False
    return input("Proceed with all Jev calls? [y/N] ").strip().lower() in {"y", "yes"}


def run_snapshot(snapshot: Snapshot) -> Path:
    directory = snapshot.parsed_file.parent
    review_file = directory / "function-review.yaml"
    score_file = directory / "scores.yaml"
    report_file = directory / "quality-report.html"

    print(f"\n=== {snapshot.name} ===")
    run(
        [
            sys.executable,
            str(REVIEWER),
            "--input",
            str(snapshot.parsed_file),
            "--output",
            str(review_file),
            "--yes",
        ]
    )
    run(
        [
            sys.executable,
            str(SCORER),
            str(review_file),
            "--metadata",
            str(snapshot.parsed_file),
            "--output",
            str(score_file),
        ]
    )
    run(
        [
            sys.executable,
            str(REPORTER),
            str(score_file),
            "--title",
            f"Code quality atlas: {snapshot.name}",
            "--output",
            str(report_file),
        ]
    )
    print(f"Completed: {report_file.resolve()}")
    return score_file


def run_combined_report(snapshots: list[Snapshot], score_files: list[Path], output_dir: Path) -> Path:
    report_file = output_dir / "quality-report.html"
    named_inputs = [
        f"{snapshot.name}={score_file}"
        for snapshot, score_file in zip(snapshots, score_files)
    ]
    run(
        [
            sys.executable,
            str(REPORTER),
            *named_inputs,
            "--title",
            "Repository quality over time",
            "--output",
            str(report_file),
        ]
    )
    return report_file


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise ValueError("--count must be at least 1")

    repo = args.repo.resolve()
    output_dir = args.output_dir.resolve()
    if not repo.is_dir():
        raise ValueError(f"repository is not a directory: {repo}")
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshots = prepare_snapshots(repo, output_dir, args.interval, args.count, args.ref)
    if not approve_cost(snapshots):
        print("Pipeline cancelled. Parsed snapshots were kept; no Jev calls were made.")
        return 2

    score_files = [run_snapshot(snapshot) for snapshot in snapshots]
    combined_report = run_combined_report(snapshots, score_files, output_dir)

    print(f"\nAll {len(snapshots)} snapshot(s) completed in {output_dir}")
    print(f"Combined report: {combined_report.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr.rstrip(), file=sys.stderr)
        print(f"Pipeline command failed with exit code {error.returncode}.", file=sys.stderr)
        raise SystemExit(error.returncode) from error
    except (OSError, ValueError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
