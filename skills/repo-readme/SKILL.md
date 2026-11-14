---
name: repo-readme
description: Use when writing, reviewing, or updating a repository README, GitHub description, website, topics, or badges.
---

# Repository documentation

Governs `project-profile.md` fields: Identity → Project kind, License,
README & GitHub metadata.

Write for humans in clear English. Keep detailed agent instructions in `AGENTS.md`
and skills. Preserve an existing agent entry-point notice as the first README line;
template corrections must not remove it. Product documentation about AI is allowed.

## Required content

- what the project does and who it is for;
- installation and the smallest useful example;
- configuration and supported commands;
- tests, CI, limitations, and links to deeper documentation.

Use only facts confirmed by the repository. Do not invent features or guarantees.

## License

Not "pick one so GitHub stops showing a warning" — a real choice with
real consequences, same option-set-with-a-default treatment as any
other governed row.

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **MIT** | Shortest, most permissive, most widely understood — almost no friction for anyone to use the code, including commercially | No patent grant, no copyleft protection against someone closing off derivatives | **Default** — a project with nothing specific pushing toward a stronger license |
| **Apache 2.0** | Adds an explicit patent grant (protects users from a patent claim by a contributor) — matters for anything with real patent exposure | Longer, slightly more to read | A project substantial enough that patent protection genuinely matters (less relevant for a small personal tool) |
| **GPL / AGPL** (copyleft) | Forces derivatives to stay open source — protects against a company taking the code closed-source | Real adoption friction: many companies have policies against using copyleft-licensed code at all; AGPL specifically triggers on network use (a SaaS built on AGPL code must open its own source) | A deliberate stance that derivatives must stay open — a real, stated choice, not a default |
| **Proprietary / none (private repo)** | No license needed at all — the project is private/closed-source by design | Not applicable to a public repo meant to be reused | This framework's own project-profile "Visibility: private" rows, or a product (not a library/tool) with no intent to be reused by others |

**Default: MIT** for anything public, matching this skill's existing
behavior — create `LICENSE` from `templates/LICENSE`, replacing
`{{YEAR}}` with the current year and `{{COPYRIGHT_HOLDER}}` with the
verified project owner. Keep package license metadata consistent when
present. Preserve existing licenses; do not replace them without
explicit user instruction. A private repo (per the Identity →
Visibility row) needs no `LICENSE` file at all — don't add one
reflexively.

## GitHub metadata

Keep the description short and specific. Use a small set of relevant topics and
set the website only when it is real and maintained. Add a CI badge only when the
workflow exists, a Release badge only for a public repository with releases, and
a License badge only when `LICENSE` exists — the License badge lives in the top
badge row; never repeat a license link in the footer once it's there.

Read the user's `rules/readme.md`. Resolve each requested template with
`bash <murpiano-dx>/sync.sh template --kind readme` or `--kind description`,
then read the returned file. Templates live inside this skill in
`templates/README.md` and `templates/repository-description.md`. The personal
workspace's skill templates take precedence over the distribution's copies.
Editing those files is enough; no registration or special user phrase is needed.
An explicitly requested template for the current task takes precedence.
Use [rules.md](rules.md) for details. Never overwrite user templates during an update.
Explicit setup migrates old workspace-level `templates/` files into this skill;
until then, template lookup still honors the old personal paths.

## Project kind

Before editing, decide the project kind. The template's `kind: ...` tags (below)
are written for four kinds — `app`, `framework`, `npm-package`, `personal-brand`
— `project-profile.md`'s own row allows three more (`library`, `landing page`,
`internal tool`); map each to the closest of the four until it earns its own
distinct tagging:

- `library` → treat as **`npm-package`** for section purposes (Install/Usage
  sections required) even when it isn't actually published to npm — the shape
  ("other code depends on this") is the same regardless of registry.
- `landing page` → treat as **`personal-brand`** (a descriptive, non-code page)
  — same "no Install/API sections" shape, for a product/company instead of a
  person.
- `internal tool` → treat as **`app`** minus anything public-facing (skip the
  Release badge, skip public install instructions aimed at outside users) —
  the internal/external distinction affects *what's shown*, not the section
  shape itself.

Ask the user only if the repository does not make it obvious.

A section in the template is tagged `kind: ...` in the comment right after its
heading. Keep the section, following its rename note if any, only for the kinds
it lists; delete the heading and its comment entirely for a kind not listed. An
untagged section is universal — keep it for every kind. The checker enforces this
when given `--project-kind`; without it, every tagged section is treated as
optional, so always pass the kind once it is known.

## Template contract

The selected template is mandatory, not inspiration. Preserve its fixed section
names and order, static text, footer, and links. Replace placeholders with facts
verified in the repository. The existing README never overrides the template.
Apply conditional instructions in the template, such as using CLI instead of API,
or dropping a section for the chosen kind. Keep the footer exactly as written —
whatever links or badge the selected template's own footer actually has; the
distribution template's footer is three identity/contact links inside `<sub>`,
separated by ` · `, with no license link (the License badge, top row, already
covers that — don't duplicate it below). A personal workspace template may
replace the footer with something else entirely (e.g. an authorship-signature
badge instead of text links) — preserve whatever that override actually
contains, don't fall back to the distribution shape. Depart from the contract
only when the user explicitly requests the exception.
If the selected template differs from the user's stated template, resolve the
discrepancy before editing; do not silently substitute another template.

The distribution template in this skill ships with placeholder footer links
(`<Your name or handle>`, `<your-profile-url>`, ...). It never carries a real
identity — that binding belongs in the user's own `rules/readme.md`-adjacent
template override (`<workspace>/skills/repo-readme/templates/README.md`), which
`select_template` already prefers over this one. Do not hardcode a real name,
profile, or contact link into this skill's own `templates/README.md`; if the
user wants their identity bound by default, point them at their personal
workspace override instead of editing the distribution copy.

Before completing a README change or committing, opening a PR, or publishing it,
run `bash <murpiano-dx>/sync.sh check-readme <project> --project-kind <kind>` and
fix every failure. Use `--template <path>` when the user explicitly selected
another template. Also review fixed prose, commands, links, and conditional
sections manually: the checker validates structure, footer, and remaining
placeholders, not factual accuracy. Report the selected template path, the
chosen project kind, and the validation result. Never claim template compliance
when validation fails.
