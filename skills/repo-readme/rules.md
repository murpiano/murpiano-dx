# README rules

## Order

1. Agent pointer and project title.
2. One-sentence purpose and the main CI/Release badges.
3. Human overview, installation, usage, configuration, and project structure.
4. Development checks, limitations, and links.

## Accuracy

Derive commands, paths, versions, and supported features from the repository.
Keep examples runnable. Do not claim automation that is not configured.

## Metadata and badges

Use a concise GitHub description and only relevant topics. The CI badge requires a
working `.github/workflows/ci.yml`. The Release badge requires a public repository
and at least one published release. Remove stale badges.

## Review

Check links, headings, code fences, spelling, and `git diff --check`. Keep the
README focused on user value; put agent-only workflow in `AGENTS.md` and skills.
