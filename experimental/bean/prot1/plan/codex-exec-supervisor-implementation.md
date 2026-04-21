# Codex Exec Supervisor Implementation Plan

## Purpose

This document captures implementation-oriented design and engineering notes for the Codex exec supervisor.

## Scope

This plan covers process orchestration, internal state ownership, helper-script implementation expectations, and deferred implementation work.
External behavior and operations-visible contract belong in `application-design/`.

## Process Model

- Implement a Python supervisor as the system entrypoint.
- The supervisor owns:
  - the TUI event loop
  - worker lifecycle management
  - a per-worker transcript buffer
  - a blocking mailbox for human-to-worker and worker-to-human messages
- Spawn each `codex --exec` worker as a subprocess with:
  - a unique `worker_id`
  - environment variables pointing at the fixed helper scripts
  - environment variables carrying `SESSION_ID`, `WORKER_ID`, and bridge connection details
- Keep worker orchestration in supervisor code even though the current UI exposes one active worker in the TUI.

## Helper Script Implementation Notes

### `get_message.py`

- Read connection and session info from environment variables.
- Emit one `get_message` JSON-RPC request.
- Print only the user message content by default for agent ergonomics.
- Support a `--json` flag to print the full JSON result for debugging.

### `send_message.py`

- Accept message content from CLI args or stdin.
- Emit one `send_message` JSON-RPC request.
- Print a short success confirmation by default.
- Support a `--json` flag to print the full JSON result.

## Internal Data Model

- `Session`: top-level supervisor run
- `Worker`: child `codex --exec` process plus status
- `Message`: `message_id`, `worker_id`, `role`, `content`, `timestamp`, optional metadata
- `Mailbox`: blocking queue for pending human-to-worker messages

Transcripts are append-only in memory.
Persistence, replay, and cross-run resume are deferred.

## Deferred Implementation Work

- Multi-worker routing UI
- transcript search
- chain and handoff controls
- persistence and replay
- cross-run resume
- networked broker support

## Related Documents

- [milestones.md](milestones.md)
- [../application-design/codex-exec-supervisor.md](../application-design/codex-exec-supervisor.md)
- [codex-exec-supervisor-testing.md](codex-exec-supervisor-testing.md)
