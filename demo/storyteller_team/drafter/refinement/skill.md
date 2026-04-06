---
name: "refinement"
description: "Refine a draft for coherence, pacing, and clarity before critique."
---

Use this skill after the first draft is complete and before handing off to `critic`.

## Objectives

- Improve coherence between scenes and character actions.
- Tighten pacing and remove redundancy.
- Clarify confusing sentences and transitions.
- Preserve core plot intent from builder outputs.

## Input Checklist

- Title
- Target audience
- Draft text
- Any hard constraints (length, tone, content limits)
- Run ID

## Procedure

1. Read the full draft once without editing.
2. Identify high-impact issues first (continuity, logic, pacing).
3. Revise for clarity and flow.
4. Keep audience vocabulary and tone consistent.
5. Prepare a short summary of changes for critic context.

## Logging Requirement

Append at least one refinement event with:

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase drafter --action "refinement pass completed" --input-summary "draft + constraints" --output-summary "coherence, pacing, and clarity updates" --task-input-text "<exact refinement input>" --task-output-text "<exact refinement output>" --inference-reasoning "<inference + why each, or 'none'>" --skill refinement`
