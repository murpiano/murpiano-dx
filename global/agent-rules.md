## murpiano-dx projects

Run `{{SYNC}} start` once at the beginning of work: it is a short local check that
does not install packages or modify files. Initialize an uninitialized project
through `repo-init` only when its owner requests it. This skill offers a private
GitHub origin and kysaro installation, stores decisions, and resumes setup step by step.

The shared rules source is `{{ROOT}}/skills/`; editable user overrides are in
`{{DATA_ROOT}}/rules/`. Initialization — `repo-init`, branches,
commits and PRs — `repo-commit`, README and metadata — `repo-readme`, releases and CI —
`repo-release`. Read only the skill for the current task and the relevant rules section;
do not reread unchanged content in the same task. No special user phrase is required.
Project rules and kysaro settings take precedence over the generic caveman-commit format.
Kysaro checks commit messages through commit-msg and CI in each project; murpiano-dx
does not replace it. The agent owns change intent, tests, and process compliance.

Project data is `AGENTS.md`, `.agents/`, saved `memory/`, and `workflow.json`
initialization state at the path returned by start. Read only task-relevant notes;
use the memory index when available. After new decisions, update the note and run
`{{SYNC}} end`. Do not copy shared rules or repeat the kysaro offer after a saved
decline. Resume incomplete setup only when requested. If a symlink target is not
writable, report its exact path. Never automatically delete or rewrite old Claude
memory and settings.

Change README, metadata, and releases only when requested. Keep service data separate
from product code; do not add agent attribution to commits or PRs. Project code
commits, pushes, and publications are not automatic. `{{SYNC}} end` may commit and
push only the murpiano-dx workspace state to its configured private remote. Publishing
murpiano-dx itself follows the same repo-commit rules as project code.
