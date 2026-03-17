from __future__ import annotations

import asyncio
from concurrent.futures import Future
import contextlib
import hashlib
import threading
import time
from typing import Callable, Protocol

from .config import BridgeConfig
from .models import Routing

try:
    import discord
except ImportError:  # pragma: no cover - optional at runtime
    discord = None


def _slugify_name_part(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value)
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "unnamed"


def _stable_agent_suffix(agent_id: str) -> str:
    return hashlib.sha1(agent_id.encode("utf-8")).hexdigest()[:6]


def slugify_channel_name(agent_kind: str, agent_name: str, agent_id: str = "") -> str:
    prefix = "subagent" if agent_kind == "subagent" else "agent"
    name_part = _slugify_name_part(agent_name)
    if agent_kind != "subagent":
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


class DiscordGateway(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def ensure_channel(self, routing: Routing, existing_channel_id: str | None) -> str: ...
    def send_message(self, channel_id: str, content: str) -> str: ...
    def refresh_typing(self, channel_id: str, ttl_seconds: int) -> None: ...
    def stop_typing(self, channel_id: str) -> None: ...
    def clear_managed_channels(
        self,
        guild_id: str,
        channel_ids: list[str],
        category_id: str,
    ) -> list[str]: ...
    def clear_all_non_general_channels(
        self,
        guild_id: str,
        general_channel_name: str,
    ) -> tuple[list[str], list[str]]: ...


class MemoryDiscordGateway:
    def __init__(self, category_id: str = "") -> None:
        self.category_id = category_id
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
                and channel.get("category_id") == self.category_id
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
            "category_id": self.category_id,
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

    def clear_managed_channels(
        self,
        guild_id: str,
        channel_ids: list[str],
        category_id: str,
    ) -> list[str]:
        deleted: list[str] = []
        for channel_id in channel_ids:
            channel = self.channels.get(channel_id)
            if (
                channel is None
                or channel.get("guild_id") != guild_id
                or channel.get("category_id") != category_id
            ):
                continue
            deleted.append(channel_id)
            self.channels.pop(channel_id, None)
            self.messages.pop(channel_id, None)
        self.deleted_channels.extend(deleted)
        return deleted

    def clear_all_non_general_channels(
        self,
        guild_id: str,
        general_channel_name: str,
    ) -> tuple[list[str], list[str]]:
        deleted: list[str] = []
        for channel_id, channel in list(self.channels.items()):
            if channel.get("guild_id") != guild_id or channel.get("name") == general_channel_name:
                continue
            deleted.append(channel_id)
            self.channels.pop(channel_id, None)
            self.messages.pop(channel_id, None)
        self.deleted_channels.extend(deleted)
        return deleted, []


class DiscordBotGateway:
    def __init__(
        self,
        config: BridgeConfig,
        on_user_reply: Callable[[str, str, str, str], None],
        on_clear_logs: Callable[[str], list[str]],
        on_clear_all: Callable[[str], tuple[list[str], list[str]]],
    ) -> None:
        if discord is None:
            raise RuntimeError(
                "discord.py is not installed. Install project dependencies before enabling BOT_KEY."
            )
        self._config = config
        self._on_user_reply = on_user_reply
        self._on_clear_logs = on_clear_logs
        self._on_clear_all = on_clear_all
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._typing_deadlines: dict[str, float] = {}
        self._typing_tasks: dict[str, asyncio.Task[None]] = {}
        intents = discord.Intents.default()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        self._client = discord.Client(intents=intents)
        self._install_handlers()

    def _render_clear_all_result(self, deleted: list[str], failed: list[str]) -> str:
        if not deleted and not failed:
            return "No non-general channels found to clear."
        if failed:
            return f"Cleared {len(deleted)} channels. Failed to delete {len(failed)} channels."
        return f"Cleared {len(deleted)} channels."

    async def _run_clear_all_from_message(self, message: discord.Message) -> None:
        report_channel = message.channel
        if getattr(message.channel, "name", "") != self._config.general_channel_name:
            general_channel = discord.utils.get(
                message.guild.text_channels,
                name=self._config.general_channel_name,
            )
            if general_channel is not None:
                report_channel = general_channel
        with contextlib.suppress(Exception):
            await report_channel.send("Clearing channels...")
        deleted, failed = await asyncio.to_thread(self._on_clear_all, str(message.guild.id))
        with contextlib.suppress(Exception):
            await report_channel.send(self._render_clear_all_result(deleted, failed))

    def _install_handlers(self) -> None:
        @self._client.event
        async def on_ready() -> None:
            self._ready.set()

        @self._client.event
        async def on_message(message: discord.Message) -> None:
            if message.author == self._client.user:
                return
            if not message.guild:
                return
            if message.content.strip() == ".clear_all_logs":
                deleted = self._on_clear_logs(str(message.guild.id))
                if not deleted:
                    with contextlib.suppress(Exception):
                        await message.channel.send("No managed log channels found.")
                elif str(message.channel.id) not in deleted:
                    with contextlib.suppress(Exception):
                        await message.channel.send(f"Cleared {len(deleted)} managed log channels.")
                return
            if message.content.strip() == ".clear_all":
                asyncio.create_task(self._run_clear_all_from_message(message))
                return
            self._on_user_reply(
                str(message.channel.id),
                message.content,
                str(message.author.id),
                str(message.id),
            )

    def start(self) -> None:
        if not self._config.bot_key:
            return
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="discord-bot", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=20)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._client.start(self._config.bot_key))

    def _submit(self, coro: asyncio.Future) -> Future:
        if self._loop is None:
            raise RuntimeError("Discord bot loop is not running.")
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def stop(self) -> None:
        if self._loop is None:
            return
        future = self._submit(self._client.close())
        future.result(timeout=10)
        if self._thread is not None:
            self._thread.join(timeout=10)

    async def _ensure_channel_async(self, routing: Routing, existing_channel_id: str | None) -> str:
        guild = self._client.get_guild(int(routing.discord_guild_id))
        if guild is None:
            guild = await self._client.fetch_guild(int(routing.discord_guild_id))
        channel = None
        if existing_channel_id:
            channel = guild.get_channel(int(existing_channel_id))
        if channel is None:
            category = None
            if self._config.category_id:
                category = guild.get_channel(int(self._config.category_id))
            expected_topic = render_channel_topic(routing)
            for candidate in guild.text_channels:
                if category is not None and getattr(candidate.category, "id", None) != category.id:
                    continue
                if category is None and getattr(candidate, "category", None) is not None:
                    continue
                if getattr(candidate, "topic", None) == expected_topic:
                    channel = candidate
                    break
        if channel is None:
            category = None
            if self._config.category_id:
                category = guild.get_channel(int(self._config.category_id))
            channel = await guild.create_text_channel(
                slugify_channel_name(
                    routing.agent_kind,
                    routing.agent_name,
                    routing.agent_id,
                ),
                category=category,
                topic=render_channel_topic(routing),
            )
        return str(channel.id)

    def ensure_channel(self, routing: Routing, existing_channel_id: str | None) -> str:
        if not self._config.bot_key:
            raise RuntimeError("BOT_KEY is required to create Discord channels.")
        future = self._submit(self._ensure_channel_async(routing, existing_channel_id))
        return future.result(timeout=30)

    async def _send_message_async(self, channel_id: str, content: str) -> str:
        channel = self._client.get_channel(int(channel_id))
        if channel is None:
            channel = await self._client.fetch_channel(int(channel_id))
        message = await channel.send(content)
        return str(message.id)

    def send_message(self, channel_id: str, content: str) -> str:
        future = self._submit(self._send_message_async(channel_id, content))
        return future.result(timeout=30)

    async def _typing_loop(self, channel_id: str) -> None:
        channel = self._client.get_channel(int(channel_id))
        if channel is None:
            channel = await self._client.fetch_channel(int(channel_id))
        while True:
            deadline = self._typing_deadlines.get(channel_id, 0)
            if time.monotonic() >= deadline:
                return
            with contextlib.suppress(Exception):
                await channel.trigger_typing()
            await asyncio.sleep(max(1, self._config.typing_heartbeat_seconds))

    def refresh_typing(self, channel_id: str, ttl_seconds: int) -> None:
        if not self._config.bot_key or self._loop is None:
            return
        self._typing_deadlines[channel_id] = time.monotonic() + ttl_seconds
        task = self._typing_tasks.get(channel_id)
        if task is None or task.done():
            self._typing_tasks[channel_id] = self._submit(self._typing_loop(channel_id))

    def stop_typing(self, channel_id: str) -> None:
        self._typing_deadlines[channel_id] = 0

    async def _delete_channel_async(self, channel_id: str) -> bool:
        channel = self._client.get_channel(int(channel_id))
        if channel is None:
            with contextlib.suppress(Exception):
                channel = await self._client.fetch_channel(int(channel_id))
        if channel is None:
            return False
        with contextlib.suppress(Exception):
            await channel.delete(reason="Requested via .clear_all_logs")
            return True
        return False

    def clear_managed_channels(
        self,
        guild_id: str,
        channel_ids: list[str],
        category_id: str,
    ) -> list[str]:
        if not self._config.bot_key:
            return []
        deleted: list[str] = []
        for channel_id in channel_ids:
            channel = self._client.get_channel(int(channel_id))
            if channel is not None:
                if getattr(channel, "guild", None) is None or str(channel.guild.id) != guild_id:
                    continue
                if str(getattr(channel, "category_id", "") or "") != category_id:
                    continue
            future = self._submit(self._delete_channel_async(channel_id))
            if future.result(timeout=30):
                deleted.append(channel_id)
        return deleted

    async def _clear_all_non_general_channels_async(
        self,
        guild_id: str,
        general_channel_name: str,
    ) -> tuple[list[str], list[str]]:
        guild = self._client.get_guild(int(guild_id))
        if guild is None:
            guild = await self._client.fetch_guild(int(guild_id))
        channels = [
            channel
            for channel in await guild.fetch_channels()
            if getattr(channel, "name", "") != general_channel_name
        ]
        ordered_channels = sorted(
            channels,
            key=lambda channel: 1 if getattr(channel, "type", None) == discord.ChannelType.category else 0,
        )
        parallelism = max(1, self._config.clear_all_parallelism)

        async def delete_batch(batch: list[discord.abc.GuildChannel]) -> tuple[list[str], list[str]]:
            results = await asyncio.gather(
                *(self._delete_channel_for_clear_all(channel) for channel in batch),
            )
            deleted_batch = [channel_id for channel_id, ok in results if ok]
            failed_batch = [channel_id for channel_id, ok in results if not ok]
            return deleted_batch, failed_batch

        deleted: list[str] = []
        failed: list[str] = []
        for start in range(0, len(ordered_channels), parallelism):
            batch = ordered_channels[start : start + parallelism]
            deleted_batch, failed_batch = await delete_batch(batch)
            deleted.extend(deleted_batch)
            failed.extend(failed_batch)
        return deleted, failed

    async def _delete_channel_for_clear_all(
        self,
        channel: discord.abc.GuildChannel,
    ) -> tuple[str, bool]:
        channel_id = str(channel.id)
        try:
            await channel.delete(reason="Requested via .clear_all")
            return channel_id, True
        except Exception:
            return channel_id, False

    def clear_all_non_general_channels(
        self,
        guild_id: str,
        general_channel_name: str,
    ) -> tuple[list[str], list[str]]:
        if not self._config.bot_key:
            return [], []
        future = self._submit(self._clear_all_non_general_channels_async(guild_id, general_channel_name))
        return future.result(timeout=60)
