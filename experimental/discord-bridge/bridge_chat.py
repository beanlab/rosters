from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import bridge_routing
import bridge_server_control


def _request(
    method: str,
    url: str,
    api_token: str,
    payload: dict[str, object] | None = None,
    timeout_seconds: float | None = 310,
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
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"bridge request failed: {exc.code} {body}") from exc
    except URLError as exc:
        raise SystemExit(f"bridge request failed: {exc.reason}") from exc


def _wait_for_reply(
    api_base_url: str,
    api_token: str,
    routing: dict[str, str],
    timeout_seconds: int | None,
) -> int:
    query_payload = dict(routing)
    if timeout_seconds is not None:
        query_payload["timeout_seconds"] = str(timeout_seconds)
    query = urlencode(query_payload)
    reply = _request(
        "GET",
        f"{api_base_url.rstrip('/')}/v1/replies/next?{query}",
        api_token,
        timeout_seconds=None,
    )
    if reply.get("shutdown"):
        sys.stdout.write("bridge shutdown requested\n")
        return 0
    reply_payload = reply.get("reply")
    if not reply_payload:
        raise SystemExit("no reply received")
    sys.stdout.write(str(reply_payload["content"]))
    if not str(reply_payload["content"]).endswith("\n"):
        sys.stdout.write("\n")
    return 0


def bridge_chat_main(argv: list[str] | None = None) -> int:
    bridge_routing.load_default_env()
    parser = argparse.ArgumentParser(
        description=(
            "Send bridge messages, wait for replies, or update agent state. "
            "Use --top-level or --subagent when agent identity would otherwise be ambiguous. "
            "Global routing flags must appear before the subcommand."
        ),
        epilog=(
            "examples:\n"
            "  bridge_chat.py --top-level --discord-guild-id <guild-id> talk --content \"What deployment target do you want to use?\"\n"
            "  bridge_chat.py --top-level --discord-guild-id <guild-id> send --content \"Build finished.\"\n"
            "  bridge_chat.py --top-level --discord-guild-id <guild-id> state working --ttl-seconds 12\n"
            "  bridge_chat.py --subagent --agent-id <spawn-id> --discord-guild-id <guild-id> "
            "log --top-level-agent-name <top-level-name> --to-subagent \"Implement the polling path.\" "
            "--subagent-name rough-plan-render --to-top-level \"I need the API contract first.\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[bridge_routing.common_parser()],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("--content", required=True)
    send_parser.add_argument("--message-id", default="")

    talk_parser = subparsers.add_parser("talk")
    talk_parser.add_argument("--content", required=True)
    talk_parser.add_argument("--message-id", default="")
    talk_parser.add_argument("--timeout-seconds", type=int, default=None, help=argparse.SUPPRESS)

    wait_parser = subparsers.add_parser("wait")
    wait_parser.add_argument("--timeout-seconds", type=int, default=None, help=argparse.SUPPRESS)

    state_parser = subparsers.add_parser("state")
    state_parser.add_argument("state", choices=["working", "awaiting_user"])
    state_parser.add_argument("--ttl-seconds", type=int, default=12)

    log_parser = subparsers.add_parser("log", help="emit a coordination log to the owning top-level channel")
    log_parser.add_argument("--parent-agent-id", default="", help=argparse.SUPPRESS)
    log_parser.add_argument("--parent-agent-name", default="", help=argparse.SUPPRESS)
    log_parser.add_argument("--top-level-agent-name", required=True)
    log_parser.add_argument("--to-subagent", required=True)
    log_parser.add_argument("--subagent-name", required=True)
    log_parser.add_argument("--to-top-level", required=True)

    args = parser.parse_args(argv)
    if not os.getenv("BOT_KEY", "").strip():
        raise SystemExit("missing BOT_KEY")
    if not (args.discord_guild_id or os.getenv("DISCORD_GUILD_ID", "")):
        raise SystemExit("missing Discord guild routing: pass --discord-guild-id or set DISCORD_GUILD_ID")

    bridge_server_control.ensure_local_bridge(args.api_base_url)
    routing = (
        bridge_routing.subagent_log_routing_from_args(args)
        if args.command == "log"
        else bridge_routing.routing_from_args(args)
    )

    if args.command == "send":
        payload = {
            "routing": routing,
            "message": {
                "message_id": args.message_id,
                "content": args.content,
                "expects_reply": False,
            },
        }
        _request("POST", f"{args.api_base_url.rstrip('/')}/v1/messages", args.api_token, payload)
        return 0

    if args.command == "talk":
        payload = {
            "routing": routing,
            "message": {
                "message_id": args.message_id,
                "content": args.content,
                "expects_reply": True,
            },
        }
        _request("POST", f"{args.api_base_url.rstrip('/')}/v1/messages", args.api_token, payload)
        return _wait_for_reply(args.api_base_url, args.api_token, routing, args.timeout_seconds)

    if args.command == "wait":
        _request(
            "POST",
            f"{args.api_base_url.rstrip('/')}/v1/state",
            args.api_token,
            {
                "routing": routing,
                "state": "awaiting_user",
                "ttl_seconds": 0,
            },
        )
        return _wait_for_reply(args.api_base_url, args.api_token, routing, args.timeout_seconds)

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
    raise SystemExit(bridge_chat_main())
