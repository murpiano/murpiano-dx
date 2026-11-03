# {{PROJECT}}

Run `{{SYNC}} start` at the beginning of work to exchange workspace updates and
check project state. If a murpiano-dx SessionStart hook already reported sync,
use `{{SYNC}} start --local` to avoid a duplicate network exchange. Report sync errors.
Read task-specific rules from `{{ROOT}}/skills/` and editable overrides in
`{{DATA_ROOT}}/rules/`: Git — `repo-commit`, README and metadata — `repo-readme`,
releases and CI — `repo-release`. Resume setup through
`repo-init` only when requested; its state is `{{STORE}}/workflow.json`.

Project data is stored in `{{STORE}}`. Keep decisions, verification commands, and
current task state as focused notes in `.agents/`. If `{{STORE}}/memory/MEMORY.md`
exists, read its index and relevant notes before changes. Do not copy shared rules;
do not store secrets or temporary files in memory.
Save focused notes during work and before compaction. Run `{{SYNC}} end` before
finishing a task; the user does not need to run this manually. Supported session hooks
also exchange workspace changes on session start/end. There is no timer; offline
or interrupted exchanges retry on the next event or explicit sync.
Only the personal workspace is synchronized; project code needs explicit Git actions.
