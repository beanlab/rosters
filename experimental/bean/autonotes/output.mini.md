# MyTeam weekly discussion

- Explored ways to record and transcribe meetings into Markdown, including local or Codex-assisted transcription.
- Discussed privacy concerns around always-on recording, shared transcripts, and what gets stored or checked in.
- Reflected on the Atonement and resurrection as one integrated event rather than separate stages.
- Reviewed a workflow runner concept built on Codex `AppServer` and a broader `myteam` development process for planning, implementation, testing, and review.

# Meeting transcription, audio recording, and privacy

The discussion started with a plan to record student meetings on a laptop, transcribe them, and store the notes in a `Meeting Minutes` folder inside each repo so future backlog items could reference them. A continuous-recording approach was described as another option: capture audio in chunks, compact it into Markdown, then continue recording. Tyler Folkman’s always-on transcription setup was mentioned as a possible model.

The group talked through practical details such as audio file size, whether to keep the audio after transcription, and how to split recordings into chunks for speech-to-text. Ideas mentioned included voice activation, silence-based truncation, and existing speech-detection tools.

Privacy was the main concern. The discussion covered the fact that recording other people can feel invasive, that anything sent to an LLM is not truly private, and that enterprise agreements or local models may reduce but do not eliminate the concern. There was also a comparison to how people reacted when Google read email for ad targeting, and a reminder that content chosen for check-in or review matters.

Open items: continue thinking about privacy and content ownership; the audio/image/ethics topics were mentioned as upcoming follow-up discussions.

# Atonement and resurrection discussion

A theological reflection was shared about Easter and the Atonement. The speaker argued that Christ’s suffering, crucifixion, and resurrection should be understood as one continuous and integrated act rather than two separate stages. In this framing, Gethsemane, the cross, and the tomb all matter together for spiritual salvation and resurrection.

The Old Testament sacrificial lamb was used as a symbol of surrogacy: the laying on of hands and the transfer of sins were described as pointing to Christ standing in humanity’s place. The discussion emphasized that Christ took upon himself the full burden of fallen human experience, including suffering, trauma, decay, and death, and then ascended back to the Father from the depths of that experience.

The response added that the death of Christ fulfills the circle begun by the Fall of Adam, and the speaker concluded that Christ answers not only the law of Moses but the broader laws of mortality, decay, entropy, and death.

# Codex workflow runner and AppServer concept

The conversation then shifted to Codex’s architecture. It was noted that the terminal experience runs in-process, while the app starts a Python `AppServer` subprocess and communicates over standard I/O using a JSON-RPC-style message flow. That existing infrastructure was seen as enough to support a different front end or a separate executable without much new infrastructure.

A new entrypoint was proposed, such as `cdx` or `myTeamStart`, ultimately living under `myteam`. It would point at a workflow folder, likely containing `flow.yaml`, for example `myTeamStart dev` loading the `dev` workflow. The runner would spin up `AppServer`, manage Codex threads, and let the UI close one thread and start another as roles change during a long conversation.

The YAML workflow shape was described in more detail: a flow would have a name and state such as `plan`, point to a role file like `planning-interface/role.md`, and define structured inputs and outputs. Outputs were described as templates for what the agent should produce, while inputs could reference prior step outputs using JSON pointers or JSONPath, letting later steps consume earlier artifacts. The outputs were said to live in memory unless explicitly written to disk.

A key open question was how to detect that a thread has ended, since semantic completion is imperfect. The speaker said this would require a UI that can interact with `AppServer` and manage thread lifecycle, but emphasized that the base Codex infrastructure already exists and the additional layer should stay small.

# `myteam` process, agent engineering, and quality

The final major theme was how `myteam` should evolve as an agent-engineering system. The speaker said the dev process has been refined and that the interface document should be updated first, with questions asked to ensure the description is accurate. After that, the framework should be refactored to support the new interface without changing the existing interface tests. Then the interface can be redesigned against the new framework, the tests adjusted to match the new design, and implementation completed until the tests pass. Review can be added at each stage.

The speaker argued that the important thing is not just which roles exist, but how information is embodied in the system. They also warned about a new kind of tech debt that appears when agents operate at a scale that exceeds human oversight. The expectation was not 10x or 100x gains, but more realistic 2x to 5x improvements that still matter a lot if quality stays high.

At the end, an update was shared that the Discord bridge scale had been adjusted and should now support Codex exact workflows.