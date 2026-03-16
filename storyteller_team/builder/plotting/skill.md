---
name: "plotting"
description: "Create and develop the plot of the story. This includes planning the main events, conflicts, and resolutions."
---

Use this skill first in the builder phase.

## Objective

Produce a clear plot schema that can drive character and world design.

## Required Inputs

- Title
- Target audience
- Genre
- Theme
- Setting
- Run ID

## Output Format

- Working title
- Premise
- Act structure (as many acts as needed)
- Core conflict
- Resolution direction

## Guidance

- Keep the plot aligned to audience and theme.
- Prefer clear causality between acts.
- Keep scope realistic for requested story length.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase builder --action "plot schema created" --input-summary "specs from director" --output-summary "premise + act structure + conflict/resolution" --task-input-text "<exact plotting input>" --task-output-text "<exact plot schema text>" --inference-reasoning "<inference + why each, or 'none'>" --skill plotting`
