---
name: knowledge-refresh
description: Use to re-check an external best-practice justification already recorded in a skill's "Basis (checked YYYY-MM-DD)" section, or to sweep every skill for sections that have gone stale. Not for deciding a convention from scratch that has no Basis section yet — write that section first (see DELEGATION-MODEL.md), this skill only refreshes what already exists.
---

# Knowledge refresh

Governs no `project-profile.md` field — this is a meta-utility, like
`framework-lint`, not a domain.

Implements `skills/DELEGATION-MODEL.md` → "External justification
freshness." Read that section first; this skill is the mechanical
process for it, not a separate rule.

## Why this exists

A convention justified by "the industry does X" is only as good as the
last time someone actually checked that it still is X. Without a dated,
re-checkable record, that justification either never gets revisited (it
goes stale silently) or gets re-researched from scratch every time
(wasteful, and inconsistent between sessions). The `Basis` section plus
this skill is the middle path: check once, record the date, reuse until
the date says otherwise.

## Mode 1 — single topic

Triggered when a decision touches a topic that might already have a
recorded `Basis`, or the user names one directly.

1. Find the governing skill via `skills/GRAPH.md`'s routing (not a guess
   — the same routing used for any other domain question).
2. Run `python3 skills/knowledge-refresh/scripts/find_basis.py` (or just
   read the skill's `## Basis (checked ...)` section if it has one) to
   get its checked date.
3. **Dated within ~30 days** — apply the recorded convention directly.
   Tell the user what you're applying and its checked date; do not
   re-research.
4. **Missing, or older than ~30 days** — tell the user the Basis is
   missing/stale, then research it fresh (WebSearch or equivalent,
   current sources). Propose the finding, and only after the user
   confirms, write or update the skill's `## Basis (checked YYYY-MM-DD)`
   section with today's date, the sources, and a one-line summary of
   each — same shape as `frontend-styling-concept`'s.

## Mode 2 — full sweep

Triggered by an explicit request to refresh the framework's knowledge
base as a whole (e.g. "раз в месяц по всей базе"). Not run on a timer or
automatically — the user asks for it.

1. Run `python3 skills/knowledge-refresh/scripts/find_basis.py
   --stale-days 30` from the framework root. It lists every `Basis`
   section under `skills/`, split into stale and fresh, each with its
   age in days.
2. For every stale entry, go through Mode 1 steps 4 one at a time with
   the user — do not bulk-apply new findings across several skills
   without the user seeing each one. A sweep surfaces what needs
   re-checking; it does not silently rewrite the framework.
3. Report a short summary at the end: how many sections were fresh,
   how many were refreshed, how many the user declined to change.

## What this skill does not do

- It does not invent a `Basis` section for a convention that never had
  one — that is the moment of first deciding something from external
  research, which belongs to whatever domain skill is being written or
  edited (see `DELEGATION-MODEL.md`), not to this meta-utility.
- It does not change the convention itself without the user confirming
  the new finding — same rule as adopting a package
  (`DELEGATION-MODEL.md` → "never adopt one unilaterally").
- It is not a cron job. If the user wants an actually unattended,
  scheduled sweep later, that is a separate, explicit request (see the
  scheduling tools available to the agent) — do not wire one up
  speculatively.
