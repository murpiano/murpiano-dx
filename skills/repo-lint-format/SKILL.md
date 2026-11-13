---
name: repo-lint-format
description: Use when setting up or reviewing a project's linter, formatter, and pre-commit hook for them — tool choice per language and what runs locally (fast, staged-files-only) vs. in CI (the full, authoritative check). Not the commit-message/agent-trace hook (repo-cleanup) or the CI workflow structure itself (repo-ci).
---

# Linter, formatter, pre-commit hook

Governs `project-profile.md` fields: Git workflow → Linter(s), Formatter,
Pre-commit hooks.

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
