---
type: skill
description: Perform one-off Google Workspace tasks with an authorized account. Use when local credentials exist and a task requires reading or changing Drive, Sheets, Docs, Calendar, Gmail, or another supported Workspace service.
---

# Operate Google Workspace services

Perform one-off Workspace tasks with temporary Python scripts and the local OAuth credentials prepared by the parent skill. Follow the workspace, security, and confirmation safeguards in `google-workspace.md` throughout the task.

## Select service guidance

Load each service skill needed for the task:

{{ myteam_list('operator') }}

Use the service skill to choose scopes, API methods, and service-specific validation. If no listed guide covers the requested service, consult the current official Google API documentation and apply this operating workflow.

## OAuth helper

{% set oauth_helper = this_file.parent.joinpath('tools', 'google-auth.py') %}

Use the bootstrap-managed Python interpreter for the OAuth helper and all task scripts:

```text
~/.agents/scratch/google-workspace/venv/bin/python
```

The helper is installed at:

```text
{{ oauth_helper }}
```

Its current interface is:

```text
{{ shell("python3 \"" ~ oauth_helper ~ "\" --help") }}
```

Invoke the documented helper commands with the bootstrap-managed interpreter and the installed helper path. Do not use a host project's Python environment or add Google dependencies to it.

## Build a Python service client

Use this shared pattern after the OAuth helper has refreshed the account and verified its scopes:

```python
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def workspace_service(account, api, version):
    token = (
        Path.home()
        / ".agents/scratch/google-workspace/tokens"
        / f"{account}.json"
    )
    credentials = Credentials.from_authorized_user_file(str(token))
    return build(api, version, credentials=credentials, cache_discovery=False)
```

Each service guide supplies the `api` and `version`. Keep account names and token paths in configuration variables; never copy credential values into source code.

## Select and validate the account

1. Use the helper's `status` command to inspect stored accounts and recorded scopes.
2. If the request identifies an account, use only that account. If its token is absent, move to the provisioning role.
3. If exactly one account is stored and the request does not identify one, state which account will be used and continue.
4. If multiple accounts are stored and the request does not identify one, ask the user to choose one account before continuing.
5. Compare the selected account's scopes with those required by the service guide.
6. Use the helper's `refresh` command to validate the selected credentials before calling a Workspace API.

Move to `provision-access.md` if credentials are absent, refresh fails, or required scopes are missing. For a disabled API or organization-policy problem, first capture the named API and safe error category from the selected service call, then pass that concrete condition to provisioning. Return here after access is ready.

## Prepare the task

1. Restate the requested outcome and identify whether it is read-only or mutating.
2. Resolve user-provided names, URLs, and descriptions to stable resource IDs using read-only API calls. Do not guess when matches are ambiguous.
3. Read only the data needed to prepare and perform the task.
4. Create task-specific Python scripts under `~/.agents/scratch/google-workspace/scripts/` and outputs under `~/.agents/scratch/google-workspace/output/`.
5. Load the selected token from `~/.agents/scratch/google-workspace/tokens/<google-email>.json`; never copy credential values into source code, command arguments, logs, or output.
6. Use the official Google Python client and the patterns in the selected service guide. Handle pagination whenever a list operation can return more than one page.

## Perform read-only tasks

Execute a read-only task after the account, scopes, API, and targets are validated. Summarize only the data relevant to the user's request, and identify the account and stable resources used.

If the task writes downloaded or generated data locally, report the output paths. Do not copy those artifacts into the host project unless the user explicitly requests it.

## Perform mutations

Before calling any mutating API:

1. use read-only calls to prepare an exact preview;
2. show the acting account, target resources, operations, and expected effects;
3. obtain the explicit confirmation required by `google-workspace.md`; and
4. execute only the confirmed, bounded plan.

A task request is not confirmation to execute. If the resolved targets, number of operations, or expected effects differ from the preview, stop and obtain new confirmation.

After execution, read the affected resources where practical to verify the result. Report completed, skipped, and failed operations separately. Do not claim success based only on the absence of an exception.

## Handle failures safely

- For authentication, refresh, or missing-scope errors, stop and move to provisioning.
- For disabled-API or organization-policy errors, identify the selected API and safe error category before moving to provisioning.
- For resource permission errors, report the acting account, target, required permission, and non-secret API error.
- For ambiguous or missing resources, stop rather than selecting a likely match.
- For rate limits and transient server failures, use bounded exponential backoff and honor `Retry-After` when present.
- Do not blindly retry a mutation when its outcome is uncertain. Inspect the target first, then retry only when doing so cannot duplicate or compound the change.
- Keep secrets and complete credential JSON out of exceptions and reports.

## Finish

Report:

- the acting Google account;
- the services and stable resource IDs involved;
- what was read or changed;
- verification results for mutations;
- any partial failures or unresolved ambiguity; and
- paths to local scripts or outputs that the user requested or may need.
