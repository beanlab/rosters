"""
type: workflow
description: Guide a user through the changes on the currently checked-out pull-request branch.
usage: no arguments; the workflow investigates, prepares, and interactively presents the changes
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from myteam import report_workflow_result, run_agent

PROMPT_DIRECTORY = Path(__file__).parent / "code-walk-through"


def run_step(step_name, prompt_path: Path, output_schema, *, session_id: str | None, interactive: bool) -> Any:
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Missing workflow prompt: {prompt_path}")

    result = run_agent(
        prompt=prompt_path.read_text(encoding="utf-8"),
        prompt_source_path=prompt_path,
        session_name=step_name,
        agent="pi",
        interactive=interactive,
        session_id=session_id,
        output=output_schema,
    )
    if result.output is None:
        raise RuntimeError(f"Workflow step {step_name} ended without a result")
    if result.session_id is None:
        raise RuntimeError(f"Workflow step {step_name} did not return a session ID")
    return result


def main() -> None:
    investigation = run_step(
        'Investigate',
        PROMPT_DIRECTORY / "01-investigate.md",
        {
            "investigation": "Complete investigation in Markdown."
        },
        session_id=None, interactive=True
    )
    planning = run_step(
        'Plan',
        PROMPT_DIRECTORY / "02-plan.md",
        {
            "walkthrough_plan": "Complete walkthrough plan in Markdown."
        },
        session_id=investigation.session_id, interactive=True
    )
    walkthrough = run_step(
        'Walk Through',
        PROMPT_DIRECTORY / "03-walk-through.md",
        {"walkthrough": "Short summary of the completed interactive walkthrough."},
        session_id=planning.session_id, interactive=True
    )

    report_workflow_result(
        json.dumps(
            {
                "investigation": investigation.output,
                "walkthrough_plan": planning.output,
                "walkthrough": walkthrough.output,
            }
        )
    )


if __name__ == "__main__":
    main()
