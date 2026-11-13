---
name: frontend-stack-selection
description: Use when choosing the actual frontend technologies for a new project — UI framework, meta-framework, bundler, package manager, state management, data fetching. Each is a real, bounded set of 2026 options with tradeoffs, not an open-ended question; this skill gives the option matrix, a recommendation, and when to deviate. Not application-type/language (stack-selection, tier 0) or an already-running project's own existing choice (read its project-profile.md instead).
---

# Frontend stack selection — the option matrix for each row

Governs `project-profile.md` fields: Frontend → UI framework, Meta-framework,
Bundler, Package manager, State management, Data fetching.

Scope: `stack-selection` decides there *is* a web/Electron/Tauri frontend and
that it's TypeScript. This skill picks what runs on top of that — the six
rows `stack-selection`'s own Step 2 table used to leave as "no default
recorded yet". None of these rows gets answered with "ask when we get
there" — each one is a bounded, real-world option set with a reasoned
default. Ask only which row's conditions this project actually matches
(team size, SSR need, existing investment), never re-derive the option set
from scratch.

Order matters: UI framework → meta-framework (constrained by it) → bundler
(mostly fixed by the meta-framework choice) → package manager (independent)
→ state management + data fetching (constrained by meta-framework's own
data layer, e.g. Next.js Server Actions). Confirm in this order, same
reasoning as `project-profile.md`'s own section-order rule.

## UI framework

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **React** | Largest ecosystem, hiring pool, and library coverage by a wide margin (Stack Overflow 2025: 44.7% overall / 46.9% professional usage, vs. Angular 18.2%, Vue 17.6%, Svelte 7.2%); every meta-framework below targets it first | Boilerplate-heavy if used unopinionated; the ecosystem churns (pick Zustand not because Redux is bad but because conventions shift) | Default — unless the team already has deep, current investment in another framework |
| **Vue** | Gentler learning curve, built-in reactivity model, strong docs (Nuxt as its meta-framework) | Smaller hiring pool and third-party library coverage than React | Team already knows Vue, or the project is small/content-driven and simplicity outweighs ecosystem size |
| **Svelte** | Compiles away at build time — smallest runtime, high developer satisfaction scores | Smallest ecosystem and hiring pool of the four; SvelteKit less battle-tested at scale than Next.js | Small, performance-critical app where bundle size dominates and the team accepts the smaller ecosystem |
| **Angular** | Full batteries-included framework (DI, routing, forms, RxJS built in) — fits large, structured enterprise teams | Steepest learning curve, most opinionated, slowest to adopt | Enterprise context already standardized on Angular, or regulatory/structural reasons demand a single prescribed way to do everything |

**Default: React.** Not because it's technically best on every axis, but
because the ecosystem-size gap is large enough that it's the safer bet for
a framework meant to serve many different future projects without
re-litigating this choice each time. Deviate only for a stated reason
(existing team skill, a Vue/Svelte codebase already in place), not
speculatively.

## Meta-framework (only relevant once UI framework = React; `none` is itself a valid, common answer)

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Next.js** | Largest ecosystem/features of any React meta-framework; App Router + Server Components + Server Actions; Turbopack as its own bundler (production default in Next 16) | Heaviest; some lock-in toward Vercel-shaped infra even though self-hosting works, teams often skip checking that | Full-stack React app needing SSR/SSG, API routes, or a large feature surface — the safe general default |
| **React Router v7 (Remix mode)** | Web-standards-first (loaders/actions map directly to HTTP), predictable for form-/action-heavy apps | Smaller ecosystem than Next.js; less opinionated structure for very large apps | Form-and-mutation-heavy app (bookings, dashboards with lots of writes) where Next.js's data model feels like a fight |
| **Astro** | Ships zero JS by default, islands architecture — any framework (including React) only where interactivity is needed | Not the right shape for a highly interactive SPA — it's built for mostly-static content | Content-heavy site (marketing, docs, blog) where most pages are static and only a few need interactivity |
| **none — plain Vite SPA** | Simplest possible setup; this is what the React team itself now points to since Create React App's deprecation | No SSR/SSG — all data fetched client-side after first paint; weak for SEO-sensitive public pages | App has no SEO requirement (`frontend-seo` already says "no" or it's behind auth) and doesn't need SSR — internal tools, authenticated dashboards |

**Default: `none` (plain Vite SPA) for an authenticated/internal app with no
public-SEO need; Next.js once SSR/SSG is actually required** (per
`frontend-seo`'s own "public pages meant to be indexed" row — read that row
first, since it decides this one). Astro only when the project is
genuinely content-first. Don't default to Next.js reflexively — it's the
heaviest option and many apps (internal tools, admin panels) never need
what it adds.

## Bundler (mostly inherited from the meta-framework above, not a free choice)

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Vite** (Rolldown-powered as of Vite 8) | Fastest dev-server cold start for non-Next.js setups; framework-agnostic; now the npm-download leader over Webpack (639M vs. 221M monthly downloads, Aug 2026 snapshot) | Production build still catching up to Turbopack/Rspack on very large monorepos in some benchmarks (sources conflict) | Default for anything not on Next.js — plain SPA, Astro, Remix/React Router, Vue, Svelte |
| **Turbopack** | Default, production-ready bundler in Next.js 16; tightly integrated | Not meaningfully usable outside Next.js — not a general-purpose choice | Already on Next.js — it's not an independent decision at that point |
| **Rspack** | ~98% Webpack-plugin-API compatible, Rust-speed; real migration path off Webpack | Smaller community than Vite; mainly a Webpack-replacement story, not a greenfield pick | Existing large Webpack codebase that needs speed without a plugin rewrite |
| **Webpack** | Still the most-used bundler by raw install count (86% of devs per 2025 State of JS), mature plugin ecosystem | No longer the default for new projects; slower than every option above | Legacy codebase already on it with no migration pressure — not a new-project choice |

**Default: Vite for anything outside Next.js; Turbopack is simply what
comes with Next.js** — this row rarely needs its own discussion once the
meta-framework is picked. Webpack/Rspack are migration-path answers for an
existing codebase, never the fresh-project default.

## Package manager

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **pnpm** | Strict hoisting eliminates phantom dependencies; ~70% less disk use than npm/Yarn via content-addressable store; strong monorepo/workspace support | Occasional friction with packages that rely on npm's looser hoisting (rare, usually fixable) | Default for a new project |
| **npm** | Ships with Node, zero setup; npm 11 added `min-release-age`/`npm trust` supply-chain hardening | Flat `node_modules`, phantom-dependency risk, largest disk footprint | Project explicitly wants zero tooling decisions, or a contributor base that can't be asked to install anything extra |
| **Bun** | Fastest installer (benchmarks range 15–17x npm); also a runtime/test-runner if adopted fully | Trades away pnpm's strict isolation; still the newest/least battle-tested of the four at the edges | Already running the Bun runtime, or install speed specifically is the bottleneck |
| **Yarn (Berry/4.x)** | Plug'n'Play + zero-installs for teams already built around that model | No longer picked for greenfield projects over pnpm | Team/monorepo already standardized on Yarn Berry — not a reason to start one |

**Default: pnpm.** Switch to npm only for an explicit zero-setup reason, to
Bun only if the Bun runtime is already the project's choice, to Yarn only
to match an existing monorepo.

## State management

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Zustand** | No boilerplate, works with Server Components, by far the most-adopted new default in 2026 guides | Less structure than Redux Toolkit — a very large app can grow unruly without self-imposed conventions | Default for client UI state in most apps |
| **Context API (built-in)** | Nothing to install; fine for low-frequency values | Re-renders every consumer on any change — not a state-management library substitute | Simple, rarely-changing values (theme, locale) — not full app state |
| **Jotai** | Fine-grained atomic reactivity, good for many independent small pieces of state | Smaller ecosystem than Zustand; atomic model is a different mental model to onboard a team onto | App genuinely has many independent, fine-grained state slices (editors, canvases, complex forms) |
| **Redux Toolkit** | Explicit structure, mature devtools/middleware ecosystem, right fit for large teams needing enforced conventions | More boilerplate and bundle weight than Zustand even in Toolkit form | Large team/enterprise app where imposed structure matters more than setup speed |

**Default: Zustand for client state, paired with the data-fetching layer
below for server state** — don't reach for a client store to cache server
data at all; that's the next row's job. Redux Toolkit only once team size
or audit/structure requirements make it worth the extra ceremony.

## Data fetching

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **TanStack Query** | The general-purpose client-side cache/fetch layer — pairs with REST, tRPC, or GraphQL; not tied to any one transport | Still needs an actual transport underneath it — it's a cache, not an API layer | Default cache layer regardless of transport choice below |
| **tRPC** | End-to-end TypeScript types with no schema layer, when client and server are the same codebase/monorepo | Only works when you control both ends in TypeScript — no third-party/public-client story | Single-client TypeScript app/monorepo talking to its own backend |
| **GraphQL** | Fits multiple clients with different data shapes, including third-party consumers | Real setup/ops overhead (resolvers, schema, often a gateway) that's wasted on a single first-party client | Several distinct clients (web, mobile, partner API) need different slices of the same data |
| **Server Actions** (meta-framework-provided, e.g. Next.js) | Simplest path for same-app mutations, no separate API layer | POST-only — blocks HTTP caching, serializes parallel calls on a page; friction pairing with TanStack Query per multiple 2026 writeups | Simple mutations inside the same Next.js app — pair with tRPC/REST for reads, not as the only data layer |
| **Plain REST + fetch** | Zero extra dependency, universally understood | No caching/dedup/types without adding something on top (hence TanStack Query) | Default fallback when none of the above conditions apply — small API surface, no type-sharing need |

**Default: TanStack Query over plain REST** for a project with no shared
TypeScript backend; **TanStack Query + tRPC** once the backend is the same
TypeScript codebase/monorepo; **GraphQL** only once a second real client
actually exists (not speculatively, same two-strikes reasoning
`frontend-design-system` uses for components).

## What this skill does not cover

Whether there's a frontend at all, or the language (`stack-selection`).
Styling architecture once the framework is picked (`frontend-styling-concept`).
Routing library choice (`frontend-routing` — note Next.js/Remix/Astro ship
their own router, so that skill mostly applies to the `none`-meta-framework
row here). Forms (`frontend-forms`). The backend's own framework/language —
no domain skill exists for that yet.

## Basis (checked 2026-11-13)

- Vite's npm-download lead over Webpack (639.5M vs. 221.2M monthly, Aug 2026
  snapshot) and GitHub star counts (82.3K vs. 66.0K): aggregated blog
  benchmark, treated as directional, not authoritative —
  [JavaScript bundlers in 2026](https://dev.to/thedailyagent/javascript-bundlers-in-2026-vite-rspack-turbopack-and-the-end-of-an-era-16hk).
  Turbopack as Next.js 16's production default, Rspack's ~98% Webpack
  plugin compatibility: [Turbopack vs Vite vs Rspack](https://www.index.dev/skill-vs-skill/turbopack-vs-vite-vs-rspack).
  2025 State of JS Webpack-usage figure (86% use it, 14% like it):
  cited secondhand in the same roundup — treat as approximate.
- pnpm as the 2026 default, its hoisting/disk-usage advantage, Bun's
  15–17x install-speed figures: [npm vs Yarn vs pnpm vs Bun, 2026](https://reintech.io/blog/npm-vs-yarn-vs-pnpm-vs-bun-2026-comparison),
  [pnpm vs npm vs Yarn vs Bun benchmarks](https://deployhq.com/blog/choosing-the-right-package-manager-npm-vs-yarn-vs-pnpm-vs-bun).
- Zustand as the 2026 default React state-management pick, Redux Toolkit
  reserved for large/enterprise teams, Context for low-frequency values
  only: [State management in 2026: Zustand vs Jotai vs Redux Toolkit](https://dev.to/jsgurujobs/state-management-in-2026-zustand-vs-jotai-vs-redux-toolkit-vs-signals-2gge).
- tRPC for same-codebase TypeScript, GraphQL for multi-client, TanStack
  Query as the transport-agnostic cache layer, Server Actions' POST-only
  caching limitation: [REST vs GraphQL vs tRPC vs gRPC in 2026](https://dev.to/pockit_tools/rest-vs-graphql-vs-trpc-vs-grpc-in-2026-the-definitive-guide-to-choosing-your-api-layer-1j8m).
- React's usage lead over Vue/Svelte/Angular: Stack Overflow 2025 Developer
  Survey figures (44.7% overall / 46.9% professional) as cited in
  [Is React Still the King in 2026?](https://svar.dev/blog/react-vs-vue-vs-svelte-for-modern-web-apps/) —
  the one source in this search round anchored to a named survey rather
  than an unattributed blog figure.
- Next.js/Remix/Astro/plain-Vite-SPA split by SSR/content/interactivity
  need, and the React team's own post-CRA guidance toward Vite for SPAs:
  [Next.js vs Remix vs Astro vs SvelteKit, 2026](https://dev.to/pockit_tools/nextjs-vs-remix-vs-astro-vs-sveltekit-in-2026-the-definitive-framework-decision-guide-lp5).

These are 2026 practitioner-consensus snapshots from aggregated blogs/guides,
not a formal standards body (unlike, say, CSS `light-dark()` in
`frontend-theming`) — re-verify via `knowledge-refresh` before trusting an
old date here, since this landscape moves faster than most of this
framework's other `Basis` sections.
