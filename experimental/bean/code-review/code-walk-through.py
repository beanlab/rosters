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


def run_step(prompt_name: str, *, session_id: str | None, interactive: bool) -> Any:
    prompt_path = PROMPT_DIRECTORY / prompt_name
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Missing workflow prompt: {prompt_path}")

    result = run_agent(
        prompt=prompt_path.read_text(encoding="utf-8"),
        prompt_source_path=prompt_path,
        agent="pi",
        interactive=interactive,
        session_id=session_id,
        output={
            "investigation": "Complete investigation in Markdown."
        }
        if prompt_name == "01-investigate.md"
        else {
            "walkthrough_plan": "Complete walkthrough plan in Markdown."
        }
        if prompt_name == "02-plan.md"
        else {"walkthrough": "Short summary of the completed interactive walkthrough."},
    )
    if result.output is None:
        raise RuntimeError(f"Workflow step {prompt_name} ended without a result")
    if result.session_id is None:
        raise RuntimeError(f"Workflow step {prompt_name} did not return a session ID")
    return result


def main() -> None:
    investigation = run_step(
        "01-investigate.md", session_id=None, interactive=True
    )
    planning = run_step(
        "02-plan.md", session_id=investigation.session_id, interactive=True
    )
    walkthrough = run_step(
        "03-walk-through.md", session_id=planning.session_id, interactive=True
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
