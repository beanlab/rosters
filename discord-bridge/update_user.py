from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import bridge_server_control
import bridge_routing


def _request(
    method: str,
    url: str,
    api_token: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    data = None
    headers: dict[str, str] = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url=url, method=method, data=data, headers=headers)
    try:
        with urlopen(request, timeout=310) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"bridge request failed: {exc.code} {body}") from exc


def update_user_main(argv: list[str] | None = None) -> int:
    bridge_routing.load_default_env()
    parser = argparse.ArgumentParser(
        description=(
            "Send state or subagent-log updates to the remote bridge. "
            "This script is intended to live under .myteam/discord-bridge so prompted agents and subagents "
            "can call it directly."
        ),
        parents=[bridge_routing.common_parser()],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    state_parser = subparsers.add_parser("state")
    state_parser.add_argument("state", choices=["working", "awaiting_user"])
    state_parser.add_argument("--ttl-seconds", type=int, default=12)

    log_parser = subparsers.add_parser("subagent-log")
    log_parser.add_argument(
        "--log-workspace-id",
        default="",
        help=argparse.SUPPRESS,
    )
    log_parser.add_argument(
        "--log-session-id",
        default="",
        help=argparse.SUPPRESS,
    )
    log_parser.add_argument(
        "--log-agent-id",
        default="",
        help=argparse.SUPPRESS,
    )
    log_parser.add_argument(
        "--log-agent-name",
        default="",
        help=argparse.SUPPRESS,
    )
    log_parser.add_argument(
        "--log-agent-kind",
        choices=["top_level", "subagent"],
        default="",
        help=argparse.SUPPRESS,
    )
    log_parser.add_argument("--parent-agent-id", default="", help=argparse.SUPPRESS)
    log_parser.add_argument("--parent-agent-name", default="", help=argparse.SUPPRESS)
    log_parser.add_argument("--top-level-agent-name", required=True)
    log_parser.add_argument("--to-subagent", required=True)
    log_parser.add_argument("--subagent-name", required=True)
    log_parser.add_argument("--to-top-level", required=True)

    args = parser.parse_args(argv)
    if not (args.discord_guild_id or os.getenv("DISCORD_GUILD_ID", "")):
        raise SystemExit("missing Discord guild routing: pass --discord-guild-id or set DISCORD_GUILD_ID")
    bridge_server_control.ensure_local_bridge(args.api_base_url)
    routing = bridge_routing.subagent_log_routing_from_args(args)

    if args.command == "state":
        payload: dict[str, Any] = {
            "routing": routing,
            "state": args.state,
            "ttl_seconds": args.ttl_seconds,
        }
        _request("POST", f"{args.api_base_url.rstrip('/')}/v1/state", args.api_token, payload)
        return 0

    payload = {
        "routing": routing,
        "exchange": {
            "top_level_agent_name": args.top_level_agent_name,
            "to_subagent": args.to_subagent,
            "subagent_name": args.subagent_name,
            "to_top_level": args.to_top_level,
        },
    }
    _request("POST", f"{args.api_base_url.rstrip('/')}/v1/subagent-logs", args.api_token, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(update_user_main())
