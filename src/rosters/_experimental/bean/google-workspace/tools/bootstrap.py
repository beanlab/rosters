#!/usr/bin/env python3
"""Create and validate the private environment used by Google Workspace skills."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Sequence

DEFAULT_WORKSPACE = Path("~/.agents/scratch/google-workspace").expanduser()
REQUIREMENTS = Path(__file__).with_name("requirements.txt")
DIRECTORIES = ("tokens", "scripts", "output")
STAMP_NAME = ".bootstrap"
BOOTSTRAP_VERSION = "1"
IMPORT_CHECK = "import google.auth, google_auth_oauthlib, googleapiclient.discovery"


class BootstrapError(Exception):
    """An expected bootstrap failure."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or validate the private Google Workspace environment."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="workspace to manage (default: %(default)s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check readiness without changing anything",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress successful check output",
    )
    return parser


def private_directory(path: Path, create: bool) -> None:
    if path.is_symlink():
        raise BootstrapError(f"Refusing symbolic-link directory: {path}")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.chmod(0o700)
    if not path.is_dir():
        raise BootstrapError(f"Required directory is missing: {path}")
    if path.stat().st_mode & 0o077:
        raise BootstrapError(f"Directory is not owner-only: {path}")


def requirement_fingerprint() -> str:
    try:
        requirements = REQUIREMENTS.read_bytes()
    except OSError as error:
        raise BootstrapError(f"Cannot read dependency specification: {REQUIREMENTS}") from error
    payload = b"\0".join(
        (
            BOOTSTRAP_VERSION.encode("ascii"),
            f"{sys.version_info.major}.{sys.version_info.minor}".encode("ascii"),
            requirements,
        )
    )
    return hashlib.sha256(payload).hexdigest()


def paths(workspace: Path) -> tuple[Path, Path, Path]:
    root = workspace.expanduser().resolve()
    venv = root / "venv"
    interpreter = venv / "bin" / "python"
    return root, venv, interpreter


def check(workspace: Path) -> None:
    root, venv, interpreter = paths(workspace)
    private_directory(root, create=False)
    for name in DIRECTORIES:
        private_directory(root / name, create=False)
    private_directory(venv, create=False)

    if not interpreter.is_file():
        raise BootstrapError(f"Virtual environment interpreter is missing: {interpreter}")

    stamp = root / STAMP_NAME
    if stamp.is_symlink() or not stamp.is_file():
        raise BootstrapError("Bootstrap stamp is missing.")
    try:
        recorded = stamp.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise BootstrapError("Bootstrap stamp cannot be read.") from error
    if recorded != requirement_fingerprint():
        raise BootstrapError("Dependencies or Python version changed; rebuild is required.")

    completed = subprocess.run(
        [str(interpreter), "-c", IMPORT_CHECK],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise BootstrapError("Virtual environment dependencies are unavailable.")


def build(workspace: Path) -> None:
    root, venv, interpreter = paths(workspace)
    private_directory(root, create=True)
    for name in DIRECTORIES:
        private_directory(root / name, create=True)

    if venv.is_symlink():
        raise BootstrapError(f"Refusing symbolic-link virtual environment: {venv}")
    if not interpreter.is_file():
        if venv.exists():
            if not venv.is_dir():
                raise BootstrapError(f"Virtual environment path is not a directory: {venv}")
            shutil.rmtree(venv)
        completed = subprocess.run(
            [sys.executable, "-m", "venv", str(venv)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=180,
        )
        if completed.returncode != 0:
            raise BootstrapError("Could not create the Google Workspace virtual environment.")
    private_directory(venv, create=True)

    completed = subprocess.run(
        [
            str(interpreter),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--requirement",
            str(REQUIREMENTS),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=600,
    )
    if completed.returncode != 0:
        raise BootstrapError("Could not install the Google Workspace Python dependencies.")

    write_stamp(root / STAMP_NAME, requirement_fingerprint())
    check(workspace)


def write_stamp(path: Path, value: str) -> None:
    descriptor: Optional[int] = None
    temporary: Optional[Path] = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".bootstrap.", dir=path.parent)
        temporary = Path(name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = None
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(0o600)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            check(args.workspace)
            if not args.quiet:
                print(f"Google Workspace environment is ready: {args.workspace.expanduser()}")
        else:
            build(args.workspace)
            print(f"Google Workspace environment bootstrapped: {args.workspace.expanduser()}")
        return 0
    except (BootstrapError, subprocess.TimeoutExpired) as error:
        if not args.quiet:
            print(f"Bootstrap error: {error}", file=sys.stderr)
        return 1
    except OSError:
        if not args.quiet:
            print("Bootstrap error: local filesystem operation failed.", file=sys.stderr)
        return 1
    except Exception:
        if not args.quiet:
            print("Bootstrap error: unexpected bootstrap failure.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
