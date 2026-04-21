# Gaps

This file tracks discrepancies between [thoughts.md](/Users/gbean/projects/rosters/experimental/bean/workflows/thoughts.md)
and [design.md](/Users/gbean/projects/rosters/experimental/bean/workflows/design.md). Each point should be reviewed and
resolved explicitly.

## 1. Interactive session confirmation flow

Observed in `thoughts.md`:
- For interactive sessions, the agent should present the filled template to the user, confirm satisfaction, and only then emit the final completion JSON.

Current state in `design.md`:
- The executor is explicitly passive after launch in v1.
- The completion contract assumes a single final JSON object and does not describe an intermediate user-confirmation loop.

Question to resolve:
- Is interactive confirmation part of v1, deferred to a later version, or intentionally out of scope?

Conclusion:
- Out of scope for v1.
- A future version should support specifying a step-generic prompt fragment that is injected into each step prompt.
- That future prompt-injection mechanism is the appropriate place to revisit any interactive-session guidance, including user confirmation before final completion output.

## 2. Step-state retention beyond outputs

Observed in `thoughts.md`:
- The engine should store step outputs, including step config and completed output section, against step keys.

Current state in `design.md`:
- The engine stores prior step outputs for later reference resolution.
- The design does not say that prior step configs are retained in the referenceable run state.

Question to resolve:
- Should the runtime retain only completed outputs for downstream references, or should it also retain step config in the persisted per-step run state?

Conclusion:
- The engine should retain the full per-step structure, including authored step config and the completed output, under each step key.
- References should resolve against that full stored step structure rather than a separate prior-outputs-only map.
- This is preferred because it keeps the referenceable runtime state aligned with the authored workflow structure and allows later steps to reuse prior inputs and other authored fields when needed.

## 3. Reference language scope

Observed in `thoughts.md`:
- The `input` section should reference step outputs with JSONPath.

Current state in `design.md`:
- V1 supports exact-string dotted references only.
- JSONPath is explicitly listed as a v1 non-goal.

Question to resolve:
- Should v1 keep the reduced dotted-reference design, or should the design be expanded to support JSONPath?

Conclusion:
- V1 should keep the current simple dotted-reference design rather than adopting JSONPath.
- The simpler syntax is sufficient for the intended v1 reference model and keeps implementation and validation straightforward.
- This conclusion still assumes references operate against the full stored per-step structure described in point 2.

## 4. Role of `cdxtty.py`

Observed in `thoughts.md`:
- The process prototyped in `cdxtty.py` should be used to spawn and monitor the child session.

Current state in `design.md`:
- `cdxtty.py` is mentioned as the prototype source for the `tty_wrapper` boundary.
- The design does not state whether the implementation must directly reuse that prototype, merely draw from it, or replace it.

Question to resolve:
- Is `cdxtty.py` a required implementation basis, a reference only, or irrelevant once the wrapper module exists?

Conclusion:
- The relevant PTY/session-management behaviors from `cdxtty.py` should be captured explicitly in `design.md`.
- Once those behaviors are documented in the design, `design.md` should not depend on or reference `cdxtty.py` as a prototype source.
- `cdxtty.py` is therefore a useful source of implementation detail, not an ongoing architectural dependency.

## 5. Step-level `--exec` mode

Observed in `thoughts.md`:
- A future step-level `--exec` mode is called out.
- That mode may require settings distinct from general model settings because the interaction mode differs.

Current state in `design.md`:
- The design mentions future per-step model and runtime settings, but does not mention `--exec` specifically.

Question to resolve:
- Should `--exec` be documented now as an explicit extension point, or left out until there is a concrete design?

Conclusion:
- `--exec` mode should remain a future direction rather than part of the v1 design.
- It may eventually require step-level runtime settings distinct from normal conversational sessions, but those semantics are not defined yet and should not shape the v1 architecture beyond keeping room for future extension.

## 6. Multi-agent backend configuration details

Observed in `thoughts.md`:
- Future support may require configurable executable, `--exec` mode, quit command, and other agent-specific settings for tools such as Claude or Opencode.
- Each step may reference the agent it wants to use.

Current state in `design.md`:
- V1 has a minimal `agent_registry` with `argv` and `exit_text`.
- Multiple agent backends beyond Codex are a v1 non-goal, though later expansion is acknowledged.

Question to resolve:
- Should the design document more concrete future-facing agent-config fields now, or keep the current minimal registry until multi-backend work is in scope?

Conclusion:
- The design should keep the agent configuration minimal for now.
- The required agent-config fields are:
  - `name`
  - executable
  - args
  - exit sequence
- Additional backend-specific settings can be deferred until they are concretely needed.
