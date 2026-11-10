---
name: frontend-security
description: Use when rendering any HTML that isn't written by hand into JSX — dangerouslySetInnerHTML, a markdown/rich-text renderer, a user-supplied URL used as href/src. Not about backend auth, secrets in commits (repo-cleanup), or CSP/headers at the infra layer.
---

# Frontend security

Scope: the one recurring frontend vulnerability class that's easy to
introduce by accident — XSS via raw-HTML injection — and the narrow
rule that prevents it. React escapes `{value}` in JSX by default; this
skill only applies once code steps outside that default.

Governs `project-profile.md` fields: Constraints & non-functional
requirements → Frontend rendering (XSS).

Backend/infra security is a separate, not-yet-written domain.

## The rule

1. **`dangerouslySetInnerHTML` is only safe when the HTML string is not
   derived from user input** — a static asset bundled at build time
   (an SVG imported with `?raw`, a hand-written constant) is fine as-is.
2. **The moment the HTML comes from anywhere a user (or another user,
   via shared/public content) could have influenced it** — a caption,
   a bio, a markdown field, anything stored and later rendered back —
   it goes through a sanitizer (DOMPurify is the standard choice)
   before it reaches `dangerouslySetInnerHTML`, every time, even if the
   source is "trusted" (your own backend, your own database) — the
   sanitization step is what makes it trusted, not where it came from.
3. **A URL used as `href`/`src` built from user input** needs the same
   caution — reject or strip a `javascript:` scheme; don't just trust
   whatever string arrives.
4. **Prefer not needing raw HTML at all** when there's a choice — a
   markdown renderer that parses to React elements (not to an HTML
   string) sidesteps the whole class of bug; reach for
   `dangerouslySetInnerHTML` only when nothing else fits (a CMS field
   that really is pre-rendered HTML, an inlined static SVG).

## What to check when you find a `dangerouslySetInnerHTML`

Trace the string back to its source, not just its type. A `string`
type tells you nothing about where the content came from — grep the
variable backward until you hit either a literal/import (safe) or a
prop/API response/form field (needs a sanitizer check).

## Basis (checked 2026-11-10)

- DOMPurify is the standard sanitizer recommended across current
  guides; sanitize even content from a "trusted" source, since the
  trust boundary is the render step, not the data's origin; naive
  string-replace filtering is bypassable and not a substitute:
  [safely using dangerouslySetInnerHTML](https://dev.to/maximlogunov/how-to-safely-use-dangerouslysetinnerhtml-in-react-applications-205f),
  [preventing XSS with dangerouslySetInnerHTML](https://dev.to/jam3/how-to-prevent-xss-attacks-when-using-dangerouslysetinnerhtml-in-react-1464).
- Secondary/community sources only for this check (no official React or
  DOMPurify documentation surfaced); re-verify DOMPurify's current
  version from its own release page rather than trusting a cited
  version number if that detail matters for an upgrade.

## What this skill does not cover

Secrets committed to a repo (`repo-cleanup`), backend input validation
or auth, CSP/security headers at the hosting/infra layer — none of
those have a framework skill yet; this one is scoped to the rendering
boundary inside frontend code.
