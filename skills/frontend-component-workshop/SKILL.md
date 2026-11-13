---
name: frontend-component-workshop
description: Use when deciding whether a project needs an isolated component dev/documentation environment (Storybook or similar), setting one up, or adding visual regression testing to it. Not about which components are shared (frontend-design-system) or component file structure (frontend-component-structure).
---

# Component dev/doc workshop

Governs `project-profile.md` fields: Frontend → Component dev/doc workshop.

Scope: an isolated environment for developing and browsing components
outside the full app — each component rendered on its own, in every
state/variant, without needing the rest of the app running. This is
tooling *for* a design system (`frontend-design-system`), not a
replacement for it; setting one up with nothing shared to show in it is
installing a workshop with no bench.

## Build trigger, not a default-on tool

Don't add this before a project has at least one component promoted to
the shared tier (`frontend-design-system`'s own trigger). A single-page
app with zero shared components has nothing a workshop earns its
dependency weight for — browsing one component's states in the running
app is just as fast. Once a project has a handful of shared components
with real variant combinations worth seeing side by side, that's the
trigger to set this up, not a project's age or size on its own.

## Default tool: Storybook

Storybook over Ladle (or Histoire) once the trigger above is met —
reasoning matches this framework's other "mainstream over
lighter-but-sparser alternative" defaults (react-i18next, React
Router): Storybook's ecosystem (built-in accessibility checks, Figma
integration, 200+ addons, the largest body of docs/examples) outweighs
its slower cold start for a solo/small-team maintainer who benefits more
from broad coverage than from the fastest possible dev-server restart.
Ladle is a stated non-default alternative for a project that specifically
wants the fastest possible startup and is willing to wire up its own
visual-regression tool, since Ladle ships no addon API of its own. See
`Basis` below.

## Visual regression testing: optional, added when it earns its cost

Not part of the default setup — add it once the shared component count
is large enough that a visual regression could plausibly slip through
unnoticed between releases, not on day one of installing Storybook.
Chromatic is the Storybook-native, paid option (snapshot overage fees
apply); Lost Pixel is the open-source route and also works with Ladle.
Pick based on whether the project already has budget for a paid tool —
this is a project-level choice to record, not a framework default.

## Setup

1. Confirm the trigger above is actually met — at least one real shared
   component exists (`frontend-design-system`).
2. Install Storybook via its own CLI against the project's existing
   framework/bundler (it detects Vite/webpack setups automatically in
   most cases); point its stories config at the shared component tier's
   folder, not at every feature folder.
3. Write one story per shared component covering its real variants —
   not a story for every feature-local component; this stays scoped to
   what's actually promoted.
4. Record the choice in `project-profile.md` → Component dev/doc
   workshop.

## Basis (checked 2026-11-13)

- Storybook remains the dominant choice for design-system work in 2026
  comparisons, with its ecosystem (accessibility testing, Figma
  integration, Chromatic, 200+ addons) as the main draw; Ladle is the
  faster, lighter alternative with no addon API, suited to a project
  that wants a fast playground and will wire up its own visual
  regression tool:
  [Storybook vs. Ladle/Histoire, 2026](https://www.techinterview.org/post/3233475411/frontend-component-documentation-storybook-2026/),
  [Storybook vs. Ladle comparison](https://toolradar.com/compare/storybook-vs-ladle).
- Chromatic (Storybook-integrated, paid) vs. Lost Pixel (open-source,
  works with both Storybook and Ladle) as the two common visual
  regression routes:
  [Visual regression testing with Ladle](https://lost-pixel-landing.vercel.app/blog/post/visual-regression-testing-with-ladle).
