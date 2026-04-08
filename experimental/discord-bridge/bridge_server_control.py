from __future__ import annotations

import contextlib
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


BRIDGE_ROOT = Path(__file__).resolve().parent
MYTEAM_ROOT = BRIDGE_ROOT.parent
PROJECT_ROOT = MYTEAM_ROOT.parent
SERVER_ROOT = BRIDGE_ROOT / "server"
SERVER_SCRIPT = SERVER_ROOT / "run_bridge_server.py"
START_LOCK_FILE = SERVER_ROOT / ".bridge-server.lock"
SERVER_LOG_FILE = SERVER_ROOT / ".bridge-server.log"
SERVER_PID_FILE = SERVER_ROOT / ".bridge-server.pid"
LOCAL_BRIDGE_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True, slots=True)
class LocalBridgeStopResult:
    stopped: bool
    forced: bool
    pid: int | None = None
    signal_name: str = ""


def ensure_local_bridge(api_base_url: str) -> None:
    parsed = urlparse(api_base_url)
    if (parsed.scheme or "http").lower() != "http":
        return
    if (parsed.hostname or "").lower() not in LOCAL_BRIDGE_HOSTS:
        return
    if _bridge_is_healthy(api_base_url):
        return

    startup_timeout = float(os.getenv("BRIDGE_SERVER_START_TIMEOUT_SECONDS", "20"))
    with _startup_lock():
        if _bridge_is_healthy(api_base_url):
            return
        _start_local_bridge_process(parsed)
        deadline = time.monotonic() + startup_timeout
        while time.monotonic() < deadline:
            if _bridge_is_healthy(api_base_url):
                return
            time.sleep(0.25)

    raise SystemExit(
        f"bridge server did not become ready at {api_base_url} within {startup_timeout:g}s; "
        f"see {SERVER_LOG_FILE}"
    )


def _bridge_is_healthy(api_base_url: str) -> bool:
    health_url = f"{api_base_url.rstrip('/')}/healthz"
    request = Request(url=health_url, method="GET")
    try:
        with urlopen(request, timeout=1.5) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def _start_local_bridge_process(parsed_base_url) -> None:
    if not SERVER_SCRIPT.exists():
        raise SystemExit(f"missing packaged bridge server script: {SERVER_SCRIPT}")

    command = [sys.executable, str(SERVER_SCRIPT)]
    env_file = _resolve_server_env_file()
    if env_file is not None:
        command.extend(["--env-file", str(env_file)])
    if parsed_base_url.hostname:
        command.extend(["--host", parsed_base_url.hostname])
    if parsed_base_url.port:
        command.extend(["--port", str(parsed_base_url.port)])

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    with SERVER_LOG_FILE.open("ab") as log_file:
        process = subprocess.Popen(
            command,
            cwd=SERVER_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        SERVER_PID_FILE.write_text(f"{process.pid}\n", encoding="utf-8")
        time.sleep(0.2)
        return_code = process.poll()
        if return_code is not None:
            _clear_server_pid_file()
            raise SystemExit(
                f"bridge server exited immediately with code {return_code}; see {SERVER_LOG_FILE}"
            )


def stop_local_bridge_process(timeout_seconds: float = 5.0) -> LocalBridgeStopResult:
    pids = _discover_local_bridge_pids()
    if not pids:
        _clear_server_pid_file()
        return LocalBridgeStopResult(stopped=False, forced=False)

    _signal_processes(pids, signal.SIGTERM)
    if _wait_for_exit(pids, timeout_seconds):
        _clear_server_pid_file()
        return LocalBridgeStopResult(
            stopped=True,
            forced=True,
            pid=min(pids),
            signal_name="SIGTERM",
        )

    _signal_processes(pids, signal.SIGKILL)
    _wait_for_exit(pids, 1.0)
    _clear_server_pid_file()
    return LocalBridgeStopResult(
        stopped=True,
        forced=True,
        pid=min(pids),
        signal_name="SIGKILL",
    )


def _resolve_server_env_file() -> Path | None:
    configured = os.getenv("BRIDGE_SERVER_ENV_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return path
        raise SystemExit(f"configured BRIDGE_SERVER_ENV_FILE does not exist: {path}")
    project_env = PROJECT_ROOT / ".env"
    if project_env.exists():
        return project_env
    return None


def _discover_local_bridge_pids() -> list[int]:
    pids: set[int] = set()

    pid = _read_server_pid_file()
    if pid is not None and _process_is_running(pid):
        pids.add(pid)

    if pids or os.name != "posix":
        return sorted(pids)

    try:
        output = subprocess.check_output(
            ["ps", "-eo", "pid=,args="],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return sorted(pids)

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pid_text, args = parts
        if not _looks_like_bridge_server_command(args):
            continue
        with contextlib.suppress(ValueError):
            pid = int(pid_text)
            if pid != os.getpid() and _process_is_running(pid):
                pids.add(pid)
    return sorted(pids)


def _read_server_pid_file() -> int | None:
    try:
        value = SERVER_PID_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _clear_server_pid_file() -> None:
    with contextlib.suppress(FileNotFoundError):
        SERVER_PID_FILE.unlink()


def _looks_like_bridge_server_command(args: str) -> bool:
    normalized = args.replace("\\", "/")
    return normalized.endswith("/discord-bridge/server/run_bridge_server.py") or (
        "/discord-bridge/server/run_bridge_server.py " in normalized
    )


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_processes(pids: list[int], sig: signal.Signals) -> None:
    for pid in pids:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, sig)


def _wait_for_exit(pids: list[int], timeout_seconds: float) -> bool:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() < deadline:
        if not any(_process_is_running(pid) for pid in pids):
            return True
        time.sleep(0.1)
    return not any(_process_is_running(pid) for pid in pids)


@contextmanager
def _startup_lock():
    START_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with START_LOCK_FILE.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
