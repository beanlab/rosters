from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RuntimeConfig:
    session_id_prefix: str = "session"
    worker_id_prefix: str = "worker"
    mailbox_timeout_seconds: float = 30.0
    bridge_timeout_seconds: float = 30.0
    bridge_socket_path: str | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            session_id_prefix=os.getenv("CODEX_SUPERVISOR_SESSION_PREFIX", "session"),
            worker_id_prefix=os.getenv("CODEX_SUPERVISOR_WORKER_PREFIX", "worker"),
            mailbox_timeout_seconds=float(
                os.getenv("CODEX_SUPERVISOR_MAILBOX_TIMEOUT_SECONDS", "30.0")
            ),
            bridge_timeout_seconds=float(os.getenv("CODEX_BRIDGE_TIMEOUT", "30.0")),
            bridge_socket_path=os.getenv("CODEX_SUPERVISOR_SOCKET_PATH"),
            log_level=os.getenv("CODEX_SUPERVISOR_LOG_LEVEL", "INFO").upper(),
        )
