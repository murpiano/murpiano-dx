# Framework backlog

Open items for the framework itself (not any one project). Referenced
from `skills/DELEGATION-MODEL.md`. Move an item here instead of letting
it live only in a conversation; remove it once it's actually done
(mention the skill/file that resolved it, don't just delete silently).

- **Backend domain** — do not pre-build; start it (concept →
  implementation → setup, per `DELEGATION-MODEL.md`) only once a real
  backend project is connected or created.
- **Seven frontend rows in `project-profile.md` have no governing skill
  yet** — build all of them, order doesn't matter, the goal is full
  coverage, not a sequence (owner's own framing, 2026-11-12/13):
  - [ ] Design system / shared components
  - [ ] Component dev/doc workshop (Storybook or equivalent)
  - [ ] Theming / dark mode
  - [ ] Motion/animation approach
  - [ ] Forms & validation
  - [ ] Routing / navigation
  - [ ] Auth / session handling (frontend) — distinct from section 4's
        backend "Auth" row; the client-side pattern (login-redirect,
        protected routes, where the session token lives), added
        2026-11-13
  Unlike the backend domain above, these are *not* waiting on a new
  project — every dogfooded project so far has needed all of them;
  build each the same way the earlier frontend domains were built
  (concept → implementation → dogfood on `my-world`). Check a box off
  and move its skill from this list to Done as each one lands. Three
  more rows (SEO/discoverability, analytics, feature flags, section 7)
  are genuinely app-type-conditional, marked "ask explicitly" so
  `repo-init` asks rather than infers "no" — these stay unbuilt until a
  project's real answer is "yes."
- **Team review process for framework changes.** Right now any change to
  `skills/`/`DELEGATION-MODEL.md`/etc. is just agreed in conversation and
  written. Fine solo; for a team sharing this framework, decide whether
  framework-structure changes need a review step (PR-style) before they
  apply to everyone's sessions.
- **Raise `copycat`'s audit gate from `critical` to `high` once Electron
  is upgraded.** `copycat` still ships Electron 32; its 7 remaining
  `npm audit` findings are all Electron's own advisories, fixed only by
  a major Electron 32 → 45 upgrade that needs real manual testing of the
  packaged Windows app (can't be verified in a sandbox). Until that
  lands, `copycat`'s CI `security` job intentionally stays at
  `--audit-level=critical`, not the framework default of `high` — see
  `.agents/2026-11-11-dependency-security.md` in `copycat`'s workspace
  data.
- **Give `copycat` a `project-profile.md`.** It's connected to the
  framework (`AGENTS.md`, dated `.agents/` notes) but was never adopted
  via `repo-init`, so it has no profile table — the dependency-security
  decision above had to go into a dated note instead of a governed row.

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
- Found and fixed a real process gap, not a skill gap: `repo-init`'s
  scan was treating "no i18n library detected" as a settled "no"
  without ever asking the owner — a near-miss this session, caught
  only because i18n came up in conversation by chance. Added a
  general principle to `project-profile/SKILL.md` ("absence of a
  signal is not a decision") plus an "ask explicitly" marker on the
  profile template's i18n row, and updated `repo-init` to actually ask
  for every field marked that way, recording a real "no" as a
  confirmed answer instead of an inferred one. Asked `my-world`'s
  owner directly: the real answer was "yes" (Russian + English) — the
  opposite of what the unconfirmed detected value said. Added
  `frontend-i18n` (default react-i18next, reasoned against Lingui and
  react-intl) to cover the implementation once it starts. The "ask
  explicitly" list is meant to stay short and curated, not grow to
  cover every blank row — see that skill's own caution.
- Added `repo-dependency-security` (Dependabot alerts + an
  `npm audit --audit-level=high` CI gate, dated `Basis` on
  Dependabot/Renovate/audit-ci). Dogfooded on both real projects, with
  different outcomes that taught the framework something real: on
  `my-world`, `npm audit fix` cleared every high/critical finding
  (devDependency-only chain), so the gate landed at the framework
  default (`high`) immediately. On `copycat`, 29 findings included
  Electron's own CVEs — Electron is a devDependency in `package.json`
  but is the actual runtime shipped to users, and fixing those needs a
  major Electron 32 → 45 upgrade that must be manually tested on a
  packaged Windows build (can't be verified in this sandbox). Rather
  than force that upgrade through to make the gate pass, the gate
  landed at `--audit-level=critical` for now (tracked above to raise
  once Electron is current) — the one genuinely critical finding (a
  `tar` vulnerability reachable only through `electron-builder`'s own
  build-time dependency chain) was still cleared via a scoped
  `package.json` `overrides` entry, verified not to break the dev
  build before committing. A first attempt to override `tar` globally
  appeared to crash `node-gyp`/`cacache` — turned out to be this
  sandbox running Node 24 instead of the project's required Node 22,
  not the override; re-verified clean on the correct Node version
  before concluding anything. Also caught and fixed, mid-task, that a
  feature branch had been cut from a stale local `main`/`master` (no
  `git pull` first) which would have silently reverted an already-merged
  feature on merge — rebased before pushing. `copycat`'s own
  `kysaro.yml` was separately pinned to Node 24 and had been failing on
  `master` since PR #67 for the same native-build reason; fixed
  alongside this work since it was directly in the way. One own mistake
  not fixed: the squash-merge commit for `copycat`'s PR exceeded
  kysaro's line-length rule despite passing a local `kysaro -m --type
  merge` pre-check — a real discrepancy between that pre-check and the
  actual `kysaro ci` rule, now one more failing check on `copycat`'s
  `master` (joining four pre-existing ones); not rewritten since
  rewriting published `master` history is out of bounds here. Pre-check
  merge messages by eye for the 72-char body-line rule too, don't trust
  `--type merge` alone.
- Wrote the concurrent-edits guidance for `project-profile.md`
  (`project-profile/SKILL.md` → "Concurrent edits"): `sync_workspace()`
  runs a real `git merge` over the workspace repo, so edits to
  different rows or different `decisions/<field-slug>.md` files merge
  cleanly on their own (each is its own line/file); only a same-row or
  same-decision-file edit by two sessions in the same sync window is a
  real conflict, and `workspace_sync.py` already aborts and preserves
  both commits unmerged rather than guessing — the new guidance says
  not to resolve that by picking a side, but to surface it and ask,
  same as the single-session "absence of a signal is not a decision"
  rule above.
- Audited whether the frontend domain was actually complete, after the
  owner asked twice in a row and got "yes, that's everything" wrong
  both times (i18n, then design system/Storybook) — a real, repeated
  process failure worth fixing structurally, not just answering better
  next time. First attempt at the fix was wrong too: wrote a second,
  separate `FRONTEND-CHECKLIST.md` table — the owner caught it
  immediately ("у нас же уже есть таблица... это два источника
  истины?"). `project-profile.md` is already that one table; the real
  fix was adding the missing concerns there as new rows with empty
  "Governed by" (same pattern as the no-backend-skill-yet note in
  section 4), not inventing a parallel document. Found via general
  frontend/design-system literature
  ([design system maturity models](https://atomize.tools/blog/design-system-maturity/),
  [component API versioning](https://www.pathtoproject.com/blog/20260505-component-api-versioning-for-enterprise-design-systems.md),
  [Storybook vs. Ladle/Histoire, 2026](https://www.techinterview.org/post/3233475411/frontend-component-documentation-storybook-2026/),
  [Next.js production checklist](https://nextjs.org/docs/app/guides/production-checklist),
  [frontendchecklist.io](https://frontendchecklist.io/checklists/launch-checklist)):
  six universal rows added to section 3 (design system, component
  workshop, theming, motion, forms & validation, routing — see the open
  item above) and three conditional "ask explicitly" rows added to
  section 7 (SEO, analytics, feature flags).
