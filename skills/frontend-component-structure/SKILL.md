---
name: frontend-component-structure
description: Use when deciding how a frontend project's files are organized — Feature-Sliced Design's layers and slices (the framework default), each slice's public-API barrel (index.ts), which files are internal, component/file naming. Not about styling mechanics (CSS Modules, tokens — that's frontend-web-styles) or picking a platform (stack-selection). Applies whenever a new slice is created, an existing one is reorganized, or a project is scaffolded.
---

# Frontend component/module structure

Scope: how a frontend project's files are organized into layers and
slices and exposed to the rest of the app — independent of styling
tech (`frontend-web-styles` covers that) and independent of platform
(`stack-selection`). Read this when scaffolding a new project,
creating a new slice, or deciding whether an existing one needs a
public-API boundary.

Governs `project-profile.md` fields: Frontend → Module structure.

## The default: Feature-Sliced Design (FSD)

Six layers, top to bottom: `app → pages → widgets → features →
entities → shared`. **A module may only import from a layer strictly
below its own** — `pages` can import `widgets`/`features`/`entities`/
`shared`, never another `pages` slice sideways and never anything in
`app`; `shared` imports nothing from the other five. This import
direction is the whole point of choosing FSD over a flatter layout: it
makes "what can depend on what" a structural fact the file tree
enforces, not a convention someone has to remember.

| Layer | Holds |
|---|---|
| `app` | App-wide setup: providers, global styles, router init — not features themselves |
| `pages` | One slice per route: composes widgets/features/entities into what that route renders |
| `widgets` | Large, self-contained UI blocks combining several features/entities for a page (e.g. a page header with nav + search + user menu) |
| `features` | One user-facing action/use-case per slice (`add-to-cart`, `toggle-favorite`) — the thing a user *does* |
| `entities` | One business entity per slice (`user`, `product`) — its own UI, data shape, and the API calls that fetch it |
| `shared` | Reusable, business-agnostic code: UI kit, utils, the API client's own config — knows nothing about any feature/entity above it |

Each slice (a named folder inside a layer, e.g. `features/add-to-cart/`)
gets exactly one `index.ts` at its root — the slice's public API, the
same barrel rule this skill always had, now scoped to the slice instead
of a flat feature folder. Outside code imports only
`@/features/add-to-cart`, never a deep path into it. Segments inside a
slice follow FSD's own naming: `ui/`, `model/`, `api/`, `lib/`,
`config/` — not every segment is needed by every slice, add the ones a
given slice actually has.

- **The barrel lives at the slice root, not inside each component.** A
  component that's purely another's internal detail (an icon only one
  feature's main component renders) stays a plain sibling file inside
  `ui/`, imported directly — it does not get its own `index.ts`.
- **Export only the public surface** from a slice's barrel: the
  component(s), hooks, and types other slices actually need.
- **Files inside a slice import each other directly**, never through
  the slice's own barrel — importing your own barrel is a circular
  dependency a bundler often hides until production.
- **A layer itself never gets a public API/`index.ts`** — only a
  *slice* inside a layer does (`shared` is segment-only, no slices, so
  this applies trivially there too). Confusing "the layer" with "a
  slice in the layer" is the single most common FSD mistake reviewers
  report.
- **Enforce the import-direction rule with
  [Steiger](https://github.com/feature-sliced/steiger)** (`npm i -D
  steiger @feature-sliced/steiger-plugin`), FSD's own official linter:
  `no-higher-level-imports` catches a sideways/upward import,
  `public-api`/`no-public-api-sidestep` catch a deep import bypassing a
  slice's barrel. Wire it into CI the same way `repo-lint-format`
  wires ESLint — a rule nobody checks mechanically erodes the first
  time someone's in a hurry.

```ts
// src/features/add-to-cart/index.ts
export { AddToCartButton } from './ui/AddToCartButton';
// price-formatting helper used only inside this slice — not exported
```

- **The one sanctioned exception: a symbol another slice needs
  eagerly, that also sits in the same barrel as a component being
  `lazy()`-split for `frontend-performance`.** A bundler decides
  chunking per *module*, not per export — if anything still statically
  imports the barrel (even just for an unrelated sibling export like a
  helper or a link-builder), the whole barrel, including the
  lazy-loaded component, stays in the eager bundle; `lazy()` silently
  does nothing (Vite/Rollup warns `INEFFECTIVE_DYNAMIC_IMPORT`). Fix by
  importing that one eager symbol from its own file, bypassing the
  barrel, instead of moving the barrel's design — only for the specific
  symbol causing the eager pull-in, not as a general escape hatch.

## Real alternatives, not a worse FSD

- **Flat feature folders** (`src/features/<name>/`, one tier, no
  enforced layers) — this skill's own previous default. Pick it for a
  solo/small project where FSD's six-layer discipline and a linter
  dependency are real overhead with nothing yet big enough to need the
  enforced boundary; the public-API-barrel rule above still applies at
  the single feature-folder level.
- **Bulletproof React** — a lighter, convention-based reference
  architecture (feature folders, each a self-contained mini-module)
  with real recognition outside the CIS community specifically, but no
  FSD-style enforced cross-layer import rules.

State the reason when picking one of these over the FSD default (team
unfamiliar with FSD and the project is small enough that the enforced
boundary isn't earning its cost yet; or a lighter convention is
genuinely enough) — don't default to FSD by omission without having
actually decided it fits, the same "state it explicitly" discipline
this framework applies to every other default.

## Naming

- **File name matches the component name**: `Header.tsx` exports
  `Header`, `PlaceLabel.tsx` exports `PlaceLabel`. No ambiguity between
  what a file is called and what it exports — near-universal consensus,
  not a judgment call.
- **Hooks**: `useXxx`, camelCase — standard React convention, not
  specific to this framework.
- **Boolean props: bare adjective/noun, no `is`/`has` prefix** —
  `open`, `owner`, `showCity`, `problem`, `armed`, not `isOpen`,
  `hasOwner`. The industry is genuinely split on this (some style
  guides want the prefix, others call it noise once the prop's type is
  visibly `boolean` at the call site) — this framework settles it by
  the convention `my-world` already used consistently throughout its
  own components before this was ever written down; see Basis.
- This is about the *component's* own naming — the CSS class naming
  inside a `.module.css` (`isOn`, `isMain`, camelCase for multi-word
  states) is `frontend-web-styles`'s rule, not this one; the two
  happen to agree on bare-vs-prefixed by coincidence of taste, not
  because one derives from the other.

## Basis (checked 2026-11-14)

- **FSD is this framework's chosen default, not a claimed industry
  standard — the owner made that call explicitly on 2026-11-14 after
  this section's own prior finding** (checked 2026-11-13, after the
  owner challenged an unqualified "FSD is the world standard" claim):
  no State-of-JS-style survey or independent (non-FSD-authored,
  non-CIS) engineering source confirms FSD as an industry-wide
  standard — the strongest praise traces to FSD's own docs/blog and
  Russian/CIS sources (Habr, Avito's engineering blog). Next.js's own
  docs stay explicitly unopinionated on project structure and name FSD
  as a third-party pattern, not an endorsed one:
  [Next.js — Project structure](https://nextjs.org/docs/app/getting-started/project-structure).
  **That finding still stands as written — it is not reversed by
  defaulting to FSD anyway.** A framework default does not require
  universal-standard status (this framework's own CSS Modules default
  over Tailwind is the same shape of choice); it requires a stated
  reason, and the owner's is explicit: this framework's own projects
  benefit from FSD's enforced layer boundaries regardless of FSD's
  adoption breadth elsewhere. Documented FSD downsides (learning
  curve, layer-boundary ambiguity) are real and still apply — named
  directly in this skill's own alternatives section, not hidden by
  making FSD the default: aggregated across multiple practitioner
  reviews, e.g.
  [Feature-Sliced Design review](https://dev.to/algoorgoal/feature-sliced-design-review-22k0).
  Bulletproof React has comparable real recognition with a lighter,
  convention-only (no enforced import layers) philosophy, named as the
  real alternative for exactly the case FSD's downsides make it a
  worse fit: [Bulletproof React](https://bestofjs.org/projects/bulletproof-react).
- Steiger as FSD's own official linter (`no-higher-level-imports` for
  the layer-import direction, `public-api`/`no-public-api-sidestep`
  for the barrel rule) — confirmed directly against the project's own
  repository, still in beta/active development as of this check:
  [feature-sliced/steiger](https://github.com/feature-sliced/steiger).
- Feature-Sliced Design: every slice has a public-API `index.ts` at its
  root; outside code imports the slice path, never a deep path into it
  — cross-slice access always goes through the public API, treating a
  direct deep import as a violation:
  [FSD architecture guide](https://smithery.ai/skills/atilladeniz/fsd-architecture),
  [issoh.co.jp, 2026](https://www.issoh.co.jp/md/tech/4218).
- Keep barrels shallow (one level) and export only the public surface;
  chaining barrels through several levels makes it hard to trace where
  code actually lives:
  [Are TypeScript barrel files an anti-pattern?](https://steven-lemon182.medium.com/are-typescript-barrel-files-an-anti-pattern-72a713004250),
  [Stanza — React code organization](https://www.stanza.dev/courses/react-modern-patterns/best-practices/react-code-organization).
- A file importing its own folder's barrel creates a circular
  dependency that minification can surface late; siblings should import
  each other directly instead:
  [import/export conventions guide](https://acemate-docs.pages.dev/docs/development/conventions/import-export-rules).
- Named exports over default exports, for consistent naming across the
  codebase and better tree-shaking/auto-import:
  [Barrel exports in JS/TS](https://blog.marcnuri.com/barrel-exports-javascript-typescript).
- File name matching the component's own name is near-universal advice:
  [React JS naming conventions](https://dev.to/kristiyanvelkov/react-js-naming-convention-lcg).
  Boolean prop naming genuinely divides sources — prefix (`is`/`has`)
  vs. a bare adjective once the type is visibly boolean at the call
  site — so this framework follows the bare form `my-world` already
  used consistently, not either camp's blog-post opinion:
  [An opinionated guide to component APIs](https://imply.io/blog/an-opinionated-guide-to-component-apis/)
  (bare adjective) vs.
  [React naming conventions](https://compile-n-run.pages.dev/docs/framework/react/react-best-practices/react-naming-conventions)
  (prefix).

Whether a barrel belongs at the *component* level too (not just the
slice level) genuinely divides practitioners — this framework settles
it at the slice level only, matching FSD's actual granularity and
keeping the "keep barrels shallow" caution satisfied by construction.

## What this skill does not cover

Styling mechanics and file colocation with a component's own style file
— `frontend-web-styles`. Deciding the platform or app type —
`stack-selection`. This skill only answers "what does this folder
export, and what stays private."
