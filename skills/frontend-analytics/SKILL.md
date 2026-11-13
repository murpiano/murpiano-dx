---
name: frontend-analytics
description: Use when a project needs to measure usage, conversion, or retention — tool choice, the cookie-consent consequence of that choice, and event naming. Not for error/performance monitoring (frontend-monitoring) or feature-flag targeting data (frontend-feature-flags), even though some tools do all three.
---

# Analytics / product telemetry

Governs `project-profile.md` fields: Constraints & non-functional
requirements → Analytics / product telemetry (ask explicitly — see project-profile/SKILL.md).

Scope: a project that genuinely needs to know how it's being used.
"None" is a complete, correct answer for a project with no such
question to answer yet — don't add telemetry speculatively just because
it's cheap to drop in.

**Ask about this row explicitly, even when no analytics script is
detected.** No tracking snippet in the code today doesn't tell you
whether the owner ever considered needing usage data — put the
question to them directly per `project-profile/SKILL.md`'s "ask
explicitly" rule, and record a real, stated "no" as the confirmed
answer rather than inferring it from the absence of a script.

## Default: a privacy-first, cookie-less tool over Google Analytics

**Plausible** (or an equivalent cookie-less, no-personal-data tool —
Fathom is the other commonly cited one) is the default, not GA4.
Reasoning, not just a privacy preference: GA4 is cookie-based and needs
real consent-banner infrastructure under GDPR/ePrivacy — a whole UX and
legal surface (banner copy, a consent-state store, conditionally
loading the script) that a cookie-less tool skips entirely by not
collecting personal data or cross-site tracking in the first place.
For a solo/small-team project, that's a large amount of unrelated work
avoided for the same basic question ("how many people visited, from
where"). See `Basis` for the sourcing and its caveat.

- **Choose GA4 (or another full-featured tool) deliberately**, not by
  default, when a project genuinely needs what the privacy-first tools
  don't offer (deep funnels, audience segmentation, ads integration) —
  and build the consent-banner infrastructure that choice requires in
  the same piece of work, not as an afterthought once legal notices the
  gap.
- **PostHog is a stated alternative** when a project also wants product
  analytics *and* feature flags from one tool — see
  `frontend-feature-flags`'s own note on this overlap.
- The "no consent banner needed" framing for cookie-less tools is
  common industry practice, not a verified legal guarantee for every
  jurisdiction — say so plainly if a project's owner is relying on it,
  rather than presenting it as settled law.

## Event naming

Keep a single, consistent shape across every event name from the
start — `object_action` (`album_created`, `trip_shared`) is a common,
readable convention; whichever shape a project picks, apply it
uniformly, since a mix of naming styles makes the event list unsearchable
within a few dozen events. Don't instrument everything available "in
case it's useful" — an event earns its place by answering a real
question someone will actually look at.

## Basis (checked 2026-11-13)

- Plausible and Fathom are repeatedly described as avoiding
  cookie-consent requirements under GDPR/ePrivacy because they don't
  store personal data, anonymize IPs by default, and avoid cross-site
  tracking, while GA4 remains cookie-based and needs a consent banner;
  Plausible is also noted as EU-headquartered (Estonia) and open-source
  (AGPL), which several sources treat as the stronger fit specifically
  for GDPR-sensitive projects:
  [Google Analytics alternatives, 2026](https://dev.to/alanwest/google-analytics-alternatives-umami-vs-plausible-vs-fathom-in-2026-280i),
  [Migrating from Google Analytics, 2026](https://www.databuddy.cc/blog/migrating-from-google-analytics-best-alternatives-2026).
  Multiple sources flag the "no consent banner needed" conclusion as
  common practice, not an independently verified legal guarantee for
  every jurisdiction (the UK/EU's ePrivacy/PECR rules specifically
  called out as worth checking directly) — carried into this skill's
  own wording above rather than stated as settled fact.
