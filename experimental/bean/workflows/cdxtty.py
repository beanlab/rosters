#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import pty
import select
import signal
import sys
import termios
import tty
from fcntl import ioctl


@dataclass
class AutoReplyRule:
    match: bytes
    reply: bytes
    used: bool = False


def _winsize(fd: int) -> bytes:
    return ioctl(fd, termios.TIOCGWINSZ, b"\0" * 8)


def _copy_winsize(src_fd: int, dst_fd: int) -> None:
    try:
        ioctl(dst_fd, termios.TIOCSWINSZ, _winsize(src_fd))
    except OSError:
        pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run codex under a child PTY so it behaves like a direct TTY session."
    )
    parser.add_argument(
        "--auto-reply",
        dest="auto_replies",
        action="append",
        nargs=2,
        metavar=("MATCH_TEXT", "REPLY_TEXT"),
        default=[],
        help=(
            "When MATCH_TEXT appears in child output, suppress it and inject REPLY_TEXT "
            "into the child PTY once. Escape sequences like \\n are supported."
        ),
    )
    parser.add_argument(
        "argv",
        nargs=argparse.REMAINDER,
        help="Command to run. Defaults to: codex",
    )
    return parser.parse_args()


def _decode_escapes(value: str) -> str:
    return bytes(value, "utf-8").decode("unicode_escape")


def _build_auto_reply_rules(items: list[list[str]]) -> list[AutoReplyRule]:
    rules: list[AutoReplyRule] = []
    for match_text, reply_text in items:
        match = _decode_escapes(match_text).encode("utf-8")
        if not match:
            raise SystemExit("--auto-reply MATCH_TEXT must not be empty")
        reply = _decode_escapes(reply_text).encode("utf-8")
        rules.append(AutoReplyRule(match=match, reply=reply))
    return rules


def _protected_suffix_length(buffer: bytes, rules: list[AutoReplyRule]) -> int:
    candidates = [rule.match for rule in rules if not rule.used]
    if not candidates:
        return 0

    max_keep = 0
    for match in candidates:
        upper = min(len(buffer), len(match) - 1)
        for size in range(upper, 0, -1):
            if buffer.endswith(match[:size]):
                max_keep = max(max_keep, size)
                break
    return max_keep


def _drain_child_output(
    pending: bytes,
    rules: list[AutoReplyRule],
    master_fd: int,
    parent_stdout: int,
) -> bytes:
    while True:
        earliest_index: int | None = None
        matched_rule: AutoReplyRule | None = None

        for rule in rules:
            if rule.used:
                continue
            index = pending.find(rule.match)
            if index == -1:
                continue
            if earliest_index is None or index < earliest_index:
                earliest_index = index
                matched_rule = rule

        if matched_rule is None or earliest_index is None:
            keep = _protected_suffix_length(pending, rules)
            flush_upto = len(pending) - keep
            if flush_upto > 0:
                os.write(parent_stdout, pending[:flush_upto])
                pending = pending[flush_upto:]
            return pending

        if earliest_index > 0:
            os.write(parent_stdout, pending[:earliest_index])

        pending = pending[earliest_index + len(matched_rule.match) :]
        matched_rule.used = True
        if matched_rule.reply:
            os.write(master_fd, matched_rule.reply)


def main() -> int:
    args = _parse_args()
    rules = _build_auto_reply_rules(args.auto_replies)
    argv = args.argv or ["codex"]
    if argv and argv[0] == "--":
        argv = argv[1:] or ["codex"]

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("cdxtty.py requires a real TTY on stdin/stdout", file=sys.stderr)
        return 2

    parent_stdin = sys.stdin.fileno()
    parent_stdout = sys.stdout.fileno()
    original_tty = termios.tcgetattr(parent_stdin)

    pid, master_fd = pty.fork()
    if pid == 0:
        os.execvp(argv[0], argv)

    _copy_winsize(parent_stdin, master_fd)

    def on_winch(_signum: int, _frame: object) -> None:
        _copy_winsize(parent_stdin, master_fd)

    previous_winch = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, on_winch)

    try:
        tty.setraw(parent_stdin)
        tty.setcbreak(parent_stdin)
        pending_output = b""

        while True:
            readable, _, _ = select.select([parent_stdin, master_fd], [], [])

            if parent_stdin in readable:
                data = os.read(parent_stdin, 1024)
                if not data:
                    os.close(master_fd)
                    break
                os.write(master_fd, data)

            if master_fd in readable:
                try:
                    data = os.read(master_fd, 1024)
                except OSError:
                    data = b""
                if not data:
                    if pending_output:
                        os.write(parent_stdout, pending_output)
                    break
                pending_output += data
                pending_output = _drain_child_output(
                    pending_output,
                    rules,
                    master_fd,
                    parent_stdout,
                )
    finally:
        termios.tcsetattr(parent_stdin, termios.TCSADRAIN, original_tty)
        signal.signal(signal.SIGWINCH, previous_winch)
        try:
            os.close(master_fd)
        except OSError:
            pass

    _, status = os.waitpid(pid, 0)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
