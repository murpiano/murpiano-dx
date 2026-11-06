# README rules

## Project kind

Pick one of `app`, `framework`, `npm-package`, `personal-brand` before editing.
A template section tagged `kind: ...` is required for the kinds it lists and
optional (delete it and its comment) for the rest; an untagged section is
required for every kind. Pass the chosen kind to the checker as
`--project-kind` so it enforces the right set instead of treating every tagged
section as optional.

## Order

Use the selected template's section names and order. Preserve its static text,
footer, and links; fill placeholders with verified project facts. Follow explicit
conditional instructions, including kind-based renames and drops. Existing README
structure does not override the template. Only an explicit user instruction
permits a departure. Preserve any existing agent entry-point notice as the first
line. Keep the footer's four links exactly as written, inside `<sub>` and
separated by ` · `, with the license link last. Do not omit the license link
unless the project is `personal-brand` and genuinely has no `LICENSE` file.
Keep unrelated development traces out of public product documentation.

## Identity

The distribution template's footer holds placeholders, not a real identity.
Real name, profile, and contact links belong only in the personal workspace's
own template override, never in this skill's `templates/README.md`.

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
Run `bash <murpiano-dx>/sync.sh check-readme <project> --project-kind <kind>`
before completion, commit, PR, or publication. Use `--template <path>` for an
explicitly selected template. Fix all failures and review factual accuracy separately.
