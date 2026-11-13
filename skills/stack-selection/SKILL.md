---
name: stack-selection
description: Use when starting a brand-new application from scratch, before any code exists — deciding the application type (web, Electron/Tauri desktop, native desktop, native/cross-platform mobile, backend service, ...) and its language/framework, then routing to the matching domain's skills. Not for adding a feature to a project whose stack is already chosen — read that domain's own skills instead (e.g. frontend-styling-concept for an existing frontend).
---

# Stack selection — entry point for a new application

Scope: the first decision for a brand-new application, before any
domain-specific skill runs. This is tier 0 in `AGENTS.md`'s Delegation
model, above *Concept* — see [../GRAPH.md](../GRAPH.md) for where it sits
among the framework's other domains.

Governs `project-profile.md` fields: Application type & platforms →
Primary platform, Secondary platforms, Target OS / browser support,
Frontend → Language.

## The governing rule here too

State a settled default, don't re-ask it. Ask only the decision that is
genuinely new for this project: which row below applies, and — only
where no default is recorded yet — which language/framework inside that
row.

## Step 0 — start the project profile

Create `.agents/project-profile.md` for this project from
`skills/project-profile/templates/project-profile.md` now, before Step 1
— every decision made in this skill and the ones it hands off to gets
written into it as it's made, so the table is this checklist, not a
report written after the fact. See `skills/project-profile/SKILL.md`.

## Step 1 — application type

Ask (or confirm from context) which of these the project is:

- Browser web app
- Desktop app via a web engine (Electron, Tauri) — downstream path is
  identical to the browser row; same render engine
- Native desktop app (a platform UI toolkit: WinUI, AppKit, Qt, ...)
- Native or cross-platform mobile app (Swift/Kotlin native, or React
  Native/Expo)
- Anything with no UI at all (backend service, CLI, library) — outside
  this skill's routing table; say so and treat it as its own future
  domain the same way (see Step 3)

Write the answer into the profile's "Application type & platforms" row.

## Step 1.5 — secondary platforms and support matrix

Not a free-text description — a bounded choice with a stated default, same
as every other row in this skill.

**Secondary platforms** (does this project also need another platform
beyond the primary one):

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **None (single platform)** | No shared-code complexity, fastest to ship | — | Default — don't add a second platform speculatively |
| **React Native / Expo, sharing logic with a React web app** | Real code/logic reuse (state, API layer) if the web app is already React | UI still needs per-platform work; React Native Web for full UI-sharing is its own, narrower tradeoff | A mobile app is genuinely planned and the web app is React |
| **Capacitor / Tauri wrapping the existing web app** | Near-zero extra UI code — ships the same web app as a desktop/mobile shell | Feels less native; app-store review scrutinizes bare web wrappers more | A thin native wrapper is enough (no native-only features needed) and shipping speed matters more than native feel |
| **Separate native codebase per platform** | True native UX/performance | Full second (or third) codebase to maintain | Native UX is a hard requirement (e.g. complex platform-specific interactions) and the team can support it |

Default: **none** until a second platform is a real, stated requirement —
the same "don't build for a hypothetical" rule this framework applies to
Docker (`repo-containerization`) and feature flags (`frontend-feature-flags`).

**Target OS / browser support** (what versions actually need to work):

| Option | Covers | Tradeoff |
|---|---|---|
| **Evergreen browsers, last 2 major versions** (Chrome, Firefox, Safari, Edge) | The overwhelming majority of real traffic for a new product with no legacy user base | Drops long-tail old-browser users — acceptable unless a stated audience needs otherwise |
| **Explicit legacy support** (e.g. a specific older Safari/Android WebView version) | A named enterprise/embedded audience that can't update | Real transpilation/polyfill cost, and constrains which CSS/JS features are usable elsewhere in this project's own skills (e.g. `frontend-theming`'s `light-dark()` needs a modern browser) |
| **Latest 2 major OS versions** (mobile/native: iOS N/N-1, Android covering ~95% of active devices per Google's own distribution data) | Standard native-app support window | A stated reason (enterprise device fleet on an old OS) to go further back |

Default: **evergreen browsers, last 2 versions** for web; **latest 2 major
OS versions** for native/mobile. Write the project's actual answer into
the "Target OS / browser support" row — this is the one row in
`project-profile.md` that doubles for both the web-browser case and the
native-OS case; don't also fill a separate browser matrix elsewhere for
the same project.

## Step 2 — language/framework for that type

| Type | Default | Status |
|---|---|---|
| Browser / Electron / Tauri | TypeScript; framework per project need (no single forced framework yet) | Default set — TS over JS, nothing else fixed |
| Native desktop toolkit | — | No default recorded yet |
| Native/cross-platform mobile | — | No default recorded yet |
| Backend/service | — | No default recorded yet |

A row with no default recorded yet means ask the user, then — once
stated — this table is the place to write the answer down as the new
default, the same way CSS Modules became the recorded default for
browser styling in `frontend-styling-concept`. Also write the chosen
language/framework into the profile's "Frontend" or "Backend" section.

## Step 3 — hand off

- Browser / Electron / Tauri → go to `frontend-stack-selection` first (UI
  framework, meta-framework, bundler, package manager, state management,
  data fetching — each a real option matrix with a recommendation, not an
  open question), then `frontend-styling-concept` (the architecture) and
  from there `frontend-project-setup` (the scaffold).
- Any row with no domain skill yet (native desktop, native/cross-platform
  mobile, backend) → say so explicitly. Propose drafting that domain's
  concept → implementation → guided-setup trio together, the same shape
  `frontend-*` already has, before writing any project code — do not
  silently improvise an unwritten convention.

## Recording a new default or a new domain

- A language/framework default settled for a row → write it into the
  Step 2 table in this file.
- A whole new domain with no skills yet → once its first skill exists,
  add it to [../GRAPH.md](../GRAPH.md) per `AGENTS.md`'s graph-trigger
  rule, and add a Step 3 line here routing to it.
