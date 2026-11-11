---
name: repo-dependency-security
description: Use when setting up or reviewing automated dependency-vulnerability scanning and update automation (npm audit, Dependabot, Renovate) for a project.
---

# Dependency security

Governs `project-profile.md` fields: Infrastructure & delivery →
Dependency scanning (ask explicitly — see project-profile/SKILL.md).

Two separate jobs, often confused: **alerting** on known vulnerabilities in
already-installed dependencies, and **updating** dependencies to pull fixes
in. Dependabot and Renovate both do some of each; neither is a full
vulnerability scanner on its own.

## Default setup

1. **Dependabot security alerts** — enable in repository settings
   (Settings → Code security → Dependabot alerts + Dependabot security
   updates). Zero-config, reads the GitHub Advisory Database against the
   lockfile, opens a PR per vulnerable dependency. This is the default:
   native to GitHub, nothing to maintain, enough for a solo/small-team
   project.
2. **`npm audit` gate in CI** — add a `security` job to the existing CI
   workflow that runs `npm audit --audit-level=high`. Default threshold is
   `high`: block the build on high/critical findings; leave moderate/low
   visible in the job log but non-blocking, to avoid the alert fatigue of
   failing CI on every low-severity transitive advisory (see `Basis`
   below). Run it on pull requests, not on every push to `main` — an
   unrelated push should not start failing because a new advisory was
   published after the last merge.
3. **A scheduled re-check** — Dependabot already scans continuously, but
   add (or confirm) a weekly scheduled CI run of the same `security` job
   so a newly published advisory against an already-installed dependency
   surfaces even with no new commits.

Renovate is the upgrade when Dependabot's config is genuinely too limited
(e.g. grouped updates across a monorepo, a Dependency Dashboard issue, more
scheduling control) — not a default swap. Switching is a real decision;
record it as one, don't do it unilaterally (`DELEGATION-MODEL.md`).

## Allowlisting a finding

Suppress by advisory ID, not by dependency path — a path-based ignore
silently stops matching the moment the vulnerable package moves to a
different place in the tree. Record *why* next to the suppression (ticket,
reason it doesn't apply) so it's not a silent, unexplained exception.

## Setup steps

1. Confirm a GitHub repository with Actions CI already running
   (`repo-release` → Tests and CI covers CI setup itself).
2. Enable Dependabot alerts + security updates in repo settings via
   `gh api` or ask the user to flip it in the UI if API access is
   insufficient.
3. Add the `security` job (`npm audit --audit-level=high`) to the CI
   workflow, triggered on `pull_request` plus a weekly `schedule`.
4. Record the choice in `project-profile.md` → Infrastructure & delivery →
   Dependency scanning.
5. Commit via `repo-commit`.

## Never

- Treat "Dependabot is on" as "vulnerabilities are handled" — alerts still
  need a human to merge or dismiss the PR; an ignored Dependabot PR queue
  is the same as no scanning.
- Suppress a finding by file path or by lowering `--audit-level` project-wide
  to make a single noisy advisory disappear.

## Done when

Dependabot alerts are on, the CI `security` job runs on PRs and on a
schedule with `--audit-level=high`, and `project-profile.md` records the
choice.

## Basis (checked 2026-11-12)

- [audit-ci](https://github.com/IBM/audit-ci) (IBM) — the common CI wrapper
  around `npm audit`/`yarn audit`/`pnpm audit`; its own examples treat
  moderate, high, and critical as blocking by default, and recommend
  allowlisting by advisory ID over by path, and running the audit
  immediately after checkout to limit exposure to a compromised
  `postinstall` script.
- [Oracle VBCS docs — Check for Security Vulnerabilities](https://docs.oracle.com/en/cloud/paas/visual-builder/visualbuilder-manage-development-process/check-security-vulnerabilities-your-projects-npm-packages-and-dependencies.html) —
  confirms `npm audit --audit-level` only changes the command's failure
  threshold, it does not filter the report; its own example fails only at
  moderate or higher.
- [Renovate vs. Dependabot, 2026 comparisons](https://www.aikido.dev/blog/dependabot-vs-renovate) —
  converging view across several 2026 write-ups: Dependabot is simpler to
  enable (near zero setup) but less configurable; Renovate is more capable
  (dependency dashboard, cross-platform, finer scheduling) but needs real
  setup work — consistent with treating Dependabot as the low-effort
  default and Renovate as an upgrade for a specific, stated need.
- Multiple 2026 sources agree neither Dependabot nor Renovate is a
  vulnerability scanner by itself — Dependabot's alerts are GitHub
  Advisory Database data tied to the lockfile; actual CVE scanning still
  wants `npm audit`/Snyk/OSV-Scanner. This framework's default (Dependabot
  alerts + an `npm audit` CI gate) already covers both halves without
  adding a third paid tool.
