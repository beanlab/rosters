# General Instructions

## Scratch space

Use `.agents/scratch/` as workspace when needed. If you need to write a file, write it here. 
This folder will typically be in `.gitignore` and not tracked.
If the content will be sensitive or private, use this folder.

Use `.agents/remember/` for content or artifacts that should be committed and remembered.
These would be documents a feature agent session would benefit from knowing and are safe to commit.

The ultimate deciding factor between `scratch/` and `remember/` is that `remember/` will be tracked by git and `scratch/` may not be.

## User interactions

When soliciting feedback from the user, **ask only one question at a time**. Don't give the user a big list of content to review and respond to: rather, write all your questions/thoughts to a file, then go through the items one at a time so the user can discuss them before making decisions. If responses or discussion around earlier items influences later items, modify or omit them as needed. For each item you discuss with the user, provide reasonable options and your recommendation.

Be concise and brief, sharing only the essential details. The user will request more details when they are needed. 

Please answer the users questions as articulated, not as you assume them to mean. If you need to clarify a question, please do. 

"Did you do X?" is not the same as "Please do X." "How would you do Y?" is not the same as "Please do Y." Respond to what was actually said. If asked "does that make sense" or similar, respond to the question; do not take action.

When asked a question, answer the question. When asked to perform a task, if the task was complicated, include a brief summary of what you did to finish the task; if the task was simple, simply say "Done." Do **not** offer what to do next.

If you notice an important detail earlier in the conversation that the user hasn't responded to, bring it to their attention. 

## Simplicity

We value simplicity and avoid premature complexity. As you think through your tasks and suggestions, always consider: "Is this as simple as it can be? Is any complexity I see necessary?" When presenting multiple options to the user, concisely summarize which options introduce more complexity and how, but also explaining the value the option would bring as a result. If an option introduces complexity but no additional value, it's not a good option.

When starting a task, start with a good-faith, best-effort approach first. This will establish a good foundation upon which further details and complexity can be added as needed. 
 