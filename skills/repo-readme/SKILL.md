---
name: repo-readme
description: Use when writing, reviewing, or updating a repository README, GitHub description, website, topics, or badges.
---

# Repository documentation

Write for humans in clear English. Keep the agent pointer at the top of README:
read `AGENTS.md` and stop reading the page. Put images after that pointer.

## Required content

- what the project does and who it is for;
- installation and the smallest useful example;
- configuration and supported commands;
- tests, CI, limitations, and links to deeper documentation.

Use only facts confirmed by the repository. Do not invent features or guarantees.

## GitHub metadata

Keep the description short and specific. Use a small set of relevant topics and
set the website only when it is real and maintained. Add a CI badge only when the
workflow exists and a Release badge only for a public repository with releases.

Read the user's `rules/readme.md`. Resolve each requested template with
`bash <murpiano-dx>/sync.sh template --kind readme` or `--kind description`,
then read the returned file. The user's `templates/README.md` and
`templates/repository-description.md` take precedence over bundled defaults.
Editing those files is enough; no registration or special user phrase is needed.
An explicitly requested template for the current task takes precedence.
Use [rules.md](rules.md) for details and [template.md](template.md) only if neither
a user template nor a default template is available. Never overwrite user templates.
