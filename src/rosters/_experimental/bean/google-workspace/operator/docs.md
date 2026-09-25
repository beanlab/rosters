---
type: skill
description: Use Python and the Google Docs API v1 for one-off document reading, creation, and structured editing. Load for tasks involving Google Docs content.
---

# Operate Google Docs

Follow `operate-services.md` for account selection, confirmation, execution, and reporting. This guide contains Docs-specific choices and hazards.

## Choose a scope

| Task | Scope |
|---|---|
| Read accessible Google Docs | `https://www.googleapis.com/auth/documents.readonly` |
| Create or edit accessible Google Docs | `https://www.googleapis.com/auth/documents` |
| Work only with documents created by or explicitly opened with this OAuth app | `https://www.googleapis.com/auth/drive.file` |

Docs has no document-list method. Load the Drive guide when a document must be discovered by name, moved, shared, exported, or deleted.

## Build the client

```python
docs = workspace_service(ACCOUNT, "docs", "v1")
```

A normal Docs URL contains the document ID after `/document/d/`.

## Read a document

For an ordinary first-tab read:

```python
document = docs.documents().get(documentId=DOCUMENT_ID).execute()
content = document.get("body", {}).get("content", [])
```

A document is structured data, not one plain string. Paragraph text is stored in `textRun.content`; tables and other elements require recursive traversal. Extract only the structures needed for the task rather than treating a simple paragraph walker as a universal document serializer.

For a multi-tab task, request `includeTabsContent=True` and traverse each `tabs[].documentTab`. Top-level body and style fields are legacy first-tab fields when tab content is not requested.

## Perform simple text replacement

For a confirmed replacement in a simple document, prefer `replaceAllText` over calculating indexes. Re-read first and require the returned revision:

```python
document = docs.documents().get(documentId=DOCUMENT_ID).execute()
body = {
    "requests": [
        {
            "replaceAllText": {
                "containsText": {"text": OLD_TEXT, "matchCase": True},
                "replaceText": NEW_TEXT,
            }
        }
    ],
    "writeControl": {"requiredRevisionId": document["revisionId"]},
}
response = docs.documents().batchUpdate(
    documentId=DOCUMENT_ID,
    body=body,
).execute()
```

Preview the match count and context so replacing repeated text cannot affect unintended locations. For multi-tab documents, inspect tab IDs and use the request's tab criteria when the operation must be limited to specific tabs.

## Perform index-sensitive or structured edits

Use this path only when replacement cannot express the task:

1. Fetch with `includeTabsContent=True` when tabs matter.
2. Locate the exact structural element and tab or segment.
3. Use the API's zero-based UTF-16 code-unit indexes, not Python character indexes or rendered-text offsets.
4. Include the correct `tabId` for multi-tab locations and ranges.
5. Submit a small ordered batch with `writeControl.requiredRevisionId` from the final read.

Revision IDs are opaque, user-specific, and guaranteed valid for only 24 hours. Use `requiredRevisionId`, not `targetRevisionId`, when any concurrent change must stop the edit. Requests execute in order, so earlier changes can shift indexes used by later requests.

Re-read the affected tab and structure to verify content and formatting. A valid batch is atomic, but later collaborator changes can still alter the final document.

Official references:

- [Docs authorization](https://developers.google.com/docs/api/auth)
- [Document structure](https://developers.google.com/docs/api/concepts/structure)
- [Batch updates](https://developers.google.com/docs/api/how-tos/overview)
