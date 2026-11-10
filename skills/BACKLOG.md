# Framework backlog

Open items for the framework itself (not any one project). Referenced
from `skills/DELEGATION-MODEL.md`. Move an item here instead of letting
it live only in a conversation; remove it once it's actually done
(mention the skill/file that resolved it, don't just delete silently).

- **Backend domain** — do not pre-build; start it (concept →
  implementation → setup, per `DELEGATION-MODEL.md`) only once a real
  backend project is connected or created.
- **Team review process for framework changes.** Right now any change to
  `skills/`/`DELEGATION-MODEL.md`/etc. is just agreed in conversation and
  written. Fine solo; for a team sharing this framework, decide whether
  framework-structure changes need a review step (PR-style) before they
  apply to everyone's sessions.
- **Concurrent edits to one project's `project-profile.md`.** Two
  sessions (or two people) editing the same project's profile/decisions
  at once — `sync.sh`'s existing merge-conflict handling (both sides
  kept, conflict reported) applies at the file level, but there's no
  profile-specific guidance yet (e.g. which section is safe to edit
  concurrently).

## Done

- Cross-platform styling concept + web implementation + guided setup
  (`frontend-styling-concept`, `frontend-web-styles`,
  `frontend-project-setup`).
- Stack-selection entry point (`stack-selection`).
- Project profile table + per-field decision records
  (`project-profile`).
- Delegation model, including the graph-trigger rule
  (`DELEGATION-MODEL.md`).
- Skill revision/retirement rule (`DELEGATION-MODEL.md`).
- Framework self-lint (`framework-lint`).
- External justification freshness rule + knowledge refresh
  (`DELEGATION-MODEL.md`, `knowledge-refresh`).
- Token naming convention: semantic by default, 8px-base/4px-sub-grid
  spacing scale, with a dated external `Basis`
  (`frontend-styling-concept`) — closes part of the "frontend domain is
  not finished" item above (naming conventions).
- Dogfooded the framework end to end on `my-world`: `repo-init`
  adoption flow, `project-profile.md` filled, and a full SCSS+BEM →
  CSS Modules migration (every `src/features/**/*.scss` and the
  `src/styles/`+`src/app/*.scss` global/app-shell layer — 24 files,
  `sass` dependency removed). What it taught the framework, now
  written into `frontend-web-styles` and `DELEGATION-MODEL.md`: the
  alias-based migration pipeline; a style class is never a JS
  `querySelector`/`closest` hook (self-referential, cross-component,
  and cross-*feature* cases all turned up real, silent breakage); a
  genuinely shared primitive kit becomes small components, not a
  forced single-owner file; raw markup injected via
  `dangerouslySetInnerHTML` needs `:global()` for its own class names;
  a CSS Modules import's type under `exactOptionalPropertyTypes` +
  `noUncheckedIndexedAccess`. Component-naming/testing/accessibility
  conventions are still open — see the "frontend domain is not
  finished" item above, now narrower than before this dogfood.
- Frontend domain fully settled: component/module structure
  (`frontend-component-structure`), testing strategy
  (`frontend-testing`), accessibility (`frontend-accessibility`,
  default WCAG 2.2 AA). Dogfooded on `my-world`'s real codebase for
  each — barrels retrofitted; test style already matched what the
  project did; for accessibility, every `alt=""` site (7) was audited
  and each has a genuinely adjacent equivalent caption, now stated as a
  one-line code comment instead of left implicit. The first pass also
  *wrongly* flagged `prefers-reduced-motion` as a per-feature gap — a
  closer look found `normalize.css` already overrides
  animation/transition duration globally via a universal (`*`)
  selector with `!important`, which covers every component regardless
  of which file mentions the media query by name. Correcting a finding
  before acting on it is itself worth recording: a keyword grep across
  files is not the same check as "is this already covered by a global
  rule" — see `frontend-accessibility`'s own reminder to read the
  actual code, not just grep for a string.
- Added WCAG 2.5.8 (Target Size Minimum, AA, new in 2.2) as a 7th
  check in `frontend-accessibility` — missing from the first pass
  (prompted by the owner asking about tap-target size as part of
  "UX nuances," a real gap, not a false alarm this time). Audited
  `my-world`'s icon buttons against it: every one is 30–48px; the
  only sub-24px controls are a native checkbox and inline text links,
  both under the criterion's own exceptions. No fix needed, recorded
  in `my-world`'s `project-profile.md`.
- Added `frontend-performance` (bundle size, Core Web Vitals
  thresholds, code-splitting) — the owner's "UX nuances" question
  surfaced this and `frontend-security` as two more real gaps beyond
  target size. Applied it to `my-world`: measured the real prod build
  (127KB gzip main chunk, no route splitting), then lazy-split
  `Archive`/`Lightbox`/`Forms` out of `Stage.tsx` — dropped the main
  chunk to 107KB gzip. Hit `INEFFECTIVE_DYNAMIC_IMPORT` warnings at
  first: a barrel re-exporting a lazy-split component alongside a
  symbol still statically imported elsewhere (`goArchive`,
  `DropZone`) keeps everything in one chunk regardless of `lazy()` —
  fixed by importing those specific symbols from their own file,
  bypassing the barrel, which is the one sanctioned exception to
  `frontend-component-structure`'s barrel rule. Verified with
  typecheck/lint/build; the project's one e2e spec (`sharing.spec.ts`)
  has 3 pre-existing failures reproduced identically on `main` without
  this change (confirmed via `git stash` + rerun) — a known flake
  unrelated to this work, not something this task introduced or fixed.
- Added `frontend-resilience` (error boundaries, loading states, empty
  states — three states kept deliberately separate) — the third and
  last gap from the owner's "UX nuances" audit. `my-world` already had
  good loading (`Boot` status union) and empty (`Away` component)
  handling; the one real gap was no error boundary at all, so a render
  crash anywhere would blank the whole page. Added
  `src/app/ErrorBoundary.tsx`, wrapping `<App>` in `main.tsx`. Verified
  it actually catches, not just typechecks: temporarily threw inside
  `GlobeStage`, ran a one-off Playwright check confirming the fallback
  rendered instead of a blank page, then reverted the throw and
  deleted the throwaway test — real runtime proof, not just a build
  passing. This closes the three-item "UX nuances" audit the owner
  asked for; `frontend-security`, `frontend-performance`, and
  `frontend-resilience` are now written, graphed, and dogfooded on
  `my-world` alongside `frontend-component-structure`/`testing`/
  `accessibility` from the earlier pass.
