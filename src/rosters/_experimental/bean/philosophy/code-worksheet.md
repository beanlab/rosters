# Code Worksheet

A preparation worksheet for an agent that wants to write good code the first time.

Use this before and during implementation. The goal is not to create a long design document. The goal is to make the important decisions explicit, keep the solution focused, and produce code that is correct, simple, maintainable, and safe to ship.

## Agent rules

- Solve only the stated task unless existing code, tests, or documentation make a missing requirement clear.
- Do not invent future requirements, extension points, abstractions, or optimizations.
- Prefer the smallest useful version that works and will not become an immediate maintenance burden.
- Follow project conventions unless there is a concrete reason not to.
- Make tradeoffs explicit when they affect correctness, maintainability, performance, safety, or delivery.
- Write for the next human: clear names, straightforward control flow, small responsibilities, and useful comments only where intent is not obvious.
- Add tests where they buy down real risk.
- Keep refactoring local and purposeful. Do not mix broad cleanup with the task unless it is needed to make the change safe.
- Treat done as useful, not merely compiling.

## How to use this worksheet

Fill in each section briefly. Bullets are enough. If a section is not relevant, write `Not relevant` and why. If context is missing, write `Not enough context` and identify the specific question.

Do not start coding until Sections 1–6 are complete enough to guide implementation.

---

## 1. Task understanding

### Stated request
- What was asked?
- What behavior, bug, or outcome should change?

### Source of truth
- Requirement, issue, user request, failing test, documentation, or existing behavior:
- Relevant files, modules, commands, or entry points:

### Success criteria
- The task is done when:
- Observable behavior that should be true after the change:
- Behavior that must not change:

### Out of scope
- Related work that should not be included:
- Tempting abstractions, cleanups, or features to avoid for now:

### Missing context
- Questions that affect correctness or product behavior:
- Assumptions that must be verified in code or tests:

---

## 2. Existing-code reconnaissance

Inspect the current code before designing the change.

### Current flow
- Where does the relevant behavior start?
- What functions/classes/modules participate?
- What data shapes, types, state, or side effects matter?

### Existing conventions
- Naming patterns:
- File/module organization:
- Error handling style:
- Testing style:
- Configuration/API patterns:

### Reuse opportunities
- Existing helpers, abstractions, validators, fixtures, or tests that should be reused:
- Existing behavior that should be preserved:

### Constraints
- Compatibility, migrations, generated files, public APIs, performance expectations, deployment concerns:
- External services, I/O, permissions, privacy, or security boundaries involved:

---

## 3. Problem framing

### Actual problem
State the smallest real problem this change must solve:

> 

### Non-problems
List things that may look relevant but are not required now:
- 

### Risk profile
Mark likely risks:
- [ ] Correctness regression
- [ ] User-visible behavior change
- [ ] Security/privacy/permission impact
- [ ] Data integrity or migration risk
- [ ] Build, type, lint, or generated artifact risk
- [ ] External dependency, timeout, retry, or partial-failure risk
- [ ] Performance or scalability risk
- [ ] Maintainability/readability risk

Notes:
- 

---

## 4. Implementation strategy

Design the simplest working approach before editing code.

### Proposed approach
- Files to change:
- Main code path to modify:
- New code to add:
- Existing code to remove or simplify:

### Why this approach fits
- How it solves the stated task directly:
- Why the complexity level is appropriate:
- How it follows existing project conventions:

### Alternatives considered
| Option | Benefit | Cost/Risk | Decision |
| --- | --- | --- | --- |
|  |  |  |  |

### Tradeoffs accepted
- Speed vs quality:
- Simplicity vs flexibility:
- Local fix vs broader refactor:
- Performance vs readability:

### Guardrails
- How incomplete paths are avoided or guarded:
- How failures are surfaced, handled, or logged:
- How rollback/compatibility is handled, if relevant:

---

## 5. Shape of the code

Use this section to keep the code clear before writing it.

### Responsibilities
- Each changed function/class/module should have one clear job:
  - 

### Interfaces and data contracts
- Inputs:
- Outputs:
- Errors/exceptions/result types:
- Invalid, empty, missing, duplicate, or out-of-range values:

### Naming plan
- Important names to introduce or change:
- Terms already used by the project that should be reused:

### Simplicity check
Answer before coding:
- Can this be done with fewer moving parts while staying readable?
- Is any new abstraction solving a visible problem now?
- Is any optimization supported by evidence or a stated constraint?
- Would a future maintainer understand the flow without a long explanation?

Adjust the plan if any answer reveals unnecessary complexity.

---

## 6. Test and verification plan

Add tests where they protect important behavior. Do not test mechanically; test risk.

### Behavior to verify
- Primary success path:
- Important edge cases:
- Failure/error paths:
- Behavior that must not regress:

### Tests to add or update
- Unit tests:
- Integration/end-to-end tests:
- Fixtures, mocks, snapshots, or generated artifacts:

### Commands to run
- Format:
- Lint:
- Typecheck:
- Unit tests:
- Relevant targeted tests:
- Build or other verification:

### If tests are not added
Explain why the change is low risk or why tests are not practical:

> 

---

## 7. Implementation checklist

Use while editing.

### Before each edit
- [ ] I know why this file needs to change.
- [ ] The change is part of the stated scope.
- [ ] I checked nearby conventions and reused existing patterns where appropriate.

### While coding
- [ ] Keep control flow straightforward.
- [ ] Prefer clear names over comments explaining unclear names.
- [ ] Keep functions/modules focused.
- [ ] Avoid speculative abstraction, configuration, caching, concurrency, or extension points.
- [ ] Handle invalid input, empty states, and failure paths intentionally.
- [ ] Keep public interfaces small, clear, and hard to misuse.
- [ ] Refactor only where it directly reduces risk or improves the changed code.
- [ ] Remove debug statements, dead code, commented-out code, and stale TODOs.

### When a shortcut is taken
Record it intentionally:
- Shortcut:
- Why acceptable now:
- Risk:
- Follow-up needed:

---

## 8. Self-review before finalizing

Review the code as if it were written by someone else.

### Solve the actual problem
- [ ] The implementation satisfies the stated success criteria.
- [ ] No unrelated behavior, files, features, or abstractions were added.
- [ ] Required behavior is not missing.

### Prefer simple, working solutions
- [ ] The control flow is easy to follow.
- [ ] Each helper or abstraction earns its existence.
- [ ] The solution has the right number of moving parts for the problem.

### Trade off carefully
- [ ] Important tradeoffs are documented in code, tests, or this worksheet.
- [ ] The change does not create avoidable future cost.
- [ ] Any accepted debt is visible and intentional.

### Bias toward shipping
- [ ] The change is small enough to review and release safely.
- [ ] Incomplete work cannot execute accidentally.
- [ ] Follow-up work is explicit where needed.

### Use judgment, not dogma
- [ ] Project conventions are followed where they help consistency.
- [ ] Any departure from convention has a concrete reason.
- [ ] Patterns/framework features are used only where they clarify or reduce risk.

### Avoid premature optimization
- [ ] No optimization was added without evidence or a clear requirement.
- [ ] Necessary optimization is protected by tests, comments, or benchmarks.

### Be opinionated when it helps
- [ ] Common usage is clear and easy.
- [ ] There are not multiple new ways to do the same thing without reason.
- [ ] Defaults and configuration are understandable.

### Own outcomes
- [ ] Errors and edge cases are handled intentionally.
- [ ] Observability/logging exists where production diagnosis would otherwise be hard.
- [ ] External dependencies have appropriate timeout/retry/failure behavior where relevant.

### Craftsmanship
- [ ] Names are specific and accurate.
- [ ] Formatting matches the surrounding code.
- [ ] Responsibilities and dependencies are cleanly separated.
- [ ] Likely future changes would be localized.
- [ ] Security, privacy, data integrity, and compatibility risks were considered.
- [ ] Tests cover the important behavior and risks.

---

## 9. Verification results

Record what actually happened, not what should have happened.

### Commands run
| Command | Result | Notes |
| --- | --- | --- |
|  |  |  |

### Commands not run
| Command | Reason |
| --- | --- |
|  |  |

### Manual checks
- 

### Known remaining risk
- 

---

## 10. Final implementation summary

Use this to prepare the final response.

### What changed
- 

### Why it was implemented this way
- 

### Tests/verification
- 

### Follow-up, if any
- 

---

## Compact version for small tasks

For very small changes, use this shorter checklist instead of filling every section.

```markdown
## Mini code worksheet

### Task
- Request:
- Success criteria:
- Out of scope:

### Existing pattern
- Relevant files:
- Convention to follow:

### Plan
- Smallest useful change:
- Edge cases/failure paths:
- Tests/verification:

### Self-check
- [ ] Solves the actual problem only
- [ ] Simple and readable
- [ ] Follows project conventions
- [ ] No speculative abstraction or optimization
- [ ] Handles important edge cases
- [ ] Tests or verification cover the risk
- [ ] No leftovers/debug/dead code

### Verification
- Commands run:
- Commands not run and why:
```
