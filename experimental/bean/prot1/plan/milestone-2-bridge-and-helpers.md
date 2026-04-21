# Milestone 2: Bridge And Helpers

## Purpose

Implement the stdio JSONL JSON-RPC contract that workers use to exchange messages with the supervisor through fixed helper scripts.

## Scope

This milestone covers request and response envelopes, request validation, timeout handling, supervisor-side bridge dispatch, and the behavior of `get_message.py` and `send_message.py`.
It depends on the runtime state foundation from milestone 1 but does not yet require real worker process supervision or the final TUI.

## What This Milestone Comprises

- JSON-RPC 2.0 request and response models
- newline-delimited JSON transport handling for one request per invocation
- bridge dispatch for `get_message` and `send_message`
- validation of `session_id`, `worker_id`, params, and supported methods
- stable error mapping for invalid params, unknown session or worker, timeout, and internal failures
- fixed helper scripts with default human-friendly output and optional `--json` output

## Implementation Guidance

- Keep the transport strict and simple: one helper process sends one request, receives one response, and exits.
- Encode all bridge responses through a single formatting path so success and failure behavior is consistent.
- Treat timeout as a defined bridge outcome, not an exceptional crash path.
- Design helper scripts as thin clients that know how to gather environment configuration, build a request, print results, and map failures to useful exit behavior.
- Support message content input for `send_message.py` from both command-line arguments and stdin.
- Make the bridge code runnable without the TUI so it can be tested in isolation.

## Deliverables

- supervisor-side JSON-RPC bridge implementation
- request parsing and response formatting utilities
- `get_message.py`
- `send_message.py`
- bridge-level validation and timeout handling

## Completion Criteria

- `get_message` can block on a mailbox and return either a message result or a timeout result.
- `send_message` can append a worker message to the transcript and return an acknowledgement.
- Unknown or stale session and worker identifiers are rejected through stable JSON-RPC errors.
- Both helper scripts can run as one-shot clients and produce the documented default outputs.

## User Verification

1. Start the supervisor in a mode that exposes the bridge without requiring the full TUI.
2. Invoke `get_message.py` against a mailbox that has no pending message and confirm it returns the documented timeout behavior.
3. Seed a user message through the simplest available local setup and invoke `get_message.py` again.
4. Confirm `get_message.py` prints the message content by default and can print the full JSON result with `--json`.
5. Invoke `send_message.py` with sample content and confirm it returns a success response and records the worker message in supervisor state.
6. Invoke one helper with an invalid session or worker identifier and confirm it is rejected with the expected error behavior.

## Out of Scope

- launching and monitoring real `codex --exec` subprocesses
- final TUI rendering and interaction flow
- complete operator-visible worker lifecycle handling

## Related Documents

- [milestones.md](milestones.md)
- [milestone-1-foundation.md](milestone-1-foundation.md)
- [milestone-3-worker-supervision.md](milestone-3-worker-supervision.md)
- [codex-exec-supervisor-testing.md](codex-exec-supervisor-testing.md)
