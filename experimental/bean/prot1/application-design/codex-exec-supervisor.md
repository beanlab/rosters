# Codex Exec Supervisor

## Purpose

This document defines the external contract for a Python supervisor that manages chained `codex --exec` worker sessions
and mediates message exchange between a human operator and those workers.

## Scope

This document covers the user-visible TUI behavior, the helper-script and RPC contract exposed to workers, and the
operational assumptions required to run the application.
Internal process orchestration, data structures, and implementation-specific test planning are covered under `plan/`.

## User Interface

The application presents a terminal chat interface with:

- a transcript area
- a current worker indicator
- a prompt input
- a status line showing worker state and recent bridge activity

The operator interacts with a single visible worker.
When the operator submits a message in the TUI, the application queues that message for the selected worker.
When the worker sends a reply through the provided helper interface, the application appends that reply to the visible
transcript immediately.

The transcript is expected to show an ordered round-trip between the operator and the worker.
The user experience does not include transcript search, explicit worker routing controls, or chain and handoff
controls.

User-visible failure modes include:

- no reply arriving before a helper timeout expires
- messages from unknown or stale workers being rejected
- worker state changes being surfaced in the status line

## Operations Interface

The application is started through a Python CLI entrypoint such as `python -m ...` or `python main.py`.

The supervisor provides two fixed local helper scripts for workers:

- `send_message.py`
- `get_message.py`

Workers rely on these scripts plus environment variables supplied by the supervisor.
The worker environment contract includes:

- `SESSION_ID`
- `WORKER_ID`
- `CODEX_BRIDGE_COMMAND` or an equivalent executable path used by the helpers to reach the supervisor bridge
- optional `CODEX_BRIDGE_TIMEOUT`

The helper-to-supervisor bridge uses newline-delimited JSON over stdio with JSON-RPC 2.0 envelopes.
Each helper invocation issues one request and receives one response.

Supported methods are:

- `get_message`
- `send_message`

`get_message` accepts `session_id`, `worker_id`, and an optional `timeout_seconds`.
It blocks until a queued user message is available or the timeout elapses.
It returns either a user message record or a timeout result.

`send_message` accepts `session_id`, `worker_id`, `content`, and optional `metadata`.
It appends a worker message to the transcript and returns an acknowledgement with message identity and timestamp data.

The supervisor validates `session_id` and `worker_id` on every request.
Unknown or stale workers are rejected with JSON-RPC errors.
The bridge uses stable error categories for invalid parameters, unknown session or worker, timeout, and internal bridge
failure.

Default operating behavior is:

- one visible worker
- blocking `get_message` with a finite default timeout
- plain-text helper output unless `--json` is requested

The application is local-only.
It does not require network services or a broker and does not expose a persistence-backed resume contract.

## Constraints and Assumptions

This is a greenfield implementation in this workspace.
The supervisor is the only long-lived stateful component in the system.
The external helper contract remains JSONL JSON-RPC even if the internal bridge implementation changes.
Multi-worker chaining and routing are intentionally deferred, though the application may later expand in that direction.

## Open Questions

- How worker lifecycle events should be surfaced in the TUI beyond the current status line is still open.
- The exact CLI module path for the supervisor entrypoint is not yet fixed.
- The future contract for multi-worker routing, persistence, and replay remains undefined.

## Related Documents

- [application-design.md](application-design.md)
- [../plan/codex-exec-supervisor-implementation.md](../plan/codex-exec-supervisor-implementation.md)
- [../plan/codex-exec-supervisor-testing.md](../plan/codex-exec-supervisor-testing.md)
