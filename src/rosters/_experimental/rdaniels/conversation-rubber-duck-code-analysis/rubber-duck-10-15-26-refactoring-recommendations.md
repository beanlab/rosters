# Rubber Duck Refactoring Recommendations

**Date:** October 15, 2026  
**Repository:** `/mnt/c/Users/rebek/School/course-ops/rubber-duck`

## Objective

Restructure Rubber Duck so business workflows are easy to change without also changing Discord, Quest, OpenAI, SQL, Docker, or other infrastructure code.

The central architectural rule is:

> Business workflows decide **what should happen**. The framework decides **how workflows run**. Adapters decide **how external systems perform effects**.

## Recommended Architecture

```text
Discord / HTTP / OpenAI / SQL / Docker / Email / S3
                         │
                      Adapters
                         │
┌─────────────────────────────────────────────────────┐
│ Conversation Framework                              │
│ routing · lifecycle · persistence · timeouts        │
│ effect execution · completion · observability       │
└─────────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────────┐
│ Business Workflows                                  │
│ registration · assignment feedback · debugging      │
│ conversation review · tutoring                      │
└─────────────────────────────────────────────────────┘
```

## 1. Give Every Business Workflow One Interface

Every workflow should receive its current state and one event, then return a transition:

```python
transition = workflow.handle(state, event)
```

A transition should contain the updated state, requested effects, and lifecycle status:

```python
Transition(
    state=new_state,
    effects=[SendMessage("Please enter your Net ID")],
    status="running",
)
```

Business workflows should not directly access Discord, Quest queues, SQL sessions, OpenAI clients, HTTP, or Docker.

This gives each workflow a small test surface: provide state and an event, then verify the returned transition.

## 2. Create a Deep Conversation Runtime Module

A `ConversationRuntime` module should own:

- Conversation identifiers
- Quest aliases
- Event and message delivery
- Queue names
- Timeout behavior
- State persistence
- Workflow completion
- Final close messages
- Error handling
- Metrics and observability events

This replaces scattered queue strings, identifier conventions, and `ConversationComplete` handling with one explicit interface.

Quest should become an internal adapter used by the runtime rather than a framework that every workflow must understand.

## 3. Represent External Actions as Explicit Effects

Business workflows should request effects instead of performing external actions directly:

```python
SendMessage(text)
SendEmail(address, verification_code)
AssignDiscordRole(user_id, role_id)
RunAgent(agent_name, prompt)
FetchAttachment(url)
ExecutePython(code)
```

The conversation framework executes these effects through adapters and returns the results as later events.

Benefits:

- Business logic remains independent of infrastructure.
- Tests can inspect effects without calling external systems.
- Discord, email, OpenAI, and storage implementations can change independently.
- Retries and error handling can be centralized by effect type.

## 4. Make Registration a State Machine

Registration should have one authoritative sequence:

```text
NEED_NET_ID
  -> NEED_EMAIL_VERIFICATION
  -> NEED_NICKNAME
  -> NEED_ROLES
  -> COMPLETE
```

Only the registration workflow should change this state.

The AI agent may assist with narrow tasks such as interpreting ambiguous input or generating friendly wording. It should not independently select or invoke registration steps.

This removes the competing ownership between `Registration.run()` and the registration agent.

## 5. Create Focused Runtime Modules

### `AgentRuntime`

Own:

- Model requests
- Model/tool execution loop
- Structured-output validation
- Provider retries
- Agent results

Move Discord messages and metrics out of its core implementation. Inject provider and telemetry adapters at internal seams.

### `ExecutionRuntime`

Own:

- Python execution requests
- Execution timeouts
- Artifact collection
- Standardized execution results

Keep Docker lifecycle, file transfer, and resource staging inside adapters or internal modules.

### `ExecutionCache`

Own shared cache policy once:

- Expiration
- Hit promotion
- Result reconstruction
- Replay behavior
- Cleanup policy

Memory and SQL adapters should implement only storage mechanics.

### `Persistence`

Own:

- Session lifecycle
- Transaction rules
- Database models
- Schema migrations
- Failure behavior

Do not let each subsystem independently create tables and commit shared sessions.

### `ConfigCompiler`

Load configuration and validate it before runtime construction:

```python
runtime_plan = ConfigCompiler.load(config_uri)
```

The resulting runtime plan should contain validated, duck-specific settings rather than raw dictionaries.

### `ToolCatalog`

Own explicit tool registration:

- Reject duplicate names
- Validate schemas
- Represent optional parameters correctly
- Avoid behavior based only on a parameter being named `ctx`

Reflection may remain an implementation detail, but it should not define the public contract.

## 6. Use Adapters Only at Real Seams

Recommended adapter pairs include:

- Discord conversation adapter and in-memory test adapter
- OpenAI adapter and mock agent adapter
- SQL persistence adapter and in-memory persistence adapter
- SQL cache store and memory cache store
- Docker execution adapter and fake execution adapter
- HTTP attachment adapter and stub attachment adapter
- Local resource adapter and S3 resource adapter
- Production email adapter and test email adapter

Business workflows should not know which adapter is active.

Avoid adding interfaces where only one implementation exists and no test or production substitute is required.

## 7. Establish One Dependency Direction

Dependencies should point toward stable business and framework interfaces:

```text
Composition root
  -> business workflows
  -> conversation framework
  -> adapter implementations

Business workflows
  -> workflow events, effects, and state types

Adapters
  -> framework interfaces
```

Business workflows must not import adapter implementations. Foundational types must not import Docker, AWS, Discord, or specific workflow models.

## 8. Suggested Package Structure

```text
src/
  framework/
    conversation_runtime.py
    workflow_runner.py
    events.py
    effects.py
    transitions.py

  workflows/
    registration/
    assignment_feedback/
    debugging_practice/
    conversation_review/
    tutoring/

  runtime/
    agents.py
    execution.py
    cache.py
    persistence.py

  adapters/
    discord.py
    quest.py
    openai.py
    sqlalchemy.py
    docker.py
    http.py
    email.py
    resources.py

  bootstrap/
    config.py
    registry.py
    main.py
```

The exact names may change, but ownership and dependency direction should remain clear.

## 9. Testing Strategy

Treat each deep module's interface as its test surface.

### Business workflow tests

Test workflows as state transitions:

```text
Given state + event
When workflow handles the event
Then expected state + effects + status are returned
```

These tests should not require Discord, Quest, OpenAI, SQL, or Docker.

### Framework tests

Test the conversation runtime using in-memory adapters:

- Incoming message delivery
- Timeout behavior
- State persistence
- Effect execution
- Completion and closing
- Retry and failure behavior

### Adapter contract tests

Run the same behavioral test suite against interchangeable adapters where possible:

- Memory and SQL cache stores
- Memory and SQL persistence
- Fake and Docker execution
- Stub and production-like HTTP fetching

Tests should use the same interfaces as production rather than replacing private attributes.

## 10. Migration Plan

Avoid a full rewrite. Move one seam at a time.

1. Validate configuration into a `RuntimePlan`.
2. Introduce `ConversationRuntime` around existing Quest behavior.
3. Centralize completion, timeout, and close behavior.
4. Adapt existing workflows to the new runtime without rewriting their internals.
5. Convert registration into the first explicit state machine.
6. Separate `AgentRuntime` from Discord and metrics.
7. Centralize cache policy above memory and SQL adapters.
8. Centralize persistence ownership and migrations.
9. Split Python execution from Docker and resource adapters.
10. Migrate remaining workflows individually.
11. Remove old queue access, completion exceptions, duplicate policy, and direct adapter access.

## Priority Order

1. Conversation runtime and explicit lifecycle
2. Registration state ownership
3. Runtime configuration validation
4. Agent runtime internal seams
5. Cache policy consolidation
6. Persistence ownership
7. Execution/runtime infrastructure separation
8. Remaining workflow migrations

## Expected Outcome

After this refactoring:

- Adding or changing a business use case primarily changes one workflow module.
- Discord, Quest, OpenAI, SQL, and Docker can evolve without rewriting workflow rules.
- Important contracts are explicit rather than encoded as matching strings and call order.
- Each behavior has one authoritative owner.
- Tests exercise production interfaces rather than private implementation details.
- `main.py` becomes a small composition root that validates configuration, selects adapters, registers workflows, and starts the runtime.
