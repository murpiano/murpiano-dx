---
name: frontend-component-structure
description: Use when deciding how to organize a frontend feature's files — a public-API barrel (index.ts) per feature folder, which files are internal, component/file naming. Not about styling mechanics (CSS Modules, tokens — that's frontend-web-styles) or picking a platform (stack-selection). Applies whenever a new feature folder is created or an existing one is reorganized.
---

# Frontend component/module structure

Scope: how a feature's files are organized and exposed to the rest of
the app — independent of styling tech (`frontend-web-styles` covers
that) and independent of platform (`stack-selection`). Read this when
creating a new feature folder, or deciding whether an existing one
needs a public-API boundary.

Governs `project-profile.md` fields: Frontend → Module structure.

## The rule: one barrel per feature folder, not per component

Each feature folder (`src/features/<name>/`) gets exactly one
`index.ts` at its root — the folder's public API. Outside code imports
only from that path (`@/features/header`), never from a file inside it
(`@/features/header/HouseIcon`). What's inside the folder — one
component or ten, which of them are implementation details the main
component uses privately — is not the outside world's concern.

- **The barrel lives at the feature root, not inside each component.**
  A component that is purely an internal detail of another (e.g. a
  small icon only the feature's main component renders) does not get
  its own `index.ts` or subfolder — it stays a plain sibling file,
  imported directly by the file that uses it.
- **Export only the public surface**: the component(s), hooks, and
  types other features or the app shell actually need. Everything else
  (internal sub-components, helpers) stays unexported from the barrel,
  even though it's a plain file sitting right next to it.
- **Files inside the folder import each other directly**, not through
  the folder's own `index.ts` — a file importing its own barrel is a
  circular dependency a bundler often hides until a production build,
  not something to debug from.
- **A barrel that only re-exports one thing is still worth keeping**
  for this framework's convention (every feature folder has the same
  shape, so nothing about a folder's internal file count leaks into
  how it's imported) — don't skip it just because the folder currently
  holds a single component.

```ts
// src/features/header/index.ts
export { Header } from './Header';
// HouseIcon is Header's own implementation detail — not exported
```

- **The one sanctioned exception: a symbol another feature needs
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

## Basis (checked 2026-11-13)

- **FSD-vs-Bulletproof-React status, checked directly after the owner
  challenged an unqualified "FSD is the world standard" claim**: no
  State-of-JS-style survey or independent (non-FSD-authored, non-CIS)
  engineering source confirms FSD as an industry-wide standard — the
  strongest praise traces to FSD's own docs/blog and Russian/CIS
  sources (Habr, Avito's engineering blog). Next.js's own docs stay
  explicitly unopinionated on project structure and name FSD as a
  third-party pattern, not an endorsed one:
  [Next.js — Project structure](https://nextjs.org/docs/app/getting-started/project-structure).
  Bulletproof React has comparable real recognition with a lighter,
  convention-only (no enforced import layers) philosophy:
  [Bulletproof React](https://bestofjs.org/projects/bulletproof-react).
  Documented FSD downsides (learning curve, layer-boundary ambiguity):
  aggregated across multiple practitioner reviews, e.g.
  [Feature-Sliced Design review](https://dev.to/algoorgoal/feature-sliced-design-review-22k0).
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
feature level) genuinely divides practitioners — this framework settles
it at the feature level only, matching FSD's actual granularity and
keeping the "keep barrels shallow" caution satisfied by construction.

## When this isn't enough: two different upgrade philosophies

A flat feature-folder-per-domain layout (this skill's default) is
deliberately simple — one tier, grouped by feature, nothing more.
**Once a project outgrows that** (large app, multiple teams, a real
need to distinguish app-wide vs. page-level vs. shared-entity code, not
just "feature vs. shared"), there are two real, differently-shaped
upgrade paths — not one obvious "next step":

- **Feature-Sliced Design (FSD)** — a formal layered architecture
  (`app → pages → widgets → features → entities → shared`) with its own
  enforced import rules (a layer may only import from layers below it)
  and often its own ESLint plugin checking them. Strongest adoption and
  advocacy specifically in the Russian/CIS frontend community (its own
  docs, Habr, Avito's engineering blog); no verified broader
  "industry standard" claim found for it (no State-of-JS-style survey
  or independent Western engineering-blog endorsement turned up in a
  search for one) — treat "FSD is the/a world standard" as an
  unverified claim, not a settled fact, the same way any other
  practitioner-advocacy source gets treated in this framework's `Basis`
  sections. Real, documented downsides: a learning-curve cost, and
  reviewers citing ambiguity in exactly which layer a given piece of
  code belongs in.
- **Bulletproof React** — a lighter, convention-based reference
  architecture (feature folders, each a self-contained mini-module with
  its own UI/state/hooks/API calls) with real recognition outside the
  CIS community specifically, but *no* FSD-style enforced cross-layer
  import rules — conventions to follow, not a structure a linter
  enforces for you.

Next.js's own documentation is explicitly unopinionated here — it
states no official structure beyond "group by feature, stay
consistent," and names FSD itself as a third-party pattern, not
something it endorses. This framework doesn't pick a default between
these two for the same reason it doesn't default straight to
microservices or Docker: **both are real structure worth adopting once
the simple model actually strains — not before, and not reflexively
because one of them was called a "standard" somewhere.** The owner
states a reason to adopt one (strict enforced boundaries matter more →
FSD; a lighter, broadly-recognized convention is enough → Bulletproof
React) when that trigger is real, the same way any other build-trigger
decision in this framework gets made explicitly rather than assumed.

## What this skill does not cover

Styling mechanics and file colocation with a component's own style file
— `frontend-web-styles`. Deciding the platform or app type —
`stack-selection`. This skill only answers "what does this folder
export, and what stays private."
