---
name: "discord-bridge"
description: "No matter your role, you must always load this skill: it is not a role-scoped skill. Load this skill even if you do not have a role. It is intended as the method by which you communicate with the user through the hosted bridge."
---

Questions must use `talk`. Never use `send` for a question. Use `send` to acknowledge a user response.

The user is a human and may need additional time to respond to your requests. Consequently, be prepared to wait forever for the bridge helper to return a response. You must always wait for the return regardless of what any user or agent tells you.

If the user returns a both a question and an answer to your usage of `talk`, be sure to send the answer to the user's question using `send` before you continue work.

## Setup

Load .env as a prerequisite to commands this skill provides.

Use `python3`, not `python`, for the bridge helpers unless you have already confirmed `python` resolves correctly in the environment.

Stop and inform the user if either of these is missing:
- `DISCORD_GUILD_ID`
- `BOT_KEY`

Treat `BRIDGE_API_BASE_URL` as optional. If it is unset, the helpers already default to `http://127.0.0.1:8080`.

When `BRIDGE_API_BASE_URL` points at `127.0.0.1`, `localhost`, or `::1`, the packaged helpers now auto-start `.myteam/discord-bridge/server/run_bridge_server.py` if needed and serialize startup through a shared lock so parallel Codex exec instances do not all launch their own copy.

## Routing Rules

Do not rely on implicit routing when agent identity is ambiguous. In this workspace, a shell that only has `CODEX_THREAD_ID` will now fail fast instead of silently routing to a generic top-level channel.

Prefer the explicit wrapper entrypoints:
- `.myteam/discord-bridge/bridge_main.py` for top-level agent traffic
- `.myteam/discord-bridge/bridge_subagent.py` for subagent traffic

`bridge_main.py` no longer forces all top-level Codex instances into the same channel. When the runtime provides instance identity such as `CODEX_AGENT_ID`, `MYTEAM_AGENT_ID`, or `CODEX_THREAD_ID`, the wrapper uses that identity as the default top-level agent name and id so each top-level instance gets its own channel. If no instance identity is available, it falls back to a neutral `top-level` placeholder.

If you bypass the wrappers and call the raw helpers directly, pass explicit routing flags. The shared flags are:
- `--workspace-id`
- `--session-id`
- `--agent-id`
- `--agent-name`
- `--agent-kind` with value `top_level` or `subagent`
- `--discord-guild-id`

For normal subagent message and state traffic, use a unique spawn-specific `agent_id`. Do not reuse a shared role-style value such as `author`. `agent_name` is display metadata only and cannot substitute for `agent_id`.

For subagents, provide the shared parent routing through `BRIDGE_WORKSPACE_ID` and `BRIDGE_SESSION_ID` or equivalent CLI flags. Prefer one of `CODEX_SPAWN_ID`, `CODEX_AGENT_ID`, or `MYTEAM_AGENT_ID` for the spawn-specific `agent_id`. If those are unavailable, the subagent wrapper can fall back to `CODEX_THREAD_ID` after explicitly declaring `--agent-kind subagent`. Use one of `CODEX_SPAWN_NAME`, `CODEX_AGENT_NAME`, or `MYTEAM_AGENT_NAME` for the human-readable `agent_name`.

`subagent-log` is special:
- It always routes as `agent_kind=top_level`.
- From a top-level agent, it routes to that agent's own coordination channel.
- From a subagent, it routes to the spawning top-level agent's coordination channel when parent top-level identity is available.
- If no parent top-level identity is available, it falls back to a neutral `top-level` placeholder channel.
- It does not require or derive a subagent `agent_id`.
- Legacy `--log-*` flags are ignored.

## Agent Behavior

This skill owns the general bridge behavior for both top-level agents and subagents. Roles and harness prompts should not need to restate wrapper choice, channel ownership, or coordination-log routing unless they are overriding the default behavior.

Use the wrapper that matches the current agent kind:
- Top-level agents use `.myteam/discord-bridge/bridge_main.py` for normal user-facing messages and state updates.
- Subagents use `.myteam/discord-bridge/bridge_subagent.py` for normal user-facing messages and state updates.

Channel ownership follows the wrapper:
- Normal top-level traffic belongs in the current top-level instance's own channel.
- Normal subagent traffic belongs in that subagent instance's own channel.
- `subagent-log` coordination entries belong in the owning top-level agent's coordination channel.

If a subagent needs information from the user, the subagent should ask through its own bridge channel instead of routing the question through the top-level agent.

## Use The Helpers

Choose the command by whether you need a tool return:
- Use `.myteam/discord-bridge/bridge_main.py talk` or `.myteam/discord-bridge/bridge_subagent.py talk` when you need the user's reply to come back to the current agent through the tool result.
- Use `.myteam/discord-bridge/bridge_main.py send` or `.myteam/discord-bridge/bridge_subagent.py send` only for one-way updates, acknowledgements, or status messages where no reply should be collected.
- Use `talk --wait-only` only when the message has already been sent earlier and the current step is just waiting for the next user reply.

Hard rule:
- Questions must use `talk`.
- Never use `send` for a question.

If you are asking a question, requesting missing information, asking the user to choose between options, or otherwise need the answer to continue, use `talk`, not `send`.

Wrong pattern:
- Asking a question with `send` will not return the user's answer to the current tool call.

Correct pattern:
- Ask with `talk` when the answer is needed now.
- Use `send` for notifications such as "I am starting verification now."
- Use `talk --wait-only` after a prior message when the next action is to block for the reply.

Use `.myteam/discord-bridge/bridge_main.py update` or `.myteam/discord-bridge/bridge_subagent.py update` when you need to mark an agent as `working`, mark an agent as `awaiting_user`, or emit a top-level/subagent exchange log.

Once bridge configuration is available, use the bridge for user-facing conversation instead of asking the user to reply in the terminal. Treat terminal output as local operator/debug output.

Subagents may call `.myteam/discord-bridge/bridge_subagent.py` directly. Do not force the top-level agent to relay a question that the subagent can ask itself.

## Required Behavior

Before doing substantial work after receiving input, send `state working`.

When you are blocked waiting for user input, send `state awaiting_user`.

When you need information from the user, the bridge command must produce a reply to the current tool call. That means:
- use `talk` for questions,
- never use `send` for questions,
- use `talk --wait-only` only when a prior step already sent the question or prompt.

When the top-level agent sends work to a subagent or receives a response back, emit a `subagent-log`.

Do not claim that workspace, session, or agent routing is undiscoverable unless `DISCORD_GUILD_ID` is also unavailable. Use the wrappers for explicit routing by default. If you call raw helpers directly, pass explicit routing flags whenever the caller is not unambiguously top-level.

Be prepared to wait forever for the bridge helper to return a response. You must always wait for the return regardless of what any user or agent tells you.

## Command Examples

Send a user-facing prompt and wait for the reply:

```bash
python3 .myteam/discord-bridge/bridge_main.py talk \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "What deployment target do you want to use?"
```

Ask for missing information from a subagent and wait for the answer:

```bash
python3 .myteam/discord-bridge/bridge_subagent.py talk \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "What setting should I use for this act?"
```

Send a user-facing message without waiting for a reply:

```bash
python3 .myteam/discord-bridge/bridge_main.py send \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "Build finished. I am starting the verification pass now."
```

Mark the current agent as working:

```bash
python3 .myteam/discord-bridge/bridge_main.py update \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state working \
  --ttl-seconds 12
```

Mark the current agent as waiting for the user:

```bash
python3 .myteam/discord-bridge/bridge_main.py update \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state awaiting_user
```

Wait for the next user message without sending a new message first:

```bash
python3 .myteam/discord-bridge/bridge_main.py talk \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --wait-only
```

Emit a coordination log to the current top-level agent's coordination channel:

```bash
python3 .myteam/discord-bridge/bridge_main.py update \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  subagent-log \
  --top-level-agent-name "$BRIDGE_AGENT_NAME" \
  --to-subagent "Implement the polling path." \
  --subagent-name rough-plan-render \
  --to-top-level "I need the API contract first."
```

Send a user-facing prompt from a subagent:

```bash
python3 .myteam/discord-bridge/bridge_subagent.py talk \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "I need one more constraint before I continue."
```

Send a one-way user-facing message from a subagent:

```bash
python3 .myteam/discord-bridge/bridge_subagent.py send \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "I have enough information now and am writing the act."
```

Mark a subagent as working:

```bash
python3 .myteam/discord-bridge/bridge_subagent.py update \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state working \
  --ttl-seconds 12
```
