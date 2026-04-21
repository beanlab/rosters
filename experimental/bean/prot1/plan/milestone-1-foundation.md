# Milestone 1: Foundation

## Purpose

Establish the basic Python application structure and the in-memory runtime model that the rest of the supervisor depends on.

## Scope

This milestone covers the local project entrypoint, core data structures, session-owned state containers, and shared utility code needed by later milestones.
It does not yet need to launch `codex --exec` workers, render the TUI, or expose a working helper bridge.

## What This Milestone Comprises

- a Python entrypoint for starting the supervisor
- configuration loading for local runtime defaults
- runtime models for `Session`, `Worker`, `Message`, and `Mailbox`
- append-only in-memory transcript storage
- a central state owner that coordinates workers, mailboxes, and transcript access
- shared timestamp and message ID creation helpers
- a minimal logging or diagnostic strategy suitable for local development

## Implementation Guidance

- Choose a package layout that cleanly separates the supervisor runtime, bridge code, helper scripts, and UI code, but do not overdesign module boundaries before later milestones exist.
- Implement the core runtime types first so later milestones can depend on stable APIs instead of ad hoc dictionaries.
- Keep transcript and mailbox storage purely in memory.
- Define state transitions for worker lifecycle early, even if some statuses are only exercised in later milestones.
- Centralize ID generation and time handling so tests can stub or control them later.
- Create the CLI bootstrap in a way that can eventually initialize the runtime, start the UI loop, and shut down cleanly.

## Deliverables

- a runnable Python supervisor entrypoint
- core runtime model definitions
- state-management code for sessions, workers, transcripts, and mailboxes
- baseline developer diagnostics for startup and shutdown paths

## Completion Criteria

- The supervisor process can start and initialize an empty session without errors.
- Core runtime types exist and can represent the states required by the application-design docs.
- Messages can be appended to an in-memory transcript through a single shared state owner.
- Mailbox primitives exist and are ready to support blocking delivery in later milestones.

## User Verification

1. Start the supervisor from the documented Python entrypoint.
2. Confirm the process initializes cleanly and shows no startup errors.
3. Confirm developer diagnostics indicate that a new session was created.
4. Run the simplest available local check or demo path that appends a message to the in-memory transcript.
5. Confirm the process can shut down cleanly without leaving partial state or crash output.

## Out of Scope

- JSON-RPC request handling
- helper script behavior
- worker subprocess launch
- TUI rendering
- full end-to-end operator/worker exchange

## Related Documents

- [milestones.md](milestones.md)
- [milestone-2-bridge-and-helpers.md](milestone-2-bridge-and-helpers.md)
- [codex-exec-supervisor-implementation.md](codex-exec-supervisor-implementation.md)
