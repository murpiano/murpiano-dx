---
name: repo-ci
description: Use when setting up or reviewing a project's general CI pipeline — provider choice, stage order, caching, and workflow-security basics. Not the release-triggering workflow specifically (repo-release, which is additive on top of this) or the pre-commit hook (repo-lint-format).
---

# CI/CD pipeline

Governs `project-profile.md` fields: Infrastructure & delivery →
CI/CD provider, CI pipeline stages.

Scope: the general-purpose pipeline that gates every PR and push — not
`repo-release`'s own release-cutting workflow, which runs *in addition
to* this one after it passes, never instead of it.

## Default provider: GitHub Actions

GitHub Actions — this framework already uses it for its own CI and
every project dogfooded so far (`my-world`, `copycat`) does too; it
needs no separate account/billing setup for a GitHub-hosted repo, which
matches this framework's general "least extra infrastructure for a
solo/small-team maintainer" bias. GitLab CI/CircleCI/Jenkins are stated
alternatives for a project already hosted elsewhere, not a default
swap.

## Stage order and structure

- **On every PR**: lint, typecheck, unit/component tests — independent
  checks run in parallel jobs where they don't depend on each other's
  output, each failing fast on its own. `repo-dependency-security`'s
  own `security` job (`npm audit`) runs alongside these the same way.
  E2E tests run as their own job, typically slower, allowed to run in
  parallel with the others rather than gating them.
- **Build** is its own step, gated on the above passing via `needs:` —
  a broken build must fail here, not surface later at deploy or release
  time.
- **Deploy** only runs after a push to `main` (or a release tag) — never
  on an arbitrary PR branch — and should sit behind a `concurrency`
  group keyed to the branch/environment so two overlapping deploys to
  the same target can't race each other.
- This is the same shape `my-world` and `copycat`'s own CI already use
  (`check`/`security`/`e2e` jobs on `pull_request`, a separate
  `deploy.yml`/`release.yml` triggered only on `main`) — not a new
  convention invented here, a description of what was already built
  and dogfooded under `repo-dependency-security` and `repo-release`.

## Caching and lockfile discipline

Use the language tooling's own built-in dependency cache (`setup-node`'s
`cache: npm`, or the equivalent for another ecosystem) keyed off the
lockfile — this is already what every dogfooded project's workflow
does. CI must never modify or regenerate the lockfile; it installs from
exactly what's committed (`npm ci`, not `npm install`).

## Workflow security basics

- Pin third-party Actions to a full commit SHA (or at minimum a
  maintained major-version tag), not a mutable branch reference.
- Set the workflow's `permissions:` to the minimum the job actually
  needs (read-only by default; `contents: write` etc. only where a job
  genuinely writes back to the repo).
- Scope secrets to the environment that needs them; don't expose a
  production deploy secret to a workflow that also runs on arbitrary
  PR branches.

## What this skill does not cover

The release-cutting workflow itself (version tags, release notes,
publishing) — `repo-release`. The pre-commit hook and linter/formatter
choice — `repo-lint-format`. The dependency-vulnerability gate —
`repo-dependency-security`.

## Basis (checked 2026-11-13)

- Running lint/typecheck/tests on every PR with build and deploy gated
  separately (deploy only after merge to main, concurrency-grouped) is
  the converging pattern across multiple 2026 GitHub Actions guides;
  pinning Actions to commit SHAs, least-privilege `permissions:`, and
  scoped secrets are recurring security recommendations, though none
  of the sources found were GitHub's own official docs — verify the
  specific syntax against GitHub's current Actions documentation before
  relying on any one guide's exact YAML:
  [GitHub Actions CI/CD for Node.js, 2026](https://dev.to/axiom_agent/github-actions-cicd-for-nodejs-the-complete-2026-guide-i79),
  [GitHub Actions best practices](https://devtoollab.com/blog/github-actions-best-practices).
