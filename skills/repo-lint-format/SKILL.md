---
name: repo-lint-format
description: Use when setting up or reviewing a project's linter, formatter, and pre-commit hook for them — tool choice per language and what runs locally (fast, staged-files-only) vs. in CI (the full, authoritative check). Not the commit-message/agent-trace hook (repo-cleanup) or the CI workflow structure itself (repo-ci).
---

# Linter, formatter, pre-commit hook

Governs `project-profile.md` fields: Git workflow → Linter(s), Formatter,
Type checking, Pre-commit hooks.

Scope: which tool checks/formats code, and where it runs — a fast,
staged-files-only pass locally (pre-commit) vs. the full, authoritative
check in CI (`repo-ci`). Distinct from `repo-cleanup`'s own hook, which
scans the *commit message* for agent traces, not the code.

## Default tools, by language

- **JavaScript/TypeScript**: ESLint (flat config, v9+) + Prettier, with
  `eslint-config-prettier` to turn off the ESLint formatting rules that
  would otherwise fight Prettier over the same thing.
- **Python**: Ruff for both lint and format — it replaces the older
  separate Black+flake8(+isort) stack with one faster tool covering the
  same ground; use it unless a project already has a working
  Black/flake8 setup predating this default (project-level override,
  not a reason to migrate unasked).
- **Go**: `gofmt` — there is no real alternative to default away from;
  the language ships its own formatter and the community treats
  deviation from it as the actual anti-pattern.

## The actual parameters, not just the tool name

Naming "ESLint + Prettier" settles nothing by itself — these are the
real, specific values this framework defaults to for each one, same
option-with-a-default treatment as everything else.

### Prettier: no `.prettierrc`, ship its own defaults as-is

**Default: don't create a config file at all.** Prettier's own shipped
defaults *are* the framework default — `semi: true`, `singleQuote:
false`, `trailingComma: "all"`, `printWidth: 80`, `tabWidth: 2`,
`arrowParens: "always"`, `bracketSpacing: true`, `endOfLine: "lf"`.
Prettier's own stated design goal is ending style arguments by having
as few knobs as possible; adding a `.prettierrc` to re-litigate them
one-by-one defeats that goal for most projects.

**Real, named alternative**: `singleQuote: true` is the one override
teams actually reach for often enough to be worth naming explicitly —
state it as a deliberate team preference in a `.prettierrc`, not a
silent drift from the default.

### ESLint: `typescript-eslint`'s `recommended-type-checked`, not bare `recommended`

**Default stack**, wired in `eslint.config.js` (see
[templates/eslint.config.js](templates/eslint.config.js)):

1. `typescript-eslint`'s **`recommended-type-checked`** config —
   `recommended` alone skips every rule that needs real type
   information (the rules that catch genuine bugs, not just style);
   type-checked linting is already the cost of using TypeScript at
   all, so there's no real reason to opt out of the rules that use it.
2. `eslint-plugin-react-hooks`'s recommended config, **only when the
   project has a React frontend** — `rules-of-hooks` and
   `exhaustive-deps` catch real runtime bugs (stale closures, hooks
   called conditionally), not style preferences; skip this step
   entirely for a backend-only TypeScript project.
3. `eslint-config-prettier` **last** in the config array, so it can
   turn off every ESLint rule that would otherwise fight Prettier over
   formatting — order matters, a later config overrides an earlier one.

**Real, named alternative**: `strict-type-checked` once a nontrivial
share of the team is genuinely proficient in TypeScript and wants the
stricter, more opinionated rule set — `typescript-eslint`'s own docs
recommend against it as a default for everyone.

### Ruff: keep its own default rule selection, don't narrow it

**Default: no `[tool.ruff.lint] select` override** — Ruff's own
default already enables the `F` (Pyflakes), `E`/`W` (pycodestyle), `B`
(flake8-bugbear, real bug patterns), `UP` (pyupgrade), and `RUF`
categories, deliberately excluding stylistic rules that would fight its
own formatter. Set `line-length = 88` (Black-compatible, Ruff's own
default) explicitly in `pyproject.toml` so it survives a reset, but
don't hand-pick a narrower rule set than Ruff already ships.

**Real, named alternative**: add `I` (import sorting, isort-equivalent)
to `select` explicitly — it's genuinely useful but not on by default,
so a project that wants it states that choice rather than assuming it.

### Go: `gofmt` has no parameters by design

Nothing to configure — this is the point of `gofmt`, not a gap in this
skill.

## Type checking: strict by default

For a TypeScript project — this framework's own default over plain
JavaScript (`stack-selection`) — turn on `strict: true` in
`tsconfig.json` from the start, not as a later tightening pass; a
codebase that starts loose and tries to turn strict mode on later
fights every existing `any` and implicit-null case at once, instead of
never having them. `mypy --strict` is the equivalent default for a
Python project that opts into static typing at all — a project with no
type annotations anywhere records "none" and that's a legitimate
answer, not a gap, since adding types retroactively is the project's
own larger decision, not this skill's to force.

## Pre-commit hook: fast and staged-files-only, not the authoritative gate

Husky (JS/TS) or `pre-commit` (Python) running **lint-staged** (or
`pre-commit`'s own staged-file filtering) is the default — lint with
autofix, then format, on changed files only. Keep this fast:

- **Don't run a full-project typecheck or the full test suite in
  pre-commit** — these are slow enough to make commits painful, and
  belong in CI (`repo-ci`), which is the actual authoritative gate
  anyway (a developer can `--no-verify` past a local hook; CI can't be
  skipped the same way). A project that deliberately wants stricter
  local gating despite the slowdown is a stated, explicit choice, not
  this skill's default.
- **Compose with `repo-cleanup`'s hook, never replace it.** That skill
  installs its own wrapping layer around a project's existing Git hook
  (calling the original hook first, then its own check) specifically so
  a later tool's setup doesn't silently delete it. Setting up Husky/
  `pre-commit` after `repo-cleanup` is already installed must preserve
  that wrapper the same way — check what's already in `.git/hooks/`
  (or `.husky/`) before overwriting a hook file.

## What this skill does not cover

The CI workflow that actually gates merges — `repo-ci`. The
agent-trace/secret-scanning hook — `repo-cleanup`. Commit message format
itself — `repo-commit`.

## Basis (checked 2026-11-13)

- ESLint flat config + Prettier + `eslint-config-prettier`, with
  Husky/lint-staged running autofix-then-format on staged files only,
  is the converging 2026 setup pattern across multiple written guides:
  [ESLint + Prettier for TypeScript, 2026](https://oneuptime.com/blog/post/2026-02-03-eslint-prettier-typescript/markdown),
  [ESLint, Prettier, Husky, Lint-Staged guide](https://builtin.com/articles/lint-staged-with-husky-pre-commit).
- Keeping heavier checks (full-project typecheck, full test suite) out
  of pre-commit and in CI instead is explicitly recommended for large
  repos specifically because pre-commit speed matters for developer
  experience and CI is the check that can't be bypassed — same sources
  as above.
- Prettier's own default values (`semi: true`, `singleQuote: false`,
  `trailingComma: "all"`, `printWidth: 80`, `tabWidth: 2`, `arrowParens:
  "always"`, `bracketSpacing: true`, `endOfLine: "lf"`), confirmed
  against the current options page, not a secondhand summary:
  [Prettier Options](https://prettier.io/docs/options).
- `typescript-eslint` recommends `recommended-type-checked` as the
  typed-linting baseline, `strict-type-checked` only once "a nontrivial
  percentage of the project's developers are highly proficient in
  TypeScript": [typescript-eslint — Shared Configs](https://typescript-eslint.io/users/configs),
  flat-config `projectService` wiring verified against the current
  typed-linting guide:
  [Linting with Type Information](https://typescript-eslint.io/getting-started/typed-linting).
- Ruff's own default rule selection already includes `F`, `E`/`W`,
  `B`, `UP`, and `RUF` (excluding stylistic rules that would fight its
  formatter) — confirmed against the current rules page, not assumed
  from an older Ruff version's narrower default:
  [Ruff rules — default rules](https://docs.astral.sh/ruff/rules/).
  `line-length = 88` is Ruff's own default, matching Black:
  [Ruff configuration](https://docs.astral.sh/ruff/configuration/).
- `eslint-plugin-react-hooks`'s flat-config `configs.flat.recommended`
  export and `eslint-config-prettier/flat`'s "last in the array" usage
  verified against each project's own README, then the exact template
  in `templates/eslint.config.js` was installed and run against a real
  `rules-of-hooks` violation (caught correctly) and a clean file (no
  false positive) before being written down here — not assumed to
  work from the docs alone:
  [eslint-plugin-react-hooks](https://github.com/facebook/react/tree/main/packages/eslint-plugin-react-hooks),
  [eslint-config-prettier](https://github.com/prettier/eslint-config-prettier).
