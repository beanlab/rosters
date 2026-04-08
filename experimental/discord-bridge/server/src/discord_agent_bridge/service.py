from __future__ import annotations

import threading
import uuid
from typing import Callable

from .discord_gateway import DiscordGateway
from .models import (
    DeliveryRecord,
    MessageRequest,
    ReplyRecord,
    Routing,
    StateUpdateRequest,
    SubagentLogRequest,
    utc_now_iso,
)
from .store import InMemoryBridgeStore


class BridgeService:
    def __init__(
        self,
        store: InMemoryBridgeStore,
        gateway: DiscordGateway,
        on_wait_started: Callable[[], None] | None = None,
        on_wait_finished: Callable[[], None] | None = None,
    ) -> None:
        self.store = store
        self.gateway = gateway
        self._channel_lock = threading.RLock()
        self._on_wait_started = on_wait_started
        self._on_wait_finished = on_wait_finished

    def _begin_waiting(self, routing: Routing) -> None:
        if self._on_wait_started is not None:
            self._on_wait_started()
        self.store.begin_waiting_for_reply(routing)

    def _maybe_stop_waiting(self) -> None:
        if self._on_wait_finished is None:
            return
        if not self.store.has_awaiting_sessions():
            self._on_wait_finished()

    def _ensure_channel(self, routing: Routing) -> str:
        with self._channel_lock:
            existing_channel_id = self.store.get_channel_id(routing)
            channel_id = self.gateway.ensure_channel(routing, existing_channel_id)
            self.store.bind_channel(routing, channel_id)
            return channel_id

    def post_message(self, request: MessageRequest) -> DeliveryRecord:
        channel_id = self._ensure_channel(request.routing)
        if request.expects_reply:
            self._begin_waiting(request.routing)
        try:
            delivery_id = self.gateway.send_message(channel_id, request.content)
        except Exception:
            if request.expects_reply:
                self.store.cancel_waiting_for_reply(request.routing)
                self._maybe_stop_waiting()
            raise

        state = "awaiting_user" if request.expects_reply else "delivered"
        if not request.expects_reply:
            self.store.set_conversation_state(request.routing, state)
        self.gateway.stop_typing(channel_id)
        return DeliveryRecord(
            channel_id=channel_id,
            delivery_id=delivery_id or f"delivery-{uuid.uuid4().hex}",
            conversation_state=state,
        )

    def update_state(self, request: StateUpdateRequest) -> dict[str, object]:
        channel_id = self._ensure_channel(request.routing)
        if request.state == "awaiting_user":
            self._begin_waiting(request.routing)
        else:
            self.store.cancel_waiting_for_reply(request.routing, state=request.state)
            self._maybe_stop_waiting()
        if request.state == "working":
            self.gateway.refresh_typing(channel_id, request.ttl_seconds)
        else:
            self.gateway.stop_typing(channel_id)
        return {
            "ok": True,
            "channel_id": channel_id,
            "conversation_state": request.state,
        }

    def post_subagent_log(self, request: SubagentLogRequest) -> dict[str, object]:
        channel_id = self._ensure_channel(request.routing)
        delivery_id = self.gateway.send_message(channel_id, request.exchange.render())
        return {
            "ok": True,
            "channel_id": channel_id,
            "delivery_id": delivery_id,
        }

    def request_shutdown(self) -> int:
        cancelled = self.store.request_shutdown()
        self._maybe_stop_waiting()
        return cancelled

    def receive_discord_reply(
        self,
        channel_id: str,
        content: str,
        discord_user_id: str,
        discord_message_id: str,
    ) -> Routing | None:
        reply = ReplyRecord(
            reply_id=f"reply-{uuid.uuid4().hex}",
            content=content,
            discord_message_id=discord_message_id,
            discord_user_id=discord_user_id,
            received_at=utc_now_iso(),
        )
        return self.store.enqueue_reply(channel_id, reply)

    def wait_for_reply(self, routing: Routing, timeout_seconds: float | None) -> dict[str, object]:
        reply, shutdown_requested = self.store.wait_for_reply(routing, timeout_seconds)
        self._maybe_stop_waiting()
        if reply is None:
            return {"ok": True, "reply": None, "shutdown": shutdown_requested}
        return {"ok": True, "reply": reply.to_dict(), "shutdown": False}

    def acknowledge_reply(self, routing: Routing, reply_id: str) -> None:
        self.store.acknowledge_reply(routing, reply_id)
