# Application Design

## Purpose

This document is the overview for the application's external behavior and operational contract.

## Scope

This design tree covers the user-visible and operations-visible contract for the Codex exec supervisor application.
Implementation planning, internal structure, and test execution details are documented under `plan/`.

## User Interface

The application provides a terminal user interface for a human operator to exchange messages with one or more supervised `codex --exec` workers.
The current behavior is a single visible worker and a single chat-style conversation flow.

## Operations Interface

The application runs as a Python supervisor process that starts and manages worker subprocesses and exposes fixed helper scripts for worker-to-supervisor communication.
Operators need to understand the startup entrypoint, helper script locations, worker environment contract, and current local-only runtime assumptions.

## Constraints and Assumptions

The application is intentionally local-only and does not include persistence, replay, or cross-run resume.
The design tree should only capture behavior and operational expectations that affect users, operators, or downstream systems.

## Open Questions

The design may later expand from one visible worker to richer multi-worker workflows.
The design for cross-run persistence and broader deployment models remains open.

## Related Documents

- [codex-exec-supervisor.md](codex-exec-supervisor.md)
- [../plan/codex-exec-supervisor-implementation.md](../plan/codex-exec-supervisor-implementation.md)
- [../plan/codex-exec-supervisor-testing.md](../plan/codex-exec-supervisor-testing.md)
