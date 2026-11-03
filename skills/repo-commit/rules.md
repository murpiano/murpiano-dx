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
