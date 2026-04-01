from __future__ import annotations

import sys

import bridge_routing
import talk_to_user
import update_user


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in {"talk", "send", "update"}:
        raise SystemExit("usage: .myteam/discord-bridge/bridge_main.py {talk|send|update} ...")

    agent_name, agent_id = bridge_routing.resolve_top_level_identity()
    routed_args = [
        "--agent-kind",
        "top_level",
        "--agent-id",
        agent_id,
        "--agent-name",
        agent_name,
    ]
    command, rest = args[0], args[1:]
    if command == "send":
        return talk_to_user.talk_to_user_main(routed_args + rest + ["--no-wait"])
    if command == "talk":
        return talk_to_user.talk_to_user_main(routed_args + rest)
    return update_user.update_user_main(routed_args + rest)


if __name__ == "__main__":
    raise SystemExit(main())
