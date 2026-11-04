---
name: repo-init
description: Initialize a project with murpiano-dx on request, offer a GitHub origin and Git linter, remember decisions, and resume setup.
---

# Project initialization

Run this skill only when the owner asks to initialize or repair a project. A normal
development task does not reinitialize the project.

1. From the project directory run `bash <murpiano-dx>/sync.sh init`.
2. If no origin exists, ask whether to create a GitHub repository, then ask for
   private or public visibility (default private). Only after approval run
   `gh repo create --private --source=. --remote=origin` or the approved `--public`
   equivalent, then repeat `init`. Record a declined offer in project notes;
   do not repeat it without a new request.
   Preserve an existing origin and report owner mismatches.
3. Read the [Kysaro](https://github.com/murpiano/kysaro) state. Check only reported problems for an already configured
   project. Do not repeat a saved decline without a new request.
4. If no decision exists, ask once whether to install [Kysaro](https://github.com/murpiano/kysaro), the Git linter. It validates
   Conventional Commits through commit-msg and commits/PRs through CI.
5. Save the decision with `sync.sh init --kysaro approved` or `declined`.
   These commands store state and do not download packages.
6. For `approved`, read [kysaro.md](kysaro.md), configure and verify the project,
   then run `sync.sh init --kysaro enabled`.
7. If setup fails, leave the approved state incomplete and report the exact step.
8. If existing tracked instructions or other agent metadata remain, report them.
   Use `repo-agent-data` when the owner asks to migrate them for publication.
   Local Git exclusions alone do not untrack already committed files.

## Completion

For projects without a license, follow `repo-readme`'s default MIT license setup
using `skills/repo-readme/templates/LICENSE`. Preserve existing licenses.

The project has a local Git repository, a preserved or approved origin, linked
project data, and a verified [Kysaro](https://github.com/murpiano/kysaro) installation when the owner approved it.
