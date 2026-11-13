---
name: frontend-monitoring
description: Use when a project ships to real users and needs client-side errors/performance reported somewhere, not just caught and hidden — tool setup, source maps, and PII scrubbing. Not the error boundary/fallback UI itself (frontend-resilience already covers that) — this is what happens to the error after it's caught.
---

# Error / performance monitoring (frontend)

Governs `project-profile.md` fields: Infrastructure & delivery →
Monitoring / logging.

Scope: a caught client-side error, or a real performance number, has
nowhere to go until this exists — `frontend-resilience`'s error
boundary stops the page from going blank, but by itself it doesn't tell
anyone an error happened. "None" is a legitimate answer for a project
with no real user base yet (a prototype, a personal project the owner
is the only user of, like `my-world`) — set this up when a project
ships to users the owner isn't personally watching over someone's
shoulder, not before.

## Default: Sentry, wired into the error boundary already in place

Sentry's browser SDK is the default — report from the error boundary's
`componentDidCatch` (or an equivalent catch point for errors outside
render) rather than only showing the fallback UI and discarding the
error. This connects directly to `frontend-resilience`: that skill's
error boundary is the catch point, this skill is what happens to what
it catches.

**GlitchTip is a named, self-hosted, Sentry-SDK-compatible alternative**
— same client SDK and API shape, self-hosted instead of Sentry's SaaS.
Reach for it specifically when `repo-hosting`'s 152-ФЗ data-localization
row applies and error reports could carry personal data (a user ID,
an email in a stack trace) that shouldn't leave Russian-jurisdiction
infrastructure — not a general-purpose swap, a named option for that
specific trigger.

## Source maps never serve from the public build

Build with hidden source maps and upload them to Sentry (or whichever
tool) during CI, keyed to a release identifier (a git SHA is the common
choice) — the public JS bundle itself ships without maps. A source map
left on the public web hands anyone your original, unminified source;
"hidden" means generated but deliberately not deployed alongside the
bundle, not just omitted from a `<script>` reference.

## PII: minimize first, scrub second

- **Minimize what's captured at all** before relying on scrubbing to
  clean it up after — scrubbing has real limits (a stack trace or a URL
  can carry sensitive data in ways a scrub rule misses), so the first
  line of defense is not sending it in the first place.
- Use the `beforeSend` hook to redact fields before an event leaves the
  browser, with an **explicit allow-list of what's safe to send in
  plaintext** rather than trusting default masking alone.
- If session replay is enabled, apply its separate privacy-masking
  config too — replay captures the screen, which is a different
  surface than an error event and needs its own masking rules.

## Basis (checked 2026-11-13)

- GlitchTip is an open-source, self-hosted, Sentry-SDK-compatible error
  tracker — a stable project fact (its own documentation states SDK
  compatibility directly), not a ranking claim needing a freshness
  re-check the way a tool-popularity comparison does.
- Source maps left on the public build expose the full original source
  to anyone who fetches the production JS; the standard fix is hidden
  source maps uploaded to the monitoring tool during CI, keyed to a
  release/git SHA, with the maps themselves never deployed publicly —
  consistent across Sentry's own tooling behavior and third-party
  write-ups:
  [Wiring up source maps in Sentry, 2026](https://www.pulse.bot/devops/news/from-random-chunks-to-real-code-wiring-up-nextjs-source-maps-in-sentry-90404e87-9422-45e2-92d7-0880573956a8/).
- `beforeSend` is the standard client-side PII-scrubbing hook; an
  explicit allow-list (not just default masking) and separate
  masking for session replay are both named as best practice, with an
  explicit caution that scrubbing is not a complete guarantee —
  minimizing what's collected matters more than relying on scrub rules
  after the fact:
  [Removing PII from Sentry error monitoring](https://hashnode.com/posts/removing-personal-information-pii-from-sentry-error-monitoring-in-javascript/63b575b0d9fb57549be0a7c3).
