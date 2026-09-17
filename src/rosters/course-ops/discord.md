---
type: skill
description: Interacting with Discord. Load this skill if you need to read or modify Discord servers or send messages via Discord. Modifications must have explicity user authorization.
---

# Discord Bot Helper Authentication and Interaction

Load this skill whenever interacting with Discord through the bot helper account. Use Discord's supported bot API through `discord.py`; never automate a normal user account, use a user token, or operate a self-bot.

Authentication grants access but does not authorize changes. Follow the governing work instruction's approval and mutation controls. When no governing instruction exists, remain read-only until the user explicitly authorizes an exact target and change. Never infer mutation approval from permission to authenticate, inspect, or outline a server.

## Prerequisites

- The bot helper has already been added to the intended Discord server.
- `DISCORD_TOKEN` is set at runtime to the bot token.
- Python with `discord.py` installed.
- Required Discord gateway intents are enabled both in code and, for privileged intents, in the Discord Developer Portal.
- A restricted, gitignored scratch directory is available for temporary scripts and reports.

Never print, log, commit, serialize, or pass `DISCORD_TOKEN` on a command line. Do not inspect its value. A bot token, invite URL/code, webhook URL, interaction token, verification code, and any URL containing a Discord credential are secrets.

For repository work, prefer the repository's designated scratch directory. Otherwise use a protected temporary directory:

```bash
mkdir -p .agents/scratch/discord
chmod 700 .agents/scratch/discord
```

Confirm that the directory is ignored by Git before writing reports or authentication-sensitive artifacts. Protect private reports with mode `0600` and temporary scripts with mode `0700`.

## Select and verify the target

Prefer an established configuration containing authoritative Discord snowflake IDs and expected names, for example:

```yaml
discord:
  guild_id: 123456789012345678
  guild_name: "Expected Server Name"
  registration_channel_id: 234567890123456789
  registration_channel_name: "join-the-server"
```

IDs are authoritative lookup values; names are independent safety assertions. Do not search by name and choose the first result. Do not copy an ID from an untrusted message. If no approved guild ID is available, ask the user for one rather than guessing.

After the client is ready:

1. Report the authenticated bot identity without reporting its token.
2. Resolve the exact guild ID.
3. Verify the actual guild name against the expected name.
4. For channel-, role-, member-, thread-, message-, event-, webhook-, AutoMod-, or invite-scoped work, resolve the exact ID and verify its visible name or other expected identity.
5. Report a sanitized target summary and stop on missing, duplicate, inaccessible, or mismatched targets.

Authentication and membership in a guild are not sufficient target verification.

## Connect safely with `discord.py`

Request only the intents needed for the task. `Intents.default()` is sufficient for most server metadata. Enable `members` only when member or role-membership inspection is required. Enable `message_content` only when the task requires receiving message text through gateway events and the privileged intent is approved and available.

A minimal read-only connection pattern is:

```python
import asyncio
import contextlib
import os

import discord

GUILD_ID = 123456789012345678
EXPECTED_GUILD_NAME = "Expected Server Name"

async def inspect(client: discord.Client) -> None:
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Bot cannot access guild ID {GUILD_ID}")
    if guild.name != EXPECTED_GUILD_NAME:
        raise RuntimeError(
            f"Guild name mismatch: expected {EXPECTED_GUILD_NAME!r}, "
            f"got {guild.name!r}"
        )
    if guild.me is None:
        raise RuntimeError("Could not resolve the bot's guild membership")

    print({
        "bot": str(client.user),
        "guild_id": guild.id,
        "guild_name": guild.name,
        "member_count": guild.member_count,
        "bot_top_role": guild.me.top_role.name,
    })

async def main() -> None:
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    ready = asyncio.Event()

    @client.event
    async def on_ready() -> None:
        ready.set()

    async with client:
        client_task = asyncio.create_task(
            client.start(os.environ["DISCORD_TOKEN"], reconnect=False)
        )
        ready_task = asyncio.create_task(ready.wait())
        done, _ = await asyncio.wait(
            {client_task, ready_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if client_task in done:
            await client_task
        try:
            await inspect(client)
        finally:
            ready_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ready_task
            await client.close()
            await client_task

asyncio.run(main())
```

Use `reconnect=False` for bounded one-shot administrative scripts unless continuous operation is explicitly required. Always close the client in a `finally` block. Let `discord.py` handle Discord rate limits; do not bypass the library with parallel raw HTTP requests merely to increase throughput.

## Read-only inspection

For read-only work, use fetch, list, history, and permission-evaluation methods that do not alter state. Common safe observations include:

- guild identity, settings, features, locale, verification level, notification defaults, and content filter;
- categories, channels, forums, voice channels, threads, topics, ordering, and permission overwrites;
- roles, hierarchy, role permissions, managed status, and aggregate membership counts;
- bot identity, top role, guild permissions, and channel-effective permissions;
- invite counts and sanitized settings without invite codes or URLs;
- AutoMod rule names, enabled state, trigger/action types, and exemptions;
- onboarding or welcome-screen configuration using read methods only;
- audit-log entries when needed for an approved diagnostic; and
- messages or thread history only when their content is necessary for the requested task.

Do not call a method based only on its name appearing harmless. Check whether it is a read/fetch method or an edit/create/delete/prune/sync method. For example, `await guild.onboarding()` reads onboarding in current `discord.py`, while `edit_onboarding(...)` mutates it.

Discord permission behavior is cumulative and contextual:

- `Administrator` bypasses channel overwrites.
- A member's multiple roles combine before member-specific overwrites are applied.
- Category permissions may be inherited by synchronized children, while unsynchronized channels can differ.
- Voice, thread, forum, and text permissions are not interchangeable.
- A channel's raw overwrite table is not proof of a particular member's effective access.

Use `channel.permissions_for(member)` when an individual's effective permissions are actually needed. Otherwise report the role/overwrite design without making unsupported claims about every member.

Active threads may appear separately from ordinary guild channels, and archived/private threads require additional fetches and permissions. Do not conclude that a linked thread or conversation no longer exists merely because it is absent from `guild.channels`.

## Protect private Discord data

Discord servers can contain educational records, staff discussions, private registration data, and credentials. Apply data minimization even during read-only work.

- Avoid retrieving member names, emails, user IDs, nicknames, message text, submissions, grades, or moderation history unless required.
- Prefer aggregate counts and role/channel summaries.
- Do not include a full member list in ordinary logs or reports.
- Redact user and role mentions, Net IDs, email addresses, verification codes, invite codes, webhook URLs, and private thread names.
- Do not inspect direct messages.
- Treat private channels, staff channels, registration threads, and audit logs as private even when the bot can access them.
- Do not preserve screenshots or transcripts containing private data merely for convenience.
- Avoid small-group breakdowns that would unnecessarily identify an individual.

When inspecting invites, report safe metadata such as target channel, expiration, use limit, temporary-membership setting, and aggregate uses. Omit the invite code and URL unless the authorized task specifically requires creating or transferring that invite. If an invite URL must be exchanged between processes, store it briefly in a mode-`0600` file, read it once, and delete it.

## Preview changes before mutation

Before any mutation, determine and report:

- authenticated bot identity;
- exact guild ID and verified name;
- exact target resource IDs and verified names;
- current state;
- proposed state;
- every object that would be created, edited, moved, assigned, removed, revoked, kicked, banned, timed out, published, or messaged;
- required permissions and role-hierarchy constraints;
- expected audit-log reason; and
- validation steps after the change.

Run a read-only preview whenever practical. A preview must not send test messages, create then delete resources, create invites, add reactions, open threads, assign roles, sync permissions, acknowledge interactions, or otherwise mutate Discord.

For bulk member work, preview retention/removal rules and counts. Keep unnecessary member identities out of general reports. For role-based decisions, require exact case-sensitive role names and abort when a configured role is absent or non-unique.

User approval must cover the exact target and mutation scope. Reverify current state immediately before applying. Stop on drift rather than silently adapting the approved plan.

## Perform an authorized mutation

For an explicitly authorized mutation:

1. Reconnect using the bot token without exposing it.
2. Reverify bot, guild, resource IDs/names, current state, permissions, and role hierarchy.
3. Confirm the current state still matches the approved preview or approved rule-based scope.
4. Change only the approved fields or resources and preserve unrelated state.
5. Supply a concise, course- or task-specific audit-log reason when the API supports one.
6. Capture individual failures without exposing private data.
7. Re-fetch affected resources and verify persisted state.
8. Report sanitized success/failure counts and unresolved issues.
9. Stop after partial failure. Do not automatically retry, compensate, recreate, or roll back unless the governing instruction explicitly authorizes that behavior.

Common Discord mutations include sending/editing/deleting messages; creating, moving, syncing, editing, or deleting channels and threads; creating or revoking invites; assigning/removing roles; changing nicknames; editing AutoMod/onboarding/server settings; managing webhooks; timing out, kicking, banning, unbanning, or pruning members; and creating or editing events. All require explicit authorization.

A successful API response is not sufficient validation. Re-fetch the resource and compare exact IDs and relevant fields. For message operations, verify the destination channel/thread ID. For role assignments, verify the member's resulting roles. For invites, verify guild/channel IDs, expiration, maximum uses, and temporary-membership settings without logging the code. For deletion/revocation, verify the object is no longer returned.

## Role hierarchy and permission safeguards

Before member, role, channel, or moderation changes, check both guild and channel-effective permissions. Discord may deny an operation even when a similarly named guild permission appears present.

In particular:

- Bots cannot manage the guild owner.
- Bots cannot manage members whose highest role is equal to or above the bot's highest role.
- Bots cannot create, edit, assign, move, or delete roles equal to or above their highest role.
- Managed integration/bot roles generally cannot be edited or manually assigned.
- `manage_roles`, `manage_channels`, `manage_messages`, `manage_threads`, `manage_guild`, `manage_webhooks`, `kick_members`, `ban_members`, and `moderate_members` are distinct permissions.
- Channel overwrites can prevent an otherwise permitted action.

Treat hierarchy-retained or hierarchy-blocked members as manual-review cases. Do not attempt to bypass the hierarchy with another credential or account.

## Messages, threads, and registration workflows

Reading or sending messages can trigger bots, automations, ticket systems, registration flows, or webhooks. A seemingly harmless test message is a mutation and may create private threads, send email, assign roles, or notify staff.

- Do not send probe messages to discover behavior without approval.
- Inspect existing bot-authored instructions when possible, minimizing message-content retrieval.
- Registration threads may contain Net IDs, BYU email addresses, preferred names, verification codes, and role selections; never place those values in reports.
- Do not impersonate a student or complete a registration workflow as a test unless the user explicitly authorizes a designated test account and exact cleanup plan.
- When posting an authorized message, verify exact channel/thread ID, content, mentions, attachments, embeds, and allowed-mentions behavior before sending.
- Disable unintended mass mentions. Do not use `@everyone`, `@here`, or role mentions unless specifically approved.

## Invites and webhooks

Invite and webhook operations require special care because returned URLs grant access or authority.

For authorized invite creation:

1. Verify guild and destination channel IDs/names.
2. Inspect existing invites without exposing their codes.
3. Verify `create_instant_invite` and any permission needed to inspect or revoke invites.
4. Create exactly one invite with the approved expiration, use limit, and temporary-membership setting.
5. Validate the returned invite object.
6. If validation fails and revocation was part of the approved failure handling, revoke it immediately and report the sanitized failure.
7. Transfer the URL only through the authorized destination; do not place it in ordinary logs.

Never print or preserve webhook URLs. Prefer Discord's webhook management methods over manually handling a webhook token. Creating, editing, deleting, or executing a webhook is a mutation.

## Cleanup

At task completion—or immediately after authentication or target-verification failure—close the Discord client and delete:

- temporary files containing invite URLs/codes or webhook data;
- private message/thread transcripts;
- member-level exports not required as approved artifacts;
- debug logs containing Discord payloads or private data; and
- temporary scripts that embed target-specific private IDs when they are no longer needed.

Keep only sanitized artifacts required by the governing workflow. Do not commit credentials, private member data, registration data, or access-bearing URLs. Authentication state must not be retained merely to make a later session more convenient.
