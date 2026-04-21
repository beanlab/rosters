from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
import threading
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RuntimeClock:
    """Centralized time source so later tests can replace it."""

    def now(self) -> datetime:
        return utc_now()


@dataclass
class IdFactory:
    """Centralized identifier generation for sessions, workers, and messages."""

    _message_counter: count = field(default_factory=lambda: count(1), init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def session_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:12]}"

    def worker_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:8]}"

    def message_id(self) -> str:
        with self._lock:
            sequence = next(self._message_counter)
        return f"msg-{sequence:06d}"
