from __future__ import annotations

import sys

import talk_to_user
import update_user


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in {"talk", "update"}:
        raise SystemExit("usage: .myteam/discord-bridge/bridge_main.py {talk|update} ...")

    routed_args = [
        "--agent-kind",
        "top_level",
        "--agent-id",
        "main",
        "--agent-name",
        "Main",
    ]
    command, rest = args[0], args[1:]
    if command == "talk":
        return talk_to_user.talk_to_user_main(routed_args + rest)
    return update_user.update_user_main(routed_args + rest)


if __name__ == "__main__":
    raise SystemExit(main())
