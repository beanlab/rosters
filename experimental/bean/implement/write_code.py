"""
type: workflow
description: delegate to this workflow all writing of new code. 
usage: myteam start .../write_code.py "thorough description of what code should be written"
"""

from __future__ import annotations

import sys

from myteam import run_agent

AGENT = 'pi'


def setup_project(instructions: str) -> str:
    result = run_agent(
        agent=AGENT,
        prompt=(
            "Do the tasks I give you one-at-a-time.\n"
            "<overall-goal>"
            f"{instructions}\n</overall-goal>\n"
            "\nYour first task is to setup the project.\n"
            "Do not implement any code, just get the project ready.\n"
            "Install dependencies, setup needed folders and entry-point files, etc.\n"
            "When finished with this step, report the result with `myteam result`."
        ),
        output={
            'setup_complete': '(bool) true'
        }
    )
    return result.session_id


def stub_public_api(session_id: str) -> list[str]:
    result = run_agent(
        agent=AGENT,
        session_id=session_id,
        prompt=(
            "Now please stub out the public API."
            "Return a list of all the functions, classes, or UI components you created via `myteam result`."
        ),
        output={
            'new_work': ['list of names of elements you stubbed out']
        }
    )
    return result.output['new_work']


def implement(next_item: str, session_id: str):
    result = run_agent(
        agent=AGENT,
        session_id=session_id,
        prompt=(
            f"Now implement just {next_item}.\n"
            "Use decomposition. The code you write should be obvious and read like pseudocode.\n"
            "If the current assignment is simple enough to implement directly, do that,\n"
            "but otherwise break it down."
            "Stub out all functions, classes, or UI components your implementation delegates to.\n"
            "Return a list of these elements via `myteam result`."
        ),
        output={
            'new_work': ['list of names of elements you stubbed out']
        }
    )
    return result.output['new_work']


def main(instructions: str) -> None:
    session_id = setup_project(instructions)
    open_work = stub_public_api(session_id)
    while open_work:
        next_item = open_work.pop()
        more_work = implement(next_item, session_id)
        open_work.extend(more_work)
        # TODO - add review, reconcile open work
        # Fork current session for review


if __name__ == "__main__":
    main(sys.argv[1])
