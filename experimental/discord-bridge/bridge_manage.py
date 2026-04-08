from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import bridge_server_control
import bridge_routing


SERVER_SRC = Path(__file__).resolve().parent / "server" / "src"
if str(SERVER_SRC) not in sys.path:
    sys.path.insert(0, str(SERVER_SRC))

from discord_agent_bridge.config import BridgeConfig
from discord_agent_bridge.discord_gateway import DiscordRestGateway
from discord_agent_bridge.models import Routing

LOCAL_BRIDGE_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _request(
    method: str,
    url: str,
    api_token: str,
    payload: dict[str, object] | None = None,
    timeout_seconds: float = 5,
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


def _is_local_bridge_url(api_base_url: str) -> bool:
    parsed = urlparse(api_base_url)
    if (parsed.scheme or "http").lower() != "http":
        return False
    return (parsed.hostname or "").lower() in LOCAL_BRIDGE_HOSTS


def _bridge_is_healthy(api_base_url: str, api_token: str) -> bool:
    headers: dict[str, str] = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    request = Request(url=f"{api_base_url.rstrip('/')}/healthz", method="GET", headers=headers)
    try:
        with urlopen(request, timeout=1.5) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def _require_guild_id(args: argparse.Namespace) -> str:
    guild_id = (args.discord_guild_id or os.getenv("DISCORD_GUILD_ID", "")).strip()
    if not guild_id:
        raise SystemExit("missing Discord guild routing: pass --discord-guild-id or set DISCORD_GUILD_ID")
    return guild_id


def _default_workspace_id() -> str:
    return os.getenv("BRIDGE_WORKSPACE_ID", Path(os.getcwd()).resolve().name)


def _default_session_id() -> str:
    return os.getenv("BRIDGE_SESSION_ID", "default-session")


def _default_general_channel_name() -> str:
    return os.getenv("DISCORD_GENERAL_CHANNEL_NAME", "general").strip() or "general"


def _stop_local_server_with_fallback(api_base_url: str, api_token: str) -> int:
    cancelled_waits = 0
    if _bridge_is_healthy(api_base_url, api_token):
        try:
            result = _request("POST", f"{api_base_url.rstrip('/')}/v1/admin/shutdown", api_token, {})
        except SystemExit:
            result = None
        if result is not None:
            cancelled_waits = int(result.get("cancelled_waits", 0))
            deadline = os.getenv("BRIDGE_SERVER_STOP_TIMEOUT_SECONDS", "5")
            try:
                timeout_seconds = max(0.0, float(deadline))
            except ValueError:
                timeout_seconds = 5.0
            started = time.monotonic()
            while time.monotonic() - started < timeout_seconds:
                if not _bridge_is_healthy(api_base_url, api_token):
                    sys.stdout.write(f"shutdown_requested cancelled_waits={cancelled_waits}\n")
                    return 0
                time.sleep(0.1)
    result = bridge_server_control.stop_local_bridge_process()
    if result.stopped:
        sys.stdout.write(
            f"forced_shutdown cancelled_waits={cancelled_waits} pid={result.pid} signal={result.signal_name}\n"
        )
        return 0
    sys.stdout.write("bridge server already stopped\n")
    return 0


def bridge_manage_main(argv: list[str] | None = None) -> int:
    bridge_routing.load_default_env()
    parser = argparse.ArgumentParser(
        description=(
            "Manage Discord bridge channels without starting the reply listener. "
            "Use --top-level or --subagent when agent identity would otherwise be ambiguous. "
            "Global routing flags must appear before the subcommand."
        ),
        epilog=(
            "examples:\n"
            "  bridge_manage.py --top-level --discord-guild-id <guild-id> ensure-channel\n"
            "  bridge_manage.py delete-channels <channel-id> <channel-id>\n"
            "  bridge_manage.py --top-level --discord-guild-id <guild-id> delete-session-channels\n"
            "  bridge_manage.py --top-level --discord-guild-id <guild-id> stop-server"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[bridge_routing.common_parser()],
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ensure-channel")

    delete_channel_parser = subparsers.add_parser("delete-channel")
    delete_channel_parser.add_argument("channel_id")

    delete_channels_parser = subparsers.add_parser("delete-channels")
    delete_channels_parser.add_argument("channel_ids", nargs="*")

    subparsers.add_parser("delete-agent-channel")

    subparsers.add_parser("delete-session-channels")
    subparsers.add_parser("stop-server")

    args = parser.parse_args(argv)

    if args.command == "stop-server":
        if _is_local_bridge_url(args.api_base_url):
            return _stop_local_server_with_fallback(args.api_base_url, args.api_token)
        if not _bridge_is_healthy(args.api_base_url, args.api_token):
            raise SystemExit(f"bridge server is not reachable at {args.api_base_url}")
        result = _request("POST", f"{args.api_base_url.rstrip('/')}/v1/admin/shutdown", args.api_token, {})
        cancelled_waits = int(result.get("cancelled_waits", 0))
        sys.stdout.write(f"shutdown_requested cancelled_waits={cancelled_waits}\n")
        return 0

    if not os.getenv("BOT_KEY", "").strip():
        raise SystemExit("missing BOT_KEY")
    config = BridgeConfig(bot_key=os.getenv("BOT_KEY", ""))
    gateway = DiscordRestGateway(config)

    if args.command == "delete-channel":
        deleted = gateway.delete_channel(args.channel_id)
        if deleted:
            sys.stdout.write(f"{args.channel_id}\n")
            return 0
        raise SystemExit(f"channel not found: {args.channel_id}")

    if args.command == "delete-channels":
        if not args.channel_ids:
            guild_id = _require_guild_id(args)
            preserved_name = _default_general_channel_name()
            channel_ids = gateway.find_guild_text_channel_ids(
                guild_id,
                exclude_names={preserved_name},
            )
            for channel_id in channel_ids:
                gateway.delete_channel(channel_id)
                sys.stdout.write(f"{channel_id}\n")
            return 0

        deleted_any = False
        missing: list[str] = []
        for channel_id in args.channel_ids:
            if gateway.delete_channel(channel_id):
                sys.stdout.write(f"{channel_id}\n")
                deleted_any = True
            else:
                missing.append(channel_id)
        if missing and not deleted_any:
            raise SystemExit(f"no matching channels found: {', '.join(missing)}")
        if missing:
            raise SystemExit(f"some channels were not found: {', '.join(missing)}")
        return 0

    guild_id = _require_guild_id(args)

    if args.command == "ensure-channel":
        routing = Routing.from_dict(bridge_routing.routing_from_args(args))
        channel_id = gateway.ensure_channel(routing, None)
        sys.stdout.write(f"{channel_id}\n")
        return 0

    if args.command == "delete-agent-channel":
        routing = Routing.from_dict(bridge_routing.routing_from_args(args))
        channel_id = gateway.find_channel_id_for_routing(routing)
        if channel_id is None:
            raise SystemExit("no matching agent channel found")
        gateway.delete_channel(channel_id)
        sys.stdout.write(f"{channel_id}\n")
        return 0

    workspace_id = (args.workspace_id or _default_workspace_id()).strip()
    session_id = (args.session_id or _default_session_id()).strip()
    requested_kind = None
    if getattr(args, "top_level", False):
        requested_kind = "top_level"
    elif getattr(args, "subagent", False):
        requested_kind = "subagent"
    elif args.agent_kind:
        requested_kind = args.agent_kind

    channel_ids = gateway.find_session_channel_ids(
        guild_id,
        workspace_id,
        session_id,
        requested_kind,
    )
    if not channel_ids:
        return 0
    for channel_id in channel_ids:
        gateway.delete_channel(channel_id)
        sys.stdout.write(f"{channel_id}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(bridge_manage_main())
