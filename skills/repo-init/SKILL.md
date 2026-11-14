---
name: repo-init
description: Initialize a project with murpiano-dx on request, offer a GitHub origin and Git linter, remember decisions, and resume setup.
---

# Project initialization

Governs `project-profile.md` fields: Identity → Repository, Visibility.

Run this skill only when the owner asks to initialize or repair a project. A normal
development task does not reinitialize the project.

This skill only covers the Git/GitHub/linter lifecycle — it does not
decide what the project is built with. For a brand-new project with no
code yet, also run `stack-selection` (see `skills/GRAPH.md`) to decide
the stack; run both, in either order, for a from-scratch project — this
skill's repo/origin/Kysaro setup and `stack-selection`'s Step 0 (which
creates `.agents/project-profile.md`) are independent and neither
substitutes for the other.

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

## Adopting an existing project's own conventions

A project connected here is not always empty — it may already have a team,
a chosen stack, and established conventions that predate this framework.
Those conventions outrank this framework's own defaults for that project;
see `skills/DELEGATION-MODEL.md` → project-level overrides.

For a project with existing code (not a fresh scaffold), before applying
any framework default (e.g. a `frontend-styling-concept` implementation):

1. Scan for stack/convention signals already in the repository: dependency
   manifests (`package.json`, `pyproject.toml`, ...), lint/format configs
   (`.eslintrc*`, `.prettierrc*`, `pyproject.toml` tool sections, ...),
   existing styling approach (Tailwind config, `*.module.css` vs global
   SCSS, a CSS-in-JS library in dependencies), commit message conventions
   (recent `git log`, any commit-msg hook), and CI configuration.
2. Fill `skills/project-profile/templates/project-profile.md` from these
   signals, marking each detected row per its own "Provenance" section.
3. Report the findings and confirm them **in the table's own order** —
   section by section, row by row, top to bottom, exactly as the
   template lists them (Identity → Application type & platforms →
   Frontend → Backend → Infrastructure & delivery → Git workflow →
   Constraints & non-functional requirements; same discipline inside
   each section). This is not a stylistic preference: the template's
   row order is itself the dependency order (an architecture decision
   like "Primary platform" or a frontend's "UI framework" sits before
   the smaller choices that follow from it, like "Package manager" or
   "E2E tests") — asking out of order, or skipping around between
   sections and circling back, breaks that logic and makes two
   adoptions of similar projects feel arbitrarily different. Confirm a
   whole section before moving to the next; within a section, go row by
   row, never jumping ahead to a later row before the current one is
   settled. For a row that would otherwise be a framework default
   decision (e.g. "this repo already uses Tailwind — treat that as the
   project's styling implementation instead of the framework's CSS
   Modules default?"), do not silently assume a detected pattern is the
   team's deliberate choice — confirm it, in its place in the order,
   not pulled forward or deferred.
   For every field the profile template marks **"ask explicitly"** (e.g.
   i18n/l10n), ask the question directly even when nothing was detected —
   an absent library means "not built yet," not "the owner decided
   against it." Record their actual answer, including a real "no." An
   "ask explicitly" row is confirmed in its own place in the order, the
   same as any other row — it does not jump to the front or get batched
   separately just because it needs asking rather than confirming.
4. Save the confirmed profile as `.agents/project-profile.md` in this
   project's own data (under `{{STORE}}`, per `global/project-rules.md`),
   not in the framework's own skill files — see
   `skills/project-profile/SKILL.md`. A future session on this project
   reads this file first and applies it instead of asking again; a
   different project is unaffected.
5. If a detected convention has no matching framework skill at all (e.g.
   a styling implementation this framework hasn't written up yet), follow
   `skills/DELEGATION-MODEL.md`'s tiering — propose drafting that
   implementation skill from what this project already does, rather than
   overriding silently or ignoring it.

## Completion

For projects without a license, follow `repo-readme`'s default MIT license setup
using `skills/repo-readme/templates/LICENSE`. Preserve existing licenses.

For a project with no README yet, or one missing the badges/description/topics
`repo-readme` covers, run `repo-readme` itself before marking initialization
done — do not leave `project-profile.md`'s "README & GitHub metadata" row
unwritten just because the owner didn't ask for it by name. A project this
framework initializes should not end up with no description, no badges, and
no GitHub topics simply because nobody knew to ask for them.

The project has a local Git repository, a preserved or approved origin, linked
project data, and a verified [Kysaro](https://github.com/murpiano/kysaro) installation when the owner approved it.
