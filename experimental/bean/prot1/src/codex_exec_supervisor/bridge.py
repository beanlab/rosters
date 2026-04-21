from __future__ import annotations

from datetime import datetime
import json
import logging
import os
import socket
import socketserver
from typing import Any

from .models import MailboxMessage, Message, MessageRole, Worker, WorkerStatus
from .rpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    STALE_WORKER,
    UNKNOWN_SESSION,
    UNKNOWN_WORKER,
    JsonRpcError,
    decode_request_line,
    encode_error,
    encode_success,
)
from .state import StaleWorkerError, SupervisorState, UnknownSessionError, UnknownWorkerError


def _require_string(params: dict[str, Any], name: str) -> str:
    value = params.get(name)
    if not isinstance(value, str) or not value:
        raise JsonRpcError(INVALID_PARAMS, f"{name} must be a non-empty string")
    return value


def _optional_dict(params: dict[str, Any], name: str) -> dict[str, Any]:
    value = params.get(name, {})
    if not isinstance(value, dict):
        raise JsonRpcError(INVALID_PARAMS, f"{name} must be an object")
    return value


def _optional_timeout(params: dict[str, Any], default_timeout: float) -> float:
    value = params.get("timeout_seconds")
    if value is None:
        return default_timeout
    if not isinstance(value, (int, float)) or value < 0:
        raise JsonRpcError(INVALID_PARAMS, "timeout_seconds must be a non-negative number")
    return float(value)


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _serialize_mailbox_message(message: MailboxMessage) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "worker_id": message.worker_id,
        "role": "user",
        "content": message.content,
        "timestamp": _serialize_datetime(message.timestamp),
        "metadata": message.metadata,
    }


def _serialize_transcript_message(message: Message) -> dict[str, Any]:
    return {
        "message_id": message.message_id,
        "worker_id": message.worker_id,
        "role": message.role.value,
        "content": message.content,
        "timestamp": _serialize_datetime(message.timestamp),
        "metadata": message.metadata,
    }


def _serialize_worker(worker: Worker) -> dict[str, Any]:
    return {
        "worker_id": worker.worker_id,
        "status": worker.status.value,
        "created_at": _serialize_datetime(worker.created_at) if worker.created_at else None,
        "updated_at": _serialize_datetime(worker.updated_at) if worker.updated_at else None,
        "metadata": worker.metadata,
    }


class BridgeDispatcher:
    def __init__(self, state: SupervisorState) -> None:
        self.state = state

    def handle_line(self, line: str) -> str:
        request_id: str | int | None = None
        try:
            request = decode_request_line(line)
            request_id = request.request_id
            result = self.dispatch(request.method, request.params)
            return encode_success(request.request_id, result)
        except JsonRpcError as exc:
            return encode_error(request_id, exc)
        except UnknownSessionError as exc:
            return encode_error(request_id, JsonRpcError(UNKNOWN_SESSION, str(exc)))
        except UnknownWorkerError as exc:
            return encode_error(request_id, JsonRpcError(UNKNOWN_WORKER, str(exc)))
        except StaleWorkerError as exc:
            return encode_error(request_id, JsonRpcError(STALE_WORKER, str(exc)))
        except Exception as exc:  # pragma: no cover
            self.state.logger.exception("bridge internal error")
            return encode_error(
                request_id,
                JsonRpcError(INTERNAL_ERROR, "internal bridge failure", {"detail": str(exc)}),
            )

    def dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "get_message":
            return self._get_message(params)
        if method == "send_message":
            return self._send_message(params)
        if method == "register_worker":
            return self._register_worker(params)
        if method == "enqueue_user_message":
            return self._enqueue_user_message(params)
        if method == "session_info":
            return self._session_info(params)
        raise JsonRpcError(METHOD_NOT_FOUND, f"unsupported method: {method}")

    def _validate_session_worker(self, params: dict[str, Any]) -> str:
        session_id = _require_string(params, "session_id")
        worker_id = _require_string(params, "worker_id")
        self.state.require_session(session_id)
        self.state.ensure_worker_active(worker_id)
        return worker_id

    def _get_message(self, params: dict[str, Any]) -> dict[str, Any]:
        worker_id = self._validate_session_worker(params)
        timeout_seconds = _optional_timeout(params, self.state.config.mailbox_timeout_seconds)
        self.state.set_worker_status(worker_id, WorkerStatus.WAITING_FOR_MESSAGE)
        message = self.state.get_next_user_message(worker_id, timeout_seconds=timeout_seconds)
        self.state.set_worker_status(worker_id, WorkerStatus.IDLE)
        if message is None:
            return {
                "status": "timeout",
                "session_id": self.state.session.session_id,
                "worker_id": worker_id,
                "timeout_seconds": timeout_seconds,
            }
        return {
            "status": "ok",
            "session_id": self.state.session.session_id,
            "worker_id": worker_id,
            "message": _serialize_mailbox_message(message),
        }

    def _send_message(self, params: dict[str, Any]) -> dict[str, Any]:
        worker_id = self._validate_session_worker(params)
        content = _require_string(params, "content")
        metadata = _optional_dict(params, "metadata")
        self.state.set_worker_status(worker_id, WorkerStatus.BUSY)
        message = self.state.append_message(
            worker_id,
            role=MessageRole.WORKER,
            content=content,
            metadata=metadata,
        )
        self.state.set_worker_status(worker_id, WorkerStatus.IDLE)
        return {
            "status": "ok",
            "session_id": self.state.session.session_id,
            "worker_id": worker_id,
            "message": _serialize_transcript_message(message),
        }

    def _register_worker(self, params: dict[str, Any]) -> dict[str, Any]:
        session_id = _require_string(params, "session_id")
        self.state.require_session(session_id)
        metadata = _optional_dict(params, "metadata")
        worker = self.state.register_worker(metadata=metadata)
        self.state.set_worker_status(worker.worker_id, WorkerStatus.IDLE)
        return {
            "session_id": self.state.session.session_id,
            "worker": _serialize_worker(self.state.require_worker(worker.worker_id)),
        }

    def _enqueue_user_message(self, params: dict[str, Any]) -> dict[str, Any]:
        worker_id = self._validate_session_worker(params)
        content = _require_string(params, "content")
        metadata = _optional_dict(params, "metadata")
        message = self.state.enqueue_user_message(worker_id, content, metadata=metadata)
        return {
            "status": "queued",
            "session_id": self.state.session.session_id,
            "worker_id": worker_id,
            "message": _serialize_mailbox_message(message),
        }

    def _session_info(self, params: dict[str, Any]) -> dict[str, Any]:
        session_id = _require_string(params, "session_id")
        session = self.state.require_session(session_id)
        return {
            "session_id": session.session_id,
            "created_at": _serialize_datetime(session.created_at),
            "transcript_size": len(session.transcript),
            "workers": [_serialize_worker(worker) for worker in session.workers.values()],
            "socket_path": self.state.config.bridge_socket_path,
        }


class _BridgeRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        line = self.rfile.readline()
        if not line:
            return
        response = self.server.dispatcher.handle_line(line.decode("utf-8").rstrip("\n"))
        self.wfile.write(response.encode("utf-8") + b"\n")
        self.wfile.flush()


class _ThreadingUnixStreamServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def __init__(self, socket_path: str, dispatcher: BridgeDispatcher) -> None:
        self.dispatcher = dispatcher
        super().__init__(socket_path, _BridgeRequestHandler)


class BridgeServer:
    def __init__(self, socket_path: str, dispatcher: BridgeDispatcher, logger: logging.Logger) -> None:
        self.socket_path = socket_path
        self.dispatcher = dispatcher
        self.logger = logger

    def serve_forever(self) -> None:
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        server = _ThreadingUnixStreamServer(self.socket_path, self.dispatcher)
        self.logger.info("bridge listening socket_path=%s", self.socket_path)
        try:
            server.serve_forever()
        finally:
            server.server_close()
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            self.logger.info("bridge stopped socket_path=%s", self.socket_path)


def default_socket_path(session_id: str) -> str:
    return f"/tmp/codex-exec-supervisor-{session_id}.sock"


def send_bridge_request(socket_path: str, request: dict[str, Any]) -> dict[str, Any]:
    line = json.dumps(request, sort_keys=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(line.encode("utf-8") + b"\n")
        response = b""
        while not response.endswith(b"\n"):
            chunk = client.recv(4096)
            if not chunk:
                break
            response += chunk
    if not response:
        raise RuntimeError("bridge returned no data")
    return json.loads(response.decode("utf-8"))
