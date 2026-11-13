---
name: repo-commit
description: Follow murpiano-dx Git rules for task branches, Conventional Commits, project Git linter settings, pull requests, and merges.
---

# Git workflow

Governs `project-profile.md` fields: Git workflow → Branching model,
Commit convention, PR requirements, Merge strategy.

Use this skill for branches, commits, pull requests, and merges. Read only the
relevant section of [rules.md](rules.md). Project rules and `.kysaro/settings/`
take precedence.

**Default branching model: GitHub flow** — short-lived feature branches
cut from the current default branch, merged back (squash by default,
see `rules.md`) once checks pass, no separate long-lived `develop`
branch. This is what the workflow below already does; it was never
previously stated as a named default in its own right. Git flow (with
a `develop` branch and release branches) is a stated, non-default
alternative for a project with a real need for parallel release trains
— not a default swap.

## Workflow

1. Run the project sync check and inspect its local instructions.
2. Create a task branch from the current default branch. Use a short lowercase
   prefix such as `feat/`, `fix/`, `docs/`, `ci/`, or `refactor/`.
3. Make the smallest coherent change and run the project checks.
4. Create a Conventional Commit. [Kysaro](https://github.com/murpiano/kysaro) validates the exact project format.
5. Push the branch and open a PR with a useful title and body when requested.
6. Wait for required checks. Merge only when checks pass and the user authorizes it.
7. After a merge (or whenever a task branch's work is otherwise finished),
   ask the user whether to delete that specific branch — locally and on the
   remote. State which branch you mean; don't assume the answer carries to
   other branches, and don't delete without asking each time.

## Commit messages

Use the configured type and scope, keep the subject imperative and concise, and
keep body lines within the project limit. Do not mention agents or hidden workflow
details in commits or PRs.

## PR template and CODEOWNERS (team-size trigger, not a solo default)

A PR description template (`.github/PULL_REQUEST_TEMPLATE.md`) and a
`CODEOWNERS` file (auto-requesting review from the right people by path)
both solve a *coordination* problem — they earn nothing for a solo
maintainer who already knows what every PR is and who should review it
(themselves). Same build-trigger pattern as Docker or feature flags:

- **Solo**: skip both. A PR template asking "what changed and why" has
  no one else to read the answer; CODEOWNERS has no one else to route to.
- **Team**: add a PR template (what changed, how it was tested, linked
  issue per `repo-tracking`) once a second person starts reviewing PRs
  they didn't write — it's the thing that makes a review possible without
  a live walkthrough every time. Add `CODEOWNERS` once the codebase has
  more than one area with a distinct responsible person/team — it's not
  useful with one person who owns everything.

## Validation

Run the project tests, `git diff --check`, and the local [Kysaro](https://github.com/murpiano/kysaro) range check when
available. Never bypass a failing hook or CI check without an explicit decision.
When README changes, follow `repo-readme` and run
`bash <murpiano-dx>/sync.sh check-readme <project>` before commit, PR, or merge.
Fix all template failures; do not silently waive them.

## Done

The branch is clean, checks pass, the PR describes the user-visible result, and
merge status matches the user’s request.
