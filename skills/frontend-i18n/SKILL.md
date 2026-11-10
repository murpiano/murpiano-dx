---
name: frontend-i18n
description: Use when a project needs more than one UI language, or when deciding whether it does — translation library choice, string extraction, pluralization, locale-aware formatting. Not about RTL layout mechanics or translating backend/email content.
---

# Frontend internationalization (i18n)

Scope: multi-language UI text — whether a project needs it (see
`project-profile/SKILL.md`'s "ask explicitly" rule; don't infer "no"
from an absent library), and once it does, how to structure it.

Governs `project-profile.md` fields: Constraints & non-functional
requirements → i18n / l10n (ask explicitly — see project-profile/SKILL.md).

## Default library: react-i18next

Recommended default for a React project needing more than one
language. Reasoning, not just a name:

- **Simplest mental model**: wrap a string in `t('key')`; no
  compile step, no macro syntax to learn before writing the first
  translated string — matters for a team without a dedicated i18n
  specialist.
- **Built-in pluralization**: `t('photoCount', { count: n })` picks
  the right form from `photoCount_one`/`photoCount_other` (or more
  forms, for languages that need them) automatically — needed the
  moment a string like "1 photo" / "12 photos" exists, which is
  common, not an edge case.
- **Largest ecosystem**: most plugins, most Stack Overflow answers,
  most maintained framework integrations — lowers the cost of getting
  stuck.

**Lingui is the alternative when bundle size is the dominant
constraint** (compile-time extraction, reportedly the lightest
runtime of the common options) — accept its compile-step and
macro-based API in exchange for the smaller bundle. Don't default to
it; choose it deliberately when a project's `frontend-performance`
budget is tight enough that the difference matters.

## The shape of the work

1. **Extract every hardcoded UI string to a translation key** —
   `t('archive.closeButton')`, not `'Close'` inline. Namespace keys by
   feature (matching `frontend-component-structure`'s feature
   folders) so a translator (or a future you) can find where a string
   is used from its key alone.
2. **Pluralization and interpolation go through the library's own
   mechanism** (`t('tripCount', { count })`), never manual string
   concatenation (`count + ' trips'`) — concatenation breaks for any
   language with different word order or plural rules, not just
   English's simple case.
3. **Dates, numbers, and currency use the platform's own `Intl`
   APIs** (`Intl.DateTimeFormat`, `Intl.NumberFormat`), locale-aware
   by construction — not a library, not hand-written formatting, and
   not the translation library's job.
4. **Load one language's strings at a time**, not every supported
   language in the main bundle — this is `frontend-performance`'s
   code-splitting rule applied to translation files specifically; a
   project with 3+ languages feels this quickly, 2 languages less so
   but the pattern costs nothing to set up correctly from the start.
5. **Migrate an existing hardcoded-strings codebase incrementally**,
   per `DELEGATION-MODEL.md`'s migration-alias rule: one feature
   folder at a time, not a single pass touching every file; a
   half-migrated state (some features translated, some not) is a
   normal, trackable mid-point, not a broken state — note it in
   `BACKLOG.md` with what's done and what's left.

## What already existing code tells you

A project with every string as a plain literal in JSX (no `t()`
calls, no `locales/`/`i18n/` folder) has never had this — don't
assume "no i18n" was a considered decision; see `project-profile`'s
"ask explicitly" rule. Conversely, pluralized/interpolated strings
already written as manual concatenation (`` `${n} photos` ``) are a
signal of exactly what migrating them will need to become once i18n
is added — a release of that effort, not new work invented by this
skill.

## Basis (checked 2026-11-11)

- react-i18next is the most widely used React i18n library with the
  largest plugin ecosystem; react-intl (FormatJS) suits strict ICU
  MessageFormat compliance; Lingui is compile-time and the lightest
  runtime of the three, trading a build step and macro syntax for
  bundle size. Reported bundle-size figures for react-i18next/i18next
  disagree across sources (roughly 10–20KB gzip depending on what's
  measured) — re-check bundlephobia.com directly before treating a
  specific number as load-bearing:
  [React i18n libraries comparison, 2026](https://tolgee.io/blog/react-i18n-libraries-comparison),
  [react-intl vs react-i18next](https://www.locize.com/blog/react-intl-vs-react-i18next).

## What this skill does not cover

RTL layout mechanics (direction-aware CSS, logical properties) — not
yet needed by any connected project; backend/email/notification
content translation — a separate concern from UI strings, no skill
yet. `frontend-performance` owns the code-splitting mechanics this
skill's loading rule depends on; `frontend-component-structure` owns
the feature-folder boundaries this skill's key-namespacing follows.
