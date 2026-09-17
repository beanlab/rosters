---
type: skill
description: Load whenever interacting with Gradescope. Describes secure Canvas LTI authentication and browser interaction through Playwright.
---

# Gradescope Authentication and Playwright Interaction

Use this procedure to authenticate with a Canvas-linked Gradescope course and interact with it through its supported web UI. A Canvas API token does not authenticate directly with Gradescope; use it to request a temporary LTI launch URL, open that URL in Playwright, and retain browser state only for the duration of the task.

Load the Canvas LMS skill before using this procedure. Authentication grants access but does not authorize changes. Follow the governing work instruction's approval and mutation controls. When no governing instruction exists, remain read-only until the user explicitly authorizes an exact target and change. Never infer mutation approval from permission to authenticate or inspect a course.

## Prerequisites

- Instructor access to the intended Canvas course and its linked Gradescope course.
- `CANVAS_API_TOKEN` set at runtime.
- Python with `canvasapi`.
- Node.js and Playwright.
- Google Chrome or a Playwright-installed Chromium browser.
- A restricted, gitignored scratch directory for temporary authentication state.

Never print, log, commit, or pass `CANVAS_API_TOKEN` on a command line. Treat LTI launch URLs, browser cookies, Playwright storage-state files, and browser profiles as temporary credentials.

Create and protect a temporary directory outside tracked source, such as:

```bash
mkdir -p .agents/scratch/gradescope
chmod 700 .agents/scratch/gradescope
```

Confirm that the directory is ignored by Git before writing authentication artifacts there.

## Verify the Canvas target

Use `canvasapi` read-only to retrieve the user-approved numeric Canvas course ID. Report and verify the API host, actual course ID, course name, and course code before requesting a launch URL. Stop if the target identity is uncertain.

```python
import os
from canvasapi import Canvas

canvas = Canvas(
    "https://byu.instructure.com",
    os.environ["CANVAS_API_TOKEN"],
)
course = canvas.get_course(CANVAS_COURSE_ID)

print({
    "id": course.id,
    "name": course.name,
    "course_code": getattr(course, "course_code", None),
})
assert int(course.id) == int(CANVAS_COURSE_ID)
```

Do not continue until these values match the intended course.

## Request a sessionless Gradescope launch

Find the current Gradescope external tool inherited by the course. Exclude legacy tools whose names contain `pre1.3`. Stop if no candidate or more than one candidate remains; do not guess.

```python
import os
from canvasapi import Canvas

canvas = Canvas(
    "https://byu.instructure.com",
    os.environ["CANVAS_API_TOKEN"],
)
course = canvas.get_course(CANVAS_COURSE_ID)

tools = list(course.get_external_tools(include_parents=True))
candidates = [
    tool for tool in tools
    if "gradescope" in getattr(tool, "name", "").lower()
    and "pre1.3" not in getattr(tool, "name", "").lower()
]
if len(candidates) != 1:
    raise RuntimeError(
        f"Expected exactly one current Gradescope tool; found {len(candidates)}"
    )

gradescope = candidates[0]
launch_url = gradescope.get_sessionless_launch_url(
    launch_type="course_navigation"
)
```

The returned URL is a temporary credential. Do not print it, put it in a report, save it in shell history, or pass it as a command-line argument. Prefer passing it directly from the requesting process to browser automation. If processes must exchange it, use a mode-`0600` file in the restricted scratch directory, read it once, and delete it immediately.

## Open the launch with Playwright

Open the launch URL in a fresh Playwright context. Gradescope may open in a new tab, so inspect all pages in `context.pages()`. Authentication succeeds only after a page reaches an HTTPS URL whose hostname is `www.gradescope.com` or `gradescope.com`; a Canvas `/courses/` URL is not evidence of Gradescope authentication.

Conceptual Playwright flow:

```javascript
import { chromium } from 'playwright';

const browser = await chromium.launch({
  channel: 'chrome',
  headless: true,
});
const context = await browser.newContext();
const page = await context.newPage();

await page.goto(launchUrl, {
  waitUntil: 'domcontentloaded',
  timeout: 60_000,
});

// Check every page because the LTI launch may open Gradescope in a new tab.
const gradescopePage = context.pages().find((candidate) => {
  const url = new URL(candidate.url());
  return url.protocol === 'https:' &&
    (url.hostname === 'gradescope.com' || url.hostname === 'www.gradescope.com');
});
if (!gradescopePage) {
  throw new Error('The LTI launch did not reach Gradescope');
}

await gradescopePage.waitForURL(/https:\/\/(www\.)?gradescope\.com\/courses\//, {
  timeout: 60_000,
});
await context.storageState({ path: authStatePath });
await browser.close();
```

Protect any storage-state file immediately:

```bash
chmod 600 "$AUTH_STATE_PATH"
```

The Gradescope course ID appears in the resulting URL:

```text
https://www.gradescope.com/courses/<gradescope-course-id>
```

Record the non-secret Gradescope course ID, name, and term for target verification. Do not record the launch URL, cookies, or storage-state contents.

## Fallback when sessionless launch fails

Use a headed Playwright browser and complete Canvas SSO interactively. Inspect all opened tabs and verify the Gradescope hostname and intended course identity. Never ask the user to provide a password, MFA code, cookie, or session token in chat or a tracked file.

## Interact through the Gradescope web UI

Use a fresh Playwright context loaded from the protected storage state. Navigate only to HTTPS Gradescope URLs under the verified course ID. Before reading or changing course data, confirm the URL course ID and visible course name/term match the intended target.

Prefer user-facing roles, labels, headings, and exact visible text over generated CSS classes. Scope locators to the relevant form, table row, dialog, or section, and require unique matches before acting. Treat missing, duplicate, or changed controls as a stop condition rather than choosing the first approximate match.

For read-only work:

- use navigation, search, filtering, expansion controls, and downloads that do not alter course state;
- do not click controls such as Save, Create, Delete, Sync, Link, Unlink, Publish, Post, Rerun, or Resubmit;
- avoid collecting names, emails, submissions, or grades unless the task requires them; and
- keep private data out of ordinary logs, screenshots, reports, and filenames.

For an authorized mutation:

1. Reverify the Gradescope course ID/name/term and linked Canvas target.
2. Follow the governing instruction's approval scope and no-drift requirements.
3. Read the current values and compare them with the approved expected state.
4. Fill or select only the approved fields. Preserve unrelated values.
5. Before clicking the final mutating control, verify the dialog/form target and summarize the values in automation logs without credentials or private student data.
6. Wait for the resulting navigation, response, or visible success state.
7. Re-open the affected page and verify the persisted values rather than trusting a toast or click completion.
8. Stop on partial failure or unexpected state; do not retry or compensate automatically unless the governing instruction explicitly permits it.

Use Playwright's file chooser or `setInputFiles()` for authorized uploads and its download events for downloads. Keep temporary uploaded/downloaded files in a restricted scratch directory. Do not reverse-engineer or call unsupported Gradescope APIs when the task specifies UI interaction.

Gradescope UI structure can change. Record reusable, verified locator strategies without cookies, launch URLs, student data, or other private information. Do not treat a locator observed in one page as universal without checking its surrounding labels and target identity.

## Reuse and cleanup

A saved Playwright state may be reused only for the same approved task and target. Create a fresh browser context from it:

```javascript
const context = await browser.newContext({ storageState: authStatePath });
```

Before reading or mutating Gradescope data, verify the Gradescope course ID/name/term and its relationship to the approved Canvas course. Authentication alone is not target verification or mutation authorization.

At task completion—or immediately after any authentication failure—close the browser and delete:

- the sessionless launch URL or exchange file;
- Playwright storage-state files;
- temporary browser profiles;
- debug screenshots or logs containing credentials or private data.

Do not commit authentication artifacts. Do not preserve them merely to make a later session more convenient.
