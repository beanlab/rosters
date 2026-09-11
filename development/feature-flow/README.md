# Generic feature flow

Run the workflow from the project being changed. Project context is optional:

```bash
myteam start /path/to/feature-flow/feature_flow.py
myteam start /path/to/feature-flow/feature_flow.py project.md
```

The project-information path is resolved from the caller's working directory. The file is rendered as Jinja, so it may use prompt helpers such as `read_file()` and `myteam_load()`; relative paths in that file resolve from the file's own directory.

## Project information to consider

A `project.md` file may describe or reference any context that agents should apply throughout the workflow. Include only details that differ from the workflow's generic guidance, such as:

- the project's purpose, users, maturity, and design priorities;
- authoritative specifications, architecture documents, and relevant source locations;
- public interfaces and compatibility or migration expectations;
- coding, dependency, security, and data-integrity constraints;
- test philosophy, commands, fixtures, and acceptable baseline failures;
- documentation locations, audiences, and conventions;
- versioning, changelog, commit, branch, and release conventions;
- generated artifacts or validation commands that must remain synchronized;
- project-specific skills or instructions that should be loaded.

The workflow provides `workflow_step` and `context_tags` while rendering the file. These allow large or specialized guidance to be included only when relevant:

```jinja
# About this project

{{ read_file('docs/project-overview.md') }}

{% if 'testing' in context_tags %}
## Testing

Run the suite with `uv run pytest`.
{% endif %}

{% if 'release' in context_tags %}
## Release conventions

The version is stored in `pyproject.toml`; release notes belong in `CHANGELOG.md`.
{% endif %}
```

A project file does not need to cover every item. Prefer concise references to authoritative documents over duplicating their contents.

## Project wrapper

A project may expose a no-argument workflow that supplies its context file automatically:

```python
"""
type: workflow
description: Develop a feature in this project.
usage: no arguments
"""
from pathlib import Path
import sys

SHARED_WORKFLOW_DIRECTORY = Path.home() / "path/to/shared/feature-flow"
sys.path.insert(0, str(SHARED_WORKFLOW_DIRECTORY))

from feature_flow import main


if __name__ == "__main__":
    main(Path(__file__).with_name("project.md"))
```

Only the wrapper and `project.md` are project-specific; the workflow logic remains shared.

## Unexpected test failures

The test-writing step distinguishes missing-feature failures from unrelated external or environmental failures. When an unrelated external issue prevents the full suite from passing, the workflow explains the issue and asks the user whether to continue with the known risk or pause. Implementation proceeds only with the user's explicit approval.
