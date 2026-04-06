---
name: "audience-fit"
description: "Adjust language, tone, and content for the intended audience."
---

Use this skill to ensure the story meets audience appropriateness and readability expectations.

## Focus Areas

- Age-appropriate vocabulary
- Tone suitability for audience and genre
- Clarity relative to target reading level
- Content appropriateness

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase editor --action "audience fit pass completed" --input-summary "near-final draft + audience target" --output-summary "language and tone adjusted for audience" --task-input-text "<exact audience-fit input>" --task-output-text "<exact audience-fit output>" --inference-reasoning "<inference + why each, or 'none'>" --skill audience-fit`
