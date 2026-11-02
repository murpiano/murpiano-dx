# {{PROJECT}}

Run `{{SYNC}} start` at the beginning of work for a short state check.
Read task-specific rules from `{{ROOT}}/skills/` and editable overrides in
`{{DATA_ROOT}}/rules/`: Git — `repo-commit`, README and metadata — `repo-readme`,
releases and CI — `repo-release`. Resume setup through
`repo-init` only when requested; its state is `{{STORE}}/workflow.json`.

Project data is stored in `{{STORE}}`. Keep decisions, verification commands, and
current task state as focused notes in `.agents/`. If `{{STORE}}/memory/MEMORY.md`
exists, read its index and relevant notes before changes. Do not copy shared rules;
do not store secrets or temporary files in memory.
