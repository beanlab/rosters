from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class Routing:
    workspace_id: str
    session_id: str
    agent_id: str
    agent_name: str
    agent_kind: str
    discord_guild_id: str
    timestamp: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Routing":
        timestamp = str(payload.get("timestamp") or utc_now_iso())
        return cls(
            workspace_id=str(payload["workspace_id"]),
            session_id=str(payload["session_id"]),
            agent_id=str(payload["agent_id"]),
            agent_name=str(payload["agent_name"]),
            agent_kind=str(payload["agent_kind"]),
            discord_guild_id=str(payload["discord_guild_id"]),
            timestamp=timestamp,
        )

    def key(self) -> tuple[str, str, str, str]:
        return (
            self.workspace_id,
            self.session_id,
            self.agent_id,
            self.discord_guild_id,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_kind": self.agent_kind,
            "discord_guild_id": self.discord_guild_id,
            "timestamp": self.timestamp,
        }


@dataclass(slots=True)
class MessageRequest:
    routing: Routing
    message_id: str
    content: str
    expects_reply: bool

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MessageRequest":
        routing = Routing.from_dict(dict(payload["routing"]))
        message = dict(payload["message"])
        return cls(
            routing=routing,
            message_id=str(message.get("message_id") or f"msg-{uuid.uuid4().hex}"),
            content=str(message["content"]),
            expects_reply=bool(message.get("expects_reply", True)),
        )


@dataclass(slots=True)
class StateUpdateRequest:
    routing: Routing
    state: str
    ttl_seconds: int

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "StateUpdateRequest":
        return cls(
            routing=Routing.from_dict(dict(payload["routing"])),
            state=str(payload["state"]),
            ttl_seconds=int(payload.get("ttl_seconds", 12)),
        )


@dataclass(slots=True)
class SubagentExchange:
    top_level_agent_name: str
    to_subagent: str
    subagent_name: str
    to_top_level: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SubagentExchange":
        return cls(
            top_level_agent_name=str(payload["top_level_agent_name"]),
            to_subagent=str(payload["to_subagent"]),
            subagent_name=str(payload["subagent_name"]),
            to_top_level=str(payload["to_top_level"]),
        )

    def render(self) -> str:
        return (
            f"Top Level Agent: {self.to_subagent}\n"
            f"{self.subagent_name}: {self.to_top_level}"
        )


@dataclass(slots=True)
class SubagentLogRequest:
    routing: Routing
    exchange: SubagentExchange

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SubagentLogRequest":
        return cls(
            routing=Routing.from_dict(dict(payload["routing"])),
            exchange=SubagentExchange.from_dict(dict(payload["exchange"])),
        )


@dataclass(slots=True)
class ReplyRecord:
    reply_id: str
    content: str
    discord_message_id: str
    discord_user_id: str
    received_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "reply_id": self.reply_id,
            "content": self.content,
            "discord_message_id": self.discord_message_id,
            "discord_user_id": self.discord_user_id,
            "received_at": self.received_at,
        }


@dataclass(slots=True)
class DeliveryRecord:
    channel_id: str
    delivery_id: str
    conversation_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": True,
            "channel_id": self.channel_id,
            "delivery_id": self.delivery_id,
            "conversation_state": self.conversation_state,
        }

