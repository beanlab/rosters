from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import bridge_routing


def _request(
    method: str,
    url: str,
    api_token: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    data = None
    headers = {"Authorization": f"Bearer {api_token}"}
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


def _wait_for_reply(
    api_base_url: str,
    api_token: str,
    routing: dict[str, str],
    timeout_seconds: int,
) -> int:
    query = urlencode({**routing, "timeout_seconds": timeout_seconds})
    reply = _request("GET", f"{api_base_url.rstrip('/')}/v1/replies/next?{query}", api_token)
    reply_payload = reply.get("reply")
    if not reply_payload:
        raise SystemExit("no reply received before timeout")
    sys.stdout.write(str(reply_payload["content"]))
    if not str(reply_payload["content"]).endswith("\n"):
        sys.stdout.write("\n")
    return 0


def talk_to_user_main(argv: list[str] | None = None) -> int:
    bridge_routing.load_default_env()
    parser = argparse.ArgumentParser(
        description=(
            "Send a talk-to-user message to the remote bridge and optionally wait for the reply. "
            "This script is intended to live at the top-level directory so prompted agents and subagents "
            "can call it directly."
        ),
        parents=[bridge_routing.common_parser()],
    )
    parser.add_argument("--content")
    parser.add_argument("--message-id", default="")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument(
        "--wait-only",
        action="store_true",
        help="Do not send a message; just mark the agent as awaiting the user and wait for the next Discord reply.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=int(os.getenv("BRIDGE_REPLY_TIMEOUT_SECONDS", "300")))
    args = parser.parse_args(argv)
    if not (args.discord_guild_id or os.getenv("DISCORD_GUILD_ID", "")):
        raise SystemExit("missing Discord guild routing: pass --discord-guild-id or set DISCORD_GUILD_ID")

    routing = bridge_routing.routing_from_args(args)
    if args.wait_only:
        if args.no_wait:
            raise SystemExit("--wait-only cannot be combined with --no-wait")
        if args.content:
            raise SystemExit("--wait-only does not accept --content")
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

    if not args.content:
        raise SystemExit("--content is required unless --wait-only is used")

    message_payload = {
        "routing": routing,
        "message": {
            "message_id": args.message_id,
            "content": args.content,
            "expects_reply": not args.no_wait,
        },
    }
    _request("POST", f"{args.api_base_url.rstrip('/')}/v1/messages", args.api_token, message_payload)
    if args.no_wait:
        return 0
    return _wait_for_reply(args.api_base_url, args.api_token, routing, args.timeout_seconds)


if __name__ == "__main__":
    raise SystemExit(talk_to_user_main())
