# Codex Exec Supervisor Testing Plan

## Purpose

This document captures implementation-focused test planning for the Codex exec supervisor.

## Scope

This plan covers unit, integration, and manual acceptance testing for the current implementation.
It does not define the external contract; that remains in `application-design/`.

## Unit Tests

- JSON-RPC request and response parsing
- session and worker ID validation
- mailbox blocking and timeout behavior
- transcript append behavior
- helper script argument parsing and default output modes

## Integration Tests

- supervisor startup and worker registration
- one full user -> `get_message.py` -> worker -> `send_message.py` -> TUI round-trip
- timeout path for `get_message`
- invalid worker and session rejection
- worker exit while waiting on messages

## Manual Acceptance Scenario

1. Launch the supervisor.
2. Spawn one `codex --exec` worker.
3. Send a user prompt from the TUI.
4. Confirm the worker retrieves it through `get_message.py`.
5. Confirm the worker reply appears through `send_message.py`.
6. Confirm the TUI transcript shows ordered user and worker messages and current worker status.

## Related Documents

- [milestones.md](milestones.md)
- [../application-design/codex-exec-supervisor.md](../application-design/codex-exec-supervisor.md)
- [codex-exec-supervisor-implementation.md](codex-exec-supervisor-implementation.md)
