---
name: "style-consistency"
description: "Align narrative voice, tone, and terminology across the story."
---

Use this skill after major content edits and before final proofread.

## Focus Areas

- Narrative voice consistency
- Stable tense and perspective
- Repeated terminology and naming consistency
- Paragraph rhythm and readability

## Constraints

- Avoid changing plot facts unless required for consistency.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase editor --action "style consistency pass completed" --input-summary "edited draft" --output-summary "voice and terminology aligned" --task-input-text "<exact style-consistency input>" --task-output-text "<exact style-consistency output>" --inference-reasoning "<inference + why each, or 'none'>" --skill style-consistency`
