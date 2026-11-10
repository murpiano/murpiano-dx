---
name: frontend-performance
description: Use when adding a dependency, a heavy visual feature (map, 3D, chart, animation-heavy view), or a new route — anything that can grow the bundle or slow first render. Not about CI build speed or backend latency.
---

# Frontend performance

Scope: three distinct problems bundled under "performance" — bundle
size, the three Core Web Vitals metrics, and code-splitting — and
when each one actually needs attention. Read this before adding a
dependency or a heavy view, not after users complain.

Governs `project-profile.md` fields: Constraints & non-functional
requirements → Performance budget.

## The three things, kept separate

1. **Bundle size** — how much JS/CSS ships before the page can run.
   Every new dependency is a build-size question, not just a feature
   question: check its size (bundlephobia-style gut check, or the
   bundler's own output) before adding it, especially for something
   used in one place.
2. **Core Web Vitals** — the three metrics that measure "feels fast,"
   each judged independently (a page can fail overall even with two
   good metrics):
   - **LCP** (Largest Contentful Paint): good ≤ 2.5s. The largest
     above-the-fold element (often a hero image or heading) rendered
     fast.
   - **INP** (Interaction to Next Paint): good ≤ 200ms. The delay
     between a click/tap and the next visual update — a slow click
     handler or a huge re-render fails this even if the page loaded
     fast.
   - **CLS** (Cumulative Layout Shift): good ≤ 0.1. Content doesn't
     jump — reserve space for images/embeds before they load (a
     known `width`/`height` or `aspect-ratio`), don't inject content
     above existing content after load.
   Measured at the 75th percentile of real users, not a single
   lab run — a one-off Lighthouse score passing doesn't guarantee the
   75th-percentile real-world number is good.
3. **Code-splitting / lazy-loading** — don't ship a heavy feature
   (a map, a 3D view, a rich-text editor) in the main bundle if it
   isn't needed on first paint. Route-level splitting first (each
   route its own chunk); component-level `lazy()`/dynamic import for
   a heavy piece inside an otherwise-light route. If the component
   lives behind a `frontend-component-structure` barrel, check that
   skill's note on `INEFFECTIVE_DYNAMIC_IMPORT` before assuming the
   split actually happened — a bundler warning, not a guess, confirms
   it.

## Default budget

State a number once a project has a real concern (an initial-load JS
budget, e.g. "≤200KB gzipped for the main chunk" is a common starting
point) — don't leave `project-profile.md`'s Performance budget row as
silently blank forever; "not stated — no measured concern yet" is a
valid explicit value for a low-traffic/personal project, different
from never having thought about it.

## What already existing code tells you

Before assuming a project has no performance practice, check: is
there a heavy feature (map/3D/chart/video) that isn't lazy-loaded;
does any image lack explicit dimensions or `aspect-ratio`; has anyone
run a bundle-size report at all. A project with no measured budget
isn't necessarily a project with a real problem — check the actual
weight before writing a finding.

## Basis (checked 2026-11-10)

- Core Web Vitals thresholds (good/needs-improvement/poor), judged at
  the 75th percentile of real-user data, from the `web-vitals` npm
  library's own exported constants (the canonical source for these
  numbers): LCP [2500ms, 4000ms], INP [200ms, 500ms], CLS [0.1, 0.25].
  INP replaced FID as the responsiveness metric in March 2024:
  [web.dev: how Core Web Vitals thresholds were defined](https://web.dev/articles/defining-core-web-vitals-thresholds),
  [Sentry: web vitals concepts](https://docs.sentry.io/product/insights/web-vitals/web-vitals-concepts).

## What this skill does not cover

Backend/API latency, CI/build-pipeline speed, server-side rendering
strategy (no meta-framework skill exists yet) — this skill is scoped
to what ships to and runs in the browser.
