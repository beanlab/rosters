"""
type: workflow
description: "Judge code with Markdown instructions and combine the results."
usage: "CODE_PATH INSTRUCTIONS_DIR [--output OUTPUT] [--model MODEL]"
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from myteam import report_workflow_result, run_agent


def judge(code: Path, instructions_file: Path, model: str | None) -> dict:
    instructions = instructions_file.read_text(encoding="utf-8")
    prompt = f"""Review the code at {code} using these instructions:

---
{instructions}
---

Inspect the code yourself. Do not modify it. Give a score from 0 to 10 and a
Markdown bullet list of concrete evidence. Include file and line references
when possible. Judge only these instructions, not general code quality.
"""
    result = run_agent(
        prompt=prompt,
        output={
            "evidence": "A Markdown bullet list of concrete evidence.",
            "score": "An integer from 0 to 10.",
        },
        session_name=f"Judge: {instructions_file.stem}",
        model=model,
        interactive=False,
        prompt_source_path=instructions_file,
    )
    if result.output is None:
        raise RuntimeError(f"Agent returned no result for {instructions_file.name}")
    return result.output


def make_report(code: Path, results: list[tuple[Path, dict]]) -> str:
    scores = [int(result["score"]) for _, result in results]
    lines = ["# Code Quality Report", "", f"Code: `{code}`", "",
             f"Overall score: **{sum(scores) / len(scores):.1f}/10**"]
    for (instructions_file, result), score in zip(results, scores):
        lines += ["", f"## {instructions_file.stem.replace('-', ' ').title()}", "",
                  f"Score: **{score}/10**", "", str(result["evidence"])]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Simple code-quality prototype")
    parser.add_argument("code", type=Path)
    parser.add_argument("instructions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", help="Model to use for each evaluation")
    args = parser.parse_args()

    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output = Path(f"{args.code.name}-code-quality-report-{timestamp}.md")

    if not args.code.exists():
        parser.error(f"Code path does not exist: {args.code}")
    instruction_files = sorted(args.instructions.glob("*.md"))
    if not instruction_files:
        parser.error(f"No Markdown instructions found in: {args.instructions}")

    results = []
    for instructions_file in instruction_files:
        results.append((instructions_file, judge(args.code.resolve(), instructions_file, args.model)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_report(args.code.resolve(), results), encoding="utf-8")
    report_workflow_result(f"Report written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
