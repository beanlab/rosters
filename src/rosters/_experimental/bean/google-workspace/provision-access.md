---
type: skill
description: Provision or repair local OAuth access to Google Workspace. Use when the OAuth client or account credentials are missing, normal refresh fails, required scopes have not been granted, an API is disabled, or Workspace policy blocks access.
---

# Provision Google Workspace access

Provision an Internal Google Workspace desktop OAuth app and local user credentials for one-off tasks. Follow the workspace and security safeguards in the parent `google-workspace.md` skill.

Provisioning includes changes to Google Cloud configuration and local credentials. Before making those changes on the user's behalf, present the bounded setup or repair plan and obtain the confirmation required by the parent skill. Authentication, account selection, consent, and administrator approval must be completed by the user; never ask for or handle the user's password or multi-factor authentication codes.

## Diagnose before provisioning

Use the helper's `status` command only to inspect local accounts, refresh-token presence, and recorded scopes. Provision credentials when the OAuth client or account token is absent or invalid, refresh fails, or required scopes are missing.

The helper cannot inspect API enablement or organization policy. Repair those only from a specific browser inspection or a non-secret error from the operator's selected service call; carry the named API and error category into the repair plan.

An expired access token is normal and should be refreshed rather than replaced. Preserve existing credentials until replacements validate.

## OAuth helper

{% set oauth_helper = this_file.parent.joinpath('tools', 'google-auth.py') %}

The helper manages the client configuration and per-account token files in the workspace defined by the parent skill. Each token filename is the account's validated Google email address.

The helper is installed at:

```text
{{ oauth_helper }}
```

Run its commands with the bootstrap-managed interpreter:

```text
~/.agents/scratch/google-workspace/venv/bin/python
```

It uses the default paths shown in its help and must never print token or client-secret values. Read its current interface before using it:

```text
{{ shell("python3 \"" ~ oauth_helper ~ "\" --help") }}
```

## Create or repair the OAuth client

Load the following skill when its description matches the current situation:

{{ myteam_list('create-oauth-client.md') }}

## Authorize an account

Use the selected service guide to determine the scopes required for the current task. Do not request every service scope in advance; the helper automatically adds the identity scopes needed to validate the account.

Run the helper's `authorize` command for the intended account with the required service scopes. The helper retains existing scopes, validates the authorized account and new credentials, and preserves the previous token if authorization fails.

The user must complete browser consent when first authorizing an account, adding scopes, or recovering from credentials that can no longer refresh.

## Inspect and refresh credentials

Use `status` to inspect available accounts and recorded scopes. If a token exists, use `refresh` to validate it before reauthorizing.

Credential access is ready when the intended account refreshes successfully and has the task's required scopes. Use `authorize` only for a new account, failed refresh, or missing scopes. Verify API enablement separately in the browser or by returning to the operator's service call.

When scopes are missing, show the user the proposed additions and obtain confirmation before running `authorize`. If an administrator or organization policy blocks access, stop and report the policy error together with the account, client, API, and scopes involved.

## Handoff to service operation

Before returning to `operate-services.md`, report only:

- the validated Google email address;
- whether refresh succeeds;
- the granted scope names;
- whether all five supported APIs are enabled; and
- any unresolved administrator or policy requirements.

Never include token values, client-secret values, or complete credential JSON in the report.
