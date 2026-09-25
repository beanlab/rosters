---
type: skill
description: Use Python and the Google Sheets API v4 for one-off spreadsheet metadata, value, formula, formatting, and structural operations. Load for tasks involving Google Sheets content.
---

# Operate Google Sheets

Follow `operate-services.md` for account selection, confirmation, execution, and reporting. This guide contains Sheets-specific choices and hazards.

## Choose a scope

| Task | Scope |
|---|---|
| Read spreadsheet metadata and values | `https://www.googleapis.com/auth/spreadsheets.readonly` |
| Change values, formulas, formatting, or structure | `https://www.googleapis.com/auth/spreadsheets` |
| Work only with spreadsheets created by or explicitly opened with this OAuth app | `https://www.googleapis.com/auth/drive.file` |

Sheets has no spreadsheet-list endpoint. If no spreadsheet ID or URL is supplied, load the Drive guide and use an appropriate Drive scope for discovery.

## Build the client

```python
sheets = workspace_service(ACCOUNT, "sheets", "v4")
```

The spreadsheet ID is the value between `/d/` and the next slash in a normal Sheets URL.

## Inspect structure and values

Establish exact sheet titles, numeric sheet IDs, locale, and timezone without loading grid data:

```python
metadata = sheets.spreadsheets().get(
    spreadsheetId=SPREADSHEET_ID,
    includeGridData=False,
    fields="spreadsheetId,properties(title,locale,timeZone),sheets(properties)",
).execute()
```

Read explicit A1 ranges rather than an unbounded sheet:

```python
result = sheets.spreadsheets().values().get(
    spreadsheetId=SPREADSHEET_ID,
    range="'Data'!A1:F100",
    valueRenderOption="UNFORMATTED_VALUE",
    dateTimeRenderOption="FORMATTED_STRING",
).execute()
rows = result.get("values", [])
```

Use `values.batchGet` for several ranges. Value range calls do not paginate. Select `FORMATTED_VALUE`, `UNFORMATTED_VALUE`, or `FORMULA` deliberately; the default is formatted display text.

Quote A1 sheet names containing spaces or punctuation with single quotes, doubling embedded apostrophes. Do not construct ranges from unescaped user input.

## Change values or structure

The mutation preview must show the spreadsheet ID, sheet title, exact ranges, existing and proposed values, and interpretation mode. `RAW` stores values literally; `USER_ENTERED` may evaluate formulas and locale-sensitive numbers or dates.

```python
response = sheets.spreadsheets().values().update(
    spreadsheetId=SPREADSHEET_ID,
    range="'Data'!B2:C3",
    valueInputOption="RAW",
    body={"majorDimension": "ROWS", "values": VALUES},
).execute()
```

Use `values.batchUpdate` for multiple value ranges.

### Only when changing spreadsheet structure

Use `spreadsheets.batchUpdate` for formatting, sheet or dimension changes, filters, and named ranges. Structural requests generally target numeric `sheetId`, not visible title. A structural batch is ordered and rejects the complete batch if any request is invalid.

Verify returned update ranges and counts, then re-read affected values or narrow metadata fields. Sheets has no general revision precondition equivalent to Docs `requiredRevisionId`; minimize read-to-write time and keep changes narrow.

Official references:

- [Sheets authorization](https://developers.google.com/sheets/api/guides/authorizing)
- [Read and write values](https://developers.google.com/sheets/api/guides/values)
- [Batch update](https://developers.google.com/sheets/api/guides/batchupdate)
