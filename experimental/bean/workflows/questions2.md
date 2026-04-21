# Questions For `design.md`

These are the questions I would raise before handing this spec to an implementation team. Each item is phrased to force a decision where the current design leaves room for incompatible interpretations.

## Open Questions

1. What is the exact authored YAML shape for a workflow file?
Why this matters: the spec says "Read a YAML workflow definition" and also says "The authored workflow is a top-level mapping keyed by step name," but it never shows whether there are workflow-level fields such as `version`, `default_agent`, or `timeouts`, nor whether steps live directly at the root or under a `steps:` key.
Response:
- Confirmed: for v1, the workflow file is only a top-level mapping of `step_name: step_definition`.
- No `steps:` wrapper.
- No workflow-level fields for now.

2. How strict should output validation be for scalar leaf values?
Why this matters: the spec says validation is "structural only" and does not infer scalar types from descriptive leaf strings. That leaves open whether any scalar is acceptable, whether `null` is allowed, whether arrays must match example shape, and whether an empty object can satisfy a nested template.
Response:
- Confirmed: template leaf placeholders are purely descriptive.
- If the template shows a nested object, the returned value at that location must be an object with the required nested keys.
- Otherwise, the returned value may be any JSON value, including string, number, boolean, `null`, object, or array.
- Descriptive leaf values in the template are not type hints and do not constrain the returned value type.

3. What exact algorithm should detect the final completion JSON in a noisy PTY transcript?
Why this matters: the spec requires the agent to finish with only one parseable JSON object, but the system is consuming a live transcript from an interactive CLI that may echo input, print progress text, emit fenced code blocks, or include braces earlier in the session. The implementation team needs a precise rule for extracting the final object without false positives.
Response:
- Confirmed approach:
- Keep the full accumulated transcript buffer.
- After each new chunk, if the accumulated buffer contains `OBJECTIVE_COMPLETE`, attempt to parse the trailing portion of the transcript as exactly one top-level JSON object.
- Accept completion only if that object matches `{"status":"OBJECTIVE_COMPLETE","content":...}`.
- If parsing fails, continue reading output.

4. What should happen if the agent emits valid completion JSON and then keeps printing output before the quit sequence takes effect?
Why this matters: the spec says the executor detects completion and then asks the wrapper to send the quit sequence, but it does not define whether extra output after detection is ignored, treated as failure, or appended to the transcript while preserving the earlier parsed result.
Response:
- Confirmed: append trailing output to the transcript, but do not let it affect step success once valid completion JSON has been accepted.
- Practical interpretation: the first accepted valid completion object wins for the step result.

5. What is the expected failure taxonomy and status enum for `StepResult` and `WorkflowRunResult`?
Why this matters: the spec lists failure modes in prose but leaves `status` as free-form strings. Without a fixed set of status values and error types, different developers will encode failures differently, which will leak into CLI behavior, tests, and future API callers.
Response:
- Leave this open for v1.
- Status and error-type values are not yet a stable contract.
- The intent is to learn from real usage and observed failure modes before defining a future enum.

6. How should per-step and whole-run memory usage be bounded if transcripts are always retained fully in memory?
Why this matters: the spec explicitly requires full transcript retention in memory for every step, including failures. That is simple, but it creates an unbounded memory risk for long-running or verbose sessions unless the team knows the expected scale or a truncation policy.
Response:
- Confirmed: unbounded transcript retention is acceptable for v1.
- No truncation, bounding, or memory monitoring is required.
- Assumption: expected workflows and transcripts fit comfortably in memory.

7. Do we need workflow-level or step-level timeout settings in v1, or are the hard-coded inactivity and graceful shutdown defaults intentionally non-configurable?
Why this matters: the current design exposes inactivity and graceful shutdown parameters at the PTY layer but does not say whether authors or CLI users can configure them. If these values are fixed in code, that should be explicit; if not, the schema needs to define where they live.
Response:
- Confirmed: in v1, timeout values are configured in code as workflow-layer global defaults.
- They are not authored in the workflow file and not configurable per step.
- Future workflow-spec revisions or a separate global config may override those defaults later.

8. What are the ordering and validation rules for step references?
Why this matters: references point to prior step outputs, but the spec does not explicitly say whether forward references are rejected at parse time, whether self-references are invalid, or whether unused/misspelled step names should fail early versus at runtime.
Response:
- Confirmed: reference validity is checked only at step runtime.
- Forward references, self-references, and misspelled step names are not rejected during workflow parsing.
- If a reference cannot be resolved when a step executes, that step fails at runtime.

9. Should duplicate YAML keys, non-identifier step names, and non-identifier nested output keys be rejected explicitly during parsing?
Why this matters: the reference syntax depends on Python-identifier-style names for both step names and keys, but YAML permits keys that would violate that rule. The spec needs to state whether those are disallowed globally or only disallowed when referenced.
Response:
- Confirmed: valid identifier-style key names should be enforced everywhere they matter to the workflow format and reference system.
- Step names must be valid identifiers.
- Nested authored keys should also use valid identifier-safe names.
- Duplicate-key behavior is still unspecified here.

10. What is the exact semantics of array-shaped output templates?
Why this matters: the reference resolver supports inserting arrays, and output validation mentions nested object shape, but the spec never states how lists are validated. For example, does a template list describe "any list", "a non-empty list", or "a list whose first element defines the schema for every element"?
Response:
- Confirmed: lists are not expected to appear in authored output templates in v1.
- No specific validation semantics are defined or enforced for template lists at this stage.

11. What working-directory and environment guarantees does the runner make to the child agent process?
Why this matters: the wrapper inherits the parent working directory and environment, but the spec does not say whether the CLI runs from the workflow file's directory, the caller's current directory, or an explicit configured project root. That choice directly affects reproducibility and prompt assumptions.
Response:
- Confirmed: child agent processes run from the caller's current working directory.
- The child also inherits the parent environment.

12. What observable CLI output should a caller get on success and failure in non-verbose mode?
Why this matters: the spec says the CLI is quiet by default and should not emit a final human-readable summary, but it also says essential validation or execution failures should surface. The team needs a concrete contract for stdout vs stderr and whether successful runs print the final step output, nothing at all, or machine-readable JSON later.
Response:
- Confirmed: on success, print nothing and proceed through the workflow silently.
- On failure, print the error and exit immediately.

13. What is the deterministic test-agent contract for integration tests?
Why this matters: the design sensibly avoids real interactive CLI tests, but the implementation team still needs a minimal fake-agent protocol: how it receives input, how it emits transcript chunks, how it simulates malformed JSON, inactivity, and delayed graceful shutdown.
Response:
- Confirmed test-agent behaviors for integration tests:
- Normal interaction flow: receive initial input, support back-and-forth communication, emit valid completion JSON, receive exit sequence, then emit brief trailing output after exit.
- Agent exits before valid completion JSON is produced.
- Agent emits malformed completion JSON.
- Graceful shutdown behavior is testable.

14. Is `pydantic` actually a required dependency for v1, or should the implementation prefer standard dataclasses plus explicit validation?
Why this matters: the spec recommends both `pydantic` and dataclasses in different places. That affects model definitions, parser behavior, error reporting, and how much validation logic lives in schema objects versus parser code.
Response:
- Confirmed: avoid `pydantic` for v1.
- Prefer standard dataclasses and explicit validation logic in parser/runtime code.

15. Do we want the workflow file format and runtime result model to be treated as private implementation details or as a stable external contract from v1 onward?
Why this matters: several ambiguous points are tolerable if the format is intentionally private and likely to change soon. They are much riskier if other tools, tests, or users will author workflow files against this spec immediately.
Response:
- Confirmed: the workflow file format is public and should be treated as an external contract.
- The runtime result model is informational/internal only and is not a stable public contract in v1.
