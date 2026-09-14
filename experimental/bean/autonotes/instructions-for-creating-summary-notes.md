# Creating Notes

Your task is to create summary notes of the provided transcript.

Use the instructions provided here. 
Do not search for or load additional skills or instructions;
everything you need is provided here.

The document should begin with:

```markdown
{header}
```

Followed by a brief bullet-list summary of the primary themes of the meeting.

Then include a section for each theme. 
Each section should begin with a h1 Markdown header and include:

- a summary of the discussion on that theme
- links to backlog items created (if any)
- any decisions that were made
- any designs discussed
- any tasks or open items

The content of the section should be organized chronologically,
not grouped by detail type (decisions, designs, etc.).

The following sections describe what to look for and how to format these items when present in the transcript.

## Backlog items

Backlog items are created on cue from the transcript.
For example, a speaker will say "let's add this to the backlog"
or something similar.

Before creating the backlog item, first determine whether
the conversation applies to an existing backlog item
or whether the material deserves to be in its own backlog entry.
What you are trying to balance is: 
*scattering relevant information about a task or feature across many entries*
versus *trying to cram excessive information about a complex idea into one entry*.
For each existing document that might be home for the new information,
reason whether the new information is a good fit for the existing entry 
or whether a new entry is better.

{backlog_integration_instructions}

## Decisions

Decisions should be formatted as context-and-decision pairs.
Decisions should have a brief title in **bold**, followed by:

- a brief framing of the context for the decision
- a brief summary of the reasoning on the subject
- a brief statement of the decision

For example:

```markdown
**Error-correction Strategy**

Context: We need a way to implement error-correction for user inputs. 
There are two viable options:  
- out-of-band LLM-as-judge
- additional prompting for primary agent

Reasoning: agents do better with a single responsibility;
we want to avoid introducing too much complexity into the primary
agent prompt.

Decision: use an out-of-band LLM-as-judge
```

The transcript does not have sufficient detail to 
provide a complete context or reasoning summary, 
just include what you have, as little as it may be,
or omit that section entirely.

## Designs

Some meetings may have very technical discussions.
Capture these portions of the meeting in more depth than 
the administrative details.

Designs should be formatted similarly to decisions,
but contain as much detail as possible for the
context, reasoning, and decisions.

Provide a complete account of the designs or work presented,
as well as ultimate design decisions made 
and the designs that were rejected and why.
 
Review this portion of the transcript and compare it to your summary.
Are there details missing? 
Does the summary contain all the information discussed? 

The design or work itself might not be complete or ready for implementation,
but the summary of the discussion should not lose important
information already presented. 

## Tasks and open items

Here, capture details identified by phrases like:
"John, will you please..." or "let's have Jane take care off...".

## Scope

Keep the summary notes focused on the business of the project.
Omit side conversations, personal details, tangents, etc.

-------
{transcript}
-------