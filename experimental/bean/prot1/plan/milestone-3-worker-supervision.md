# Milestone 3: Worker Supervision

## Purpose

Connect the supervisor runtime and bridge to actual `codex --exec` worker subprocesses.

## Scope

This milestone covers worker registration, subprocess startup and shutdown, environment injection, mailbox wiring, transcript updates from worker activity, and lifecycle status tracking.
It depends on the runtime model and bridge/helpers from the earlier milestones.

## What This Milestone Comprises

- worker creation and registration within the active session
- subprocess launch for `codex --exec`
- injection of `SESSION_ID`, `WORKER_ID`, `CODEX_BRIDGE_COMMAND`, and optional timeout settings into the worker environment
- worker status tracking for startup, running, exit, and stale or failed conditions
- linkage between operator messages, worker mailboxes, and transcript updates
- cleanup behavior when a worker exits while messages are pending or while helper calls are in flight

## Implementation Guidance

- Keep worker orchestration inside the supervisor even though the current UI exposes a single active worker.
- Treat worker registration as explicit state so the bridge can validate requests against known live workers.
- Make worker shutdown paths deterministic; later milestones should not need to guess whether a worker is still valid.
- Ensure transcript writes for user and worker messages go through the same state owner so ordering remains consistent.
- Surface enough lifecycle information for the UI status line, even if richer UI controls are still deferred.
- Handle worker exit during mailbox waits as a first-class condition rather than a silent deadlock.

## Deliverables

- subprocess management for worker lifecycle
- environment setup for worker helper usage
- session registration and stale-worker invalidation
- transcript and mailbox coordination for live workers

## Completion Criteria

- The supervisor can launch a worker subprocess with the required environment contract.
- A registered worker can be recognized by bridge validation and a stale or exited worker can be rejected correctly.
- User messages can be queued for a worker mailbox through supervisor state.
- Worker-originated messages received through the bridge are stored in transcript order.

## User Verification

1. Start the supervisor and launch one `codex --exec` worker through the implemented supervisor flow.
2. Confirm the worker starts with the expected environment contract and is registered as an active worker.
3. Queue a user message for that worker through the simplest available runtime interface.
4. Confirm the worker can retrieve the queued message through the helper bridge.
5. End the worker process and confirm the supervisor marks it exited or stale.
6. Attempt another bridge call using that worker identity and confirm the supervisor rejects it as no longer valid.

## Out of Scope

- polished terminal UI behavior
- transcript presentation details beyond what the runtime must expose
- multi-worker routing controls

## Related Documents

- [milestones.md](milestones.md)
- [milestone-2-bridge-and-helpers.md](milestone-2-bridge-and-helpers.md)
- [milestone-4-tui-and-mvp-validation.md](milestone-4-tui-and-mvp-validation.md)
- [codex-exec-supervisor-implementation.md](codex-exec-supervisor-implementation.md)
