# Code Review Guidance

A checklist for an agent doing a code review using pragmatic engineering and software craftsmanship principles.

Use this document to produce concrete, actionable review feedback. Base feedback only on observable evidence from the code, tests, diff, documentation, and stated requirements. Do not guess the author's intent, motivation, or skill level.

## Agent review rules

- Review the changed code first.
- Do not invent requirements that are not stated in the task, tests, documentation, or surrounding code.
- Do not criticize unrelated existing code unless the change depends on it, worsens it, or makes it relevant.
- Do not recommend large rewrites unless there is a specific correctness, safety, maintainability, or delivery reason.
- Do not repeat the same issue under multiple principles. If one issue fits several principles, report it once under the most relevant principle.
- If tests, build, lint, typecheck, or other verification were not run or are not visible, say so.
- Prefer useful feedback over exhaustive feedback. Do not force a comment under every principle.

## Review preparation

Before reviewing, identify:

- the stated requirement, bug, or intended behavior,
- the changed files and the main behavior being changed,
- tests added, removed, or modified,
- validation available from CI, test output, lint, typecheck, or build logs,
- context that is missing or uncertain.

If the requirement is unclear, focus feedback on observable risks and mark requirement-specific questions as **Not enough context**.

## How to use this checklist

For each principle:

1. Make the simple observations listed in that section.
2. Decide whether the principle is relevant to this review.
3. If there is no meaningful issue, say **No issue observed** or omit the section.
4. If there is not enough context, say **Not enough context** instead of speculating.
5. When giving feedback, point to the specific file, function, behavior, or test gap.
6. Explain the impact on correctness, maintainability, safety, simplicity, or delivery.
7. Suggest a concrete next step.

## Feedback severity

Use one of these labels when feedback is needed:

- **Blocker:** likely correctness, security, data-loss, build, test, or production-safety issue.
- **Should fix:** meaningful maintainability, reliability, test, or design issue.
- **Consider:** optional improvement or alternative approach.
- **Nit:** small naming, formatting, wording, or local clarity issue.

Severity calibration:

- Use **Blocker** only when the issue is likely to cause incorrect behavior, security risk, data loss, build failure, test failure, or unsafe production behavior.
- Use **Should fix** when the issue should be addressed before merge but is not an immediate blocker.
- Use **Consider** for improvements where the current code is acceptable but a different approach may be better.
- Use **Nit** only when the issue does not meaningfully affect behavior, maintainability, safety, or reviewability.
- When unsure between two severities, choose the lower severity and explain the uncertainty.

## Pragmatic engineering

### 1. Solve the actual problem

Observe:
- Does the change directly address the stated requirement or bug?
- Does the diff include unrelated behavior, files, features, or abstractions?
- Are there new public APIs, configuration options, or extension points that are not needed by the requirement?
- Are any required behaviors missing from the implementation?

Feedback guidance:
- If the code does unrelated work, recommend narrowing the scope.
- If the solution misses part of the requirement, identify the missing behavior.
- If speculative abstractions were added, suggest removing them until there is a real use case.

### 2. Prefer simple, working solutions

Observe:
- Is the control flow easy to follow from names, structure, types, and tests?
- Are functions, classes, modules, or helpers doing one clear job?
- Are there extra layers of indirection that do not reduce duplication, clarify behavior, or isolate change?
- Could the same behavior be implemented with fewer moving parts while remaining readable?

Feedback guidance:
- If complexity does not provide a clear benefit, recommend a simpler structure.
- If logic is hard to follow, suggest extracting, renaming, flattening, or consolidating code.
- Prefer specific simplifications over general comments like “make this cleaner.”

### 3. Trade off carefully

Observe:
- Does the implementation favor one concern, such as speed, flexibility, or short-term delivery, at the expense of another?
- Are important tradeoffs documented in code comments, tests, commit notes, or surrounding documentation?
- Does the chosen approach create obvious future cost, such as tight coupling, duplicated behavior, or hard-to-change interfaces?
- Does the complexity of the implementation match the size, frequency, and risk of the behavior being changed?

Feedback guidance:
- If a tradeoff creates real risk, name the risk and suggest an alternative.
- If the tradeoff may be acceptable but unclear, ask for a short explanation or comment.
- Avoid abstract objections; tie the concern to a concrete maintenance or correctness cost.

### 4. Bias toward shipping

Observe:
- Is the change focused enough to review, test, and release safely?
- Does it avoid bundling unrelated refactors with feature or bug-fix work?
- Are incomplete paths guarded, disabled, or clearly marked as follow-up work?
- Could the change be split into smaller, safer pieces?

Feedback guidance:
- If the change is too large or mixed-purpose, suggest splitting it.
- If incomplete code can execute, ask for guards, tests, or removal.
- If follow-up work is required, recommend making it explicit.

### 5. Use judgment, not dogma

Observe:
- Does the code follow existing project conventions where they help consistency?
- Does it depart from conventions without an observable reason in the code, tests, or documentation?
- Are patterns or frameworks used where plain code would be clearer?
- Does each abstraction solve a visible problem in this codebase?

Feedback guidance:
- If a convention is ignored, point to the existing pattern and ask for consistency or explanation.
- If a pattern adds complexity without benefit, suggest using the simpler local style.
- Avoid saying a technique is “bad” in general; explain why it does or does not fit this case.

### 6. Avoid premature optimization

Observe:
- Does the code add caching, concurrency, batching, memoization, custom data structures, or low-level optimization?
- Is there a measured bottleneck, documented constraint, or clear scale requirement?
- Did the optimization make the code harder to read, test, or change?
- Are there tests covering the optimized behavior?

Feedback guidance:
- If optimization is unsupported and costly, recommend removing or simplifying it.
- If optimization is needed, ask for a comment, benchmark, or test that explains and protects it.
- Distinguish between necessary efficiency and speculative performance work.

### 7. Be opinionated when it helps

Observe:
- Are naming, file layout, APIs, and configuration consistent with the rest of the project?
- Can a future contributor identify the normal way to call, configure, or extend this code from names, types, tests, or examples?
- Are there multiple ways to do the same thing without a clear reason?
- Does the code make common use cases easy and uncommon cases explicit?

Feedback guidance:
- If the change introduces inconsistency, suggest aligning with existing conventions.
- If contributors would have to guess how to use the code, recommend clearer defaults or structure.
- If multiple patterns now exist, suggest consolidating on one.

### 8. Own outcomes

Observe:
- Are errors handled intentionally rather than ignored or swallowed?
- Are edge cases, invalid inputs, empty states, and failure paths considered?
- Is logging or observability present where production diagnosis would be difficult without it?
- Is there a safe behavior for retries, partial failures, timeouts, or external dependency failures where relevant?

Feedback guidance:
- If failures are not handled, identify the specific failure path and expected behavior.
- If production diagnosis would be difficult, suggest targeted logging or observability.
- If external dependencies are involved, check for timeouts, retries, and graceful degradation where appropriate.

## Software craftsmanship

### 9. Take pride in the work

Observe:
- Are variable, function, class, and file names specific and accurate?
- Are names, structure, types, or comments sufficient to explain the purpose of the code?
- Are there leftover debug statements, dead code, commented-out code, or unexplained TODOs?
- Is formatting consistent with the surrounding code?

Feedback guidance:
- If names are vague or misleading, suggest better names.
- If intent is unclear, recommend a small restructure, clearer naming, or a brief comment.
- If there are obvious leftovers, ask for cleanup before merging.

### 10. Sustainability

Observe:
- Are responsibilities separated clearly between functions, classes, modules, or services?
- Are dependencies introduced only where needed?
- Would a likely future change be localized, or would it require edits across many places?
- Are public interfaces small, clear, and hard to misuse?

Feedback guidance:
- If responsibilities are mixed, suggest a clearer boundary.
- If coupling is introduced, explain what future change it would make harder.
- If an interface is confusing or easy to misuse, recommend a safer shape or clearer contract.

### 11. Refactoring as a normal activity

Observe:
- Does the change duplicate existing logic?
- Does it make nearby code harder or easier to understand?
- Is there a small refactor that would reduce risk in this change?
- Is a large refactor being mixed into a change where it increases review risk?

Feedback guidance:
- Suggest small refactors when they directly improve the current change.
- If refactoring is too large for this review, recommend splitting it into a separate change.
- Avoid asking for broad cleanup unrelated to the modified code.

### 12. Professional responsibility

Observe:
- Could this change break existing user behavior?
- Are security, privacy, data integrity, or permission checks affected?
- Are migrations, compatibility, or rollback concerns relevant?
- Are risky changes covered by tests or safeguards?

Feedback guidance:
- Treat correctness, security, privacy, and data-loss risks as high priority.
- Ask for tests or mitigation when user-facing behavior could regress.
- If deployment or rollback risk exists, request a safer rollout plan or compatibility handling.

### 13. Attention to detail

Observe:
- Are boundary cases handled, such as null, empty, missing, invalid, duplicate, or out-of-range values?
- Are types, validation, and assumptions consistent?
- Are error messages, user messages, and comments accurate?
- Are imports, dependencies, and generated artifacts clean?

Feedback guidance:
- Point to the exact detail and why it matters.
- Prefer precise corrections over broad style criticism.
- Distinguish small nits from issues that affect behavior or maintainability.

### 14. Build with discipline

Observe:
- Are tests present for new or changed behavior?
- Do tests cover important success, failure, and edge cases?
- Does the change fit existing linting, formatting, typing, build, and CI expectations?
- Are setup steps, fixtures, mocks, or generated files reproducible?

Feedback guidance:
- If behavior changed without tests, ask for targeted tests.
- If tests are brittle or overly broad, suggest more focused coverage.
- If automation would fail or be hard to reproduce, ask for the missing build, fixture, or documentation update.

## Review style

### 15. Improve through the review

Observe:
- Is there a recurring mistake or pattern that can be corrected with one clear suggestion?
- Is there a better local pattern already used elsewhere in the codebase?
- Would an example, reference, or short explanation make the feedback easier to apply?
- Can the review teach without making assumptions about the author's ability or intent?

Feedback guidance:
- Explain the reason behind important suggestions.
- Link the suggestion to project conventions, tests, behavior, or maintainability.
- Keep feedback respectful, specific, and actionable.

### 16. Teach and mentor through feedback

Observe:
- Does each review comment explain the practical impact of the issue?
- Is the suggested fix clear enough to act on?
- Are comments grouped when the same issue appears repeatedly?
- Is the tone focused on the code rather than the person?

Feedback guidance:
- Write comments that help the author understand and improve the code.
- Include examples when they make the suggestion clearer.
- Avoid vague feedback such as “this is bad,” “clean this up,” or “use best practices.”

## Review output format

Use this structure when producing the review:

```markdown
## Summary
- Briefly state the overall review result.
- Mention the highest-priority risks first.

## Verification
- Tests run:
- Tests not run:
- Build/lint/typecheck status:
- Manual reasoning only:

## Findings

### [Severity] — [Principle]: Short issue title
- **Location:** file path, function, or behavior
- **Observation:** what the code does
- **Impact:** why it matters
- **Recommendation:** concrete next step

## No issue observed
- Only include this section when it adds confidence. Do not list every principle mechanically.

## Not enough context
- List any questions that require product, deployment, or requirement context.
```

Keep the final review concise. Prioritize issues that improve correctness, maintainability, safety, simplicity, or test confidence.

## Example finding

```markdown
### Should fix — Own outcomes: external API failure is swallowed
- **Location:** `src/payments/client.ts`, `submitPayment`
- **Observation:** The catch block returns `null` without logging or surfacing the error.
- **Impact:** Callers cannot distinguish a failed payment request from an empty response, making retries and diagnosis difficult.
- **Recommendation:** Return a typed error result or rethrow with context, and add a test for the failure path.
```
