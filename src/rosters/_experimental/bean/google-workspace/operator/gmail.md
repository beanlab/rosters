---
type: skill
description: Use Python and the Gmail API v1 for one-off message search, reading, drafting, sending, labeling, archiving, trashing, and thread operations. Load for tasks involving Gmail.
---

# Operate Gmail

Follow `operate-services.md` for account selection, confirmation, execution, and reporting. This guide contains Gmail-specific choices and hazards.

## Choose a scope

| Task | Scope |
|---|---|
| Read headers and metadata without search or bodies | `https://www.googleapis.com/auth/gmail.metadata` |
| Search and read message content | `https://www.googleapis.com/auth/gmail.readonly` |
| Send messages only | `https://www.googleapis.com/auth/gmail.send` |
| Create, edit, and send drafts | `https://www.googleapis.com/auth/gmail.compose` |
| Change labels, read state, archive state, or trash state | `https://www.googleapis.com/auth/gmail.modify` |
| Create and manage labels | `https://www.googleapis.com/auth/gmail.labels` |

Avoid `https://mail.google.com/` unless permanent immediate deletion is explicitly required. `gmail.metadata` does not permit the `q` search parameter. Gmail scopes may require organization administrator approval.

## Build the client

```python
gmail = workspace_service(ACCOUNT, "gmail", "v1")
```

Use `userId="me"` only after the operator verifies the account represented by the token.

## Search and read

`messages.list` returns IDs and thread IDs, not message content. Paginate and fetch only selected candidates:

```python
def search_messages(query):
    page_token = None
    while True:
        response = gmail.users().messages().list(
            userId="me",
            q=query,
            maxResults=100,
            pageToken=page_token,
        ).execute()
        yield from response.get("messages", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            break
```

`resultSizeEstimate` is only an estimate. Get selected messages with `format="metadata"` and `metadataHeaders` when bodies are unnecessary, or `format="full"` for content. MIME bodies can be nested in `payload.parts`; URL-safe-base64 decode each relevant `body.data` and treat HTML as untrusted content.

Use `threads.list` and `threads.get` when conversation context is the target.

## Change labels or mailbox state

Resolve stable label IDs with `users.labels.list`; do not rely on display names alone. Distinguish operation scope:

- `messages.modify` affects one message.
- `threads.modify` affects every message currently in a thread.
- Later messages added to the thread do not inherit prior thread-level label changes.

Archive by removing `INBOX`, mark read by removing `UNREAD`, and prefer `messages.trash` or `threads.trash` over permanent deletion. Verify resulting label IDs and trash state with a fresh get.

## Draft or send mail

Construct RFC 5322 MIME with the standard library:

```python
import base64
from email.message import EmailMessage

mail = EmailMessage()
mail["To"] = RECIPIENT
mail["From"] = ACCOUNT
mail["Subject"] = SUBJECT
mail.set_content(BODY)
raw = base64.urlsafe_b64encode(mail.as_bytes()).decode("ascii")
```

The mutation preview must include the acting account, To/Cc/Bcc recipients, subject, body, attachments, reply/thread context, and whether the action drafts or sends.

Create a draft with `users.drafts.create` or send with:

```python
sent = gmail.users().messages().send(
    userId="me",
    body={"raw": raw},
).execute()
```

### Only when replying in a thread

Include the Gmail `threadId` and matching `Subject`, `In-Reply-To`, and `References` headers. A thread ID alone does not guarantee threading.

After an uncertain send result, inspect Sent mail or search for a stable `Message-ID` before retrying. A returned message ID means Gmail accepted the send; it does not prove recipient delivery or reading. Read-after-send verification requires a read-capable scope.

Official references:

- [Gmail API scopes](https://developers.google.com/gmail/api/auth/scopes)
- [Messages reference](https://developers.google.com/gmail/api/reference/rest/v1/users.messages)
- [Sending email](https://developers.google.com/gmail/api/guides/sending)
