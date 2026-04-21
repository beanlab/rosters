# Delivery Questions For `design.md`

This file tracks the questions that should be answered before handing the spec to an implementation team.

Status values:
- `open`: needs a product or technical decision
- `decided`: conclusion captured below

## Questions

1. Status: `decided`
   Topic: Step completion contract
   Question: What exact wire contract marks a step as complete and provides its structured output?
   Why it matters: The design says the executor must "detect the final structured completion payload," but it never defines the payload shape, delimiters, or whether the agent must emit pure JSON, tagged JSON, or some other sentinel-based block. Without this, the executor and prompt format cannot be implemented consistently.
   Relevant spec: `design.md` sections `step_executor`, `tty_wrapper`, and `Data Flow`
   Conclusion: `thoughts.md` specifies that the agent should produce a final output consisting only of one JSON object shaped like `{"status": "OBJECTIVE_COMPLETE", "content": <structured output>}`. The executor should watch the transcript for a parseable final JSON object with this status and treat `content` as the step output payload.

2. Status: `decided`
   Topic: Step schema
   Question: What fields are required and optional on `StepDefinition` besides `agent` and `input`?
   Why it matters: The parser is responsible for validation, but the authored workflow shape is underspecified. Developers need to know whether steps have names, ids, prompt templates, expected output schemas, retry policy, timeouts, and descriptions.
   Relevant spec: `design.md` sections `workflow_parser`, `step_executor`, and `models`
   Conclusion: Follow `thoughts.md` for v1. The authored workflow is a top-level YAML mapping keyed by step name. Each step may contain `prompt`, optional `input`, and `output`. Step names come from the top-level keys rather than an internal `name` field. `agent` may still be supported per `design.md`, but it is not shown in the current examples.

3. Status: `decided`
   Topic: Output validation
   Question: How is each step's output schema declared and validated?
   Why it matters: The design says the executor parses and validates completed output, but it does not define where the expected schema lives or whether validation is per-step, global, or implicit.
   Relevant spec: `design.md` sections `step_executor` and `models`
   Conclusion: The step's authored `output` block is the schema declaration for v1. Its leaf values are agent-readable descriptions, not machine-readable type constraints. Validation should check that the returned `content` contains the required keys and nested object shape from the `output` template, but it should not enforce scalar types beyond basic structural presence.

4. Status: `decided`
   Topic: Prompt construction
   Question: What exact prompt format is sent to the agent for a step, including instructions about output format and reference-resolved input?
   Why it matters: Prompt construction is named as executor responsibility, but there is no authored prompt field or canonical prompt template. This is a core behavioral dependency, not an implementation detail.
   Relevant spec: `design.md` sections `step_executor` and `Data Flow`
   Conclusion: Use one canonical prompt template in v1. The executor should prepend the fixed session instruction that explains the final JSON contract, then include resolved `input` under an `Input:` heading when present, the authored `prompt` under an `Objective:` heading, and the authored `output` block under an `Output template:` heading. The prompt should end by reminding the agent to return only the final JSON object when complete.

5. Status: `decided`
   Topic: Failure semantics
   Question: What counts as step failure, and what is returned in `StepResult` and `WorkflowRunResult` for each failure mode?
   Why it matters: The engine "stops on failure," but the failure taxonomy is missing. We need to distinguish agent process exit, malformed final output, timeout, reference resolution failure, and parser validation errors.
   Relevant spec: `design.md` sections `workflow_engine`, `step_executor`, and `models`
   Conclusion: In v1, treat the following as step failures: reference resolution failure before launch, agent process launch failure, session exit before valid completion JSON is seen, malformed final JSON, final JSON with the wrong shape or missing required keys, and timeout or inactivity timeout. `StepResult` should include `step_name`, `status`, `output` when successful, `error_type`, `error_message`, and optional `transcript`. `WorkflowRunResult` should include ordered step results, overall workflow `status`, and the failing step name when applicable. Final-JSON-specific error handling may evolve in a later version.

6. Status: `decided`
   Topic: Timeouts and liveness
   Question: What timeouts or inactivity thresholds should v1 enforce for PTY sessions and workflow runs?
   Why it matters: A TTY-driven agent can hang indefinitely. The wrapper owns subprocess lifecycle, but the spec does not define how long to wait for startup, output inactivity, or graceful shutdown.
   Relevant spec: `design.md` sections `tty_wrapper` and `workflow_engine`
   Conclusion: Use an inactivity timeout of 5 minutes. Do not enforce a maximum step duration in v1 as long as output continues within the inactivity window. After the executor decides the step is complete and sends the quit sequence, allow up to 30 seconds for graceful exit before forcefully terminating the child process. No separate startup timeout is required beyond normal process launch failure handling.

7. Status: `decided`
   Topic: Transcript handling
   Question: What transcript data should be retained in memory and surfaced in results for debugging?
   Why it matters: The executor "accumulates streamed output," but the result model does not say whether raw transcript, parsed final payload, stderr-equivalent bytes, or handler decisions are preserved.
   Relevant spec: `design.md` sections `step_executor`, `tty_wrapper`, and `models`
   Conclusion: Retain the full raw transcript in memory for every step in v1 and attach it to every `StepResult`, regardless of success or failure. Persistence policy can be decided later by the workflow runner or higher-level tooling.

8. Status: `decided`
   Topic: Human or tool follow-up turns
   Question: Under what circumstances is the output handler expected to send additional input back to the child session?
   Why it matters: The wrapper supports multi-turn interaction, but the design never defines the policy. If v1 is intended to be single-prompt and single-final-response, the interface can stay much simpler.
   Relevant spec: `design.md` sections `step_executor` and `tty_wrapper`
   Conclusion: In v1, the agent session may be conversational or interactive internally, but the workflow runner does not actively participate in that interaction after sending the initial prompt. The wrapper passively listens to the PTY transcript, and when it detects the expected completion JSON it triggers session shutdown and step completion. The only post-launch input the runner should send is the configured quit sequence.

9. Status: `decided`
   Topic: Reference escaping
   Question: How can workflow authors express a literal string that starts with `$` without invoking reference resolution?
   Why it matters: The reference rules reserve exact-string `$...` values, but there is no escape mechanism for literal values.
   Relevant spec: `design.md` section `reference_resolver`
   Conclusion: Use `$$` as the v1 escape for literal leading-dollar strings. For exact-string values, `$$foo` resolves to the literal string `$foo`, including cases like `$$step1.output` that would otherwise be treated as references.

10. Status: `decided`
    Topic: Reference path syntax
    Question: Are numeric array indexes supported in dotted reference paths, and what characters are legal in step names and object keys?
    Why it matters: The resolver syntax is only loosely described. Developers need deterministic parsing rules.
    Relevant spec: `design.md` section `reference_resolver`
    Conclusion: Keep reference syntax minimal in v1. References support object-key traversal only, not arrays. Step names and referenceable object keys must satisfy standard Python identifier rules, so dotted paths can be parsed unambiguously as `step_name.key_name.more_keys`. JSONPath remains out of scope for v1.

11. Status: `decided`
    Topic: Unknown agents
    Question: Should an unknown `agent` name fail at parse time or execution time, and can workflows provide local agent config overrides?
    Why it matters: The registry boundary is clear, but the validation timing is not. This changes parser responsibility and user feedback quality.
    Relevant spec: `design.md` sections `workflow_parser` and `agent_registry`
    Conclusion: Unknown `agent` names should fail during workflow validation, before execution begins. Workflow-authored agent configurations are out of scope for v1; agent configs will likely live in global runtime configuration. If a step omits `agent`, the executor uses the configured default agent.

12. Status: `decided`
    Topic: Execution environment
    Question: What working directory, environment variables, and terminal dimensions should the PTY wrapper use?
    Why it matters: Agent behavior is highly environment-sensitive. Reproducibility requires explicit defaults.
    Relevant spec: `design.md` sections `tty_wrapper` and `agent_registry`
    Conclusion: In v1, the PTY wrapper should inherit working directory, environment variables, and terminal dimensions from the parent process. No workflow-level overrides are required.

13. Status: `decided`
    Topic: CLI surface
    Question: What should `cli.py` support in v1 beyond "run this workflow"?
    Why it matters: The package layout includes a CLI entrypoint, but there is no command contract for arguments, output mode, or exit codes.
    Relevant spec: `design.md` section `Suggested Package Layout`
    Conclusion: The v1 CLI should run a single workflow file. It should not stream step output to the terminal by default; transcript or step output streaming should only happen when `--verbose` is enabled. Exit code `0` indicates success, and non-zero exit codes indicate validation or workflow execution failure. Do not add a final human-readable summary in v1.

14. Status: `decided`
    Topic: Logging and observability
    Question: What runtime events should be logged, and at what verbosity levels?
    Why it matters: A PTY-driven runner will be hard to debug without a minimum logging contract.
    Relevant spec: cross-cutting, especially `workflow_engine`, `step_executor`, and `tty_wrapper`
    Conclusion: In normal mode, keep external logging minimal and quiet by default, surfacing only essential validation or execution failures. In `--verbose` mode, log workflow and step lifecycle events, stream live PTY output, and log the resolved step inputs and parsed step outputs. Full transcripts remain attached to `StepResult` in memory regardless of verbosity.

15. Status: `decided`
    Topic: Testing seams
    Question: What interfaces are expected to be mocked or faked in tests, especially around PTY I/O and agent output streams?
    Why it matters: The design is modular, but it does not state the intended seams for unit versus integration testing.
    Relevant spec: module boundaries overall
    Conclusion: In v1, require unit tests for `workflow_parser` and `reference_resolver`. Cover end-to-end behavior with integration tests that run against a deterministic local test agent rather than the real interactive agent CLI. Additional unit seams around executor or engine internals can be added later if needed.

## Conclusions

1. Step completion contract
   Source: `thoughts.md`
   Decision: A step completes when the agent emits a final output containing only a JSON object of the form `{"status": "OBJECTIVE_COMPLETE", "content": ...}`.
   Implementation note: The executor should parse the final JSON object, verify `status == "OBJECTIVE_COMPLETE"`, and store `content` as the resolved step output.

2. Step schema
   Source: `thoughts.md`
   Decision: The workflow is a top-level mapping of step-name to step-config. Each step config includes `prompt`, optional `input`, and `output`, with optional per-step `agent` support retained from `design.md`.
   Implementation note: `StepDefinition` should treat the top-level key as the step name rather than requiring a nested `name` property.

3. Output validation
   Source: user decision, consistent with `thoughts.md`
   Decision: `output` is a structural template with descriptive leaf text for the agent. Validation only checks required keys and nested shape.
   Implementation note: v1 should not infer or enforce scalar types from the descriptive strings in the template.

4. Prompt construction
   Source: user decision
   Decision: Use a single canonical prompt template that includes the fixed JSON completion instruction, optional resolved input, the step objective, and the output template.
   Implementation note: Render resolved `input` and authored `output` as YAML blocks under `Input:` and `Output template:` headings, and end with a reminder to return only the final JSON object.

5. Failure semantics
   Source: user decision
   Decision: Stop the workflow on the first failed step. Use a small explicit failure taxonomy covering pre-launch reference errors, launch failures, early session exit, malformed completion JSON, invalid completion payload shape, and timeout conditions.
   Implementation note: Keep v1 error reporting simple and structured; more nuanced JSON-recovery behavior can be added later.

6. Timeouts and liveness
   Source: user decision
   Decision: Use a 5-minute inactivity timeout, no max step duration, and a 30-second graceful quit timeout.
   Implementation note: A step may run indefinitely in v1 if it continues to emit output within the inactivity window.

7. Transcript handling
   Source: user decision
   Decision: Keep the full transcript for every step result.
   Implementation note: v1 keeps transcripts in-memory only; durable persistence is a later concern.

8. Human or tool follow-up turns
   Source: user decision
   Decision: Sessions may be interactive from the agent's perspective, but the runner is passive after the initial prompt.
   Implementation note: The wrapper listens for the completion payload and then sends only the quit sequence; it does not conduct a multi-turn protocol with the child in v1.

9. Reference escaping
   Source: user decision
   Decision: Use `$$` to escape literal leading-dollar strings.
   Implementation note: This applies only to exact-string scalar values that would otherwise be interpreted as references.

10. Reference path syntax
   Source: user decision
   Decision: Support only dotted object-key traversal in v1. No arrays.
   Implementation note: Step names and referenceable keys must be valid Python identifiers.

11. Unknown agents
   Source: user decision
   Decision: Fail early during validation for unknown agent names.
   Implementation note: Agent definitions are global runtime config, not workflow-local config, in v1.

12. Execution environment
   Source: user decision
   Decision: Inherit cwd, env, and terminal size from the parent process.
   Implementation note: This keeps v1 behavior aligned with the invoking shell and CLI environment.

13. CLI surface
   Source: user decision
   Decision: Support running one workflow file, quiet by default, with optional `--verbose` streaming.
   Implementation note: Skip final summary output in v1; rely on exit codes and returned results.

14. Logging and observability
   Source: user decision
   Decision: Keep normal mode quiet; use `--verbose` for lifecycle logging, PTY stream logging, and resolved step input/output logging.
   Implementation note: Transcript retention is independent of verbosity and always captured in memory on the step result.

15. Testing seams
   Source: user decision
   Decision: Require unit tests for parser and reference resolution, plus integration tests using a local test agent.
   Implementation note: Keep the initial testing strategy focused on the highest-value deterministic surfaces.

## Canonical Prompt Example

~~~text
I will give you an objective for this session.

When the objective is complete, your final output must be only a JSON object in this form:

{"status":"OBJECTIVE_COMPLETE","content":<filled result object>}

The `content` value must match the requested output structure.

Input:
```yaml
haikus:
  dogs: Dogs dream by the hearth
  cats: Cats vanish into dusk
  user_choice: Rain taps the porch rail
```

Objective:
Review the provided haikus.
Rank them in terms of which best captures the essence and style of haiku.

Output template:
```yaml
best_haiku:
  haiku: the selected haiku text
  reason: why this haiku was chosen
```

Return only the final JSON object when the objective is complete.
~~~
