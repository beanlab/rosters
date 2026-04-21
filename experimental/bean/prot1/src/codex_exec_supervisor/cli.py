from __future__ import annotations

import argparse
import json
import sys

from .bridge import BridgeDispatcher, BridgeServer, default_socket_path, send_bridge_request
from .config import RuntimeConfig
from .diagnostics import configure_logging
from .ids import IdFactory, RuntimeClock
from .models import WorkerStatus
from .state import SupervisorState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex exec supervisor")
    parser.add_argument(
        "--demo-message",
        default="Supervisor foundation check",
        help="Message content used by the demo command.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("start", help="Initialize an empty supervisor session.")
    subparsers.add_parser("demo", help="Run a local state demo for milestone verification.")

    bridge_serve = subparsers.add_parser(
        "bridge-serve",
        help="Run the local bridge server without the TUI.",
    )
    bridge_serve.add_argument("--socket-path", default=None, help="Unix socket path for the bridge.")
    bridge_serve.add_argument(
        "--register-worker",
        action="store_true",
        help="Register one worker on startup for local verification.",
    )
    bridge_serve.add_argument("--json", action="store_true", help="Print startup details as JSON.")

    bridge_client = subparsers.add_parser(
        "bridge-client",
        help="Relay one JSON-RPC request to the active bridge socket.",
    )
    bridge_client.add_argument("--socket-path", default=None, help="Unix socket path for the bridge.")

    register_worker = subparsers.add_parser(
        "register-worker",
        help="Register a worker through the running bridge server.",
    )
    register_worker.add_argument("--socket-path", default=None, help="Unix socket path for the bridge.")
    register_worker.add_argument("--session-id", required=True, help="Supervisor session identifier.")
    register_worker.add_argument("--json", action="store_true", help="Print the full JSON result.")

    enqueue_message = subparsers.add_parser(
        "enqueue-user-message",
        help="Queue a user message through the running bridge server.",
    )
    enqueue_message.add_argument("--socket-path", default=None, help="Unix socket path for the bridge.")
    enqueue_message.add_argument("--session-id", required=True, help="Supervisor session identifier.")
    enqueue_message.add_argument("--worker-id", required=True, help="Target worker identifier.")
    enqueue_message.add_argument("content", nargs="+", help="Message content to queue.")
    enqueue_message.add_argument("--json", action="store_true", help="Print the full JSON result.")

    session_info = subparsers.add_parser(
        "session-info",
        help="Inspect the current bridge-backed session state.",
    )
    session_info.add_argument("--socket-path", default=None, help="Unix socket path for the bridge.")
    session_info.add_argument("--session-id", required=True, help="Supervisor session identifier.")
    session_info.add_argument("--json", action="store_true", help="Print the full JSON result.")
    return parser


def run_start(state: SupervisorState) -> int:
    state.logger.info("supervisor initialized session_id=%s", state.session.session_id)
    state.logger.info("supervisor shutdown session_id=%s", state.session.session_id)
    return 0


def run_demo(state: SupervisorState, demo_message: str) -> int:
    worker = state.register_worker(metadata={"visible": True})
    state.set_worker_status(worker.worker_id, WorkerStatus.IDLE)
    state.enqueue_user_message(worker.worker_id, demo_message, metadata={"source": "demo"})
    mailbox_message = state.get_next_user_message(worker.worker_id, timeout_seconds=0.1)
    if mailbox_message is None:
        state.logger.error("demo failed to retrieve mailbox message")
        return 1
    message = state.transcript_snapshot()[-1]
    print(
        f"session={state.session.session_id} worker={worker.worker_id} "
        f"message={message.message_id} transcript_size={len(state.session.transcript)}"
    )
    state.logger.info("supervisor shutdown session_id=%s", state.session.session_id)
    return 0


def _print_result(result: dict[str, object], json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(result, sort_keys=True))
        return
    print(" ".join(f"{key}={value}" for key, value in result.items()))


def _bridge_request(
    socket_path: str | None,
    method: str,
    params: dict[str, object],
) -> dict[str, object]:
    path = socket_path or RuntimeConfig.from_env().bridge_socket_path
    if not path:
        raise RuntimeError("bridge socket path is required")
    response = send_bridge_request(
        path,
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    if "error" in response:
        error = response["error"]
        raise RuntimeError(f"{error['message']} (code={error['code']})")
    return response["result"]


def run_bridge_client(socket_path: str | None) -> int:
    path = socket_path or RuntimeConfig.from_env().bridge_socket_path
    if not path:
        print("bridge socket path is required", file=sys.stderr)
        return 2
    request = sys.stdin.readline()
    if not request:
        print("bridge-client requires one JSON-RPC request on stdin", file=sys.stderr)
        return 2
    try:
        response = send_bridge_request(path, json.loads(request))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(response, sort_keys=True))
    return 0


def run_bridge_serve(
    state: SupervisorState,
    socket_path: str | None,
    register_worker: bool,
    json_mode: bool,
) -> int:
    resolved_socket_path = socket_path or state.config.bridge_socket_path or default_socket_path(
        state.session.session_id
    )
    state.config = RuntimeConfig(
        session_id_prefix=state.config.session_id_prefix,
        worker_id_prefix=state.config.worker_id_prefix,
        mailbox_timeout_seconds=state.config.mailbox_timeout_seconds,
        bridge_timeout_seconds=state.config.bridge_timeout_seconds,
        bridge_socket_path=resolved_socket_path,
        log_level=state.config.log_level,
    )
    startup: dict[str, object] = {
        "session_id": state.session.session_id,
        "socket_path": resolved_socket_path,
    }
    if register_worker:
        worker = state.register_worker(metadata={"visible": True})
        state.set_worker_status(worker.worker_id, WorkerStatus.IDLE)
        startup["worker_id"] = worker.worker_id
    _print_result(startup, json_mode)
    try:
        BridgeServer(resolved_socket_path, BridgeDispatcher(state), state.logger).serve_forever()
    except KeyboardInterrupt:
        state.logger.info("bridge server interrupted session_id=%s", state.session.session_id)
    state.logger.info("supervisor shutdown session_id=%s", state.session.session_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bridge-client":
        return run_bridge_client(args.socket_path)

    config = RuntimeConfig.from_env()
    logger = configure_logging(config.log_level)
    state = SupervisorState.create(
        config=config,
        logger=logger,
        clock=RuntimeClock(),
        ids=IdFactory(),
    )

    if args.command in (None, "start"):
        return run_start(state)
    if args.command == "demo":
        return run_demo(state, args.demo_message)
    if args.command == "bridge-serve":
        return run_bridge_serve(state, args.socket_path, args.register_worker, args.json)
    if args.command == "register-worker":
        result = _bridge_request(
            args.socket_path,
            "register_worker",
            {"session_id": args.session_id, "metadata": {"visible": True}},
        )
        _print_result(
            {
                "session_id": result["session_id"],
                "worker_id": result["worker"]["worker_id"],
                "status": result["worker"]["status"],
            },
            args.json,
        )
        return 0
    if args.command == "enqueue-user-message":
        result = _bridge_request(
            args.socket_path,
            "enqueue_user_message",
            {
                "session_id": args.session_id,
                "worker_id": args.worker_id,
                "content": " ".join(args.content),
            },
        )
        _print_result(
            {
                "status": result["status"],
                "worker_id": result["worker_id"],
                "message_id": result["message"]["message_id"],
            },
            args.json,
        )
        return 0
    if args.command == "session-info":
        result = _bridge_request(
            args.socket_path,
            "session_info",
            {"session_id": args.session_id},
        )
        if args.json:
            _print_result(result, True)
        else:
            print(
                f"session_id={result['session_id']} transcript_size={result['transcript_size']} "
                f"workers={len(result['workers'])} socket_path={result['socket_path']}"
            )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2
