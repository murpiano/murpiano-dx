---
name: repo-commit
description: Follow murpiano-dx Git rules for task branches, Conventional Commits, project kysaro settings, pull requests, and merges.
---

# Git workflow

Use this skill for branches, commits, pull requests, and merges. Read only the
relevant section of [rules.md](rules.md). Project rules and `.kysaro/settings/`
take precedence.

## Workflow

1. Run the project sync check and inspect its local instructions.
2. Create a task branch from the current default branch. Use a short lowercase
   prefix such as `feat/`, `fix/`, `docs/`, `ci/`, or `refactor/`.
3. Make the smallest coherent change and run the project checks.
4. Create a Conventional Commit. Kysaro validates the exact project format.
5. Push the branch and open a PR with a useful title and body when requested.
6. Wait for required checks. Merge only when checks pass and the user authorizes it.

## Commit messages

Use the configured type and scope, keep the subject imperative and concise, and
keep body lines within the project limit. Do not mention agents or hidden workflow
details in commits or PRs.

## Validation

Run the project tests, `git diff --check`, and the local kysaro range check when
available. Never bypass a failing hook or CI check without an explicit decision.

## Done

The branch is clean, checks pass, the PR describes the user-visible result, and
merge status matches the user’s request.
