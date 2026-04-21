# Implementation Milestones

## Purpose

This document is the index for the implementation milestones required to reach the first MVP of the Codex exec supervisor.

## Scope

This milestone plan breaks the current implementation work into sequential slices that can be built, reviewed, and verified independently.
Each milestone links to a dedicated document that describes what the milestone includes, how it should be implemented, and what must be true before it is considered complete.

## Milestones

1. [milestone-1-foundation.md](milestone-1-foundation.md)
   Establish the Python project entrypoint, core runtime types, and the in-memory session state model.
2. [milestone-2-bridge-and-helpers.md](milestone-2-bridge-and-helpers.md)
   Implement the JSONL JSON-RPC bridge contract and the fixed helper scripts used by workers.
3. [milestone-3-worker-supervision.md](milestone-3-worker-supervision.md)
   Add worker process management, environment injection, mailbox coordination, and transcript updates.
4. [milestone-4-tui-and-mvp-validation.md](milestone-4-tui-and-mvp-validation.md)
   Deliver the single-worker terminal UI and verify the full operator-to-worker round-trip that defines the first MVP.

## Constraints and Assumptions

Milestones are ordered so that each one produces a stable base for the next.
The milestone set is limited to the current MVP scope and excludes deferred work such as multi-worker routing UI, persistence, replay, and networked deployment.

## Open Questions

- The exact package layout can be chosen during implementation as long as it preserves the documented external contract.
- Some test coverage may be introduced in earlier milestones when it is the fastest way to stabilize shared infrastructure.

## Related Documents

- [codex-exec-supervisor-implementation.md](codex-exec-supervisor-implementation.md)
- [codex-exec-supervisor-testing.md](codex-exec-supervisor-testing.md)
- [../application-design/codex-exec-supervisor.md](../application-design/codex-exec-supervisor.md)
