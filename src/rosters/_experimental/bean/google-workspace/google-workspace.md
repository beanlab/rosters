---
type: skill
description: Use locally stored OAuth credentials to perform one-off tasks with Google Workspace services. Use when a task involves Google Drive, Sheets, Docs, Calendar, Gmail, or another Google Workspace API.
---

# Google Workspace

Use this skill to perform one-off tasks with Google Workspace services through user OAuth credentials stored on the local machine.

{% set bootstrap = this_file.parent.joinpath('tools', 'bootstrap.py') %}

{% if shell(
    "python3 \"" ~ bootstrap ~ "\" --check --quiet || printf 'not-ready'"
).strip() %}
## Bootstrap local environment

The Google Workspace environment is not ready.

Explain that bootstrap will create the private `~/.agents/scratch/google-workspace/` workspace, build its Python virtual environment, and install the required Google libraries. Obtain explicit user confirmation, then run:

```bash
python3 "{{ bootstrap }}"
```

After bootstrap succeeds, continue with this skill.
{% endif %}

## Select a role

Use the available role whose description matches the current situation:

{{ myteam_list(
    'provision-access.md',
    'operate-services.md'
) }}

Begin as a service operator unless the task is specifically to set up access. Move to provisioning when credentials are absent or invalid, required scopes are missing, or the operator identifies a specific API or organization-policy configuration problem.

## Local workspace

Use `~/.agents/scratch/google-workspace/` for credentials, temporary scripts, downloaded Workspace data, and generated output. Do not place credentials in the host project.

The bootstrap tool creates the expected folder tree and Python environment with owner-only directory permissions. Credential-producing tools must keep credential files readable and writable only by the owner.

Never commit credentials or copy them outside this workspace. Never print or expose access tokens, refresh tokens, client secrets, or complete credential files.

## Shared safeguards

- Request only the scopes needed for the task.
- Identify the Google account represented by the credentials before using it.
- Treat any operation that creates, edits, sends, shares, moves, or deletes Workspace data as a mutation.
- Before every mutation, show the user what will change and obtain explicit confirmation. A request to perform the task is not itself confirmation to execute the mutation.
- If a task requires several mutations, present a bounded plan and obtain confirmation for that plan. Ask again if the target, scope, or effects change.
- Prefer read-only inspection while preparing a mutation.
- After a mutation, verify the result where practical and report what changed.
