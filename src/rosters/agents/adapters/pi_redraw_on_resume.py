"""A myteam agent adapter for testing Pi with the forced-redraw extension."""

from pathlib import Path

from myteam.workflows.agents import pi as builtin

EXEC = "caffeinate"
EXIT_COMMAND = builtin.EXIT_COMMAND
get_session_info = builtin.get_session_info
get_usage_info = builtin.get_usage_info

REDRAW_EXTENSION = Path(__file__).parent.parent.joinpath('extensions', "pi_refresh_on_resume.ts")


def build_argv(**kwargs) -> list[str]:
    extra_args = [
        *(kwargs.get("extra_args") or ()),
        "--extension",
        str(REDRAW_EXTENSION),
    ]
    if (model := kwargs.get('model')) and '/' not in model:
        extra_args.extend(('--provider', 'openai'))

    return [
        "caffeinate",
        *builtin.build_argv(**{**kwargs, "extra_args": extra_args}),
    ]
