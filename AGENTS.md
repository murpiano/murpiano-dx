# Agent instructions

This file is the agent entry point for `murpiano-dx`.

## Read order

1. Run `bash sync.sh start` once at the beginning of work.
2. Read only the skill that matches the task:
   - `skills/project-profile/SKILL.md` for the project's one standing
     pipeline table (`.agents/project-profile.md`) — read this whenever the
     user references "the pipeline," asks to walk/continue/resume it, or
     names an interaction mode (learning / co-pilot / autonomous) for a
     new or existing project; its own Interaction mode row (see
     `skills/DELEGATION-MODEL.md`) then governs how much you explain versus
     just do for every row that follows.
   - `skills/repo-init/SKILL.md` for project initialization;
   - `skills/repo-commit/SKILL.md` for branches, commits, and pull requests;
   - `skills/repo-readme/SKILL.md` for README and repository metadata;
   - `skills/repo-release/SKILL.md` for releases and CI.
   - `skills/repo-agent-data/SKILL.md` for moving existing agent files out of a project's published tree.
   - `skills/repo-cleanup/SKILL.md` for scanning or removing agent-development traces and secrets before publishing.
   - For anything else — starting a new application, or any domain-architecture
     question (frontend, and later backend, mobile, etc.) — start from
     `skills/GRAPH.md`, the framework's overview graph, rather than guessing
     which skill applies; it links onward to the right domain.
3. Read the relevant project data under `projects/` only when the task needs it.
4. Run the checks required by the selected skill.

## Project rules

- Use English for communication. Keep code, commands, paths, and technical identifiers unchanged.
- `skills/` is the source of truth for the workflow. Do not duplicate its full rules here.
- Do not publish, push, merge, or create releases unless the user explicitly asks for it.
- Preserve existing project memory. Move it only for an authorized migration; never discard it automatically.
- Do not add agent attribution to commits, pull requests, or product files.

After changing workflow rules or project memory, run `bash sync.sh end`.

## Delegation model

The user orchestrates; the agent does the work and owns keeping this
framework's knowledge current. Full rules: [skills/DELEGATION-MODEL.md](skills/DELEGATION-MODEL.md)
— state settled conventions instead of re-asking, guide new work step by
step, land every substantive discussion back into a skill before the task
ends, keep the concept → implementation → guided-setup chain explicit per
domain, and maintain `skills/GRAPH.md` mechanically as skills gain children.
Open framework-level work (not any one project's) lives in
[skills/BACKLOG.md](skills/BACKLOG.md) — check it before starting
unrelated new framework work, and run
[skills/framework-lint](skills/framework-lint/SKILL.md) after a
structural change.

## Maintaining this framework

After merging a change to `murpiano-dx` itself into `main`, refresh any already
provisioned local workspace with `MURPIANO_DX_DATA_DIR=<workspace> bash sync.sh update`,
run from this checkout. It force-updates the runtime files and `global/` templates;
`skills/` and `defaults/` stay additive (existing files there are never overwritten).

Any workspace — not only this maintainer checkout — is told about a newer release on
its own. Every `sync.sh start` compares the workspace's recorded version
(`<workspace>/.murpiano-dx-version`, written by `install.sh`/`sync.sh update`) against
the latest GitHub release of `murpiano/murpiano-dx`. When a newer one exists, the
command's own output carries a notice: the new version, a short summary of what
changed, a link to the full release notes, and the exact update command. On seeing
that notice, explain it to the user in your own words and ask whether to update before
continuing — never run the update without asking. The notice itself says how:
`bash sync.sh update --fetch <tag>` (or `--fetch latest`) clones that release from
GitHub into a temporary directory and updates the workspace from it — no local
`murpiano-dx` checkout is needed for this path.

Agents this framework talks to are listed in `global/agent-profiles.json` (command, label,
env var, default instructions directory, filename). It currently ships Codex and Claude
Code, the two verified here. An optional `<workspace>/rules/agent-profiles.json`, same
array shape, adds another agent (if it reads a plain-text global instructions file at
session start) or overrides a shipped entry by reusing its `command` value. Do not add a
speculative entry for an agent you have not verified actually reads a file at the path
given; when unsure, say so and leave it to the user to confirm and add.

The optional `<workspace>/rules/personal-agent-rules.md` is the single source for a
user's own cross-agent instructions (language, tone, house rules). When present, its
content is merged identically into every connected agent's instruction file under its
own `<!-- >>> murpiano-dx-personal -->` markers by `agent_setup.py` (same mechanism as
the `murpiano-dx` block). Edit that one file and re-run `install.sh` (or `sync.sh update`
plus `install.sh`) to propagate it; do not hand-edit the generated markers in each agent's
file.

The optional `<workspace>/rules/personal-claude-settings.json` restores Claude Code
settings on `install.sh` the same way: a JSON object deep-merged into the real
`settings.json` (e.g. `enabledPlugins`, `modelSettings`). Existing keys such as `hooks`
and `permissions` are preserved; only the keys named here are added or overwritten.

Codex's `config.toml` has no equivalent. It is TOML, not JSON or Markdown: a
marker-delimited text block would redefine tables already in the file (`[features]`,
`[mcp_servers...]`, ...), which TOML forbids — tried once, it produced a file that would
not parse. Restoring Codex settings (`model_reasoning_effort`, `[mcp_servers.context7]`,
...) after a fresh install stays a manual, documented step; do not reintroduce a
text-merge for this file without a real TOML-aware merge.

Secrets (API keys, the release token) never belong in `personal-claude-settings.json` or
anywhere under `rules/`; they are not part of what `install.sh` restores.

## Restoring on a new machine

Walk the user through this in order; do not skip a step just because it is manual.

1. Automatic: `bash install.sh --restore [url]` clones the personal workspace (the
   `rules/`, `global/`, memory, and project data described above) and runs `install.sh`
   on it. This alone restores the framework, the per-project instructions and
   pre-commit scan for every project the user reconnects, the shared
   `personal-agent-rules.md` content in every detected agent, and anything named in
   `personal-claude-settings.json`.
2. Manual, but the data survives: `rules/personal-codex-config-reference.toml`, if
   present, is never applied automatically (see above). Read it, read the new machine's
   real `~/.codex/config.toml`, and for each value the reference has that the real file
   is missing or differs on, propose the exact edit and apply it only after the user
   confirms — one value at a time, not a bulk paste.
3. Manual, nothing to restore from: the release token
   (`~/.config/murpiano-dx/release-token`) is a secret and is never stored anywhere this
   framework can read on restore. Ask whether the user wants releases working on this
   machine; if so, run `bash install.sh --release-token` and let them paste it there.
4. Manual: project repositories themselves. List the projects under
   `<workspace>/projects/` and ask the user which ones they want on this machine; each
   is a separate `git clone` of its own origin, then a normal connect (`sync.sh start`
   or `init`) picks its instructions and pre-commit scan back up.
5. If something the user expected to carry over did not — a setting, a file, a
   skill — do not silently drop it: say what did not transfer and why, and record a
   decision with the user about where it should live so the next restore covers it.
