# Code Quality Report

Code: `/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam`

Overall score: **7.6/10**

## Cognitive Complexity

Score: **7/10**

- Score rationale: Most small helpers use guard clauses and straight-line returns, so ordinary parsing/configuration code is easy to follow (for example, `src/myteam/workflows/commands.py:247-253` and `src/myteam/workflows/agent_session.py:423-427`).
- `src/myteam/workflows/execution/supervisor.py:108-155` contains a long `while` event loop with several state-dependent branches: command draining, process reaping, completion detection, idle waiting, wakeup handling, PTY pumping, and EOF handling. The nested conditions and multiple `continue` paths make the supervisor lifecycle difficult to follow in one function, even though the branches are operationally necessary.
- `src/myteam/workflows/execution/workflow_store.py:236-293` performs several distinct graph operations in one method: filtering nodes, deriving parents with type-dependent branches, validating missing parents and roots, detecting branching/cycles/disconnection, traversing the chain, and formatting output. The loop/conditional nesting forces the reader to track both graph validation and serialization concerns simultaneously.
- `src/myteam/workflows/agent_session.py:448-502` combines result-channel polling, PTY polling, deadline-based termination, output pumping, EOF recovery, exception handling, and result collection inside one infinite loop. The duplicated completion paths at `478-482` and `495-502`, plus the nested `try/except` at `496-499`, increase the mental state needed to determine how the function exits.
- `src/myteam/workflows/agent_session.py:523-545` has layered exception handling and type-dependent result normalization (`list`, `UsageInfo`, or `dict`) nested under an optional callback check. It is localized and understandable, but still requires following several alternative shapes in one function.
- `src/myteam/workflows/agents/runtime.py:59-104` has multiple configuration-loading branches and exception translations for local versus packaged agents. The early returns help, but the function still interleaves source selection, dynamic import, validation, and user-facing error mapping.

## Coupling

Score: **5/10**

- `src/myteam/workflows/agent_session.py:62-145` makes `run_agent` coordinate configuration loading, prompt rendering, runtime-agent selection, registration RPC, PTY process creation, result-channel ownership, and session cleanup. Its imports at `:20-52` expose dependencies on configuration, templates, prompt rendering, RPC protocol constants, PTY forwarding/process/terminal modules, and result models, so changes to several infrastructure details can require changes in this public workflow function.
- `src/myteam/workflows/agent_session.py:448-502` directly combines `AgentResultServer`, `ManagedPtyProcess`, `RealTerminal`, PTY polling/forwarding, stdout writing, timeout handling, and agent exit signaling. This is a broad orchestration interface with concrete terminal/process and result-channel knowledge rather than a small capability seam.
- `src/myteam/workflows/commands.py:15-16` imports `build_agent_prompt` from the standalone agent-session module. The workflow-command module therefore depends on an implementation module that also owns agent process execution; the prompt helper is a cross-responsibility dependency, and moving/refactoring agent execution risks the workflow-start path.
- `src/myteam/workflows/commands.py:185-244` branches on raw environment variables and directly constructs either a `Supervisor` or `RpcClient`, then knows the RPC kinds, parent workflow/agent identifiers, absolute workflow path, polling protocol, and acknowledgment lifecycle. Nested workflow behavior is consequently coupled to transport details and process orchestration.
- `src/myteam/workflows/execution/supervisor.py:39-64` hard-wires `WorkflowStore`, `RealTerminal`, `WorkflowStack`, `WorkflowRpcServer`, a command queue, wakeup pipe, and shutdown event into one constructor/context manager. `:157-202` then coordinates their transaction, PTY, result, and resume semantics, so modifications to any of these concrete modules can propagate into the supervisor.
- `src/myteam/workflows/execution/workflow_rpc.py:30-35,75-139` receives concrete `WorkflowStore`, `Queue[Command]`, `Event`, and wake callback dependencies, while `_accept_start_workflow` constructs a concrete `StartWorkflowCommand` and invokes store validation/creation. The RPC adapter is coupled to both the in-memory hierarchy model and the supervisor’s command representation.
- `src/myteam/workflows/execution/workflow_store.py:170-202` is not only domain state; its public methods parse RPC dictionaries, validate wire fields, and return wire-shaped response dictionaries for polling, acknowledgment, and result reporting. This couples persistence/hierarchy rules to the socket protocol, so a transport schema change must touch the store.
- `src/myteam/workflows/agents/runtime.py:299-354` adapts multiple external agent-config conventions by introspecting signatures and retrying positional calls after catching `TypeError`. The runtime layer consequently encodes legacy/current adapter shapes and all supported `build_argv` parameter knowledge, increasing coupling between plugin implementations and runtime compatibility logic.
- `src/myteam/config.py:192-206` keeps both `.myteam.yaml` and legacy `.myteam/.config.yaml` layouts in the same defaults-loading path. This is intentional compatibility, but it means callers and configuration evolution remain coupled to two storage conventions and precedence rules.

## Essential Complexity

Score: **10/10**

- The project’s executable source is Python, and a repository-wide search of `src` found no `goto`, labels, or equivalent arbitrary jumps; control flow is expressed through structured `if`/`elif`/`else`, `for`, `while`, `try`/`except`, and function returns.
- The `break` and `continue` statements are loop-local: for example, the socket server’s timeout `continue` and shutdown `break` are inside the same `while` loop at [src/myteam/workflows/agent_result_channel.py:81-90](src/myteam/workflows/agent_result_channel.py:81), with the same pattern in [src/myteam/workflows/execution/workflow_rpc.py:58-67](src/myteam/workflows/execution/workflow_rpc.py:58).
- The supervisor’s polling branches all re-enter the enclosing `while` loop via `continue`, while completion returns from the loop/function; they do not jump into the middle of another region ([src/myteam/workflows/execution/supervisor.py:108-155](src/myteam/workflows/execution/supervisor.py:108)).
- Nested loops use ordinary structured exits: the agent-session forwarding loop terminates through returns or continues its own loop ([src/myteam/workflows/agent_session.py:473-502](src/myteam/workflows/agent_session.py:473)), and the nested search loops in `agent_utils.py` return or continue only within their enclosing loops ([src/myteam/workflows/agents/agent_utils.py:98-111](src/myteam/workflows/agents/agent_utils.py:98)).
- Under McCabe essential-complexity semantics, the inspected Python control-flow graphs have the structured baseline (essential complexity 1); there is no evidence of irreducible flow requiring refactoring for this metric.

## Function_Naming

Score: **9/10**

- Score reflects that most function names directly describe their behavior and inputs, e.g. `load_myteam_config`, `split_markdown_frontmatter`, `list_resource_entries`, `build_agent_prompt`, `resolve_session_path`, and `drain_pty_output` (for example, `src/myteam/config.py:86`, `src/myteam/frontmatter.py:22`, `src/myteam/listing.py:80`, `src/myteam/workflows/agent_session.py:396`, `src/myteam/workflows/agents/agent_utils.py:93`, and `src/myteam/workflows/execution/pty_forwarding.py:145`).
- Related helper names are usually specific enough to convey their role without implementation details: `_load_jinja_function_module`, `_normalize_timeout_output`, `_tree_file_destination`, `_workflow_process_result_from_supervisor_result`, and `_require_positional_parameter_count` (for example, `src/myteam/prompt_rendering.py:111`, `src/myteam/prompt_rendering.py:160`, `src/myteam/rosters/__init__.py:117`, `src/myteam/workflows/commands.py:255`, and `src/myteam/workflows/agents/runtime.py:268`).
- A few private helpers are overly generic and require reading their callers or bodies: `_choose` does a three-level precedence selection but does not say what is being chosen (`src/myteam/workflows/agent_session.py:423`); `_invalid` raises a workflow-metadata validation error but does not identify the invalid metadata (`src/myteam/workflow_metadata.py:69`); and `_format_info` formats a resource-info record but omits that subject from its name (`src/myteam/listing.py:182`).
- Short conventional names such as `main`, `add`, `close`, `write`, and `_mtime` are understandable in their local contexts, but they provide little standalone semantic detail; `_mtime` is particularly terse for a helper used to sort session paths by modification time (`src/myteam/workflows/agents/agent_utils.py:102-114`).

## Good Code

Score: **7/10**

- **Positive:** Configuration parsing is cohesive and explicit: YAML shape, mapping types, empty names/targets, and Pydantic validation errors are checked with actionable `ValueError` messages in `src/myteam/config.py:102-155`.
- **Positive:** Workflow hierarchy code is focused around `WorkflowStore`, uses an `RLock`, and validates missing parents, branching, cycles, disconnected nodes, and duplicate roots in `src/myteam/workflows/execution/workflow_store.py:37-49` and `:236-277`.
- **Positive:** Resource cleanup is generally handled deliberately: agent registration is unregistered on failure in `src/myteam/workflows/agent_session.py:123-145`, PTY descriptors/processes are closed in `src/myteam/workflows/execution/pty_process.py:158-176`, and included-template stack cleanup uses `finally` in `src/myteam/prompt_rendering.py:215-229`.
- **Positive:** Error paths usually add useful context, such as shell command, exit code, combined output, and timeout details in `src/myteam/prompt_rendering.py:129-155`, and RPC input validation is centralized in `src/myteam/workflows/execution/workflow_rpc.py:113-171`.
- **Negative:** Several public/internal helpers omit return annotations despite the instruction to use type hints where supported, including `WorkflowRpcServer.start/close/_serve/_handle_connection` at `src/myteam/workflows/execution/workflow_rpc.py:39-69`, registration methods at `src/myteam/workflows/agent_session.py:260-298`, and multiple roster helpers at `src/myteam/rosters/__init__.py:53-103` and `:124-125`. The roster module also relies on unparameterized `dict`/`list` types there.
- **Negative:** Error handling is overly broad in important paths and can hide actionable failures: `except BaseException` with swallowed cleanup errors occurs in `src/myteam/workflows/agent_session.py:138-143`, `:269-276`, and `:214-224`; metadata/session discovery suppresses every `Exception` in `src/myteam/workflows/agent_session.py:523-537`; and network/download functions catch every `Exception` in `src/myteam/rosters/__init__.py:53-72`.
- **Negative:** `render_prompt_text` exposes a `shell(command)` helper implemented with `shell=True` in `src/myteam/prompt_rendering.py:129-155`. Although failures are reported, accepting a raw shell command makes the interface less explicit and maintainable and requires careful trust-boundary documentation.
- **Verification:** `python -m compileall -q src tests` completed successfully. The environment has neither `pytest` nor `uv`, so the test suite could not be run.

Overall, the code is structured and has substantial explicit validation and cleanup, but inconsistent typing and broad exception suppression keep it from being exemplary under these instructions.

## Maintainability Index

Score: **5/10**

- Scope: inspected Python implementation files under `src/myteam/**/*.py` (5,745 physical lines); excluded tests, Markdown/docs, README files, lockfiles, and templates as non-primary implementation scope. No generated-code exclusion was needed for this source scope.
- Analyzer/formula/version: no MI analyzer was installed (`radon` and `lizard` were unavailable), so this is a manual MI-oriented screening based on source size, visible control-flow branching, and operator/operand surface; no numeric analyzer result is being claimed. Results should not be compared with another formula/tool or scope.
- `src/myteam/workflows/agent_session.py` is the largest module at 545 lines. `run_agent` spans lines 62–145 and combines defaults/configuration, prompt rendering, argv construction, registration, exception cleanup, and process execution; `_run_agent_process` spans lines 148–225 and combines PTY launch, indicators, result validation, metadata, and cleanup.
- Other large implementation modules add substantial maintenance surface: `src/myteam/workflows/commands.py` is 378 lines, `src/myteam/workflows/agents/runtime.py` is 361 lines, `src/myteam/workflows/execution/workflow_store.py` is 293 lines, and `src/myteam/rosters/__init__.py` is 288 lines.
- `src/myteam/workflows/commands.py:161-182` has several equivalent command-line spellings handled through repeated conditionals; `:185-218` coordinates normalization, workflow resolution, supervisor selection, process execution, and result conversion. This increases decision and vocabulary counts in a central module.
- `src/myteam/workflows/agents/runtime.py:59-104` contains multiple configuration-loading branches and exception translations; `:220-244` supports two session-info APIs; and `:299-354` performs signature inspection, accepted-argument filtering, a keyword call, and a positional fallback. These compatibility paths materially increase control-flow and operator/operand surface.
- `src/myteam/workflows/execution/supervisor.py:108-155` contains a long event loop with repeated state checks, select/wakeup handling, PTY pumping, and exit handling. `src/myteam/workflows/agent_session.py:448-502` similarly combines nested callbacks, polling, deadlines, termination, draining, and multiple return paths. These are the clearest low-MI inspection targets.
- The inspected code has some focused helpers and docstrings, but MI alone cannot establish design quality or explain causation; the score is a screening judgment only, as required.

## Naming

Score: **10/10**

- Score basis: Python modules and filenames use snake_case throughout the inspected tree (for example, `src/myteam/workflows/agent_session.py` and `src/myteam/workflows/execution/workflow_rpc.py`).
- Functions, methods, parameters, and local variables consistently use snake_case; examples include `normalize_session_name`, `load_myteam_config`, `build_argv`, `session_id`, and `extra_args` in `src/myteam/config.py:23-42` and `src/myteam/workflows/agents/codex.py:35-43`.
- Classes consistently use PascalCase, including `AgentSettingsModel`, `WorkflowDefaults`, `MyteamConfig` (`src/myteam/config.py:32-79`), `WorkflowProcessResult`, `AgentSettings`, and `MarkdownWorkflowInfo` (`src/myteam/workflows/commands.py:29-64`).
- Constants consistently use UPPER_SNAKE_CASE, such as `AGENT_SETTING_FIELDS` (`src/myteam/config.py:61`), `PRICING_INFO` (`src/myteam/workflows/agents/codex.py:10-16`), and the protocol constants in `src/myteam/workflows/execution/protocol.py:10-24`.
- The few camelCase strings found (`sessionId`, `cacheRead`, `cacheWrite`, `totalTokens`) are external agent/JSON schema keys, not Python identifiers; the surrounding code remains snake_case (`src/myteam/workflows/agents/claude.py:110-121`, `src/myteam/workflows/agents/pi.py:86-110`). No internal naming-standard violation was found.

## Nesting Depth

Score: **8/10**

- Counting each function body as the baseline, and counting `if`/`elif` branches, loops, `try`/exception regions, and `with` blocks as enclosing blocks (but treating mutually exclusive `elif` dispatch as one decision path), the deepest meaningful path is approximately 5 blocks in `iter_jsonl_reverse`: `try` -> `with` -> `while` -> `for` -> payload-type `if` at [src/myteam/workflows/agents/agent_utils.py:44](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/agents/agent_utils.py:44) and [src/myteam/workflows/agents/agent_utils.py:51](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/agents/agent_utils.py:51). This is a legitimate nesting-depth hotspot, though the loop and resource-management structure are intrinsic to reverse streaming.
- `drain_pty_output` reaches about 4 blocks on its output-forwarding path: `while` -> `if` stdout-ready -> `if` chunk -> `if` forwarding enabled, at [src/myteam/workflows/execution/pty_forwarding.py:167](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/execution/pty_forwarding.py:167) and [src/myteam/workflows/execution/pty_forwarding.py:186](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/execution/pty_forwarding.py:186). The corresponding stderr path repeats the same shape at lines 195-200.
- `_resolve_session_metadata` reaches about 4 blocks for the dictionary usage case: optional callback `if` -> inner `try` -> non-`None` `if` -> type branch, at [src/myteam/workflows/agent_session.py:533](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/agent_session.py:533) and [src/myteam/workflows/agent_session.py:535](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/agent_session.py:535), with the final alternatives at lines 539-544. This is moderate nesting and could be simplified if it becomes harder to scan, but it is localized.
- `run_until_complete` has about 4 blocks on the wakeup path (`with` -> `while` -> active-session `if` -> ready-fd `if`) at [src/myteam/workflows/execution/supervisor.py:111](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/execution/supervisor.py:111) and [src/myteam/workflows/execution/supervisor.py:123](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/workflows/execution/supervisor.py:123), but the early `continue` keeps the path understandable.
- `_dispatch` appears to have ten conditional levels syntactically at [src/myteam/cli.py:56](/mnt/c/Users/rebek/School/F26/CS401R_F26/myteam/src/myteam/cli.py:56), but these are a flat mutually exclusive `if`/`elif` chain, not nested control flow; the deepest meaningful path is one branch.
- Overall, nesting is usually shallow and guard clauses/early returns are common. The few 4-5 block paths are concentrated in streaming, I/O, and metadata handling where some nesting is natural. Score: 8/10.

## Size And Duplication

Score: **7/10**

- Size is generally moderate and distributed: a simple `find` + `wc -l` count gives 5,507 lines across 40 non-template Python source files under `src/myteam` (generated/template files excluded). Most modules are below 300 lines; this supports comprehension rather than indicating broad size-driven cost.
- Two modules are notably large: `src/myteam/workflows/agent_session.py` is 545 lines and `src/myteam/workflows/commands.py` is 378 lines. The former contains the end-to-end agent lifecycle, PTY forwarding, registration, prompt construction, and result handling (`agent_session.py:62-225`, `228-298`, `448-560`), so its length is largely cohesive; the latter combines workflow creation, settings resolution, workflow execution, payload conversion, and printing (`commands.py:67-112`, `115-182`, `185-288`, `335-368`), increasing navigation/change cost somewhat.
- `start_workflow` and `start_workflow_cli` duplicate the same input normalization and `_start_workflow_result` call (`src/myteam/workflows/commands.py:115-156`), with only output/error behavior differing afterward. A change to accepted input semantics must be kept aligned in both entry points.
- The three built-in agent adapters repeat a substantial command-builder shape: initialize argv, add non-interactive mode, add session/fork options, add model/options, append extra args, and append the prompt (`src/myteam/workflows/agents/codex.py:35-57`, `claude.py:51-76`, `pi.py:18-41`). The flags are agent-specific, so all duplication is not accidental, but the shared sequencing and option plumbing still create repeated change surface when the common agent API evolves.
- Session-path/project-directory resolution is independently implemented in Claude and Pi adapters (`src/myteam/workflows/agents/claude.py:142-160` and `src/myteam/workflows/agents/pi.py:59-70`, `118-120`). Their directory encodings intentionally differ, so extracting the full rule would be risky; however, the repeated resolve-session scaffolding is a smaller stable concept that could otherwise be centralized.
- Usage aggregation is separately implemented in Codex, Claude, and Pi (`src/myteam/workflows/agents/codex.py:74-118`, `claude.py:87-139`, `pi.py:52-115`). The transcript schemas genuinely differ, but each adapter repeats model/usage extraction, token conversion, `UsageInfo` construction, and cost handling. This is the clearest duplication hotspot because billing or usage-field changes can require synchronized edits.
- `WorkflowStore` contains repeated completion bookkeeping in `complete_request` and `complete_exit_request` (`src/myteam/workflows/execution/workflow_store.py:143-168`): lock, result storage, missing-record handling, agent purge, status/result assignment, and parent return. The exit path has different payload/status rules, so the duplication is limited but still adds maintenance surface.
- Overall score: 7/10. The system is not broadly oversized and most repetition reflects genuinely different external agent protocols, but the repeated adapter plumbing and duplicated workflow entry/completion paths create recurring comprehension and change costs.
