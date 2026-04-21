# Milestone 4: TUI And MVP Validation

## Purpose

Deliver the operator-facing terminal interface and prove the first MVP through the full supervisor-to-worker message loop.

## Scope

This milestone covers the single-worker TUI, operator input handling, transcript rendering, worker status display, and the end-to-end validation needed to confirm the current MVP.
It depends on the runtime, bridge, helper, and supervision work from prior milestones.

## What This Milestone Comprises

- transcript area rendering
- current worker indicator
- prompt input for operator messages
- status line for worker state and recent bridge activity
- UI wiring that appends operator messages to the selected worker mailbox
- immediate transcript updates for worker replies received through `send_message`
- automated and manual validation of the full round-trip flow

## Implementation Guidance

- Keep the UI intentionally narrow: one active worker, one conversation flow, and no routing or search features.
- Render the transcript from the shared append-only message store rather than keeping a separate UI-only source of truth.
- Expose worker status changes in a form that the status line can consume directly from runtime state.
- Ensure the UI remains responsive while `get_message` calls block in helper processes.
- Focus MVP validation on the ordered operator-to-worker-to-operator round-trip defined in the application-design docs.
- Finish with a manual acceptance workflow that exercises the same path as the intended first demonstration.

## Deliverables

- a working terminal UI for one active worker
- operator input handling connected to worker mailboxes
- transcript rendering backed by shared supervisor state
- end-to-end validation for timeout, invalid worker rejection, and the successful round-trip path

## Completion Criteria

- The operator can launch the supervisor and use the TUI to send a message to the active worker.
- The worker can retrieve that message through `get_message.py`.
- The worker can respond through `send_message.py` and the reply appears in the transcript immediately.
- The UI displays current worker identity and status information.
- The manual acceptance scenario from the testing plan passes end to end.

## User Verification

1. Launch the supervisor and confirm the TUI shows the transcript area, current worker indicator, prompt input, and status line.
2. Start or attach the active worker and confirm the status line reflects the worker state.
3. Enter a message in the TUI and confirm it is queued for the worker.
4. Confirm the worker retrieves the message with `get_message.py`.
5. Confirm the worker replies with `send_message.py` and the response appears in the transcript immediately.
6. Trigger at least one timeout or invalid-worker path and confirm the UI surfaces the result without breaking the session.
7. Complete the full manual acceptance scenario from the testing plan.

## Out of Scope

- multi-worker routing UI
- transcript search
- chain and handoff controls
- persistence or replay

## Related Documents

- [milestones.md](milestones.md)
- [milestone-3-worker-supervision.md](milestone-3-worker-supervision.md)
- [codex-exec-supervisor-testing.md](codex-exec-supervisor-testing.md)
- [../application-design/codex-exec-supervisor.md](../application-design/codex-exec-supervisor.md)
