---
name: frontend-seo
description: Use when a project has pages meant to be publicly indexed or shared (not just an authenticated app shell) — per-route meta tags, Open Graph, canonical URLs, structured data, and whether the rendering strategy even lets crawlers see them. Not for an app with no public, indexable pages.
---

# SEO / discoverability

Governs `project-profile.md` fields: Constraints & non-functional
requirements → SEO / discoverability (ask explicitly — see project-profile/SKILL.md).

Scope: pages meant to be found by a search engine or rendered as a rich
preview when shared (a chat app, Slack, social media). A project with
no such pages — an authenticated dashboard, an internal tool, an app
behind a login wall — records "no" here and that's a real, final
answer; search engines and link-preview bots never see an
authenticated view, so none of this skill applies to it.

## The rendering problem comes before the meta tags

Metadata injected into the DOM after the JavaScript bundle hydrates can
be invisible to a crawler or a link-unfurling bot that doesn't execute
JS (many don't, or time out before hydration finishes) — the tags must
exist in the HTML the server actually sends.

- **A meta-framework with SSR/SSG (Next.js, Remix, Astro)** is the
  right call at the `stack-selection` stage for any new project where
  SEO genuinely matters — this is that skill's decision, made before
  this one, not something to retrofit later.
- **An existing client-only SPA** can't cheaply become SSR after the
  fact. The realistic options are prerendering (generating static HTML
  snapshots of the indexable routes at build time) or, as a lesser
  fallback, `react-helmet-async`-style dynamic tag injection — accept
  that the fallback has real limits (some crawlers/bots won't wait for
  it) rather than treating it as equivalent to SSR.

## Per-route metadata, not one static block

Every indexable route gets its own title, meta description, canonical
URL, and Open Graph tags — a single static `<title>` that never changes
across routes is one of the most common real-world SEO mistakes. Keep
these in one metadata map/config keyed by route, derived from a single
base URL, rather than hand-writing tags in each route component — this
is the same "one source of truth" discipline `frontend-styling-concept`
applies to tokens, applied here to metadata. Ties into `frontend-
routing`'s own per-route responsibilities (this is the metadata
counterpart to that skill's title/focus/scroll handling on navigation).

- **Canonical**: exactly one per page, absolute URL, with trailing
  slashes/case normalized — a page that both sets its own canonical and
  inherits a stale one from a shared template produces two conflicting
  tags, which search engines resolve unpredictably.
- **Open Graph**: `og:title`, `og:description`, `og:image` (at least
  1200×630px), `og:url`, `og:type`.
- **Structured data (JSON-LD)**: add it for content types search
  engines can turn into rich results (articles, products, FAQs,
  breadcrumbs) — skip it for pages with nothing structured to say.
- **Multi-language** (`frontend-i18n`): add `hreflang` alternates
  pointing at each language's own URL for the same content, so search
  engines serve the right language version instead of guessing.

## Basis (checked 2026-11-13)

- Metadata must be present in the HTML a crawler receives, not injected
  only after hydration; per-route title/description/canonical/OG tags,
  with a single canonical per page and trailing-slash/case
  normalization, are the recurring, convergent recommendations across
  multiple 2026 React-SEO guides:
  [SEO best practices for modern web apps](https://hackernoon.com/seo-best-practices-for-modern-web-apps),
  [The complete technical SEO guide for React, 2026](https://dev.to/jaimin_umaraniya_c1fa0102/the-complete-technical-seo-guide-for-react-applications-2026-3h6h).
  Sources agree a meta-framework with SSR (Next.js App Router most
  commonly named) is the stronger fix for a new project; prerendering
  or `react-helmet-async`-style dynamic injection are the realistic
  options for an existing SPA, with real limits acknowledged rather
  than treated as equivalent to SSR.
