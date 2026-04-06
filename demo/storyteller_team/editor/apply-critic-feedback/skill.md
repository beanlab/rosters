---
name: "apply-critic-feedback"
description: "Apply prioritized critic feedback and document resolution status."
---

Use this skill first in the editor phase.

## Objectives

- Implement critic requests in priority order (P1, P2, then P3).
- Preserve story identity while addressing major weaknesses.
- Record item-level status: resolved, partial, or not applied.

## Procedure

1. Parse critic notes into concrete edit tasks.
2. Apply changes directly to the provided story file path on disk.
3. Build a resolution summary with reasons for any non-applied items.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase editor --action "critic feedback applied" --input-summary "critic priorities and requests" --output-summary "updated draft + resolution status" --task-input-text "<exact feedback input>" --task-output-text "<exact applied-changes output>" --inference-reasoning "<inference + why each, or 'none'>" --skill apply-critic-feedback`
