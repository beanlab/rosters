# Thoughts

## Workflow process

- Spawn codex. Inject prompt
  - Objective of the session, format of the output 
  - When objective is complete, yield output
- Engine intercepts output, quits session, moves to next step

### Example workflow

```yaml
step1:
  prompt: I need three haikus. Please write them for me.
  output:
    haiku_dogs: A haiku about dogs
    haiku_cats: A haiku about cats
    haiku_user_choice: A haiku about a topic provided by the user
step2:
  input: $step1.output
  prompt: |
    Review the provided haikus. 
    Rank them in terms of which best captures the essence and style of haiku.
  output:
    best_haiku:
      haiku: the haiku text
      reason: why this haiku was chosen over the others
```

### Prompt for step session

I will give you an objective for our conversation.
When that objective is met, output a response
with only a JSON object containing the information
described in the objective (the objective will include
a YAML template for your JSON).

```json
{
  "status": "OBJECTIVE_COMPLETE",
  "content": ...JSON version of YAML template goes here...
}
```

**If this is an interactive session**: 
when you think the objective has been meet,
present the user with the filled YAML template
and confirm if they are satisfied. 
If they are, then output the JSON object that contains the information.

If this is not an interactive session, 
output the JSON object as your final output.

**Example**
For an objective like this:

```
Please give me three odd numbers.
output:
  number1: an odd number
  number2: another odd number
  number3: a third odd number
```

Assuming you picked the numbers 7, 13, and 29, your **final** output would be:

```json
{"status": "OBJECTIVE_COMPLETE", "content": {"number1": 7, "number2": 13, "number3": 29}}
```

### Engine

- Read the YAML workflow
- Iterate workflow key-values
- Store step outputs (step config + completed output section) against keys
- Allow `input` section to reference step outputs with jsonpath

### Execution of a single step

- Given: step name and step config
- Prepare input from config
- Prepare prompt: prompt + output
- Run session
  - watch for output format; when it comes, end the session (inject `/quit\n`)
  - return parsed output

Use process prototyped in `cdxtty.py` to spawn and monitor the child session

## Future features

- resume prior session in a step
- `--exec` mode for a step
  - This may need to be different from general model settings because the interaction mode is different
- model settings and other params
- configure different settings for executable, `--exec` mode, `/quit`, etc. for other tools
  - claude, opencode, etc.
  - config that registers the necessary information for an agent executable. Ship with codex.
    - Each step can reference the agent it wants to use.