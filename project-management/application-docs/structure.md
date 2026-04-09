## Structure

For simple projects, the entire application design can reside in a single document.
For complex projects, the design should be broken up across many documents, 
and possibly organized within nested folders.

Start with a single document named `application-design.md`.
As the project grows and that document exceeds 400 lines, 
it is time to consider how the project documents can be refactored (see "Refactoring").

When multiple documents are needed, organize the information hierarchically
by interface theme. Give extra, careful thought to how the information should
be organized. Really think this through. Be critical of initial ideas
and refine them until they are sound.

In medium-sized projects, you might have all the documents in the `application-design/` folder,
with a document for each major UX component of the application.
As these documents themselves grow large, 
they might be decomposed into a subfolder of separate documents.

When more than a single file is used, the `application-design.md` document
should reference the other documents. It should serve as an overview and table-of-contents.
As subfolders are created, follow a similar pattern of an index document 
that references the child documents and is referenced by the parent document.

