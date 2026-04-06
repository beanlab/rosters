---
name: "grammar-spellcheck"
description: "Correct grammar, spelling, punctuation, and sentence mechanics."
---

Use this skill to produce mechanically correct prose before final delivery.

## Focus Areas

- Spelling
- Grammar
- Punctuation
- Sentence fragments/run-ons
- Basic agreement and tense consistency

## Constraints

- Do not introduce plot changes.
- Preserve voice unless a sentence is unclear or incorrect.

## Logging Requirement

`python .myteam/logging/append_story_log.py --title "<title>" --run-id "<run_id>" --phase editor --action "grammar/spelling pass completed" --input-summary "post-feedback draft" --output-summary "mechanical language corrections" --task-input-text "<exact grammar pass input>" --task-output-text "<exact grammar pass output>" --inference-reasoning "<inference + why each, or 'none'>" --skill grammar-spellcheck`
