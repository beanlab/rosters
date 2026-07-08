# MyTeam weekly discussion

- Meeting transcription can be used to produce repo-local meeting minutes and later backlog updates.
- Audio workflows are technically manageable, but privacy, data handling, and ownership need explicit care.
- A proposed `myteam` workflow runner could reuse Codex `AppServer` to orchestrate multi-role conversations from YAML flows.
- The `myteam` development process is being refined around preserving the right information and quality gates at each step.
- The Discord bridge scale work was updated, though its relevance may shift with the Codex/AppServer workflow direction.

# Meeting transcription and audio workflows

The meeting opened with a discussion of recording student meetings and using automated transcription to create repo-local notes. The proposed workflow was to record meetings on a laptop, generate meeting notes, and keep a `Meeting Minutes` folder inside each repo so future prompts can refer to prior meetings and create backlog items from them.

A continuously recording audio workflow was discussed. The idea was to record chunks of audio, compact and organize them into Markdown files, and then keep recording subsequent chunks. Tyler Folkman's workflow was mentioned as an example: he reportedly wears a microphone, records his entire day, transcribes it into Markdown, and later data-izes it. It was unclear which transcription model he uses, though he may be using local speech-to-text models because he has recently posted about local models for several tasks.

For the current workflow, the practical decision was to let Codex manage the transcript because the cost is low enough to be worth it.

**Meeting Transcript Handling**

Context: The team wants reusable meeting notes and possibly backlog updates from student-meeting recordings.

Reasoning: Running transcription through Codex is inexpensive, and the resulting notes can live alongside project context in each repo.

Decision: Use Codex to manage meeting transcripts for now and store meeting minutes in project repos.

The group also discussed recording controls and audio size. Voice activation is possible, but the speaker was not concerned about raw audio size. Once audio has been transcribed, it could be recycled. Existing tools can perform speech/activity detection and truncate audio based on silence. One participant noted that a 24-hour high-quality audio file might be around 22 GB, and a lower-quality mono file could be around 2 GB. They had already tried speech-to-text in 18-minute chunks, found that too long, and used `ffmpeg` to split the audio before transcription.

Open items:

- Continue building the meeting transcription workflow.
- Use existing tools such as `ffmpeg` and speech/activity detection to split or trim audio when needed.
- The class schedule mentioned images tomorrow, audio Tuesday, and an ethics discussion on content ownership.

# Privacy and data handling for recordings

After the audio workflow discussion, the remaining concern was privacy: both for the person recording and for other people whose conversations may be captured. The group discussed the tension between recording everything for accountability and the reality that sending recordings or transcripts to an LLM can make the material no longer private.

Enterprise agreements were mentioned as one possible mitigation. The CES account and associated tokens are expected to have contractual data protections, assuming the vendors are good stewards and do not leak data. Local models were also discussed as a stronger privacy option: if transcription is done locally, such as with a local Qwen-based setup, the privacy infringement may be smaller.

The team distinguished raw recording from curated project notes. Checking irrelevant personal content into GitHub, such as someone talking about vacation, would be inappropriate. A better workflow would include human review and ownership of the transcription/minutes, keeping only the business-relevant material that participants are comfortable retaining.

**Curated Recording Notes**

Context: Full-day or meeting recordings can capture personal and irrelevant content, and transcripts may be sent to external systems.

Reasoning: Enterprise agreements and local models can reduce risk, but the content that is retained and shared still needs human judgment.

Decision: Treat curated, business-focused meeting minutes differently from raw recordings; use human review to keep only appropriate project-relevant material.

Open items:

- Continue discussing privacy expectations for recorded meetings.
- Consider when local transcription is preferable to sending audio or transcripts to hosted LLMs.
- Ensure repo-committed minutes omit irrelevant personal material.

# Codex AppServer workflow orchestration

The main technical discussion focused on reusing Codex internals for a `myteam` workflow runner. The speaker had inspected the Codex source and found that Codex currently has two execution models: the terminal runs everything in-process, while the app `Popen`-spawns a Python `AppServer`. The app front end communicates with that server over standard I/O using a JSON-RPC-style protocol. The server then spawns and manages Codex threads.

That infrastructure appears to make it possible to build another front end on top of `AppServer`, possibly without a UI or with a terminal UI, while still letting Codex manage the underlying threads. This led to a proposed executable, possibly named `cdx` or `myTeamStart`, though the preferred direction is for it to live in `myteam`. A user could run something like `myTeamStart dev`, pointing to a folder with `flow.yml` or `flow.yaml`; the executable would load that workflow and run it.

Backlog item created:

- [MyTeam workflow AppServer orchestration](backlog/myteam_workflow_appserver_orchestration.md)

The intended behavior is to spin up `AppServer`, let threads communicate with it as normal Codex channels, and listen through the UI to messages and conversations. When one conversation concludes, the workflow runner could close that thread and start a new one in the same UI. To the user, this would feel like one long Codex conversation, but under the hood Codex would shift roles and context at each workflow step. Closing a thread would be equivalent to closing a role; starting a new thread would begin the next role.

The proposed YAML design includes named states such as `plan`, with a role reference, inputs, and outputs. A role might be identified by a `myteam` role directory name such as `planning-interface`, which would resolve to something like `planning-interface/role.md`.

Outputs would be loosely structured. For example, a step could define an output key such as `plan_doc` with a description of what should be produced. That output block would be passed into the role's context so the agent knows what the user expects at completion. The agent would create the output and the infrastructure would hold it in memory. If output should be persisted, the agent could write a file and return the path. Outputs could also be text, such as summaries or bullet lists. The design resembles a structured output template, where keys define expected fields and values describe what belongs in them.

Inputs could be arbitrary JSON. Later steps could reference earlier outputs, such as passing the planning step's output into a development step. Possible reference mechanisms included `$.plan.output`, direct mappings such as `plan_doc: plan_doc`, JSON references, JSON Pointer, or JSONPath. The system would need to reference multiple steps, pull out pieces of prior output, linearize dependencies, and run steps in the needed order.

A participant asked whether the planning output would be the agent's own output or a file. The answer was that the agent would create it and the infrastructure would hold it in memory; explicit files can be written when needed. Another participant noted that structured output can be forced through JSON. The speaker agreed, while noting that a conversational thread does not naturally have a single exact output, so there is design work around whether the infrastructure can force structured output at thread conclusion.

Another open design question is how the system knows a step has ended. Semantic detection was mentioned, but the group noted that semantic stopping can be hard because a conversation may appear to pause or end while still being mid-conversation.

**Workflow Runner Architecture**

Context: `myteam` needs a way to orchestrate planning, development, testing, and review roles without building a large amount of new infrastructure.

Reasoning: Codex already has an `AppServer`, standard I/O communication, and thread management. Reusing that infrastructure would reduce maintenance burden and allow the workflow layer to stay small.

Decision: Explore a small Python workflow-management layer that uses Codex `AppServer` and existing communication channels rather than creating a separate thread-management system.

Tasks and open items:

- Anyone with time may work on the `AppServer` workflow runner idea.
- The speaker may work on it Friday during the two-hour window between cultures.
- Investigate whether `AppServer` allows full lifecycle control of threads.
- Explore how to conclude a thread and force or collect structured outputs.
- Decide how workflow-step completion should be detected.

# MyTeam development process and agent-engineering practices

The speaker mentioned a PR that others could review, but said it would probably be merged later in the day. The PR further refines the `myteam` development process.

The broader discussion then shifted to agent engineering. The speaker contrasted many existing harnesses, which define roles by domain such as front-end, back-end, or dev role, with the evolving `myteam` approach. The point was that what matters is not just how an agent plans, but how the process embodies information in the system.

The described `myteam` process starts by updating an interface document so it accurately captures the intended application change. The agent must ask questions and iterate to define what is new or changed. Next, the framework is changed so it can support the new features, while existing interface tests should not need to change. Those tests provide confidence that the framework refactor still supports the interface.

After the framework is ready, the team designs again: how should the interface change be implemented given the current framework state, and how should the implementation draw on the framework? Then tests are changed to match the new interface design, and finally implementation proceeds until those tests pass.

Review can be inserted throughout: reviewing the design doc, the conversation, missed questions, the framework refactor, whether the framework is over-encumbered, and whether the tests miss anything. The underlying theme was that the process should build and maintain the right information and quality at each step, rather than merely checking workflow boxes.

The speaker warned about a new form of technical debt from letting Codex run beyond the scale that a human can understand. Such systems may look impressive initially but eventually become difficult to evolve, hard to maintain, and boxed into poor design choices. The expected productivity improvement was framed as more like 2x to 5x rather than 10x or 100x, but still extremely valuable. The team needs to study people who can control the process well, understand what is happening, and preserve quality at every step, because poor quality may compound quickly.

**Agent Engineering Quality Principle**

Context: Agent harnesses can generate work quickly, but unchecked agent output can create systems that exceed human comprehension and accumulate hidden technical debt.

Reasoning: Durable production systems require humans to understand and guide the process, maintain design information, and enforce quality at each step.

Decision: Continue refining `myteam` around information flow, staged design/refactor/test/implementation steps, and repeated review rather than simple role checklists.

Tasks and open items:

- Review the current PR if desired.
- The speaker plans to merge the PR later in the day.
- Continue refining the `myteam` development process around interface docs, framework readiness, implementation design, test updates, implementation, and review.

# Discord bridge scale update

At the end of the meeting, a participant reported that they updated the Discord bridge scale. They were unsure how relevant it would remain because the meeting had just focused on Codex and server configuration. The response was that this is R&D, and the update was still welcome and interesting.

Tasks and open items:

- No new follow-up task was assigned for the Discord bridge during this meeting.
