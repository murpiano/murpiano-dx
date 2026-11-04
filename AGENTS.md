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
