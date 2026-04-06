from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
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
LOCAL_BRIDGE_HOSTS = {"127.0.0.1", "localhost", "::1"}


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
        time.sleep(0.2)
        return_code = process.poll()
        if return_code is not None:
            raise SystemExit(
                f"bridge server exited immediately with code {return_code}; see {SERVER_LOG_FILE}"
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
