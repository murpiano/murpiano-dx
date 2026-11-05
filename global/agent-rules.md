## murpiano-dx projects

Run `{{SYNC}} start` once at the beginning of work. If a murpiano-dx SessionStart
hook has already reported synchronization, use `{{SYNC}} start --local` instead
to check project state without another network exchange. Otherwise start saves
pending local changes and exchanges updates with the workspace origin. It does not
install packages or initialize the connected project. Report pending sync errors.
Initialize projects through `repo-init` only on request. Offer a GitHub origin with
private/public visibility and [Kysaro](https://github.com/murpiano/kysaro), the Git linter;
save decisions and resume setup step by step.

The shared rules source is `{{ROOT}}/skills/`; editable user overrides are in
`{{DATA_ROOT}}/rules/`. Initialization — `repo-init`, branches,
commits and PRs — `repo-commit`, README and metadata — `repo-readme`, releases and CI —
`repo-release`. For requested migration of existing agent files out of a project's
published tree, use `repo-agent-data`; to scan or clean agent-development traces and
secrets before publishing, use `repo-cleanup` — its pre-commit scan is installed
automatically for a tracked project. Read only the skill for the current task and the relevant rules section;
do not reread unchanged content in the same task. No special user phrase is required.
Project rules and [Kysaro](https://github.com/murpiano/kysaro) settings take precedence over the generic caveman-commit format.
[Kysaro](https://github.com/murpiano/kysaro) is the Git linter. It checks commit messages through commit-msg and CI in each project; murpiano-dx
does not replace it. The agent owns change intent, tests, and process compliance.

Project data is `AGENTS.md`, `.agents/`, saved `memory/`, and `workflow.json`
initialization state at the path returned by start. Read only task-relevant notes;
use the memory index when available. Save focused notes as decisions happen, before
context compaction, and before ending a task. Run `{{SYNC}} end` after a completed
task for immediate sync; do not ask the user to run it. Supported session hooks also
synchronize at session start and end; there is no timer. Offline or interrupted
exchanges retry at the next session event or explicit sync. Both sides are kept on
merge conflicts; report conflicts for resolution. Never claim chats
or unwritten thoughts are captured. Do not copy shared rules or repeat the
[Kysaro](https://github.com/murpiano/kysaro) offer after a saved
decline. Resume incomplete setup only when requested. If a symlink target is not
writable, report its exact path. Never automatically delete or rewrite existing
memory and settings.

Change README, metadata, and releases only when requested. Keep service data separate
from product code; do not add agent attribution to commits or PRs. Project code
commits, pushes, and publications are not automatic. `{{SYNC}} end` may commit and
push only the murpiano-dx workspace state to its configured origin, private or public.
Do not put passwords or access tokens in notes. Publishing
murpiano-dx itself follows the same repo-commit rules as project code.
The user can also commit/push the personal workspace with ordinary Git commands
or ask an agent to do so. Hooks never replace user hooks or bypass their trust review.

When you and the user agree on a lasting cross-agent preference during a session —
language, tone, a house rule, anything meant to hold regardless of which agent is
running — write it into `{{DATA_ROOT}}/rules/personal-agent-rules.md` yourself (create
the file if it does not exist yet) and run `bash {{ROOT}}/install.sh` to merge it into
every connected agent's instructions. Do not just remember it for this session or
assume another agent will pick it up on its own; nothing currently prompts you to do
this, so do it without being asked. Propose the exact text and the command first if the
preference is still being worked out, but once it is settled, do not leave it
unrecorded.
