---
name: "discord-bridge"
description: "This skill is used when you need to speak with the user for any reason. It should be used for: asking questions of the user, sending confirmation to the user, obtaining information from the user, etc. Assume nothing you send through the CLI will be read, so you must use this skill."
---

Questions must use `talk`. Never use `send` for a question. Use `send` to acknowledge a user response.

The user is a human and may need additional time to respond. When you ask through the bridge, be prepared to wait forever for the reply unless the caller explicitly sets a timeout.

If you are blocked on a response, repoll rather than resorting to use of the CLI. The user will never see anything you send via the CLI.

If the user returns both a question and an answer to your `talk`, send the answer back to the user with `send` before you continue work.

## Setup

Load `.env` before using this skill.

Use `python3`, not `python`, for the bridge helpers unless you have already confirmed `python` resolves correctly in the environment.

Stop and inform the user if the configured guild id or bot token is missing.

The required environment variable names are `BOT_KEY` for the Discord bot token and `DISCORD_GUILD_ID` for guild routing. The helpers do not read `DISCORD_BOT_TOKEN`.

The API base URL is optional. If it is unset, the helpers default to `http://127.0.0.1:8080`.

When the API base URL points at `127.0.0.1`, `localhost`, or `::1`, the packaged helpers auto-start `.myteam/discord-bridge/server/run_bridge_server.py` if needed and serialize startup through a shared lock. The server stays up for bridge state and routing, but the Discord reply listener only starts while a bridge wait is active.

## Tool Surface

Use exactly two public bridge tools:
- `.myteam/discord-bridge/bridge_chat.py`
- `.myteam/discord-bridge/bridge_manage.py`

`bridge_chat.py` supports:
- `send`
- `talk`
- `wait`
- `state`
- `log` for coordination logs to the owning top-level channel

`bridge_manage.py` supports:
- `ensure-channel`
- `delete-channel`
- `delete-channels` for bulk deletion by explicit Discord channel IDs, or all text channels except `general` when no IDs are passed
- `delete-agent-channel`
- `delete-session-channels`
- `stop-server` to cancel active waits and shut down the local bridge server cleanly

## Routing

Prefer explicit scope flags when identity is ambiguous:
- `--top-level`
- `--subagent`

These routing flags are global parser options. Put them before the subcommand, not after it.

Shared routing flags:
- `--workspace-id`
- `--session-id`
- `--agent-id`
- `--agent-name`
- `--agent-kind` with value `top_level` or `subagent`
- `--discord-guild-id`

For normal top-level traffic, use a stable top-level `agent_id` if you want to reuse the same Discord channel across process restarts.

For subagents, pass a unique spawn-specific `agent_id`. `agent_name` is display metadata only and cannot substitute for `agent_id`.

Do not rely on `CODEX_THREAD_ID` as implicit subagent identity. The bridge now rejects thread-only subagent routing because it is not spawn-specific enough and can merge distinct subagents into the same Discord channel.

Channel reuse is based on routing metadata stored in the Discord channel topic, not on the lifetime of the local bridge process or reply listener.

`log` is special:
- It always routes as `agent_kind=top_level`.
- From a top-level agent, it routes to that agent's own coordination channel.
- From a subagent, it routes to the spawning top-level agent's coordination channel when parent top-level identity is available.
- If no parent top-level identity is available, it falls back to a neutral `top-level` placeholder channel.

## Required Behavior

Before doing substantial work after receiving input, send `state working`.

When you are blocked waiting for user input, send `state awaiting_user`.

When you need information from the user, the bridge command must produce a reply to the current tool call. That means:
- use `talk` for questions,
- never use `send` for questions,
- use `wait` only when a prior step already sent the prompt and the current step is just waiting for the next reply.

When the top-level agent sends work to a subagent or receives a response back, emit a `log`.

Subagents may call `.myteam/discord-bridge/bridge_chat.py` directly. Do not force the top-level agent to relay a question that the subagent can ask itself.

## Examples

Ask the user a question and wait for the reply:

```bash
python3 .myteam/discord-bridge/bridge_chat.py \
  --top-level \
  --discord-guild-id <guild-id> \
  talk \
  --content "What deployment target do you want to use?"
```

Send a one-way user-facing message:

```bash
python3 .myteam/discord-bridge/bridge_chat.py \
  --top-level \
  --discord-guild-id <guild-id> \
  send \
  --content "Build finished. I am starting verification now."
```

Wait for the next user reply after a prior prompt:

```bash
python3 .myteam/discord-bridge/bridge_chat.py \
  --top-level \
  --discord-guild-id <guild-id> \
  wait
```

Mark the current agent as working:

```bash
python3 .myteam/discord-bridge/bridge_chat.py \
  --top-level \
  --discord-guild-id <guild-id> \
  state \
  working \
  --ttl-seconds 12
```

Emit a coordination log to the owning top-level agent channel:

```bash
python3 .myteam/discord-bridge/bridge_chat.py \
  --subagent \
  --discord-guild-id <guild-id> \
  --agent-id <spawn-id> \
  log \
  --top-level-agent-name <top-level-name> \
  --to-subagent "Implement the polling path." \
  --subagent-name rough-plan-render \
  --to-top-level "I need the API contract first."
```

Ensure the current agent channel exists without starting the reply listener:

```bash
python3 .myteam/discord-bridge/bridge_manage.py \
  --top-level \
  --discord-guild-id <guild-id> \
  ensure-channel
```

Delete a batch of Discord text channels directly by channel ID without using the local bridge server:

```bash
python3 .myteam/discord-bridge/bridge_manage.py \
  delete-channels \
  123456789012345678 \
  234567890123456789 \
  345678901234567890
```

Delete every Discord text channel in the configured guild except the configured preserved channel name (which defaults to `general`):

```bash
python3 .myteam/discord-bridge/bridge_manage.py \
  --discord-guild-id <guild-id> \
  delete-channels
```

Stop the bridge server cleanly and wake any blocked `talk` or `wait` callers. For local bridges, this now falls back to force-stopping the tracked bridge process when the HTTP server is unhealthy, which also disconnects the Discord bot because it runs in the same process:

```bash
python3 .myteam/discord-bridge/bridge_manage.py \
  --top-level \
  --discord-guild-id <guild-id> \
  stop-server
```
