from __future__ import annotations

import argparse
import json
import sys

from .helper_common import HelperInvocationError, call_bridge, default_timeout, helper_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch the next user message for the active worker.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON result.")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help="Override the bridge timeout for this request.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        session_id, worker_id = helper_context()
        timeout_seconds = args.timeout_seconds
        if timeout_seconds is None:
            timeout_seconds = default_timeout()
        params = {"session_id": session_id, "worker_id": worker_id}
        if timeout_seconds is not None:
            params["timeout_seconds"] = timeout_seconds
        result = call_bridge({"jsonrpc": "2.0", "id": 1, "method": "get_message", "params": params})
    except HelperInvocationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True))
        return 0
    if result.get("status") == "timeout":
        print("timeout")
        return 0
    message = result.get("message", {})
    print(message.get("content", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
