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
- Built all seven frontend domains the audit above found missing:
  `frontend-routing` (client-state-only vs. router library, route-change
  title/focus/scroll/code-splitting), `frontend-design-system`
  (feature-local-until-promoted rule, closed variant API),
  `frontend-component-workshop` (Storybook default, built only once a
  shared component exists), `frontend-theming` (CSS `light-dark()` +
  `color-scheme`, flash-of-wrong-theme handling), `frontend-motion`
  (duration/easing tokens, CSS-first with Motion/View-Transitions for
  what CSS can't do), `frontend-forms` (React Hook Form + Zod default,
  client/server validation split), and `frontend-auth` (session
  storage location, `HttpOnly` cookie default vs. a BaaS's own
  `localStorage`-based SDK, protected-route UX vs. real server
  enforcement). Each has a dated `Basis` section from real 2026
  sources, not unaided reasoning. Also added one more gap the audit
  itself missed until the owner asked for it explicitly: frontend
  auth/session handling, distinct from the backend "Auth" row that
  already existed. Dogfooded against `my-world`'s actual state where
  each row could be confirmed immediately (e.g. routing: client-state
  only, confirmed; design system: correctly "none — feature-local
  only," not a gap; auth: Supabase's own `localStorage` session,
  accepted tradeoff, no custom backend to put a cookie in front of it);
  the remaining domains (theming, motion, forms, Storybook) don't yet
  have a real decision to dogfood since `my-world` hasn't needed them
  (dark mode, an animation library, a forms library, or a shared
  component to showcase) — their profile rows record that honestly as
  "none stated," not a forced adoption just to exercise the new skill.
- Built the three app-type-conditional skills too
  (`frontend-seo`, `frontend-analytics`, `frontend-feature-flags`) plus
  one more conditional gap found while writing them
  (`frontend-monitoring`, for `project-profile.md` section 5's
  previously-ungoverned "Monitoring / logging" row — the reporting
  counterpart to `frontend-resilience`'s error boundary, which catches
  an error but never says where it goes). The owner explicitly chose
  to finish writing the framework's own knowledge before adopting it
  into any project ("сначала фреймворк, потом проекты") — these stay
  marked "ask explicitly" in the profile template (still correctly
  *conditional per project*, per `project-profile/SKILL.md`'s own
  caution against marking every blank row that way), but now have a
  real skill behind them the moment a project's answer is "yes,"
  instead of a blank "Governed by" cell. Each has a dated `Basis`:
  Plausible/cookie-less analytics over GA4's consent-banner
  requirement, Sentry with hidden source maps and `beforeSend`
  PII-scrubbing, hand-rolled flags until a real multi-user/no-deploy
  trigger justifies a service, and SSR/prerendering as the real fix
  for SPA SEO rather than treating client-injected meta tags as
  equivalent.
- Owner named six more rows that had been sitting ungoverned in
  `project-profile.md` since before this audit started (Linter(s),
  Formatter, Pre-commit hooks' lint/format half, CI/CD provider, CI
  pipeline stages, Containerization, Orchestration) — a reminder that
  the earlier "found everything" audits were scoped to *new* frontend
  concerns and never swept the framework's own pre-existing ungoverned
  rows. Added `repo-lint-format` (ESLint+Prettier/Ruff/gofmt by
  language, Husky/lint-staged kept fast and staged-files-only, composes
  with `repo-cleanup`'s hook rather than replacing it), `repo-ci`
  (GitHub Actions default, PR-gated lint/test/build with deploy gated
  to `main` — already the shape `my-world`/`copycat`'s own CI uses, not
  a new convention), and `repo-containerization` (no Docker by default;
  real trigger is a self-hosted target or a co-located
  database/worker — `my-world`'s own GitHub Pages deploy is the
  worked "doesn't need it" example). Each has a dated `Basis`. This
  raises the real question of whether another sweep is owed — see
  `repo-init/SKILL.md`'s fixed-order rule, which exists so a *new*
  project's adoption never skips a row again, but doesn't retroactively
  guarantee this framework's own template had no pre-existing gaps.
- **Full row-by-row audit of `project-profile.md`** (owner's own
  request: "проверь, что у нас все пункты... не будут случайно
  пропущены"), checking not just "is there a value" but "does a skill
  that exists actually get linked, and does `framework-lint` itself
  catch it if not." Found four real bugs — a skill existed, genuinely
  covered a row, but was never wired to it, so `framework-lint` was
  structurally blind to the gap (a skill with no `Governs` line at all
  produces zero claims and is invisible to the cross-check):
  - `frontend-testing` existed but had no `Governs` line at all —
    "Unit/component tests" and "E2E tests" sat ungoverned despite a
    whole skill already deciding them. Fixed.
  - `frontend-component-structure` existed but had no `Governs` line
    and *no row to attach to* — the template had never had a "Module
    structure" field at all. Added the row (Frontend section, right
    after Meta-framework) and the `Governs` line.
  - `repo-commit`'s workflow already assumes GitHub flow (short-lived
    branches off the default branch, no `develop`) but never named it
    as the "Branching model" row's actual default. Fixed — stated the
    default explicitly, Git flow as a non-default alternative.
  - `stack-selection`'s own Step 2 table already writes "TypeScript"
    into the profile as the Browser/Electron/Tauri default, but the
    "Language" row's "Governed by" cell was blank. Fixed.
  Also found and fixed a latent bug in `framework-lint` itself while
  doing this: `check_governs` matched rows by field name alone, with
  no section scoping — harmless today because the only repeated field
  name (`Language`, in both Frontend and Backend) didn't yet have a
  skill on both sides, but a second skill ever claiming "Language" for
  the Backend row would have silently collided with `stack-selection`'s
  Frontend claim instead of being flagged as two separate things. Made
  both the table parser and the `Governs`-line parser section-aware
  ((section, field) keys instead of just field). Also added a small,
  clearly justified extension while already touching this: `Type
  checking` (TS `strict: true` / `mypy --strict` default) folded into
  `repo-lint-format`, since it sits right next to the lint/format
  tooling decision that skill already owns.
  **Rows checked and left deliberately ungoverned** (not a gap, a
  genuine "no framework default" — distinguishing this from the bugs
  above matters, since the owner's whole concern is not confusing the
  two): Meta-framework, Bundler, Package manager, State management,
  Data fetching — `stack-selection`'s own pattern already states the
  rule for these ("a row with no default recorded yet means ask the
  user, then write the answer down as the new default" — true of every
  dogfooded project so far, which all independently landed on Vite+npm
  without that ever being written down as *the* answer). Hosting/
  deploy target, Environments, Secrets management, Security/
  compliance, Target OS/browser support, Secondary platforms, Browser/
  device support matrix — plain descriptive/project-specific
  information with no single technical convention to govern across
  every project. The whole Backend section stays under its existing
  blanket note (no backend domain skill exists yet).
- **Correction to the entry above: "deliberately ungoverned" was the
  wrong call for most of those rows.** The owner pushed back: a row
  left as free text means the agent will never reliably know to
  present real options when it reaches that row — "plain descriptive
  info" isn't true of a question with a real, bounded answer set, only
  of ones that genuinely have none. Fixed by writing the option sets
  instead of leaving them deferred:
  - `frontend-stack-selection` (new) — UI framework, meta-framework,
    bundler, package manager, state management, data fetching. Each a
    real 2026 option table (pros/cons, a dated `Basis`, a default) —
    not "ask when we get there."
  - `repo-hosting` (new) — hosting/deploy target, environments,
    secrets management, and security/compliance (GDPR/SOC2/HIPAA
    applicability explained, not just named).
  - `stack-selection` — extended with a Step 1.5 decision table for
    secondary platforms and target OS/browser support, consolidating
    the old duplicate "Browser/device support matrix" row (section 7)
    into the section-2 "Target OS / browser support" row — same
    question asked twice under two names was itself a found bug.
  - `DELEGATION-MODEL.md` — added a standing rule ("Every governed cell
    gets a populated option set, not a deferred question") so this
    doesn't quietly regress the next time a new domain gets written:
    a governed row must ship with its skill's real option set, and a
    deliberately-deferred row (Docker, Storybook, feature flags, ...)
    must say so explicitly with its trigger condition when reached,
    never sit blank.
  What's left correctly as plain fact, no technology decision possible
  (Identity section's One-line description, Team, Project status):
  these have no "options" to compare — they're just what the project
  is, not a choice between named alternatives.
