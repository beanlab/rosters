---
type: skill
description: Use Python and the Google Drive API v3 for one-off file discovery, metadata, download, export, upload, move, sharing, trash, and deletion tasks. Load for operations involving Drive files or folders.
---

# Operate Google Drive

Follow `operate-services.md` for account selection, confirmation, execution, and reporting. This guide contains Drive-specific choices and hazards.

## Choose a scope

| Task | Scope |
|---|---|
| Read file metadata only | `https://www.googleapis.com/auth/drive.metadata.readonly` |
| Read metadata and content | `https://www.googleapis.com/auth/drive.readonly` |
| Create, edit, move, share, trash, or delete arbitrary accessible files | `https://www.googleapis.com/auth/drive` |
| Work only with files created by or explicitly opened with this OAuth app | `https://www.googleapis.com/auth/drive.file` |

`drive.file` is not a general Drive search scope. Use it only when its file-eligibility constraint is known to cover the target.

## Build the client

Use the shared factory from `operate-services.md`:

```python
drive = workspace_service(ACCOUNT, "drive", "v3")
```

## Find the exact file

Drive names are not unique. Prefer a supplied URL or file ID. Otherwise use a narrow query, request stable IDs, paginate to completion, and stop on ambiguity:

```python
def list_files(query):
    page_token = None
    while True:
        response = drive.files().list(
            q=query,
            spaces="drive",
            pageSize=100,
            pageToken=page_token,
            fields=(
                "nextPageToken,incompleteSearch,"
                "files(id,name,mimeType,parents,modifiedTime,version,trashed,resourceKey)"
            ),
        ).execute()
        if response.get("incompleteSearch"):
            raise RuntimeError("Drive search was incomplete; narrow the corpus")
        yield from response.get("files", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            break
```

Escape user-supplied Drive query values. Filter out trashed files unless they are relevant. Read definitive metadata with `files.get` before acting.

### When a link contains a resource key

Preserve the URL's `resourcekey` parameter and add it to requests for that protected file:

```python
request = drive.files().get(
    fileId=FILE_ID,
    fields="id,name,mimeType,parents,modifiedTime,version,trashed,webViewLink",
    supportsAllDrives=True,
)
request.headers["X-Goog-Drive-Resource-Keys"] = f"{FILE_ID}/{RESOURCE_KEY}"
file = request.execute()
```

Apply the same header to download, export, or mutation requests. Keep resource keys out of logs and reports.

### When the target is in a shared drive

For shared-drive search, use `corpora="drive"`, the exact `driveId`, `includeItemsFromAllDrives=True`, and `supportsAllDrives=True`. Narrow the corpus rather than accepting an incomplete all-Drives search.

## Read content

Use `files.get_media()` for uploaded binary files. Google-native Docs, Sheets, and Slides must be exported with `files.export_media(fileId=..., mimeType=...)`. Stream large responses with `googleapiclient.http.MediaIoBaseDownload`.

## Apply Drive-specific mutations

Read current metadata, parents, version, and sharing state for the mutation preview. Send only changed fields because `files.update` has patch semantics:

```python
updated = drive.files().update(
    fileId=FILE_ID,
    body={"name": NEW_NAME},
    supportsAllDrives=True,
    fields="id,name,parents,modifiedTime,version,trashed,webViewLink",
).execute()
```

Move a file with `addParents` and `removeParents`; do not send a stale full resource. Permission previews must identify the grantee, role, target, notification behavior, and any ownership transfer. Prefer `files.update(body={"trashed": True})` over permanent deletion unless permanent deletion is explicitly confirmed.

Verify changed metadata, parents, trash state, or permissions with a fresh `files.get` or permissions read.

Official references:

- [Drive API scopes](https://developers.google.com/drive/api/guides/api-specific-auth)
- [Search for files](https://developers.google.com/drive/api/guides/search-files)
- [Files resource](https://developers.google.com/drive/api/reference/rest/v3/files)
