> Agent entry point: read [AGENTS.md](https://github.com/murpiano/murpiano-dx/blob/main/AGENTS.md) and stop reading this README. This page is for humans.

![murpiano Developer Experience](resources/logo.png)

# murpiano-dx

**One set of development rules for all your projects. One place for their agent data.**

murpiano-dx is a development assistant framework for working with coding agents.
Install it once and connect your projects. Their agents then use your shared rules
for Git, README files, descriptions, badges, CI, and releases.

Use it with any coding agent that can read local files and run shell commands.
The rules are plain Markdown files. No particular agent is required.

Project instructions, saved agent notes, decisions, and setup state live in your
personal murpiano-dx. Local links let agents use these files from each project.
The links are excluded from Git, so these files stay out of future project
commits. Your projects follow one style without publishing their internal work notes.
Existing projects may need the [agent-data migration](#already-have-agent-files-in-a-project) below first.

[![CI](https://github.com/murpiano/murpiano-dx/actions/workflows/ci.yml/badge.svg)](https://github.com/murpiano/murpiano-dx/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/murpiano/murpiano-dx?color=informational)](https://github.com/murpiano/murpiano-dx/releases/latest)

[How it works](#how-it-works) · [Run locally](#run-locally) · [CLI](#cli)

## What you can do

| Task | What murpiano-dx provides |
| --- | --- |
| Connect a project | Setup steps, a choice of private/public GitHub repository, and an offer to install the [Kysaro](https://github.com/murpiano/kysaro) Git linter |
| Keep agent data out of project commits | Central storage for instructions, notes, decisions, and setup state; local links are excluded from Git |
| Migrate an existing project | A preview and verified move of existing agent files into murpiano-dx, including files already tracked by Git |
| Work with Git | Rules for task branches, Conventional Commits, pull requests, and merges |
| Check Git conventions | The [Kysaro](https://github.com/murpiano/kysaro) Git linter, installed in each project to check commits and pull requests |
| Describe a project | Shared templates for README files, repository descriptions, and badges |
| Set up CI | Instructions for automatic tests and other checks on changes |
| Prepare a release | Rules for version numbers, tags, release notes, and release automation |

**The agent does the work.** murpiano-dx supplies the instructions and stores saved
context. The [Kysaro](https://github.com/murpiano/kysaro) Git linter checks the configured Git conventions. CI runs the project's
tests and checks on GitHub. A release publishes a named version after those
checks pass.

Saved context means files the agent writes, such as notes and decisions. It does
not mean every chat message or every tool call is captured automatically.

## How it works

You get a personal folder at `~/.murpiano-dx`. It holds the framework, your rules,
your templates, and a separate folder of saved agent data for each connected
project. You can edit these files directly.

After you connect a project, its agent reads the shared rules and keeps project
notes in this central folder. Connect another project, and it uses the same rules
with its own notes.

![murpiano-dx in the center, an optional GitHub backup above it, and two independent projects on either side. Each agent reads shared rules and saves its own project data in murpiano-dx.](resources/project-data-flow.svg)

The two lines for each project show two different things: **rules go to the
agent; saved notes and setup state live in murpiano-dx.** The project keeps its
own source code and Git history. Each project's notes stay in its own folder.

For example, ask an agent to write a README. It reads your shared README rules
and template. Ask it to commit a change, and it follows your Git rules. You do
not need to repeat those rules in every project or every chat.

## Run locally

Requirements: Linux or WSL, Bash, Git, Python 3.11+, and GitHub CLI (`gh`).
Node.js and npm are needed only if you install the [Kysaro](https://github.com/murpiano/kysaro) Git linter.
Sign in with `gh auth login` to use GitHub account defaults and backups.

Install from this repository:

```bash
git clone https://github.com/murpiano/murpiano-dx.git
cd murpiano-dx
bash install.sh
```

Setup asks for your Git identity and GitHub account, creates your personal
`~/.murpiano-dx` folder, and prepares instructions for your coding agent.
It asks whether to create a GitHub repository for your personal copy. Choose
private or public, or keep it local. You can also connect an existing repository.
The choice is saved; an existing origin is preserved. A public backup makes your
saved settings and project notes public too.

**One setup command connects the agents it finds.** Codex and Claude Code are
connected automatically when their command is on `PATH` or their configuration
folder exists. Both use the same murpiano-dx rules and project data.
Your existing instructions stay in place; setup updates only its own marked block.
Setup also adds session-start and session-end hooks without replacing your existing
hooks. In Codex, review and trust the new hooks once through `/hooks` or
Settings > Hooks. Disabled hooks and administrator restrictions are respected.

If you install another supported agent later, run `murpiano-dx setup` again.
Restart the agent session to load its updated instructions. Custom profile paths
set through `CODEX_HOME` or `CLAUDE_CONFIG_DIR` are respected.

The public repository contains the framework and default rules. Your personal
copy contains your settings and project notes. Its optional GitHub repository
is a backup of that personal copy.

### Connect your first project

Open the project with your coding agent and ask:

> Initialize this project with murpiano-dx.

For an agent without an automatic adapter, start with:

> Read ~/.murpiano-dx/AGENTS.md and initialize this project with murpiano-dx.

Connected projects have an `AGENTS.md` entry point. If your agent does not read
that filename automatically, tell it to read the file or add a reference to it
in the agent's own local instructions. Skill discovery and session hooks depend
on the agent; the shared rules and commands stay the same.

The agent connects its instructions and notes to your personal murpiano-dx.
If the project has no GitHub repository, it offers to create one with your choice
of private or public visibility.
It also asks whether to install the [Kysaro](https://github.com/murpiano/kysaro) Git linter. Existing files and saved setup decisions
are preserved.

For a new project, `AGENTS.md` and `.agents/` are stored in murpiano-dx from the
start. For an existing project, untracked copies move there during connection.
Already tracked files and other existing agent folders need the migration below.

Then work normally: “write the README”, “commit this change”, “set up CI”, or
“prepare a release”. The connected agent reads the relevant rules for the task.

### Already have agent files in a project?

Ask the agent:

> Move this project's existing agent files into murpiano-dx and keep them out of future commits.

The `repo-agent-data` skill previews the files it finds. It then copies the reviewed
data into your project's folder in murpiano-dx and checks that the copy matches.
It leaves working local links and removes previously tracked metadata from the
Git index. You can keep working with the agent as before.

For example, `AGENTS.md`, `.agents/`, and existing agent settings can live in murpiano-dx while
your code stays in the project. Other note folders can be added to the migration
explicitly. Code, README files, CI, and Git-linter settings stay in the project.

The migration stages removals for your next commit; it does not commit or push
them. Files in old commits remain in history. Moving files cannot erase previous
publications, and known-filename detection cannot find every possible note
embedded in code or documentation. The skill includes a review of current files.

### Saving and automatic backup

**You do not run sync commands by hand.** The agent saves notes during work.
Those files are immediately stored in your personal murpiano-dx folder.

- **Session opens:** the start hook saves pending local changes, gets remote
  updates, merges compatible changes, and sends anything left from the last session.
- **Session ends:** the end hook starts one sync to commit and send saved files.
  This exchange can finish after the client closes; there is no periodic worker.
- **Task finishes:** the agent saves its notes and requests an immediate sync too.
  This also works with agents that have no lifecycle-hook adapter.

There is no timer or once-a-minute synchronization. Without an origin, sync keeps
local commits only. Public and private origins both work. You can still commit and
push the personal folder with ordinary Git commands, or ask the agent to do it.

The agent decides when a session ends. In Codex, closing or switching a tab may
not trigger `SessionEnd` immediately. New hooks require one-time trust approval.
See [Codex lifecycle hooks](https://learn.chatgpt.com/docs/hooks) and
[Claude Code hooks](https://code.claude.com/docs/en/hooks#sessionend).
Forced termination or a WSL/PC shutdown can interrupt an exchange. Saved files
remain local and are retried at the next session start/end or explicit sync.
A merge conflict preserves both versions in Git until resolved; nothing is force-pushed.
Diagnostics are in `logs/session-sync.log`, excluded from the backup.

Only saved files are backed up, not unwritten chat messages. Project source code
is never committed or pushed by these hooks. Keep passwords and access tokens outside notes.

### Use your setup on another machine

Clone your personal copy and run its setup:

```bash
git clone git@github.com:OWNER/murpiano-dx-workspace.git ~/.murpiano-dx
~/.murpiano-dx/murpiano-dx setup
```

Your rules, templates, and saved project data come from that copy. Setup detects
the agents on the new machine and connects them without replacing your existing rules.
Reconnect local project folders with `murpiano-dx link`; restore project Git hooks
where needed.

If the command is already available, `murpiano-dx restore` combines cloning and
setup. It uses your signed-in GitHub account and the repository name
`murpiano-dx-workspace` (or the earlier `murpiano-dx-private` name). For a different name, pass its URL:

```bash
murpiano-dx restore git@github.com:OWNER/custom-name.git
```

### Development checks

The public repository includes tests and GitHub workflows for maintaining the
framework. These are excluded from the installed personal copy.

```bash
python3 -B -m unittest discover -s tests -v
bash -n install.sh sync.sh murpiano-dx skills/repo-release/release.sh
```

## Where things live

Edit the files in your personal folder:

```text
~/.murpiano-dx/
├── AGENTS.md                  entry point for any coding agent
├── rules/                     your shared Git, README, CI, and release rules
├── config/machine.json        saved Git identity and GitHub account
├── config/backup.json         saved GitHub backup choice
├── skills/                    each skill owns its instructions, rules, and templates
│   ├── repo-readme/templates/  README and repository-description templates
│   └── repo-release/templates/ release-notes and workflow templates
├── projects/OWNER/REPO/        separate data for each connected project
│   ├── workflow.json          setup decisions, including the Git linter
│   ├── files/
│   │   ├── AGENTS.md          project instructions
│   │   └── .agents/           saved project notes
│   └── memory/                existing saved memory, when present
└── logs/
```

Connected projects use local links to their saved agent files. Project-specific
rules and Git-linter settings take precedence over shared defaults.

### Your templates

Edit `skills/repo-readme/templates/README.md`,
`skills/repo-readme/templates/repository-description.md`, or
`skills/repo-release/templates/release-notes.md`. The next matching task uses your file automatically;
you do not register it or repeat its name to the agent. If that file is missing,
the framework uses its bundled default. To use an extra file for one task, tell
the agent which file to read.

Setup migrates the former workspace-level `templates/` files into the owning
skills without changing their contents. Lookup still honors the old paths until
you run setup. Conflicting old and new personal templates stop migration and keep
both files. Redundant defaults and the former README fallback are archived in
`.runtime-backup/skill-templates/`; they are not active templates.

Automatic release notes use `{{CHANGES}}` for generated changes and optionally
`{{VERSION}}` and `{{PREVIOUS_VERSION}}`. When setting up or updating releases,
the agent copies your template to the project's `.github/release-notes.md` so CI
can read it. Later edits to your personal template apply to the next setup/update;
already configured CI keeps its committed copy until you ask the agent to update it.

## CLI

Setup adds `murpiano-dx` to `~/.local/bin`. Run project commands from the project
folder, or pass its path.

| Command | Purpose |
| --- | --- |
| `murpiano-dx setup` | Set up your personal copy and automatically connect detected agents |
| `murpiano-dx restore [url]` | Clone an existing personal copy and run setup |
| `murpiano-dx init [path]` | Connect a project and report its setup state |
| `murpiano-dx start [path]` | Exchange workspace updates and show project state |
| `murpiano-dx end [path]` | Refresh project links and synchronize workspace data immediately |
| `murpiano-dx link` | Reconnect known projects under `~/projects` or `PROJECTS_DIR` |
| `murpiano-dx workspace` | Prepare the personal workspace and migrate legacy templates |
| `murpiano-dx template --kind readme` | Show the selected README template path |
| `murpiano-dx check-readme [path]` | Validate README headings, footer, and placeholders |

Agents use `init --kysaro approved`, `declined`, or `enabled` to record your
decision and verify the [Kysaro](https://github.com/murpiano/kysaro) Git linter setup. You do not need to manage these states by hand.

## Rough edges

- Projects need a GitHub origin owned by your configured account to connect.
- Your personal folder must remain available for project links to work.
- Only written files are synchronized; chats and unwritten thoughts are not captured.
- README validation checks structure, footer, and placeholders. Factual accuracy still needs review.

---

<sub>[Bogdan Trotsenko](https://github.com/murpiano) · [murpiano](https://github.com/murpiano) · [Telegram](https://t.me/murpiano) · [MIT](LICENSE)</sub>
