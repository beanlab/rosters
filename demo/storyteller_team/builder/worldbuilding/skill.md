---
name: "worldbuilding"
description: "Create and develop the world in which the story takes place. This includes the geography, culture, history, and rules of the setting."
---

Use this skill after plotting and character design.

## Objective

Define only the world details required to make the story believable and coherent.

## Required Inputs

- Title
- Target audience
- Genre
- Theme
- Setting
- Plot schema
- Character set
- Run ID

## Output Format

- World summary
- Key locations
- Social/cultural context
- System rules (magic, tech, politics, economy) if relevant
- Constraints that affect plot and character choices

## Guidance

- Depth should match audience and story scope.
- Avoid lore that does not influence story decisions.
- Ensure world rules stay consistent and testable in draft scenes.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase builder --action "world notes created" --input-summary "plot schema + characters + specs" --output-summary "setting systems, locations, and constraints" --task-input-text "<exact worldbuilding input>" --task-output-text "<exact world notes text>" --inference-reasoning "<inference + why each, or 'none'>" --skill worldbuilding`
