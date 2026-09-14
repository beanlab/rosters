"""
type: workflow
description: This workflow implements the requested task.
usage: Pass a Markdown description of the task and all needed context as single positional arg.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path
from pprint import pformat
from textwrap import dedent
from typing import Any, Callable, TypeVar, TypedDict

from myteam import run_agent

if not hasattr(logging, "get_logger"):
    logging.get_logger = logging.getLogger  # type: ignore[attr-defined]

LOG_FILE = Path.cwd() / f"{datetime.now().strftime('%Y-%m-%d-%H-%M')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(lineno)d %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)

logger = logging.get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])

AGENT = 'pi'


def log_call(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        logger.debug(
            "calling %s args=%s kwargs=%s",
            func.__name__,
            pformat(args),
            pformat(kwargs),
            stacklevel=2,
        )
        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.exception("failed %s", func.__name__, stacklevel=2)
            raise
        logger.debug(
            "finished %s result=%s",
            func.__name__,
            pformat(result),
            stacklevel=2,
        )
        return result

    return wrapper  # type: ignore[return-value]


class TaskResult(TypedDict):
    summary_of_changes: str
    new_work: list[str]


TASK_OUTPUT = {
    'summary_of_changes': '(str) a description of how the task is implemented',
    'new_work': ['a list of functions and classes that now need to be implemented; '
                 'include the filename with each item']
}

PLAN_INSTRUCTIONS = dedent("""
    Each step in the plan must contain the specific task to be done AND the specific context needed
    for another agent to do the task correctly.
    
    The context should include all information another agent will need to do the task.
    This includes:
    - Vision of the project
    - The specific task to do
    - Relevant files
    - Purpose of the change and context of the change within the project
    - Any notes as needed to capture nuance about the task
    
    The context should NOT include extra information, including opinions about how to do the work.
    
    Each step should be described in Markdown with this format:
    
    ```markdown
    # Task
    A brief description of the task
    
    # Context
    A thorough articulation of the context needed.
    ```
""")

PLAN_OUTPUT = {
    'plan': ['list of Markdown strings, each describing a step in the plan']
}


HUMAN_REVIEW = dedent("""
    Before you report your result, please present your information to the user for review.
    **AFTER** the user approves, report using `myteam result`.
""")

# NOTE: the task always includes context

@log_call
def consider_task(task: str) -> bool:
    result = run_agent(
        agent=AGENT,
        prompt=dedent(f"""
        --- TASK ---
        {task}
        ------------
        
        You are part of a multi-agent workflow. 
        
        Your specific assignment is to determine 
        whether the task described above is simple enough to implement directly
        or whether it should be broken down further.
        
        YOU SHOULD NOT IMPLEMENT THE TASK. DO NOT MAKE CHANGES.
        
        Decision Guidance:
        
        We are trying to break down the problem into bite-sized pieces that give 
        the team time to review before more work is done. We are also trying to keep 
        the implementation focused on the task at hand by limiting scope in the individual steps.
        
        Code is written one function at a time in a top-down approach. 
        `main` is the first function written, but when it is written, dependencies are stubbed out
        and then implemented in turn.
        
        So, if the task is to implement a function or class, return true.
        
        Some tasks are not code tasks, such as project setup. Tasks that work best as automic 
        work, like a git commit involving the staging of separate files, should be treated as a single
        task. 
        
        Again: we're just trying to break things down to a bite-size level,
        but without creating unnecessary complexity. 
        
        Don't reinvent the wheel: if the task can be solved with a few shell commands, let's do it.
        Don't request that the task be dissected further.
    
        {HUMAN_REVIEW}
        """),
        output={
            'do_it': '(bool) true if simple enough for direct implementation, false if more complex than that.'
        }
    )
    return result.output['do_it']


@log_call
def implement(task: str) -> TaskResult:
    result = run_agent(
        agent=AGENT,
        prompt=dedent(f"""
        --- TASK ---
        {task}
        ------------
        
        You are part of a large multi-agent team. Your specific assignment is to
        implement the task described above. **Do only this task and nothing more.**
        
        If the task includes a recorded replay baseline, keep that baseline as the
        source of truth and do not change the expected sequence unless a later
        replay assertion fails.
        
        Keep the implementation simple. Do not add abstraction or complexity until it is needed.
        
        **Before you write code**, ask:
        - is there a built-in way to do the same thing? Use it.
        - is there a 3rd party dependency we already have that can do this? Use it.
        - is there a common, dependable 3rd party package that does this well? Get it and use it.
        - is there already code in the codebase that does this? Use it.
        - is there already code in the codebase that, with a reasonable refactor, could support this use case also? Refactor and use it.
        - only if all these other options won't work, write code to solve the problem.
         
        **You are to use a distinct style**:
        The function should read like pseudo-code, with a clear self-documenting
        style. A reader should be able to look at the code, read it out loud,
        and understand the intent and logical flow of the function.
        
        **You are to follow a distinct process**:
        Write only one function, class, or UI component layer at a time.
        Use thorough decomposition, ensuring each implemented portion of code remains
        self-documenting, simple, and of obvious intent.
         
        For example, a function that needs to query the user for a list of items and
        then print that list of items might look like:
        
        ```py
        def query_and_display_items(how_many: int):
            items = query_items(how_many)
            display_items(items)
        ```
        
        A function is a simple wiring diagram of the logic of the function.
        
        When naming functions, choose a name that is simple and accurate,
        but not overly verbose or specific to the implementation.
        Consider multiple names that could be used for a function,
        and select the one that is most simple while still being descriptive.
        
        Now, some functions are **so** simple, they shouldn't be decomposed further.
        For example, a single loop to display the items:
        
        ```py
        def display_items(items: list[str]):
            for item in items:
                print('-', item)
        ```
        
        When thinking through the implementation of a function,
        you need to decide whether to decompose into additional functions
        or simply implement the needed logic. Consider multiple possibilities,
        then pick the approach that strikes the best balance between
        the single-responsibility-principle and excessive decomposition.
        
        Only decompose a function when doing so meaningfully reduces complexity.
        
        As you implement a function, you will likely need to reference
        new functions. Include function stubs for these functions,
        **but do not implement them**.

        For example, if you had just implemented `query_and_display_items`
        in the example above, you would also include:
        
        ```py
        def query_items(how_many: int) -> list[str]:
            pass
            
            
        def display_items(items: list[str]):
            pass
        ```
        
        Define new functions above their call site.
        
        Avoid side effects across function boundaries
        except where necessary.
        
        Always include type hints.
        
        Use classes only when:
        
        - You need a custom data structure
        - You need to manage setup and teardown of state (in which case design a context manager)
        - You need to abstract complex dependencies behind a simplified API
        
        When implementing a class, implement the functions that are needed on the class.
        If the class has dependencies on new outside functions, stub them out as described above.
        Use leading underscore for all class members and methods that are private.
        
        **Concluding your work**:
        When finished implementing the described task, return a description of what you did,
        including new classes or functions that have been stubbed out.
        
        Be sure to also include all the new work that now needs to be done in `new_work`.
        This should be a list of functions/classes/components that your reference in your work,
        but which haven't been implemented yet.
        
        These functions and classes will be implemented at a later step.
        
        {HUMAN_REVIEW}
        """),
        output=TASK_OUTPUT
    )
    return result.output


@log_call
def plan_task(task: str) -> list[str]:
    result = run_agent(
        agent=AGENT,
        prompt=dedent(
            f"""
            --- TASK ---
            {task}
            ------------
            
            You are part of a multi-agent workflow all working together to accomplish the task. 
            Your specific assignment is to create a plan for how to implement the task.
            
            The plan should focus on the high-level steps needed to complete the task. 
            Do not break these high-level steps into sub-steps; this will be done later.
            
            {PLAN_INSTRUCTIONS}
            
            {HUMAN_REVIEW}
        """),
        output=PLAN_OUTPUT
    )
    return result.output['plan']


@log_call
def update_plan(task: str, plan: list[str], task_result: TaskResult) -> str:
    result = run_agent(
        agent=AGENT,
        prompt=dedent(
            f"""
            --- TASK ---
            {task}
            ------------
            
            --- PLAN ---
            {'\n\n'.join(plan)}
            ------------
            
            --- LATEST CHANGE ---
            {task_result['summary_of_changes']}            
            ---------------------
            
            --- NEW WORK ---
            {'\n'.join(task_result['new_work'])}
            ---------------------
            
            You are part of a multi-agent workflow seeking to accomplish the described task,
            following the described plan.
            
            Another agent just did the work described in LATEST CHANGE.
            
            Your specific assignment right now is to create an updated plan that accounts for the latest changes.
            Remove tasks that are now obsolete. Include new tasks that reflect the new work that now needs to be done.
            
            If a task does not need to be changed, preserve it as-is. Only add/remove/change tasks
            that are meaningfully affect by the latest changes.
            
            {PLAN_INSTRUCTIONS}
            
            If the plan is empty, and there is no work suggested, return an empty plan.
            
            {HUMAN_REVIEW}
        """),
        output=PLAN_OUTPUT
    )
    return result.output['plan']


@log_call
def summarize(task: str, task_results: list[TaskResult]) -> TaskResult:
    result = run_agent(
        agent=AGENT,
        prompt=dedent(f"""
        --- TASK ---
        {task}
        ------------
        
        --- RESULTS ---
        {'\n\n'.join(res['summary_of_changes'] for res in task_results)}
        ---------------
        
        You are part of a multi-agent workflow addressing the described task.
        
        Agents have performed the work described in RESULTS.
        
        Your specific assignment is to summarize all the changes into a single,
        high-level description of how the TASK has been addressed.
        
        Return an empty list for 'new_work'.
        
        {HUMAN_REVIEW}
        """),
        output=TASK_OUTPUT
    )
    return result.output


@log_call
def delegate(task: str) -> TaskResult:
    do_it = consider_task(task)

    if do_it:
        result = implement(task)
        return result

    else:
        plan = plan_task(task)

        task_results = []
        while plan:
            sub_task = plan.pop(0)
            task_result = delegate(sub_task)
            task_results.append(task_result)
            if plan or task_result['new_work']:
                plan = update_plan(task, plan, task_result)

        return summarize(task, task_results)


@log_call
def main(task: str) -> None:
    result = delegate(task)
    print(result['summary_of_changes'])


if __name__ == "__main__":
    main(sys.argv[1])
