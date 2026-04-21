from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Condition
from typing import Any


class WorkerStatus(str, Enum):
    CREATED = "created"
    STARTING = "starting"
    IDLE = "idle"
    WAITING_FOR_MESSAGE = "waiting_for_message"
    BUSY = "busy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class MessageRole(str, Enum):
    USER = "user"
    WORKER = "worker"
    SYSTEM = "system"


@dataclass(frozen=True)
class Message:
    message_id: str
    worker_id: str
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MailboxMessage:
    message_id: str
    worker_id: str
    content: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Mailbox:
    worker_id: str
    _queue: deque[MailboxMessage] = field(default_factory=deque, init=False)
    _condition: Condition = field(default_factory=Condition, init=False)

    def put(self, message: MailboxMessage) -> None:
        with self._condition:
            self._queue.append(message)
            self._condition.notify()

    def get(self, timeout_seconds: float | None = None) -> MailboxMessage | None:
        with self._condition:
            if timeout_seconds is None:
                while not self._queue:
                    self._condition.wait()
            elif not self._queue:
                self._condition.wait(timeout_seconds)
            if not self._queue:
                return None
            return self._queue.popleft()

    def size(self) -> int:
        with self._condition:
            return len(self._queue)


@dataclass
class Worker:
    worker_id: str
    status: WorkerStatus = WorkerStatus.CREATED
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_status(self, status: WorkerStatus, timestamp: datetime) -> None:
        self.status = status
        self.updated_at = timestamp


@dataclass
class Session:
    session_id: str
    created_at: datetime
    workers: dict[str, Worker] = field(default_factory=dict)
    transcript: list[Message] = field(default_factory=list)
    mailboxes: dict[str, Mailbox] = field(default_factory=dict)
