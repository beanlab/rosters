---
type: skill
description: If you need to interact with the Canvas LMS in any way, you MUST load this skill. It contains critical security and data-integrity guidance.
---

We work at Brigham Young University. We use Canvas LMS to administer our courses.

The URL is `https://byu.instructure.com`.
The API token environment variable is named `CANVAS_API_TOKEN`.

Unless give EXPLICIT permission (and you MUST always double check before taking action),
preform ONLY READ operations. 

If the user has given clear authorization for a mutating change in Canvas,
you must confirm with the user exactly what you are going to do. 
This includes a description of your intent, an outline of the logic you will perform, 
and a description of what will be changed. You MUST follow this procedure for EVERY mutating change.

Use the `canvasapi` Python package to interact with the Canvas API.

