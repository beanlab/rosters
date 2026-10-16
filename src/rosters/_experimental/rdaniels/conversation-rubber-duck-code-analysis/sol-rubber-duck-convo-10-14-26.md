# Rubber Duck Architecture Conversation Findings

## Context and Cost

- **Repository reviewed:** `/mnt/c/Users/rebek/School/course-ops/rubber-duck`
- **Repository purpose:** A configurable Discord bot platform for AI-assisted learning workflows.
- **Review date:** October 14, 2026
- **Conversation goal:** Understand the codebase, identify its most important structural problems, and develop concise explanations of why they matter.
- **Token usage:** Not exposed to the assistant by the current Codex runtime.
- **Total conversation cost:** Not available. An exact calculation requires input/output token counts, model identity, and billing rate; inventing an estimate would be misleading.

## System Overview

```text
Discord
  -> DiscordBot receives an event
  -> RubberDuckApp routes the event
  -> DuckOrchestrator starts a conversation
  -> The configured duck workflow runs
  -> AIClient calls OpenAI and registered tools
  -> Results are sent back to Discord
```

Configuration selects the duck workflow for each Discord channel. Quest supplies workflow persistence, aliases, and event queues. SQL stores workflow state, metrics, feedback, and optional tool-cache data.

## Main Findings

### 1. Brittle Invisible Contracts Between Modules

This is the most important issue. Several modules must independently know and obey conventions that are not centralized or enforced:

- Exact queue names such as `messages` and `feedback`
- Discord thread or message IDs reused as Quest workflow aliases
- The required order in which aliases and queues are established
- `ConversationComplete` meaning normal workflow termination
- Expected dictionary keys and nested configuration shapes

For example, `RubberDuckApp` sends follow-up events to a queue named `messages`, while `TalkTool` independently waits on a queue with the same name. Python does not verify that these strings agree. Changing one location can silently leave a workflow waiting on the wrong queue.

> The system relies on invisible intermodule contracts. Modules must manually agree on queue names, identifiers, exceptions, dictionary keys, and call order. Because those rules are not owned or validated in one place, a change in one module can silently break another.

### 2. Registration Has Competing Owners

Registration has two overlapping control mechanisms:

1. `Registration.run()` executes a fixed sequence: Net ID, email verification, nickname, and roles.
2. An AI registration agent can invoke those same registration operations as tools.

If the fixed sequence returns a partial `RegistrationInfo`, `RegistrationWorkflow` summarizes the progress as text and asks the AI agent to finish the process. This creates two completion paths and makes ownership unclear.

A concrete mismatch already exists: `RegistrationInfo` defines `roles_assigned`, while the implementation writes `roles`.

> Registration has two possible orchestrators. Both can control the same operations, so state ownership and sequencing are ambiguous and can drift apart.

**Likely fix:** Choose one authoritative orchestrator, preferably a deterministic registration state machine. AI may assist with narrow decisions or wording, but should not independently control step transitions.

### 3. Configuration Is Parsed but Not Validated

Configuration files are loaded into ordinary dictionaries and annotated as `Config`. `TypedDict` documents expected structure but does not validate YAML or JSON at runtime. Validation is scattered among constructors and workflows as direct dictionary access and partial checks.

> The application does not verify at startup that configuration dictionaries contain the expected values. Invalid configuration survives too long and produces confusing downstream failures.

### 4. `AIClient` Has Too Many Internal Responsibilities

`AIClient` handles OpenAI requests, tool execution, retries, Discord typing and retry messages, conversation history, structured-output validation, metrics, and agent-as-tool construction. Its external interface is useful, but unrelated concerns collide internally. Tests expose this by replacing private attributes.

> `AIClient` provides a useful interface but internally mixes AI execution, Discord behavior, retries, and telemetry, making it difficult to change or test safely.

### 5. Cache Policy Is Duplicated

`InMemoryToolCache` and `SqlToolCache` appropriately store data differently, but both independently implement expiration, hit counting, result replay, output reconstruction, cleanup, and administration. Both hit checks also ignore expiration until cleanup runs.

> Memory and SQL should differ only in storage mechanics, but cache policy is duplicated across both implementations and can drift.

### 6. Heavy Infrastructure Leaks Through Foundational Interfaces

The lightweight-looking `utils.protocols` module imports `FileResult` from `python_exec_container`. That transitively pulls in Docker, resource staging, and AWS/S3 dependencies.

> Shared interfaces depend on a heavyweight implementation, so unrelated modules pull in Docker and AWS dependencies they do not need.

### 7. `PythonExecContainer` Is Internally Monolithic

`PythonExecContainer` owns Docker lifecycle, resource staging, container file transfer, generated execution code, timeouts, artifact extraction, and dataset metadata.

> The execution module bundles many infrastructure concerns, and shared code depends on it, causing heavyweight dependencies to spread.

### 8. Database Ownership Is Scattered

Workflow persistence, metrics, and tool caching independently create tables, manage sessions, commit transactions, and define failure behavior. They use multiple SQLAlchemy declarative bases. Metrics methods hide database failures and perform synchronous commits behind async methods.

> There is no consistent persistence module owning schemas, sessions, transactions, and failure behavior, so database behavior is fragmented.

### 9. `Reporter` Does Too Much

`Reporter` combines command parsing, SQL-shaped input handling, DataFrame transformations, pricing, validation, graph rendering, help text, and interactive terminal behavior.

> Reporting combines command language, data processing, pricing, and visualization in one module, making changes difficult to isolate and test.

### 10. `PersistentQueue` Overstates Its Durability

Queue operations update an in-memory list. Persistence occurs when the surrounding long-running context exits, so a crash can lose recent changes.

> The queue is called persistent, but durability depends on graceful shutdown, so its interface implies stronger guarantees than its implementation provides.

### 11. `Armory` Depends on Reflection and Hidden Rules

Tool registration depends on decorators, context being named `ctx`, reflection, unique names, and correct schema inference. Duplicate names can silently overwrite tools, and optional arguments may appear required.

> Armory tool registration relies on naming, reflection, and decorator conventions that are not clearly enforced, creating another brittle invisible contract.

### 12. `DuckContext` Is Too Broad

`DuckContext` carries Discord IDs, user identity, message content, thread information, and timeout settings through workflows, AI execution, and tools. Most consumers need only a subset.

> A broad Discord-shaped context leaks transport details into unrelated modules and makes them harder to test independently.

### 13. HTTP Fetching Lives in the Discord Adapter

`DiscordBot.read_url()` performs arbitrary URL fetching with synchronous `requests.get()` inside an async method. Fetching web content is not a Discord responsibility, and the synchronous request can block the event loop.

> Generic HTTP behavior lives in the wrong module and can block asynchronous Discord processing.

### 14. `main.py` Contains Too Much Construction Knowledge

`main.py` knows every duck type, workflow constructor, configuration shape, tool type, cache type, database dependency, Discord dependency, and background task. Adding a workflow requires editing a central string-based type switch.

> The composition root has become a large factory containing knowledge about every module, creating a central point of coupling and frequent change.

### 15. Workflow Modules Mix Different Kinds of Logic

Assignment feedback combines user conversation, URL downloads, Markdown parsing, YAML loading, project detection, AI grading, rubric traversal, and response formatting. Registration similarly mixes conversation, email, Discord roles, retry behavior, validation, state, and escalation.

> Workflows mix orchestration, domain rules, infrastructure, and presentation, so individual behaviors cannot be changed or tested independently.

### 16. Rubric Structures Are Implicit Dictionaries

Consumers must remember keys such as `exercises`, `rubric_text`, `traceback`, and `error_type`. Assignment feedback also reads the same files separately for rubric content and rules.

> Rubric structure is another implicit dictionary contract, with duplicated loading logic and no central validation or typed model.

### 17. The Most Important Seams Lack Tests

Tests cover selected formatting, retry behavior, SQL happy paths, and helpers. They largely miss conversation lifecycle, registration sequencing, final configuration validation, cache-adapter consistency, reporting, Docker execution, queue durability, and Armory registration.

> Tests cover isolated details while the brittle intermodule contracts and major workflow paths remain mostly untested.

### 18. Package Dependencies Do Not Follow a Clear Direction

Utility code depends on metrics while metrics also depends on utilities. Generic storage serialization imports models from a specific debugging workflow.

> The package structure does not consistently reflect ownership, so foundational modules sometimes depend on higher-level product behavior.

### 19. Workflow Completion Uses an Unusual Control Exception

`ConversationComplete` inherits from `BaseException`, so ordinary `except Exception` handlers do not catch it. Each workflow must remember to handle it correctly.

> Normal workflow completion uses an unusual exception whose handling is distributed across workflows rather than centralized at the lifecycle seam.

### 20. Storage Representation Leaks Into Reporting

`SQLMetricsHandler` returns lists whose first row contains column names and remaining rows contain values. `Reporter` must know and convert this storage-specific representation.

> Storage exposes its internal row representation instead of meaningful records, coupling reporting to database formatting details.

### 21. Workflow Storage Is Weakly Constrained

`SqlBlobStorage` fetches all namespace records and searches them in Python rather than querying by name and key. The database does not enforce uniqueness for the logical `(name, key)` identity.

> Workflow storage ignores database querying strengths and does not enforce its own identity rules at the database level.

### 22. The `conversation` Package Does Not Own Conversation Behavior

The package mostly contains thin delegators to `AIClient`, while timeouts, history, message waiting, completion, and event delivery live elsewhere.

> The package name suggests clear ownership, but real conversation behavior remains scattered across workflows and Quest integration.

### 23. Dead or Dormant Code Adds Risk

`BashExecuteCommand` is not registered but remains in the command module and can execute strings with `shell=True`.

> Unused code still creates cognitive and security risk because it can be misunderstood, accidentally reconnected, or unnecessarily maintained.

### 24. Duplicate SQL Blob-Storage Implementations Exist

The repository defines a local `SqlBlobStorage`, while other runtime code uses Quest's SQL blob storage.

> Two implementations of the same persistence concept coexist without a clear authoritative owner.

### 25. Database Schema Creation Is Distributed

Metrics, workflow records, and tool cache independently create SQLAlchemy bases and tables during runtime.

> There is no centralized schema or migration strategy, so database evolution is distributed and difficult to coordinate safely.

### 26. Resource Staging Mixes Local and S3 Implementations

One module branches between local and S3 behavior and creates its S3 dependency globally rather than receiving an adapter.

> Two real storage environments exist, but their implementations are mixed rather than placed behind a clean seam.

### 27. Fatal Startup Errors Are Swallowed

The top-level `main()` catches every exception, logs and prints it, but does not re-raise. Deployment systems may observe a normal exit instead of a failure.

> The application hides fatal failure from its environment, weakening operational error detection.

### 28. `utils` Has Become a Catch-All Package

The package contains configuration, Docker execution, resource staging, email, logging, persistence, retry, protocols, and feedback notification.

> Unrelated infrastructure is grouped under a vague name, making ownership and dependency direction harder to understand.

## Overall Diagnosis

The recurring themes are:

1. **Invisible contracts:** Important agreements exist only as matching strings, dictionary shapes, naming conventions, and call order.
2. **Unclear ownership:** Multiple modules or mechanisms can control the same behavior.
3. **Mixed responsibilities:** Modules combine behavior that changes for unrelated reasons.
4. **Weak seams:** Tests must replace private attributes or import heavyweight infrastructure.
5. **Late validation:** Invalid data survives until a distant runtime failure.
6. **Inconsistent dependency direction:** Foundational modules depend on higher-level implementations.

The first architectural improvement should be a single conversation-runtime module that owns Quest aliases, event delivery, queue names, timeouts, completion, and close behavior. Registration should then receive one authoritative state-machine owner, followed by startup configuration validation.

## Questions and Prompts That Uncover These Issues

### Initial Exploration

1. "I do not know this codebase. Explain its primary runtime flow from an incoming request to the final response."
2. "What are the major modules, and what behavior is each supposed to own?"
3. "Which files must I understand simultaneously to follow one user interaction?"
4. "Highlight the structural issues most likely to cause defects or make changes risky."

### Invisible Contracts

5. "Which modules must agree on exact string values, dictionary keys, IDs, exception types, or call order?"
6. "Where are magic queue names, workflow names, event names, or aliases created and consumed?"
7. "What could one module rename or reorder without the compiler warning that another module will break?"
8. "Which important interface rules exist only in implementation details?"

### Ownership and Orchestration

9. "For each workflow, which single module decides what step runs next?"
10. "Are there multiple valid paths that can complete the same workflow?"
11. "Who owns authoritative workflow state, and are there competing representations?"
12. "Does any workflow combine deterministic orchestration with AI tool-driven orchestration?"
13. "If a workflow stops partway through, who is responsible for resuming it?"

### Configuration and Data Validation

14. "Is external configuration validated once at startup, or checked piecemeal by consumers?"
15. "Do type annotations provide runtime validation, or are parsed dictionaries merely labelled with types?"
16. "Where would a missing or misspelled configuration key fail?"
17. "Which dictionary structures require callers to memorize undocumented keys?"

### Module Design

18. "Which modules handle concerns that change for unrelated reasons?"
19. "For each large module, what does its public interface hide, and what still leaks to callers?"
20. "Would deleting this module remove complexity, or merely spread it among callers?"
21. "Which modules are externally useful but need internal seams for testing?"
22. "Which foundational modules import concrete infrastructure implementations?"

### Adapters and Duplication

23. "Where do multiple adapters implement the same policy instead of only different storage or transport mechanics?"
24. "Compare the memory and SQL implementations method by method. Which behavior is duplicated?"
25. "Are two implementations of the same persistence concept present without a clear authoritative version?"
26. "Which seams have two genuine adapters, and which abstractions have only one implementation?"

### Async and Infrastructure

27. "Which async functions perform synchronous network, file, or database work?"
28. "Could any synchronous dependency block the main event loop?"
29. "Which lightweight imports transitively load Docker, cloud SDKs, or database drivers?"
30. "Are infrastructure dependencies constructed globally or injected at a clear seam?"

### Persistence

31. "Which module owns database sessions, transactions, schemas, migrations, and failure semantics?"
32. "Are database errors reported to callers or silently logged?"
33. "Does anything described as persistent write on each mutation, or only during graceful shutdown?"
34. "Are logical uniqueness and identity rules enforced by the database?"
35. "Does storage return meaningful records or leak raw table formatting?"

### Testing

36. "Do tests use the same interfaces as production, or replace private attributes and internals?"
37. "Which cross-module contracts have no integration or contract tests?"
38. "Can the same behavioral test suite run against every adapter?"
39. "Which modules require Docker, AWS, Discord, Quest, or OpenAI merely to import or construct?"
40. "What important failure modes are not represented in the current tests?"

### Prioritization

41. "Which issue has the widest change ripple across the codebase?"
42. "Which structural issue has already produced an observable defect?"
43. "Which refactor would create the most useful shared test surface?"
44. "What should be fixed first to improve locality and reduce invisible contracts?"
45. "Which findings are architectural, and which are localized implementation defects?"
