# MyTeam workflow AppServer orchestration

Create a separate executable for `myteam` workflows that can manage Codex conversations by using Codex's existing `AppServer` infrastructure.

## Context

Codex currently has two ways of doing things:

- when the terminal opens, it runs all in-process
- when the app is used, it `Popen`-spawns a Python server called `AppServer`
  - the front end communicates with the server through standard I/O
  - the communication is JSON-RPC-style
  - the server spawns and manages Codex threads

The existing app/server infrastructure means a different front end could be created without having to build all the underlying Codex thread infrastructure again.

## Proposed executable

Create a separate executable, not `codex`; possible names mentioned included:

- `cdx`
- `myTeamStart`

The desired direction is for it to ultimately live in `myteam` as a new branch of behavior.

The command would point at a folder representing a workflow. For example:

```sh
myTeamStart dev
```

The `dev` folder would contain `flow.yml` or `flow.yaml`, which the executable would load and run.

## Workflow behavior

The executable would:

1. spin up Codex `AppServer`
2. allow threads to communicate with that server as normal channels, like the Codex app does now
3. listen through the UI to messages and conversations
4. close a thread when a conversation step concludes
5. start a new thread in the same UI for the next step

The intended user experience is one long conversation with Codex, while Codex shifts roles and context throughout the workflow. Closing a thread is like closing one role; opening the next thread starts a new role.

## Flow YAML design

The flow definition should allow a state/step such as `plan` to specify:

- a name
- a state
- a role
- inputs
- outputs

For roles, the flow could identify a `myteam` role by directory name, such as `planning-interface`, resolving to something like:

```text
planning-interface/role.md
```

### Outputs

Outputs are loosely structured. For example, an output key such as `plan_doc` would include a description of what it is. The output block is passed into the context for the role so the agent knows what the user expects when the step is done.

The agent creates the output, and the infrastructure holds it in memory. If something explicitly needs to be saved, the agent can write it to a file and output the path. Outputs could also be plain text, such as a summary or bullet list.

The output shape is a template-like structure: keys define the structured output, and values are strings describing what belongs there.

Structured output through JSON may be useful, but because the interaction is a conversation/thread, there is design exploration needed around whether the infrastructure can force a structured output when concluding a thread.

### Inputs

Inputs can be arbitrary JSON. Later steps can reference previous outputs, such as referencing the plan step's `plan_doc`. Possible reference styles mentioned included:

- `$.plan.output`
- `plan_doc: plan_doc`
- JSON references
- JSON Pointer
- JSONPath

The workflow should be able to reference multiple steps, pull pieces out, linearize dependencies, and run the steps in order.

## Open design questions

- Can a Codex thread be controlled well enough to fully manage its lifecycle through the `AppServer`?
- Can the infrastructure force structured output when a conversational thread is concluding?
- How should the system know that a step has ended?
  - semantic detection was mentioned as a possibility
  - semantic detection may be hard because the conversation might appear to stop while still being mid-conversation

## Implementation approach

The desired implementation should require minimal new infrastructure: mainly a small Python layer for managing workflow steps. Codex `AppServer`, communication channels, and thread management should remain Codex's existing infrastructure as much as possible.

Minimizing new maintenance burden is a priority.

## Related notes

This idea came from inspecting Codex source while working with workflow. Running `AppServer` alone appeared to do nothing until its interaction model was understood from the source.
