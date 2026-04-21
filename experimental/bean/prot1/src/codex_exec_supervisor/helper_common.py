from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from typing import Any

from .rpc import decode_response_line


class HelperInvocationError(RuntimeError):
    """Raised when a helper cannot reach or interpret the bridge client."""


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise HelperInvocationError(f"missing required environment variable: {name}")
    return value


def default_bridge_command() -> list[str]:
    configured = os.getenv("CODEX_BRIDGE_COMMAND")
    if configured:
        return shlex.split(configured)
    return [sys.executable, "-m", "codex_exec_supervisor", "bridge-client"]


def helper_context() -> tuple[str, str]:
    return require_env("SESSION_ID"), require_env("WORKER_ID")


def default_timeout() -> float | None:
    raw = os.getenv("CODEX_BRIDGE_TIMEOUT")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise HelperInvocationError("CODEX_BRIDGE_TIMEOUT must be numeric") from exc
    if value < 0:
        raise HelperInvocationError("CODEX_BRIDGE_TIMEOUT must be non-negative")
    return value


def call_bridge(request: dict[str, Any]) -> dict[str, Any]:
    process = subprocess.run(
        default_bridge_command(),
        input=json.dumps(request, sort_keys=True) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip() or "bridge client failed"
        raise HelperInvocationError(detail)
    stdout = process.stdout.strip()
    if not stdout:
        raise HelperInvocationError("bridge client returned no output")
    response = decode_response_line(stdout)
    if response.is_error:
        error = response.error or {}
        raise HelperInvocationError(
            f"{error.get('message', 'bridge request failed')} "
            f"(code={error.get('code', 'unknown')})"
        )
    return response.result or {}
