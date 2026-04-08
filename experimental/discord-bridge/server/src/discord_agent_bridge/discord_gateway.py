from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import threading
import time
from typing import Any, Callable, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .config import BridgeConfig
from .models import Routing

try:
    import discord
except ImportError:  # pragma: no cover - optional at runtime
    discord = None


DISCORD_API_BASE_URL = "https://discord.com/api/v10"


def _slugify_name_part(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "unnamed"


def _stable_agent_suffix(agent_id: str) -> str:
    return hashlib.sha1(agent_id.encode("utf-8")).hexdigest()[:6]


def slugify_channel_name(agent_kind: str, agent_name: str, agent_id: str = "") -> str:
    prefix = "subagent" if agent_kind == "subagent" else "agent"
    name_part = _slugify_name_part(agent_name)
    if not agent_id:
        return f"{prefix}-{name_part}"[:100]

    visible_suffix = _stable_agent_suffix(agent_id or agent_name)
    reserved = len(prefix) + len(visible_suffix) + 2
    available = max(1, 100 - reserved)
    return f"{prefix}-{name_part[:available]}-{visible_suffix}"


def render_channel_topic(routing: Routing) -> str:
    return (
        f"workspace={routing.workspace_id} session={routing.session_id} "
        f"agent={routing.agent_name} agent_id={routing.agent_id} kind={routing.agent_kind}"
    )


def parse_channel_topic(topic: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for part in topic.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key] = value
    return values


class DiscordGateway(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def ensure_channel(self, routing: Routing, existing_channel_id: str | None) -> str: ...
    def send_message(self, channel_id: str, content: str) -> str: ...
    def refresh_typing(self, channel_id: str, ttl_seconds: int) -> None: ...
    def stop_typing(self, channel_id: str) -> None: ...


class MemoryDiscordGateway:
    def __init__(self) -> None:
        self.channels: dict[str, dict[str, str]] = {}
        self.messages: dict[str, list[str]] = {}
        self.typing_refreshes: list[tuple[str, int]] = []
        self.stopped_typing: list[str] = []
        self.deleted_channels: list[str] = []
        self._next_channel_number = 1

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def ensure_channel(self, routing: Routing, existing_channel_id: str | None) -> str:
        if existing_channel_id and existing_channel_id in self.channels:
            return existing_channel_id
        expected_topic = render_channel_topic(routing)
        for channel_id, channel in self.channels.items():
            if (
                channel.get("guild_id") == routing.discord_guild_id
                and channel.get("topic") == expected_topic
            ):
                return channel_id
        channel_id = f"channel-{self._next_channel_number}"
        self._next_channel_number += 1
        self.channels[channel_id] = {
            "name": slugify_channel_name(
                routing.agent_kind,
                routing.agent_name,
                routing.agent_id,
            ),
            "topic": render_channel_topic(routing),
            "guild_id": routing.discord_guild_id,
        }
        self.messages[channel_id] = []
        return channel_id

    def send_message(self, channel_id: str, content: str) -> str:
        self.messages.setdefault(channel_id, []).append(content)
        return f"delivery-{len(self.messages[channel_id])}"

    def refresh_typing(self, channel_id: str, ttl_seconds: int) -> None:
        self.typing_refreshes.append((channel_id, ttl_seconds))

    def stop_typing(self, channel_id: str) -> None:
        self.stopped_typing.append(channel_id)

    def delete_channel(self, channel_id: str) -> bool:
        if channel_id not in self.channels:
            return False
        self.channels.pop(channel_id, None)
        self.messages.pop(channel_id, None)
        self.deleted_channels.append(channel_id)
        return True

    def find_channel_id_for_routing(self, routing: Routing) -> str | None:
        expected_topic = render_channel_topic(routing)
        for channel_id, channel in self.channels.items():
            if (
                channel.get("guild_id") == routing.discord_guild_id
                and channel.get("topic") == expected_topic
            ):
                return channel_id
        return None

    def find_session_channel_ids(
        self,
        guild_id: str,
        workspace_id: str,
        session_id: str,
        agent_kind: str | None = None,
    ) -> list[str]:
        matches: list[str] = []
        for channel_id, channel in self.channels.items():
            if channel.get("guild_id") != guild_id:
                continue
            topic_values = parse_channel_topic(channel.get("topic", ""))
            if topic_values.get("workspace") != workspace_id:
                continue
            if topic_values.get("session") != session_id:
                continue
            if agent_kind and topic_values.get("kind") != agent_kind:
                continue
            matches.append(channel_id)
        return matches


class _TypingHeartbeatManager:
    def __init__(self, trigger_typing: Callable[[str], None], interval_seconds: int) -> None:
        self._trigger_typing = trigger_typing
        self._interval_seconds = max(1, interval_seconds)
        self._lock = threading.Lock()
        self._deadlines: dict[str, float] = {}
        self._threads: dict[str, threading.Thread] = {}

    def refresh(self, channel_id: str, ttl_seconds: int) -> None:
        with self._lock:
            self._deadlines[channel_id] = time.monotonic() + max(0, ttl_seconds)
            thread = self._threads.get(channel_id)
            if thread is None or not thread.is_alive():
                thread = threading.Thread(
                    target=self._run,
                    args=(channel_id,),
                    name=f"discord-typing-{channel_id}",
                    daemon=True,
                )
                self._threads[channel_id] = thread
                thread.start()

    def stop(self, channel_id: str) -> None:
        with self._lock:
            self._deadlines[channel_id] = 0

    def close(self) -> None:
        with self._lock:
            for channel_id in list(self._deadlines):
                self._deadlines[channel_id] = 0

    def _run(self, channel_id: str) -> None:
        while True:
            with self._lock:
                deadline = self._deadlines.get(channel_id, 0)
            if time.monotonic() >= deadline:
                with self._lock:
                    self._threads.pop(channel_id, None)
                    self._deadlines.pop(channel_id, None)
                return
            with contextlib.suppress(Exception):
                self._trigger_typing(channel_id)
            time.sleep(self._interval_seconds)


class DiscordRestGateway:
    def __init__(self, config: BridgeConfig) -> None:
        self._config = config
        self._typing = _TypingHeartbeatManager(self._trigger_typing_now, config.typing_heartbeat_seconds)

    def start(self) -> None:
        return None

    def stop(self) -> None:
        self._typing.close()

    def ensure_channel(self, routing: Routing, existing_channel_id: str | None) -> str:
        self._require_bot_key("create Discord channels")
        if existing_channel_id:
            channel = self.get_channel(existing_channel_id, not_found_ok=True)
            if channel and str(channel.get("guild_id", "")) == routing.discord_guild_id:
                return str(channel["id"])

        channel = self._find_channel_by_topic(routing.discord_guild_id, render_channel_topic(routing))
        if channel is None:
            channel = self._request(
                "POST",
                f"/guilds/{routing.discord_guild_id}/channels",
                {
                    "name": slugify_channel_name(
                        routing.agent_kind,
                        routing.agent_name,
                        routing.agent_id,
                    ),
                    "topic": render_channel_topic(routing),
                    "type": 0,
                },
            )
        return str(channel["id"])

    def send_message(self, channel_id: str, content: str) -> str:
        self._require_bot_key("send Discord messages")
        response = self._request(
            "POST",
            f"/channels/{channel_id}/messages",
            {"content": content},
        )
        return str(response["id"])

    def refresh_typing(self, channel_id: str, ttl_seconds: int) -> None:
        if not self._config.bot_key:
            return
        self._typing.refresh(channel_id, ttl_seconds)

    def stop_typing(self, channel_id: str) -> None:
        self._typing.stop(channel_id)

    def delete_channel(self, channel_id: str) -> bool:
        self._require_bot_key("delete Discord channels")
        channel = self.get_channel(channel_id, not_found_ok=True)
        if channel is None:
            return False
        self._request("DELETE", f"/channels/{channel_id}", not_found_ok=True)
        return True

    def get_channel(self, channel_id: str, not_found_ok: bool = False) -> dict[str, Any] | None:
        return self._request("GET", f"/channels/{channel_id}", not_found_ok=not_found_ok)

    def find_channel_id_for_routing(self, routing: Routing) -> str | None:
        channel = self._find_channel_by_topic(routing.discord_guild_id, render_channel_topic(routing))
        if channel is None:
            return None
        return str(channel["id"])

    def find_session_channel_ids(
        self,
        guild_id: str,
        workspace_id: str,
        session_id: str,
        agent_kind: str | None = None,
    ) -> list[str]:
        channels = self._list_guild_channels(guild_id)
        matches: list[str] = []
        for channel in channels:
            topic_values = parse_channel_topic(str(channel.get("topic", "")))
            if topic_values.get("workspace") != workspace_id:
                continue
            if topic_values.get("session") != session_id:
                continue
            if agent_kind and topic_values.get("kind") != agent_kind:
                continue
            matches.append(str(channel["id"]))
        return matches

    def find_guild_text_channel_ids(
        self,
        guild_id: str,
        *,
        exclude_names: set[str] | None = None,
    ) -> list[str]:
        excluded = {name.strip().lower() for name in (exclude_names or set()) if name.strip()}
        matches: list[str] = []
        for channel in self._list_guild_channels(guild_id):
            if str(channel.get("name", "")).strip().lower() in excluded:
                continue
            matches.append(str(channel["id"]))
        return matches

    def _find_channel_by_topic(self, guild_id: str, topic: str) -> dict[str, Any] | None:
        for channel in self._list_guild_channels(guild_id):
            if str(channel.get("topic", "")) == topic:
                return channel
        return None

    def _list_guild_channels(self, guild_id: str) -> list[dict[str, Any]]:
        channels = self._request("GET", f"/guilds/{guild_id}/channels")
        return [
            channel
            for channel in channels
            if int(channel.get("type", -1)) == 0
        ]

    def _trigger_typing_now(self, channel_id: str) -> None:
        self._request("POST", f"/channels/{channel_id}/typing")

    def _require_bot_key(self, action: str) -> None:
        if not self._config.bot_key:
            raise RuntimeError(f"BOT_KEY is required to {action}.")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        not_found_ok: bool = False,
    ) -> Any:
        self._require_bot_key("access Discord")
        url = f"{DISCORD_API_BASE_URL}{path}"
        headers = {
            "Authorization": f"Bot {self._config.bot_key}",
            "User-Agent": "discord-agent-bridge/1.0",
        }
        encoded_payload = None if payload is None else json.dumps(payload).encode("utf-8")
        if encoded_payload is not None:
            headers["Content-Type"] = "application/json"

        while True:
            request = Request(url=url, method=method, data=encoded_payload, headers=headers)
            try:
                with urlopen(request, timeout=30) as response:
                    body = response.read().decode("utf-8")
                    if not body:
                        return {}
                    return json.loads(body)
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 404 and not_found_ok:
                    return None
                if exc.code == 429:
                    retry_after = 1.0
                    with contextlib.suppress(Exception):
                        retry_after = max(0.25, float(json.loads(body).get("retry_after", 1.0)))
                    time.sleep(retry_after)
                    continue
                raise RuntimeError(f"Discord API request failed: {exc.code} {body}") from exc


class DiscordReplyListener:
    _SHUTDOWN_TIMEOUT_SECONDS = 2.0

    def __init__(
        self,
        config: BridgeConfig,
        on_user_reply: Callable[[str, str, str, str], None],
    ) -> None:
        if discord is None:
            raise RuntimeError(
                "discord.py is not installed. Install project dependencies before enabling BOT_KEY."
            )
        self._config = config
        self._on_user_reply = on_user_reply
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: discord.Client | None = None
        self._ready = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        if not self._config.bot_key:
            raise RuntimeError("BOT_KEY is required to listen for Discord replies.")
        with self._lock:
            if self._thread is not None:
                return
            self._ready.clear()
            self._client = self._build_client()
            self._thread = threading.Thread(target=self._run, name="discord-reply-listener", daemon=True)
            self._thread.start()
        if not self._ready.wait(timeout=20):
            raise RuntimeError("Discord reply listener did not become ready within 20 seconds.")

    def stop(self) -> None:
        with self._lock:
            loop = self._loop
            client = self._client
            thread = self._thread
        if loop is None or client is None:
            return
        with contextlib.suppress(Exception):
            future = asyncio.run_coroutine_threadsafe(client.close(), loop)
            future.result(timeout=self._SHUTDOWN_TIMEOUT_SECONDS)
        if thread is not None:
            thread.join(timeout=self._SHUTDOWN_TIMEOUT_SECONDS)
        with self._lock:
            if self._thread is thread and thread is not None and not thread.is_alive():
                self._thread = None
                self._client = None

    def _build_client(self) -> discord.Client:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready() -> None:
            self._ready.set()

        @client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == client.user:
                return
            if not message.guild:
                return
            self._on_user_reply(
                str(message.channel.id),
                message.content,
                str(message.author.id),
                str(message.id),
            )

        return client

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        with self._lock:
            self._loop = loop
            client = self._client
        asyncio.set_event_loop(loop)
        try:
            if client is None:
                return
            loop.run_until_complete(client.start(self._config.bot_key))
        finally:
            with self._lock:
                self._loop = None
                self._thread = None
                self._client = None
            self._ready.clear()
            with contextlib.suppress(Exception):
                loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
