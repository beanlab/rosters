---
name: "final-proofread"
description: "Run a final pass for continuity, formatting, and release readiness."
---

Use this as the last editor skill before returning the final story.

## Final Checklist

- Continuity check (names, places, timeline)
- Formatting consistency
- Clean section and paragraph breaks
- No unresolved placeholders or notes

## Deliverable

- Final story text written to the provided story file path and ready for user delivery.
- Brief edit summary and critic-item status summary.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase editor --action "final proofread completed" --input-summary "post-edit near-final draft" --output-summary "release-ready story" --task-input-text "<exact final-proofread input>" --task-output-text "<exact final-proofread output>" --inference-reasoning "<inference + why each, or 'none'>" --skill final-proofread --next-payload "Story ready for director/user delivery"`
