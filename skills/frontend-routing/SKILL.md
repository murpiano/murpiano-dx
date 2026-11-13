---
name: frontend-routing
description: Use when deciding whether a frontend needs a router library at all, picking one when it does, or handling the accessibility/performance side-effects of a route change (focus, title, scroll, code-splitting). Not for a meta-framework's own built-in router (Next.js, Remix, Astro already decide this) or for in-component focus management unrelated to navigation (frontend-accessibility).
---

# Routing & navigation

Governs `project-profile.md` fields: Frontend → Routing / navigation.

## The decision: does this project need a router at all

A router earns its place when at least one of these is true — not by
default just because the app has more than one view:

- A view should be bookmarkable, shareable, or survive a page refresh
  at the same place the user was.
- The browser's own back/forward buttons need to do something
  meaningful (leave a sub-view, not leave the app).
- Views are numerous or deep enough that a URL-addressed structure
  keeps them organized better than a hand-rolled state machine would.

**Client-state only (no router library)** is correct, not a shortcut,
when none of those hold — a single interactive view with UI-state
"sections" (tabs, panels, an open/closed detail) that nobody needs to
link to directly. `my-world` is the worked example: one globe view,
navigation is which trip/album/photo is focused, modeled as plain state
(`src/state/archive-nav.ts`) — adding a router there would add a
dependency and a URL-sync layer for state nothing needs to bookmark.

## Default when a router is needed

- **A meta-framework already decided this** (Next.js, Remix, Astro) —
  use its own router; this skill's library choice below does not apply.
- **Plain SPA (Vite + React, no meta-framework): React Router**, in its
  library mode (not its full-stack/Remix-merged mode, which this
  framework doesn't default into). Reasoning: broadest ecosystem and
  the long incumbent, so documentation/examples/Stack Overflow coverage
  is deepest — the same "simplicity for a non-expert solo maintainer"
  reasoning `frontend-i18n` used for react-i18next over fancier
  alternatives. See `Basis` below for the tradeoff against TanStack
  Router.
- **TanStack Router is a stated non-default alternative**, not a
  framework default, for a project that specifically wants end-to-end
  TypeScript type safety across route params/search params and is
  willing to take on its smaller ecosystem and more limited SSR story
  for that.

## Route-change side effects (every router, including a meta-framework's own)

A route change is not just "swap the component" — four things need to
happen together, independent of which router library is in use:

1. **`document.title`** updates to describe the new view. Screen
   readers announce the title on navigation; a stale title is a real
   accessibility miss, not a cosmetic one.
2. **Focus moves to the new view's heading** (its `<h1>`, made
   programmatically focusable with `tabindex="-1"`) or to `<main>` —
   browsers reset focus to the top of the document on a real page load,
   but an SPA route swap doesn't do this for free; the app has to move
   focus itself. This is the navigation-specific case of
   `frontend-accessibility`'s general focus-management rule, not a
   separate concept — read that skill for in-component focus (dialogs,
   menus), this skill only for the moment a route changes.
3. **Scroll resets on forward navigation, restores on back/forward.**
   Set `history.scrollRestoration = 'manual'` and own it — the
   browser's automatic restoration does not reliably work across SPA
   route changes. Coordinate this with the focus move above so the two
   don't fight (moving focus to a heading shouldn't itself cause an
   unrelated scroll jump).
4. **Each route is its own code-split chunk** where the route's
   component is non-trivial — this is `frontend-performance`'s
   `lazy()` rule applied at the route boundary; a router that eagerly
   bundles every route defeats the point of having routes at all.

## Basis (checked 2026-11-13)

- React Router vs. TanStack Router, 2026: sources converge on "no single
  default" but agree on the shape of the tradeoff — React Router is the
  long-standing incumbent with the larger ecosystem, while TanStack
  Router's draw is end-to-end type safety for a TypeScript-first SPA at
  the cost of a smaller ecosystem and weaker SSR support:
  [TanStack Router vs React Router, 2026](https://betterstack.com/community/comparisons/tanstack-router-vs-react-router/),
  [TanStack Router guide, 2026](https://dev.to/stacknotice/tanstack-router-complete-guide-2026-type-safe-react-routing-a1c).
  A meta-framework (Next.js App Router, Remix) makes a separate router
  choice redundant — several sources note TanStack Router is redundant
  on top of Next.js.
- Route-change focus/title handling: the BBC GEL routing guidance and
  Helsinki's SPA accessibility notes agree browsers do not reset focus
  on an SPA route swap the way they do on a real page load, so the app
  must move focus to the new view's heading itself and update
  `document.title`, since screen readers announce the title on
  navigation:
  [BBC GEL — routing](https://bbc.github.io/gel/foundations/routing),
  [Helsinki Accessibility Model — SPA notes](https://saavutettavuusmalli.hel.fi/toteutus-ja-ohjelmistotestaus/single-page-applications-spas-notes-on-accessibility/),
  [web.dev — managed focus](https://web.dev/managed-focus).
- Scroll restoration: the browser's built-in mechanism generally does
  not work across SPA route changes; `history.scrollRestoration =
  'manual'` plus an app-owned per-route scroll position (reset on
  forward nav, restored on back/forward) is the common pattern:
  [Scroll restoration in SPAs](https://personal-doh.pages.dev/blogs/scroll-restoration-in-spas).
