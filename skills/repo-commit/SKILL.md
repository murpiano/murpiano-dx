---
name: repo-commit
description: Follow murpiano-dx Git rules for task branches, Conventional Commits, project Git linter settings, pull requests, and merges.
---

# Git workflow

Governs `project-profile.md` fields: Git workflow → Commit convention,
PR requirements, Merge strategy.

Use this skill for branches, commits, pull requests, and merges. Read only the
relevant section of [rules.md](rules.md). Project rules and `.kysaro/settings/`
take precedence.

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

## Validation

Run the project tests, `git diff --check`, and the local [Kysaro](https://github.com/murpiano/kysaro) range check when
available. Never bypass a failing hook or CI check without an explicit decision.
When README changes, follow `repo-readme` and run
`bash <murpiano-dx>/sync.sh check-readme <project>` before commit, PR, or merge.
Fix all template failures; do not silently waive them.

## Done

The branch is clean, checks pass, the PR describes the user-visible result, and
merge status matches the user’s request.
