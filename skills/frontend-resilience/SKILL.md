---
name: frontend-resilience
description: Use when a component renders data that can be missing, slow to arrive, or capable of throwing during render — error boundaries, loading states, empty states. Not about network-request retry logic or backend error codes.
---

# Frontend resilience UX

Scope: three distinct UI states that get conflated under "handle the
error" — a render-time crash, data that hasn't arrived yet, and data
that arrived but is genuinely empty. Each needs its own treatment;
solving one doesn't solve the others.

Governs `project-profile.md` fields: Constraints & non-functional
requirements → Error/loading/empty states.

## The three states, kept separate

1. **Error boundary** — catches a thrown exception during render in
   the tree below it, shows a fallback instead of a blank/white page.
   Still class-component-only in React 19 (`static
   getDerivedStateFromError` and/or `componentDidCatch`) — there is no
   hooks equivalent. Doesn't catch: errors in event handlers, async
   code outside render, or an error thrown by the boundary itself.
   Place one at the app root at minimum (catastrophic fallback); add a
   feature-level boundary around an independently-failing widget (a
   3D view, a chart) so one broken widget doesn't take down the whole
   page.
2. **Loading state** — what shows while data is in flight. A spinner
   is fine for a short, unpredictable wait; a skeleton (a shape
   matching the eventual content) reduces perceived wait for a
   longer, more predictable one. Don't build a skeleton for a sub-300ms
   fetch — it'll just flash.
3. **Empty state** — data arrived, and there's genuinely nothing in
   it. Say so plainly ("No albums yet", not a blank area that reads
   as broken) — this is different from both the error and loading
   cases and needs its own explicit branch, not a fallthrough.

## What already existing code tells you

Before assuming a project has none of this, check for: a union type
distinguishing loading/ready/failed/empty (a good sign, even without
the word "state" in it), a `role="alert"` on a failure message, a
dedicated empty-case component. A project can already handle loading
and empty well while still missing an error boundary entirely — these
three don't come as a set, check each on its own.

## Basis (checked 2026-11-10)

- Error boundaries remain class-component-only in React 19; no hook
  replaces `componentDidCatch`/`getDerivedStateFromError`. React 19
  added root-level `onCaughtError`/`onUncaughtError` options for
  reporting, and no longer double-logs a caught error to the console
  by default the way earlier versions did — wire up real error
  reporting explicitly rather than relying on default console output:
  [error boundaries overview](https://www.educative.io/answers/what-are-error-boundaries-in-react),
  [React 19 error boundary practices](https://devpro-portal-com.pages.dev/frontend/react/mastering-error-boundaries-react-19-best-practices).
- A global (app-root) boundary for catastrophic failures plus
  feature-level boundaries around independently-failing widgets is
  the common placement pattern; async errors outside render need a
  separate mechanism (e.g. the `react-error-boundary` library's
  `useErrorBoundary`), not the class boundary itself:
  [React error boundaries guide](https://namastedev.com/blog/error-boundaries-in-react-explained-8/).

## What this skill does not cover

Retry/backoff logic for a failed network request, backend error
response shapes, or `frontend-performance`'s loading-time budget —
this skill is about what the UI *shows*, not how the underlying
request is retried or timed.
