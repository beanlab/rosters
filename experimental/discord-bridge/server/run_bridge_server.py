from __future__ import annotations

import argparse
import contextlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
PID_FILE = ROOT / ".bridge-server.pid"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from discord_agent_bridge.config import BridgeConfig, load_config
from discord_agent_bridge.discord_gateway import DiscordReplyListener, DiscordRestGateway, MemoryDiscordGateway
from discord_agent_bridge.models import MessageRequest, Routing, StateUpdateRequest, SubagentLogRequest
from discord_agent_bridge.service import BridgeService
from discord_agent_bridge.store import InMemoryBridgeStore


class BridgeRuntime:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.store = InMemoryBridgeStore()
        self._shutdown_callback: callable[[], None] | None = None
        self._listener_lock = threading.Lock()
        if config.bot_key:
            gateway = DiscordRestGateway(config)
        else:
            gateway = MemoryDiscordGateway()
        self.gateway = gateway
        self.listener = (
            DiscordReplyListener(config, self._receive_reply)
            if config.enable_bot and config.bot_key
            else None
        )
        self.service = BridgeService(
            self.store,
            self.gateway,
            on_wait_started=self.ensure_listener_started,
            on_wait_finished=self.stop_listener_if_idle,
        )

    def _receive_reply(
        self,
        channel_id: str,
        content: str,
        discord_user_id: str,
        discord_message_id: str,
    ) -> None:
        self.service.receive_discord_reply(
            channel_id=channel_id,
            content=content,
            discord_user_id=discord_user_id,
            discord_message_id=discord_message_id,
        )

    def start(self) -> None:
        self.gateway.start()

    def stop(self) -> None:
        with self._listener_lock:
            if self.listener is not None:
                self.listener.stop()
        self.gateway.stop()

    def bind_shutdown_callback(self, callback: callable[[], None]) -> None:
        self._shutdown_callback = callback

    def request_shutdown(self, cancel_waiters: bool = False) -> int:
        cancelled = self.service.request_shutdown() if cancel_waiters else 0
        self.stop()
        if self._shutdown_callback is not None:
            threading.Thread(target=self._shutdown_callback, name="bridge-server-shutdown", daemon=True).start()
        return cancelled

    def ensure_listener_started(self) -> None:
        if self.listener is None:
            raise RuntimeError("Discord reply listening is unavailable. Check BOT_KEY and BRIDGE_ENABLE_BOT.")
        with self._listener_lock:
            self.listener.start()

    def stop_listener_if_idle(self) -> None:
        if self.listener is None or self.store.has_awaiting_sessions():
            return
        with self._listener_lock:
            if not self.store.has_awaiting_sessions():
                self.listener.stop()

    def clear_all_logs(self, guild_id: str) -> list[str]:
        channel_ids = self.store.channel_ids_for_guild(guild_id)
        deleted = []
        if hasattr(self.gateway, "delete_channel"):
            deleted = [
                channel_id
                for channel_id in channel_ids
                if self.gateway.delete_channel(channel_id)
            ]
        self.store.forget_channels(deleted)
        return deleted

    def clear_all_non_general(self, guild_id: str) -> tuple[list[str], list[str]]:
        return [], []


class BridgeHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], runtime: BridgeRuntime) -> None:
        super().__init__(server_address, BridgeRequestHandler)
        self.runtime = runtime


class BridgeRequestHandler(BaseHTTPRequestHandler):
    server: BridgeHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._send_json(HTTPStatus.OK, {"ok": True})
                return
            if parsed.path == "/v1/replies/next":
                self._handle_get_reply(parsed.query)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
        except BrokenPipeError:
            return
        except Exception as exc:
            with contextlib.suppress(BrokenPipeError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            if not self._authorized():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
                return
            payload = self._read_json()
            if parsed.path == "/v1/messages":
                request = MessageRequest.from_dict(payload)
                result = self.server.runtime.service.post_message(request)
                self._send_json(HTTPStatus.OK, result.to_dict())
                return
            if parsed.path == "/v1/state":
                request = StateUpdateRequest.from_dict(payload)
                result = self.server.runtime.service.update_state(request)
                self._send_json(HTTPStatus.OK, result)
                return
            if parsed.path == "/v1/subagent-logs":
                request = SubagentLogRequest.from_dict(payload)
                result = self.server.runtime.service.post_subagent_log(request)
                self._send_json(HTTPStatus.OK, result)
                return
            if parsed.path == "/v1/admin/shutdown":
                result = {
                    "ok": True,
                    "cancelled_waits": self.server.runtime.request_shutdown(cancel_waiters=True),
                    "shutdown_requested": True,
                }
                self._send_json(HTTPStatus.OK, result)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
        except BrokenPipeError:
            return
        except Exception as exc:
            with contextlib.suppress(BrokenPipeError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return None

    def _authorized(self) -> bool:
        expected = self.server.runtime.config.api_token
        if not expected:
            return True
        auth_header = self.headers.get("Authorization", "")
        return auth_header == f"Bearer {expected}"

    def _read_json(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        return json.loads(data)

    def _handle_get_reply(self, query: str) -> None:
        if not self._authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return
        params = parse_qs(query)
        routing = Routing.from_dict(
            {
                "workspace_id": params.get("workspace_id", [""])[0],
                "session_id": params.get("session_id", [""])[0],
                "agent_id": params.get("agent_id", [""])[0],
                "agent_name": params.get("agent_name", [""])[0],
                "agent_kind": params.get("agent_kind", ["top_level"])[0],
                "discord_guild_id": params.get("discord_guild_id", [""])[0],
                "timestamp": params.get("timestamp", [""])[0],
            }
        )
        raw_timeout = params.get("timeout_seconds", [""])[0].strip()
        timeout_seconds = float(raw_timeout) if raw_timeout else None
        result = self.server.runtime.service.wait_for_reply(routing, timeout_seconds)
        self._send_json(HTTPStatus.OK, result)
        reply = result.get("reply")
        if isinstance(reply, dict):
            reply_id = str(reply.get("reply_id", "")).strip()
            if reply_id:
                self.server.runtime.service.acknowledge_reply(routing, reply_id)

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_server(config: BridgeConfig) -> tuple[BridgeRuntime, BridgeHTTPServer]:
    runtime = BridgeRuntime(config)
    server = BridgeHTTPServer((config.host, config.port), runtime)
    runtime.bind_shutdown_callback(server.shutdown)
    return runtime, server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Discord agent bridge server.")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--disable-bot", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.env_file)
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.disable_bot:
        config.enable_bot = False

    runtime, server = build_server(config)
    runtime.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.stop()
        with contextlib.suppress(FileNotFoundError):
            PID_FILE.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
