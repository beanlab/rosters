from __future__ import annotations

import argparse
import json
import sys

from .helper_common import HelperInvocationError, call_bridge, helper_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a worker reply to the supervisor.")
    parser.add_argument("content", nargs="*", help="Message content. Reads stdin when omitted.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON result.")
    return parser


def _read_content(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    return sys.stdin.read().strip()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    content = _read_content(args.content)
    if not content:
        print("message content is required", file=sys.stderr)
        return 2
    try:
        session_id, worker_id = helper_context()
        result = call_bridge(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "send_message",
                "params": {
                    "session_id": session_id,
                    "worker_id": worker_id,
                    "content": content,
                },
            }
        )
    except HelperInvocationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True))
        return 0
    message = result.get("message", {})
    print(f"sent {message.get('message_id', '')}".strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
