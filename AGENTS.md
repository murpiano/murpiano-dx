# Agent instructions

This file is the agent entry point for `murpiano-dx`.

## Read order

1. Run `bash sync.sh start` once at the beginning of work.
2. Read only the skill that matches the task:
   - `skills/repo-init/SKILL.md` for project initialization;
   - `skills/repo-commit/SKILL.md` for branches, commits, and pull requests;
   - `skills/repo-readme/SKILL.md` for README and repository metadata;
   - `skills/repo-release/SKILL.md` for releases and CI.
   - `skills/repo-agent-data/SKILL.md` for moving existing agent files out of a project's published tree.
   - `skills/repo-cleanup/SKILL.md` for scanning or removing agent-development traces and secrets before publishing.
3. Read the relevant project data under `projects/` only when the task needs it.
4. Run the checks required by the selected skill.

## Project rules

- Use English for communication. Keep code, commands, paths, and technical identifiers unchanged.
- `skills/` is the source of truth for the workflow. Do not duplicate its full rules here.
- Do not publish, push, merge, or create releases unless the user explicitly asks for it.
- Preserve existing project memory. Move it only for an authorized migration; never discard it automatically.
- Do not add agent attribution to commits, pull requests, or product files.

After changing workflow rules or project memory, run `bash sync.sh end`.

## Maintaining this framework

After merging a change to `murpiano-dx` itself into `main`, refresh any already
provisioned local workspace with `MURPIANO_DX_DATA_DIR=<workspace> bash sync.sh update`,
run from this checkout. It force-updates the runtime files and `global/` templates;
`skills/` and `defaults/` stay additive (existing files there are never overwritten).

The optional `<workspace>/rules/personal-agent-rules.md` is the single source for a
user's own cross-agent instructions (language, tone, house rules). When present, its
content is merged identically into every connected agent's instruction file under its
own `<!-- >>> murpiano-dx-personal -->` markers by `agent_setup.py` (same mechanism as
the `murpiano-dx` block). Edit that one file and re-run `install.sh` (or `sync.sh update`
plus `install.sh`) to propagate it; do not hand-edit the generated markers in each agent's
file.

Two more optional, machine-portable files under `<workspace>/rules/` restore agent
settings on `install.sh`, the same way the instructions above restore agent content:
- `personal-claude-settings.json`: a JSON object merged into Claude Code's
  `settings.json` (e.g. `enabledPlugins`, `modelSettings`). Existing keys such as
  `hooks` and `permissions` are preserved; only the keys named here are added or
  overwritten.
- `personal-codex-config.toml`: raw TOML merged into Codex's `config.toml` under its
  own `# >>> murpiano-dx-settings` markers, alongside the rest of that file.
Secrets (API keys, the release token) never belong in either file or anywhere under
`rules/`; they are not part of what `install.sh` restores.
