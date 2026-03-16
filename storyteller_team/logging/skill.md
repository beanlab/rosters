---
name: Hybrid Story Logging
description: Append phase markdown logs and structured JSONL events for each story run.
---

Use this skill whenever you need to log actions during story production.

## Goal

Keep logs readable for humans and queryable for tooling.

- Human-readable logs: `st-logs/<story_slug>/<run_id>/0X-<phase>.md`
- Machine-readable logs: `st-logs/<story_slug>/<run_id>/events.jsonl`

## Required Inputs

- `title`
- `phase` (`builder`, `drafter`, `critic`, or `editor`)
- `action`
- `input_summary`
- `output_summary`
- `task_input_text` or `task_input_file` (verbatim task input)
- `task_output_text` or `task_output_file` (verbatim task output written by the agent)
- `inference_reasoning` or `inference_reasoning_file` (all inferences + why each one is reasonable)

Optional:

- `run_id` (if missing, tool generates one)
- `skill` (when a specific skill ran inside a phase agent)
- `next_payload`
- `files_touched` (comma-separated)

## Tool

Use the local tool:

`python .myteam/logging/append_story_log.py --title "<title>" --phase <phase> --action "<...>" --input-summary "<...>" --output-summary "<...>" --task-input-text "<exact input text>" --task-output-text "<exact output text>" --inference-reasoning "<inference + why for each item, or explicitly 'none'>"`.

You can pass `--run-id` to keep all steps in the same run directory.
For long verbatim content, prefer file flags: `--task-input-file`, `--task-output-file`, and `--inference-reasoning-file`.

## Logging Rules

1. Always append. Never delete previous log content.
2. Log exactly what the agent wrote for each task in the verbatim task output field.
3. For every inferred value, log both:
   - what was inferred
   - why that inference is reasonable from available context
4. If no inference was made, say so explicitly in `inference_reasoning`.
5. End phase-completing entries with a clear next-step payload.
6. Keep decision records precise and complete.
