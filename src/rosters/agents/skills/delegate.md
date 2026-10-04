---
type: workflow
model: gpt-5.6-luna
session_name: delegate.md
description: An agent assistant. Delegate specific, scoped tasks to this agent as needed, especially when fresh context is important to the task. 
usage: When calling this workflow, please provide a brief-but-descriptive name for this session using `--session-name <name>`. The default model is gpt-5.6-luna (an economy tier model). If the task requires higher intelligence, specify the model with `--model 'gpt-5.6-sol'`.
input: 
  instructions: (str) What you would like done. Include context and all other relevant information. Include what you want included in the output result.
output:
  result: (str) The text requested in the input instructions.
---

{{ instructions }}
