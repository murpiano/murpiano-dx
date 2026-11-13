---
name: repo-tracking
description: Use when deciding how a project tracks issues, bugs, and feature work — a dedicated tracker vs. a plain file, and how tightly it ties to commits/PRs. Not this framework's own BACKLOG.md pattern specifically (that's a worked example of the "no team" row below) or PR requirements themselves (repo-commit).
---

# Issue / task tracking

Governs `project-profile.md` fields: Git workflow → Issue / task tracking.

Scope: where work items (bugs, features, chores) live before and during
implementation, and how a commit/PR connects back to one. Distinct from
`repo-commit`'s own PR-requirements row (reviewers, required checks) —
this is about tracking *what* needs doing, not *how* a change gets merged.

## The real split: solo vs. team changes the right default

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **A plain backlog file in the repo** (this framework's own `BACKLOG.md` pattern) | Zero tooling, versioned with the code, diffable, no account/login friction | No status board, no assignment, no cross-repo view | **Default for solo work** — a single person doesn't need a board to know what they're doing; a file reviewed in the same PRs as the code it describes is strictly less overhead |
| **GitHub Issues (+ Projects)** | Free with the repo already hosted there, PRs auto-link and auto-close issues on merge, zero extra account for anyone already using GitHub | Weaker triage/workflow tooling than a dedicated tracker (no cycles, no velocity view) | A small team already on GitHub that needs visible, assignable items but not a heavyweight process |
| **Linear** | Fast, opinionated, built for software teams specifically — PRs auto-link to issues, free tier covers small teams | Per-seat cost past the free tier, another account/tool outside GitHub | A team that's outgrown GitHub Issues' triage/workflow limits but doesn't want Jira's complexity |
| **Jira** | Deepest configurability, audit trails, ITSM integration | Steepest setup/learning curve of these options; frequently cited as the wrong default for a small team specifically because of this | An enterprise context already standardized on it, or real custom-workflow/compliance needs justify the complexity |

**Default: a plain backlog file (solo) → GitHub Issues (small team on
GitHub) → Linear (team that's outgrown Issues' workflow).** Don't start
with Jira — every source on this is consistent that it's the wrong
default for anything smaller than an organization with existing Jira
process needs.

## Issue templates (GitHub Issues, team-size trigger)

Same reasoning as `repo-commit`'s PR-template/CODEOWNERS section: a
bug-report/feature-request issue template (`.github/ISSUE_TEMPLATE/`)
solves the problem of a *reporter who isn't the maintainer* writing a
usable report — it's wasted structure when the only person filing issues
is the same person who'd triage them. Skip it solo; add it once someone
other than the maintainer starts filing issues (a team, or real external
users/contributors on a public repo).

## Linking work to code

Regardless of which option: a commit or PR that implements a tracked
item should reference it (an issue number, a Linear ID in the branch
name or PR description) — not for ceremony, but so `git log`/PR history
answers "why was this done" without re-deriving it from the diff alone.
This framework's own `BACKLOG.md` convention (move an item to "Done"
naming the commit/skill that resolved it) is the backlog-file version of
the same link.

## What this skill does not cover

PR review requirements, merge strategy (`repo-commit`). This framework's
own `BACKLOG.md`/`skills/DELEGATION-MODEL.md` process for *this*
project's own development — that's murpiano-dx's own instance of the
"solo backlog file" default above, not a separate convention.

## Basis (checked 2026-11-13)

- GitHub Issues as the free, zero-friction default once a team exists,
  Linear as the speed/DX-focused upgrade once Issues' workflow tooling
  is outgrown, Jira as the wrong default for a small team specifically
  (configurability that matters at organization scale, not team scale):
  aggregated across multiple 2026 comparison posts, e.g.
  [Linear vs Jira for software development teams, 2026](https://dev.to/themoneyplaybooks/linear-vs-jira-for-software-development-teams-2026-an-honest-head-to-head-19j2).
  Pricing/tier details conflict slightly by source and change over time;
  verify current pricing before committing a team to one.
