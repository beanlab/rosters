from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import threading
from typing import Deque

from .models import ReplyRecord, Routing


@dataclass(slots=True)
class SessionState:
    routing: Routing
    channel_id: str | None = None
    conversation_state: str = "idle"
    pending_replies: Deque[ReplyRecord] = field(default_factory=deque)


class InMemoryBridgeStore:
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
            session.pending_replies.append(reply)
            session.conversation_state = "reply_received"
            self._reply_condition.notify_all()
            return session.routing

    def wait_for_reply(self, routing: Routing, timeout_seconds: float) -> ReplyRecord | None:
        key = self._key(routing)
        with self._reply_condition:
            session = self.get_or_create_session(routing)
            if session.pending_replies:
                return session.pending_replies.popleft()
            notified = self._reply_condition.wait_for(
                lambda: bool(self._sessions[key].pending_replies),
                timeout=timeout_seconds,
            )
            if not notified:
                return None
            return self._sessions[key].pending_replies.popleft()

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
