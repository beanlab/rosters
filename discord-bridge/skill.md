---
name: "Discord Bridge"
description: "Use when you need hosted Discord bridge messaging, reply waits, agent state updates, or top-level/subagent routing through .myteam/discord-bridge/bridge_main.py, .myteam/discord-bridge/bridge_subagent.py, .myteam/discord-bridge/talk_to_user.py, .myteam/discord-bridge/update_user.py, or .myteam/discord-bridge/bridge_routing.py."
---

Load this skill before using the hosted Discord bridge helpers.

## Setup

After running `myteam get role ...`, load `.env`.

Use `python3`, not `python`, for the bridge helpers unless you have already confirmed `python` resolves correctly in the environment.

Stop if either of these is missing:
- `BRIDGE_API_TOKEN`
- `DISCORD_GUILD_ID`

Treat `BRIDGE_API_BASE_URL` as optional. If it is unset, the helpers already default to `http://127.0.0.1:8080`.

## Routing Rules

Do not rely on implicit routing when agent identity is ambiguous. In this workspace, a shell that only has `CODEX_THREAD_ID` will now fail fast instead of silently routing to `Main`.

Prefer the explicit wrapper entrypoints:
- `.myteam/discord-bridge/bridge_main.py` for top-level agent traffic
- `.myteam/discord-bridge/bridge_subagent.py` for subagent traffic

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
- It always routes to the shared main-agent coordination channel for the active workspace, session, and guild.
- It forces `agent_name=Main`, `agent_id=main`, and `agent_kind=top_level`.
- It does not require or derive a subagent `agent_id`.
- Legacy `--log-*` flags are ignored.

## Use The Helpers

Use `.myteam/discord-bridge/bridge_main.py talk` or `.myteam/discord-bridge/bridge_subagent.py talk` when you need to send a user-facing message through the hosted bridge, wait for a reply, hand the turn to the user without sending a new message, or ask the user anything at all.

Use `.myteam/discord-bridge/bridge_main.py update` or `.myteam/discord-bridge/bridge_subagent.py update` when you need to mark an agent as `working`, mark an agent as `awaiting_user`, or emit a top-level/subagent exchange log.

Once bridge configuration is available, use the bridge for user-facing conversation instead of asking the user to reply in the terminal. Treat terminal output as local operator/debug output.

Subagents may call `.myteam/discord-bridge/bridge_subagent.py` directly. Do not force the top-level agent to relay a question that the subagent can ask itself.

## Required Behavior

Before doing substantial work after receiving input, send `state working`.

When you are blocked waiting for user input, send `state awaiting_user`.

When the top-level agent sends work to a subagent or receives a response back, emit a `subagent-log`.

Do not claim that workspace, session, or agent routing is undiscoverable unless `DISCORD_GUILD_ID` is also unavailable. Use the wrappers for explicit routing by default. If you call raw helpers directly, pass explicit routing flags whenever the caller is not unambiguously top-level.

## Command Examples

Send a user-facing prompt and wait for the reply:

```bash
python3 .myteam/discord-bridge/bridge_main.py talk \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "What deployment target do you want to use?"
```

Mark the current agent as working:

```bash
python3 .myteam/discord-bridge/bridge_main.py update \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state working \
  --ttl-seconds 12
```

Mark the current agent as waiting for the user:

```bash
python3 .myteam/discord-bridge/bridge_main.py update \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state awaiting_user
```

Wait for the next user message without sending a new message first:

```bash
python3 .myteam/discord-bridge/bridge_main.py talk \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --wait-only
```

Emit a coordination log to the shared main-agent channel:

```bash
python3 .myteam/discord-bridge/bridge_main.py update \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  subagent-log \
  --top-level-agent-name Main \
  --to-subagent "Implement the polling path." \
  --subagent-name rough-plan-render \
  --to-top-level "I need the API contract first."
```

Send a user-facing prompt from a subagent:

```bash
python3 .myteam/discord-bridge/bridge_subagent.py talk \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "I need one more constraint before I continue."
```

Mark a subagent as working:

```bash
python3 .myteam/discord-bridge/bridge_subagent.py update \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state working \
  --ttl-seconds 12
```
