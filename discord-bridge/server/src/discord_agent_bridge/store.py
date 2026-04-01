from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import time
from typing import Deque

from .models import ReplyRecord, Routing


@dataclass(slots=True)
class SessionState:
    routing: Routing
    channel_id: str | None = None
    conversation_state: str = "idle"
    pending_replies: Deque[ReplyRecord] = field(default_factory=deque)
    wait_started_at_ms: int = 0


class InMemoryBridgeStore:
    _DISCORD_EPOCH_MS = 1420070400000

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reply_condition = threading.Condition(self._lock)
        self._sessions: dict[tuple[str, str, str, str], SessionState] = {}
        self._channel_to_key: dict[str, tuple[str, str, str, str]] = {}

    def _key(self, routing: Routing) -> tuple[str, str, str, str]:
        return routing.key()

    def get_or_create_session(self, routing: Routing) -> SessionState:
        key = self._key(routing)
        with self._lock:
            session = self._sessions.get(key)
            if session is None:
                session = SessionState(routing=routing)
                self._sessions[key] = session
            else:
                session.routing = routing
            return session

    def get_channel_id(self, routing: Routing) -> str | None:
        with self._lock:
            session = self._sessions.get(self._key(routing))
            return None if session is None else session.channel_id

    def bind_channel(self, routing: Routing, channel_id: str) -> None:
        key = self._key(routing)
        with self._lock:
            session = self.get_or_create_session(routing)
            session.channel_id = channel_id
            self._channel_to_key[channel_id] = key

    def routing_for_channel(self, channel_id: str) -> Routing | None:
        with self._lock:
            key = self._channel_to_key.get(channel_id)
            if key is None:
                return None
            session = self._sessions.get(key)
            return None if session is None else session.routing

    def set_conversation_state(self, routing: Routing, state: str) -> None:
        with self._lock:
            session = self.get_or_create_session(routing)
            session.conversation_state = state

    def begin_waiting_for_reply(self, routing: Routing) -> None:
        with self._lock:
            session = self.get_or_create_session(routing)
            session.conversation_state = "awaiting_user"
            session.pending_replies.clear()
            session.wait_started_at_ms = self._current_time_ms()

    def get_conversation_state(self, routing: Routing) -> str:
        with self._lock:
            session = self.get_or_create_session(routing)
            return session.conversation_state

    def enqueue_reply(self, channel_id: str, reply: ReplyRecord) -> Routing | None:
        with self._lock:
            key = self._channel_to_key.get(channel_id)
            if key is None:
                return None
            session = self._sessions[key]
            if session.conversation_state != "awaiting_user":
                return None
            if self._reply_created_at_ms(reply) < session.wait_started_at_ms:
                return None
            session.pending_replies.append(reply)
            session.conversation_state = "reply_received"
            self._reply_condition.notify_all()
            return session.routing

    def wait_for_reply(self, routing: Routing, timeout_seconds: float | None) -> ReplyRecord | None:
        key = self._key(routing)
        with self._reply_condition:
            session = self.get_or_create_session(routing)
            if session.pending_replies:
                return self._consume_pending_reply(session)
            notified = self._reply_condition.wait_for(
                lambda: bool(self._sessions[key].pending_replies),
                timeout=timeout_seconds,
            )
            if not notified and timeout_seconds is not None:
                session.conversation_state = "idle"
                session.pending_replies.clear()
                session.wait_started_at_ms = 0
                return None
            return self._consume_pending_reply(self._sessions[key])

    def channel_ids_for_guild(self, guild_id: str) -> list[str]:
        with self._lock:
            return [
                session.channel_id
                for session in self._sessions.values()
                if session.channel_id and session.routing.discord_guild_id == guild_id
            ]

    def forget_channels(self, channel_ids: list[str]) -> None:
        if not channel_ids:
            return
        with self._lock:
            removed = set(channel_ids)
            for channel_id in removed:
                self._channel_to_key.pop(channel_id, None)
            for session in self._sessions.values():
                if session.channel_id in removed:
                    session.channel_id = None
                    session.conversation_state = "idle"
                    session.pending_replies.clear()
                    session.wait_started_at_ms = 0

    def _consume_pending_reply(self, session: SessionState) -> ReplyRecord:
        reply = session.pending_replies.popleft()
        session.pending_replies.clear()
        session.conversation_state = "idle"
        session.wait_started_at_ms = 0
        return reply

    def _current_time_ms(self) -> int:
        return time.time_ns() // 1_000_000

    def _reply_created_at_ms(self, reply: ReplyRecord) -> int:
        try:
            return (int(reply.discord_message_id) >> 22) + self._DISCORD_EPOCH_MS
        except (TypeError, ValueError):
            try:
                return int(
                    datetime.fromisoformat(reply.received_at.replace("Z", "+00:00"))
                    .astimezone(timezone.utc)
                    .timestamp()
                    * 1000
                )
            except ValueError:
                return self._current_time_ms()
