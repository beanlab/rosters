# MyTeam weekly discussion

- Discussed a meeting-transcription workflow that records audio, transcribes it to Markdown, and stores minutes in each repo.
- Considered privacy implications of always-on recording, especially around other people being present.
- Explored a Codex-based workflow runner built on the existing `AppServer`, with YAML-defined flows and role-based thread management.
- Reviewed the `myteam` development process: update the interface doc, refactor the framework, redesign, update tests, and implement with review at each step.
- Noted an updated Discord bridge scale intended to support Codex exact workflows.

# Meeting transcription workflow and privacy

Summary: The group discussed using the laptop to record meetings, transcribe them, and save meeting minutes in a `Meeting Minutes` folder in each repo. A continuous recording approach was described where audio is chunked, compacted, and organized into Markdown files. Speech-to-text chunking, speech detection, and truncating based on silence were discussed as ways to manage the audio.

Decisions: Use Codex to manage transcription for now, since the cost is low and the audio can be recycled after transcription.

Designs: A possible workflow was described that records audio in chunks, transcribes them into Markdown, and continues recording. Local transcription was mentioned as a possible privacy-preserving option.

Tasks and open items:
- Explore recording and transcription workflows that handle chunking and silence detection.
- Keep privacy in mind, especially when other people are being recorded and when transcripts are shared.

# Codex workflow runner and role-based threads

Summary: The discussion focused on the existing Codex architecture, where the terminal runs in-process and the app spawns `AppServer`, with the front end communicating over standard I/O. The proposal was to build a separate executable for `myteam` that can load a workflow folder containing `flow.yaml`, start `AppServer`, and manage threaded conversations as roles that can be closed and restarted in the same UI.

Decisions: Reuse the existing `AppServer` and communication channels rather than adding major new infrastructure. Keep the additional layer small, with a Python workflow-management layer handling step orchestration.

Designs: Proposed YAML workflow definitions with a name, a state such as `plan`, a role path like `planning-interface/role.md`, and explicit inputs and outputs. Outputs are structured expectations for the agent, while inputs can reference prior step outputs via JSON Pointer or JSONPath. The infrastructure would hold agent outputs in memory, with optional file output if needed. Thread-ending semantics were identified as an area to explore.

Tasks and open items:
- Build or explore a separate executable for `myteam` or `cdx` that wraps Codex workflows.
- Investigate thread lifecycle control and how to determine when a step has ended.
- Consider the Friday time slot to work on the workflow runner.

# myteam development process and quality control

Summary: The team discussed a development flow for `myteam` that focuses on preserving information at each stage. The proposed sequence is to update the interface doc through questions and iteration, refactor the framework to support the new interface, redesign implementation against the framework state, update tests to reflect the new design, and then implement until tests pass. Review can be applied at each stage.

Decisions: The process should emphasize how information is embodied in the system, not just whether the right boxes are checked. The framework and interface tests should remain in place during the refactor so they can validate the changes.

Designs: The discussion framed a likely source of future tech debt: systems that run beyond the scale a human can easily keep track of. The goal is to keep production systems within a range that human oversight can still manage, aiming for practical productivity gains rather than extreme automation.

Tasks and open items:
- Continue refining the `myteam` development process.
- Review the PR that was sent out and merge it later today.
- The updated Discord bridge scale should support the Codex exact workflows.
