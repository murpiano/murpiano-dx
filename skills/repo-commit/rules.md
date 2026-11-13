# Git rules

## Branches

Create one short-lived branch per task from the current default branch. Use
`feat/`, `fix/`, `docs/`, `ci/`, `refactor/`, or `chore/` followed by a lowercase
hyphenated name. Never develop directly on `main`.

## Commits

Use Conventional Commits: `type(scope): imperative summary`. Keep commits small,
coherent, and buildable. Explain why in the body when the change is not obvious.
Run project checks and `git diff --check` before committing. [Kysaro](https://github.com/murpiano/kysaro) settings are
the final machine-readable authority.

## Pull requests

Use a concise title, explain the user-visible result, list verification, and link
the issue when one exists. Do not include agent traces or hidden instructions.
Wait for required CI and [Kysaro](https://github.com/murpiano/kysaro) checks before merging.

## Merge

Merge only after checks pass and the user authorizes publication. Keep `main`
buildable and delete merged task branches when the hosting platform allows it.

### Merge strategy

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Squash** | One commit per PR on `main` — a clean, readable history where each commit is a complete, reviewed unit of work; matches a task branch's own many small work-in-progress commits collapsing into the one thing that actually shipped | Loses the individual commits' own history (rarely needed once squashed, since the PR description already has the summary) | **Default** — matches this framework's own GitHub-flow default (short-lived task branches, one coherent change per PR) |
| **Merge commit** | Preserves every individual commit plus an explicit merge point | Noisier history — every task branch's work-in-progress commits stay visible on `main` forever | A team that specifically wants per-commit history preserved (e.g. commits are independently meaningful, not just WIP checkpoints) |
| **Rebase** | Linear history with no merge commits at all, individual commits preserved | Rewrites commit hashes — risky on a shared branch, requires force-push discipline | A team fully comfortable with rebase workflows and wanting a linear history without squashing away individual commits |

**Default: squash.** This is what the Workflow section above already
does in practice; stated here as the named default rather than only
implied by the steps.
