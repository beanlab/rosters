---
type: skill
description: Create or repair the organization-owned Google Cloud project, Internal Google Auth configuration, enabled Workspace APIs, and Desktop OAuth client. Load when the local OAuth client is missing or invalid and an interactive browser-capable agent will perform the Google Cloud setup.
---

# Create an Internal Workspace OAuth client

Use an interactive browser to configure Google Cloud and download the Desktop OAuth client used by the provisioning skill. Follow the confirmation and credential-handling safeguards in the parent `google-workspace.md` skill.

## Confirm browser capability

Before starting, verify that you can:

- navigate an interactive browser, inspect pages, click controls, and enter non-secret form values;
- let the user take over for sign-in, account selection, reauthentication, and multi-factor authentication; and
- retrieve a browser download and move it to a local path.

Web search and page-fetch tools are not interactive browser capabilities. If any required capability is unavailable, stop and tell the user which browser actions they must perform. Never ask the user to provide a password or authentication code in chat.

## Inspect before changing anything

1. Open the [Google Cloud console](https://console.cloud.google.com/).
2. If authentication is required, give control to the user and wait until they confirm that sign-in is complete.
3. Identify the signed-in Google account, selected Cloud project, and owning organization without changing them.
4. Confirm that the account and organization belong to the intended Google Workspace domain.
5. Inspect whether a suitable organization-owned project and Google Auth configuration already exist.
6. Present a bounded plan naming the account, organization, project to create or modify, APIs to enable, OAuth audience, client type, and download destination. Obtain explicit confirmation before making any change.

A confirmation covers only the presented plan. Stop and ask again if the account, organization, project, or required changes differ from it.

## Select or create the Cloud project

Use an existing project only when it is owned by the intended Workspace organization and is appropriate for this local OAuth client. Otherwise:

1. Open the project selector and choose **New Project**.
2. Enter the confirmed project name.
3. Select the intended organization and location.
4. Create the project and wait for creation to finish.
5. Select the new project and verify its project name, project ID, and organization before continuing.

If the organization cannot be selected, stop. The user may need to switch accounts or ask a Cloud/Workspace administrator to create the project or grant access. Do not create the OAuth app in an unrelated personal project.

## Enable the Workspace APIs

In **APIs & Services** > **Library** > **Google Workspace**, enable each of these APIs for the selected project:

- Google Drive API (`drive.googleapis.com`)
- Google Sheets API (`sheets.googleapis.com`)
- Google Docs API (`docs.googleapis.com`)
- Google Calendar API (`calendar-json.googleapis.com`)
- Gmail API (`gmail.googleapis.com`)

For each API, treat **Manage** or another clear enabled-state indicator as already enabled; otherwise use **Enable** and wait for completion. Recheck the selected project before every enable action. Enabling APIs does not grant access to user data.

## Configure the Internal audience

1. Open **Google Auth Platform** for the selected project.
2. If it is not configured, choose **Get Started** and provide:
   - a recognizable internal app name;
   - a user support email controlled by the organization;
   - **Internal** as the audience; and
   - an organization-controlled developer contact email.
3. If Google presents an API Services User Data Policy acknowledgement, give control to the user so they can review and accept it, then finish configuration.
4. If Google Auth Platform was already configured, inspect **Branding** and **Audience** and make only the confirmed changes needed to meet the same criteria.

Do not choose External or use External testing mode. If Internal is unavailable, verify that the project belongs to the intended Workspace or Cloud Identity organization. If it does and Internal remains unavailable, stop and report the permissions or organization-policy issue.

Do not add broad Workspace scopes in Google Auth Platform. The OAuth helper requests user scopes incrementally for each task.

## Create and download the Desktop client

1. Open **Google Auth Platform** > **Clients**.
2. Reuse an existing client only if it is clearly the confirmed Desktop client for this local agent use. Otherwise choose **Create Client**, set **Application type** to **Desktop app**, name it, and create it.
3. Download the client's JSON configuration using the console's download control.
4. Move the downloaded file to:

   ```text
   ~/.agents/scratch/google-workspace/oauth-client.json
   ```

5. Apply owner read/write permissions to the file, following the parent skill.
6. Verify locally that the JSON contains an `installed` object. Do not print the file or any client-secret value.
7. Recheck **Audience** in the browser and verify that it says **Internal**. The downloaded JSON does not contain the audience setting.

If browser automation cannot access the download, ask the user to download it and place it at the exact path above, then continue with the non-secret structural check.

## Finish

Report only:

- the Google account and Workspace organization used;
- the project name and project ID;
- that the audience visibly shows **Internal**;
- that all five APIs are enabled;
- that the client type is **Desktop app**; and
- that the client configuration exists at the expected local path.

Do not report the client secret or complete client JSON. Return to `provision-access.md` to authorize and validate each Google account.

Use Google's current documentation if console labels have changed:

- [Configure OAuth consent](https://developers.google.com/workspace/guides/configure-oauth-consent)
- [Create access credentials](https://developers.google.com/workspace/guides/create-credentials)
- [Enable Workspace APIs](https://developers.google.com/workspace/guides/enable-apis)
