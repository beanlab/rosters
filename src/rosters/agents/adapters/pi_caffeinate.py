"""A myteam agent adapter - make pi keep macOS awake while it's running."""

from myteam.workflows.agents import pi as builtin

EXEC = "caffeinate"
EXIT_COMMAND = builtin.EXIT_COMMAND
get_session_info = builtin.get_session_info
get_usage_info = builtin.get_usage_info


def build_argv(
    **kwargs,
) -> list[str]:
    args = [
        "caffeinate",
        *builtin.build_argv(
            **kwargs
        )
    ]
    return args
