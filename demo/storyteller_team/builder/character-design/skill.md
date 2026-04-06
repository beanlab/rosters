---
name: "character design"
description: "Design characters for the story. This includes their personality, background, and physical appearance."
---

Use this skill after plotting.

## Objective

Create a character set that naturally supports the plot and theme.

## Required Inputs

- Title
- Target audience
- Genre
- Theme
- Setting
- Premise/plot schema
- Run ID

## Output Format

For each key character include:

- Name
- Role in story
- Motivation
- Internal conflict
- External conflict
- Voice/personality notes
- Arc direction

## Guidance

- Ensure characters have distinct goals and tension points.
- Tie each major character directly to plot progression.
- Keep traits and complexity appropriate for target audience.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase builder --action "character set created" --input-summary "plot schema + specs" --output-summary "character roster with motivations and arcs" --task-input-text "<exact character-design input>" --task-output-text "<exact character set text>" --inference-reasoning "<inference + why each, or 'none'>" --skill character-design`
