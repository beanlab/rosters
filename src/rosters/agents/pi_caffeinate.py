"""A myteam agent adapter - make pi keep macOS awake while it's running."""

from myteam.workflows.agents import pi as builtin

EXEC = "caffeinate"
EXIT_COMMAND = builtin.EXIT_COMMAND
get_session_info = builtin.get_session_info
get_usage_info = builtin.get_usage_info


def build_argv(
    prompt_text: str,
    interactive: bool = True,
    session_id: str | None = None,
    fork: bool = False,
    model: str | None = None,
    extra_args: tuple[str, ...] | None = None,
    session_name: str | None = None,
) -> list[str]:
    return [
        "caffeinate",
        *builtin.build_argv(
            prompt_text=prompt_text,
            interactive=interactive,
            session_id=session_id,
            fork=fork,
            model=model,
            extra_args=extra_args,
            session_name=session_name,
        ),
        '--provider', 'openai-codex'
    ]
