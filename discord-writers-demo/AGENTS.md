Run `myteam get role <role>` with your role. 
If you have not been given a role, use `myteam get role`.

If you have a role, you are a subagent for bridge routing purposes unless the task explicitly says otherwise.

You have access to two ordinary local scripts for communicating with a hosted Discord bridge:

- `talk_to_user.py`
- `update_user.py`

These are normal scripts, not formal structured tool integrations. When you need them, run them directly with the required arguments.

Use `python3`, not `python`, when running these scripts unless you have already confirmed `python` resolves correctly in the environment.

Use `talk_to_user.py` when:
- you need to send a user-facing message through the hosted bridge
- you need to wait for a user reply
- you need to hand the turn to the user on Discord without adding a new outbound message first
- you need any user input for any reason

Use `update_user.py` when:
- you need to mark an agent as `working`
- you need to mark an agent as `awaiting_user`
- you need to emit a top-level/subagent exchange log

Required routing arguments for both scripts:
- `--workspace-id`
- `--session-id`
- `--agent-id`
- `--agent-name`
- `--agent-kind` with value `top_level` or `subagent`
- `--discord-guild-id`

The routing arguments above may be omitted when the default routing identity is acceptable.
For spawned subagents on normal `talk_to_user.py` and `update_user.py state` paths, a unique spawn-specific `agent_id` is mandatory. `agent_name` stays human-readable display metadata and cannot substitute for `agent_id`.

Required bridge connection values:
- `--api-token` or `BRIDGE_API_TOKEN`
- `--discord-guild-id` or `DISCORD_GUILD_ID`

Optional bridge connection value:
- `--api-base-url` or `BRIDGE_API_BASE_URL`
  If omitted, the helpers default to `http://127.0.0.1:8080`.

Rules:
- Before doing substantial work after receiving input, send `state working` with `update_user.py`.
- When blocked waiting for user input, send `state awaiting_user` with `update_user.py`.
- When asking the user a question, use `talk_to_user.py`.
- Subagents are allowed to call `talk_to_user.py` directly and should do so themselves when they need user input. Do not force the top-level agent to relay a question that your own subagent can ask directly.
- Use the bridge scripts for all user-facing conversation once bridge configuration is available. Do not ask the user to reply in the terminal when the Discord path is available.
- Terminal output should be treated as local operator/debug output, not as the primary conversation path with the user.
- Do not claim that workspace/session/agent routing IDs are undiscoverable unless `DISCORD_GUILD_ID` is also unavailable. Use the helper defaults when explicit IDs are not provided.
- When the top-level agent sends work to a subagent or receives a response back, emit a `subagent-log` event with `update_user.py`.
- `subagent-log` is a shared coordination log. It always routes to the active workspace/session/guild's `agent-main` channel, regardless of whether the caller is the top-level agent or a subagent.
- `subagent-log` preserves the caller's workspace, session, and guild context, and forces `agent_name=Main`, `agent_id=main`, and `agent_kind=top_level`.
- `subagent-log` does not derive or require a subagent `agent_id`; only normal subagent message/state routing requires a unique spawn-specific `agent_id`.
- Legacy `--log-*` routing flags are ignored for `subagent-log`. Do not rely on them to retarget the destination.
- Treat these scripts as the communication path to the hosted bridge. Do not assume any extra schema, tool wrapper, or automatic integration exists.
- If `BRIDGE_API_TOKEN` or `DISCORD_GUILD_ID` is missing, stop and report that configuration is missing.
- Do not stop just because `BRIDGE_API_BASE_URL` is unset; the helpers already default it to `http://127.0.0.1:8080`. Only require an explicit base URL when the bridge is not running at that default address.

Examples:

Send a user-facing prompt and wait for the reply:

```bash
python3 talk_to_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "What deployment target do you want to use?"
```

Mark the current agent as working:

```bash
python3 update_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state working \
  --ttl-seconds 12
```

Mark the current agent as waiting for the user:

```bash
python3 update_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state awaiting_user
```

Emit a subagent log to the shared main coordination channel:

```bash
python3 update_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  subagent-log \
  --top-level-agent-name Main \
  --to-subagent "Implement the polling path." \
  --subagent-name rough-plan-render \
  --to-top-level "I need the API contract first."
```

Wait for the next user message on Discord without sending a new message first:

```bash
python3 talk_to_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --wait-only
```

Subagent bootstrap example:

```bash
export BRIDGE_AGENT_KIND=subagent
export BRIDGE_WORKSPACE_ID=ws1
export BRIDGE_SESSION_ID=sess1
export CODEX_SPAWN_NAME=rough-plan-render
export CODEX_SPAWN_ID=rough-plan-render-7f3a
python3 talk_to_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  --content "What setting should I use for this act?"
```

Emit a subagent log from a subagent and still target the shared main coordination channel:

```bash
python3 update_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --api-token "$BRIDGE_API_TOKEN" \
  --workspace-id ws1 \
  --session-id sess1 \
  --agent-id rough-plan-render \
  --agent-name rough-plan-render \
  --agent-kind subagent \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  subagent-log \
  --top-level-agent-name Main \
  --to-subagent "Implement the polling path." \
  --subagent-name rough-plan-render \
  --to-top-level "I need the API contract first."
```

Local repo bootstrap example:

```bash
source ../discord-server/.env
python3 update_user.py \
  --api-base-url http://127.0.0.1:8080 \
  --workspace-id ws1 \
  --session-id sess1 \
  --agent-id planner-1 \
  --agent-name Planner \
  --agent-kind top_level \
  --discord-guild-id "$DISCORD_GUILD_ID" \
  state working \
  --ttl-seconds 12
```

## Notes

- `talk_to_user.py` is for user-facing prompts and optional reply waiting.
- `talk_to_user.py --wait-only` is the handoff path when the user should continue by typing in Discord without a fresh outbound prompt.
- For subagents, set `BRIDGE_AGENT_KIND=subagent`, share the parent `BRIDGE_WORKSPACE_ID` and `BRIDGE_SESSION_ID`, and provide a unique spawn-specific `agent_id` through `--agent-id`, `CODEX_SPAWN_ID`, `CODEX_AGENT_ID`, or `MYTEAM_AGENT_ID` before using the normal bridge helpers. Provide `agent_name` separately as the human-readable display name through `--agent-name`, `CODEX_SPAWN_NAME`, `CODEX_AGENT_NAME`, or `MYTEAM_AGENT_NAME`.
- Do not rely on role-style `BRIDGE_AGENT_NAME`/`BRIDGE_AGENT_ID` values such as `Author` or `author` for subagents. The helpers now reject normal subagent requests that omit a spawn-specific `agent_id`, and they reject name-only subagent routing.
- Do not rely on cwd-derived workspace routing for subagents. The helpers now reject subagent requests that do not include shared `BRIDGE_WORKSPACE_ID` and `BRIDGE_SESSION_ID` values or equivalent CLI arguments.
- `update_user.py state working` keeps the remote side informed that the agent is actively processing.
- `update_user.py state awaiting_user` indicates the turn has passed back to the user.
- `update_user.py subagent-log` is for top-level/subagent coordination logs, not direct user messaging, and it always routes to the shared `agent-main` channel for the active workspace/session/guild.
