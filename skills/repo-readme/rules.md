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
line. Keep the footer exactly as written in the selected template — the
distribution template's footer is three identity/contact links inside `<sub>`,
separated by ` · `; the License badge lives in the top badge row instead, so
the footer never repeats a license link. A personal workspace override may
replace the footer with something else entirely (e.g. an authorship badge) —
preserve that shape, don't fall back to the distribution one.
Keep unrelated development traces out of public product documentation.

## Identity

The distribution template's footer holds placeholders, not a real identity.
Real name, profile, and contact links belong only in the personal workspace's
own template override, never in this skill's `templates/README.md`.

## Accuracy

Derive commands, paths, versions, and supported features from the repository.
Keep examples runnable. Do not claim automation that is not configured.

## Metadata and badges

The GitHub description states user value or primary workflow, in the template's
own words (`templates/repository-description.md`) — never a stack/library listing;
that belongs in topics, not restated in prose. GitHub always displays topics
alphabetically regardless of the order they're added in — don't try to order
them; pick a small, relevant mix of what it does (e.g. `clipboard-manager`,
`travel`) and what it's built with (language, framework, notable library,
platform/OS if relevant), only topics a user would actually search by. The CI
badge requires a working `.github/workflows/ci.yml`. The Release badge requires
a public repository and at least one published release. The License badge
requires a `LICENSE` file; it belongs in the top badge row, never the footer.
Remove stale badges.

## Review

Check links, headings, code fences, spelling, and `git diff --check`. Keep the
README focused on user value; put agent-only workflow in `AGENTS.md` and skills.
Run `bash <murpiano-dx>/sync.sh check-readme <project> --project-kind <kind>`
before completion, commit, PR, or publication. Use `--template <path>` for an
explicitly selected template. Fix all failures and review factual accuracy separately.
