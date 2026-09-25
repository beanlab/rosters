---
type: skill
description: Use Python and the Google Calendar API v3 for one-off calendar discovery, availability, event reading, creation, invitation, update, and deletion tasks. Load for operations involving Google Calendar.
---

# Operate Google Calendar

Follow `operate-services.md` for account selection, confirmation, execution, and reporting. This guide contains Calendar-specific choices and hazards.

## Choose a scope

| Task | Scope |
|---|---|
| Read events | `https://www.googleapis.com/auth/calendar.events.readonly` |
| Create or change events | `https://www.googleapis.com/auth/calendar.events` |
| Query availability without event details | `https://www.googleapis.com/auth/calendar.freebusy` |
| Discover calendars | `https://www.googleapis.com/auth/calendar.calendarlist.readonly` |

For tasks restricted to calendars the user owns, use the narrower `https://www.googleapis.com/auth/calendar.events.owned.readonly` or `https://www.googleapis.com/auth/calendar.events.owned`. Use the broad `calendar` scope only for calendar or ACL administration. A known calendar ID, including `primary`, avoids calendar-list scope solely for discovery.

## Build the client

```python
calendar = workspace_service(ACCOUNT, "calendar", "v3")
```

## Resolve calendars and events

Calendar display names are not stable identifiers. Paginate `calendarList.list` and select by `id`, access role, primary flag, and summary.

List a bounded event window with timezone-aware RFC 3339 timestamps:

```python
def list_events(calendar_id, time_min, time_max):
    page_token = None
    while True:
        response = calendar.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
            maxResults=250,
        ).execute()
        yield from response.get("items", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            break
```

All-day events use `date`; timed events use `dateTime` and an explicit timezone. Event end times are exclusive.

### Only when the event recurs

`singleEvents=True` expands recurring series into instances; omit it when the recurring master is the target. Identify whether a mutation targets the series or one instance.

## Change events

A mutation preview must distinguish the exact calendar, recurring series versus instance, timezone, attendees, notification behavior, and conferencing changes. Re-read an existing event immediately before changing it and retain its `etag`.

For a partial update, use patch semantics and make notification behavior explicit:

```python
request = calendar.events().patch(
    calendarId=CALENDAR_ID,
    eventId=EVENT_ID,
    body=PATCH,
    sendUpdates="all",  # all, externalOnly, or none
)
request.headers["If-Match"] = CURRENT_ETAG
updated = request.execute()
```

Use `events.update` only when replacing the complete event resource. `sendNotifications` is deprecated; use `sendUpdates`.

### Only when using Google Meet

Use `conferenceDataVersion=1` when creating or preserving conference data.

If an insert result is uncertain, inspect the bounded event window before retrying to avoid duplicate events or invitations. For deletion, preview attendee notification behavior explicitly.

Verify with `events.get`, comparing start, end, timezone, attendees, recurrence, conference data, and status. API success means Calendar accepted the change; it does not prove invitee delivery or acceptance.

Official references:

- [Calendar authorization](https://developers.google.com/calendar/api/auth)
- [Events reference](https://developers.google.com/calendar/api/v3/reference/events)
