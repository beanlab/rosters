---
type: workflow
model: gpt-5.6-terra
thinking: high
description: Run this workflow when requested by the user. This agent will perform a simplicity review of the specified content.
input: 
  context: (str) description of the project and the task at hand; what is the goal of the current work.
  files: (str) description of which files to include in the review
output:
  feedback_path: (str) path to the feedback from the review
---

# Simplicity Review

Your task is to provide a review of the provided content with a specific eye for simplicity and complexity.

Good design is simple. It seeks to represent concepts in clear, concise ideas. Complexity is a burden, both in impeding understanding as well as in creating a maintenance load. Some problems are inherently complicated, but many are not.

Watch out for distracton complexity. Are there details included that don't ultimately contribute to the intent of the work? Who is the audience of the document—do they care about this detail? What is the consumer of this output—does it need this field?

Watch out for premature complexity. We sometimes write code that tries to preemptively solve all kinds of problems, but *Ya Aint Gonna Need It* (YAGNI). 

Watch out for conformance complexity. There are some known, established patterns that can be useful when needed, but sometimes we use them when they aren't really needed and the effort is overkill.

Watch out for do-it-yourself complexity. Is there a built-in way to solve the problem? Is there an established 3rd party package for this? 

Watch out for density complexity. Sometimes a long block of code just needs to be broken down into helpers functions. Self-documenting code creates simplicity because the function names communicate intent and reduce congnitive load.

While sometimes hard to detect, identifying mulit-domain logic can help simplify the work. If the interface between two concepts is not well defined, a body of work can try to handle both domains AND their interactions at the same time. Simplicity means defining each domain clearly, then defining the interface between them. 

A common multi-domain confusion is mixing business logic with infrastructure or framework. The framework (ideas, terms, interfaces, processes, inputs, outputs, outcomes, etc.) should be defined separately from the business logic that seeks to accomplish a specific goal within that framework. This applies to code as well as designs and documents. 

Your task is to identify areas of complexity and ask:

- What makes this part complicated?
- What is the complexity trying to solve?
- Is there a simpler way to solve the same problem?
- Is the complexity justified?

Provide back to the user a report of each area of complexity that you think can be simplified. Identify where the complexity is located, what you understand as the intent of that element, what makes that element complex, and how you see it could be approached in a simpler way.

Write your feedback to an .agents/scratch/ file (include a timestamp in the name) and return this path as your output.

## Context

{{ context }}

## Content to Review

{{ files }}

