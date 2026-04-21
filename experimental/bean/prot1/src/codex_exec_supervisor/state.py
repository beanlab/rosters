from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import RLock
from typing import Any

from .config import RuntimeConfig
from .ids import IdFactory, RuntimeClock
from .models import Mailbox, MailboxMessage, Message, MessageRole, Session, Worker, WorkerStatus


class UnknownWorkerError(KeyError):
    """Raised when a worker identifier does not belong to the session."""


class UnknownSessionError(KeyError):
    """Raised when a session identifier does not belong to the supervisor state."""


class StaleWorkerError(RuntimeError):
    """Raised when a worker is known but no longer allowed to use the bridge."""


@dataclass
class SupervisorState:
    config: RuntimeConfig
    logger: logging.Logger
    clock: RuntimeClock
    ids: IdFactory
    session: Session
    _lock: RLock

    @classmethod
    def create(
        cls,
        config: RuntimeConfig,
        logger: logging.Logger,
        clock: RuntimeClock | None = None,
        ids: IdFactory | None = None,
    ) -> "SupervisorState":
        runtime_clock = clock or RuntimeClock()
        id_factory = ids or IdFactory()
        created_at = runtime_clock.now()
        session = Session(
            session_id=id_factory.session_id(config.session_id_prefix),
            created_at=created_at,
        )
        logger.info("created session session_id=%s", session.session_id)
        return cls(
            config=config,
            logger=logger,
            clock=runtime_clock,
            ids=id_factory,
            session=session,
            _lock=RLock(),
        )

    def register_worker(self, metadata: dict[str, Any] | None = None) -> Worker:
        with self._lock:
            now = self.clock.now()
            worker = Worker(
                worker_id=self.ids.worker_id(self.config.worker_id_prefix),
                status=WorkerStatus.CREATED,
                created_at=now,
                updated_at=now,
                metadata=dict(metadata or {}),
            )
            self.session.workers[worker.worker_id] = worker
            self.session.mailboxes[worker.worker_id] = Mailbox(worker_id=worker.worker_id)
            self.logger.info("registered worker worker_id=%s", worker.worker_id)
            return worker

    def set_worker_status(self, worker_id: str, status: WorkerStatus) -> Worker:
        with self._lock:
            worker = self.require_worker(worker_id)
            worker.set_status(status, self.clock.now())
            self.logger.info(
                "worker state changed worker_id=%s status=%s",
                worker.worker_id,
                worker.status.value,
            )
            return worker

    def append_message(
        self,
        worker_id: str,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        with self._lock:
            self.require_worker(worker_id)
            message = Message(
                message_id=self.ids.message_id(),
                worker_id=worker_id,
                role=role,
                content=content,
                timestamp=self.clock.now(),
                metadata=dict(metadata or {}),
            )
            self.session.transcript.append(message)
            self.logger.info(
                "appended message message_id=%s worker_id=%s role=%s",
                message.message_id,
                message.worker_id,
                message.role.value,
            )
            return message

    def enqueue_user_message(
        self,
        worker_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MailboxMessage:
        with self._lock:
            self.ensure_worker_active(worker_id)
            mailbox = self.require_mailbox(worker_id)
            normalized_metadata = dict(metadata or {})
            message_id = self.ids.message_id()
            now = self.clock.now()
            message = MailboxMessage(
                message_id=message_id,
                worker_id=worker_id,
                content=content,
                timestamp=now,
                metadata=normalized_metadata,
            )
            mailbox.put(message)
            self.session.transcript.append(
                Message(
                    message_id=message_id,
                    worker_id=worker_id,
                    role=MessageRole.USER,
                    content=content,
                    timestamp=now,
                    metadata=normalized_metadata,
                )
            )
            self.logger.info("queued mailbox message worker_id=%s", worker_id)
            return message

    def get_next_user_message(
        self,
        worker_id: str,
        timeout_seconds: float | None = None,
    ) -> MailboxMessage | None:
        mailbox = self.require_mailbox(worker_id)
        timeout = self.config.mailbox_timeout_seconds if timeout_seconds is None else timeout_seconds
        message = mailbox.get(timeout)
        if message is None:
            self.logger.info("mailbox timeout worker_id=%s timeout_seconds=%s", worker_id, timeout)
        else:
            self.logger.info("delivered mailbox message worker_id=%s", worker_id)
        return message

    def transcript_snapshot(self) -> list[Message]:
        with self._lock:
            return list(self.session.transcript)

    def require_session(self, session_id: str) -> Session:
        if self.session.session_id != session_id:
            raise UnknownSessionError(f"unknown session_id={session_id}")
        return self.session

    def require_worker(self, worker_id: str) -> Worker:
        worker = self.session.workers.get(worker_id)
        if worker is None:
            raise UnknownWorkerError(f"unknown worker_id={worker_id}")
        return worker

    def require_mailbox(self, worker_id: str) -> Mailbox:
        mailbox = self.session.mailboxes.get(worker_id)
        if mailbox is None:
            raise UnknownWorkerError(f"unknown worker_id={worker_id}")
        return mailbox

    def ensure_worker_active(self, worker_id: str) -> Worker:
        worker = self.require_worker(worker_id)
        if worker.status in {WorkerStatus.STOPPING, WorkerStatus.STOPPED, WorkerStatus.FAILED}:
            raise StaleWorkerError(
                f"stale worker_id={worker_id} status={worker.status.value}"
            )
        return worker
