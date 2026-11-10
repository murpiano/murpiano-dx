---
name: frontend-styling-concept
description: Use when deciding or documenting the cross-platform styling architecture for a project — how design tokens flow between web, Electron/Tauri, React Native, or another native UI engine, or when starting a new frontend codebase's style layer from scratch. Not for day-to-day component styling inside an already-set-up web project — that is frontend-web-styles. Not for backend/API/database work.
---

# Cross-platform styling concept

Scope: the platform-agnostic rules every styling approach in this
framework follows, and the table that maps them to a concrete mechanism
per platform. Read this once when a project's style architecture is being
decided; for routine styling inside an existing web project, read
`frontend-web-styles` instead — it already encodes this concept.
Child skills and their status: [GRAPH.md](GRAPH.md).

Governs `project-profile.md` fields: Frontend → Styling approach.

## The four rules, true on every platform

1. **One token source of truth.** Colors, spacing, radii, type scale,
   breakpoints, motion — defined once, per project, not duplicated per
   platform. Every platform-specific style file *consumes* tokens; none
   of them invents its own copy of a value.
2. **Style colocated with its component.** The file that holds a
   component's styles lives next to that component, named after it.
   Deleting the component deletes its styles; nothing orphaned in a
   shared tree.
3. **Scope isolated per component.** A style written for one component
   must not leak into or collide with another component's names. The
   mechanism that guarantees this differs per platform (below), but the
   guarantee itself is non-negotiable everywhere.
4. **Baseline reset before tokens apply.** Every render engine ships its
   own default rendering quirks (a browser's default stylesheet, a
   native widget's default padding, a platform's default font). Those
   defaults are neutralized once, in one place, before any token or
   component style is applied — never patched over ad hoc per component.

These four rules are the contract. What changes per platform is only
*how* each rule is mechanically satisfied — because the render engines
are not compatible with each other.

## Token naming convention (rule 1, in detail)

Rule 1 says tokens have one source of truth; this says how to *name*
them, independent of which platform/technology expresses them (CSS
custom property, SCSS `$variable`, Tailwind `theme.extend`, a JS/TS
token module for React Native — the names below apply to all of them):

- **Default to semantic (role) names** — `--bg`, `--accent`,
  `--text-muted` — not thematic/decorative names (`--sky`, `--lamp`,
  `--star`). A role's name stays correct even if the value behind it
  changes (a new theme, a rebrand); a decorative name ties the token to
  one metaphor and has to be renamed or reinterpreted later.
- **Thematic names are a stated exception, not a default.** Choose them
  only when the project has a fixed, deliberate visual identity with no
  planned theming (a personal/art project built around one specific
  metaphor) — state this as the project's own reason, the same way any
  other non-default choice in this framework is settled once and not
  re-asked later.
- **Spacing/radius/size scales: name the token by its value, on an 8px
  base grid with a 4px sub-grid for tight spacing only** (icon/label
  gaps, badge padding, compact controls) — e.g. `--space-4`,
  `--space-8`, `--space-12`, `--space-16`, `--space-24`, `--space-32`.
  Name tokens after the resulting value, not an arbitrary index
  (Tailwind's `space-3` = 12px needs a lookup; `--space-12` doesn't).
  Values between steps get rounded to the nearest step, not given their
  own one-off token.

## Basis (checked 2026-11-07)

External sources, not just this framework's own reasoning — see "External
justification freshness" in `skills/DELEGATION-MODEL.md` for how to reuse
or refresh this:

- Two-layer *primitive → semantic* naming, and semantic winning for
  theming/stability, is common practice across design systems:
  [UX Collective](https://uxdesign.cc/naming-design-tokens-9454818ed7cb),
  [Red Hat Design System](https://github.com/RedHat-UX/red-hat-design-system/wiki/Semantic-Token-Names),
  [Door3](https://www.door3.com/blog/naming-design-tokens-guide).
- Value-named spacing tokens over an index or t-shirt scale: Mark
  Dalgleish (Braid design system) argues a predictable step
  (`--space-8`) has no disadvantage over a t-shirt name, which is
  indirection when designers don't think in those categories —
  [gist](https://gist.github.com/markdalgleish/c7c293dd5fe96620558e7b1d793ac07a).
- 8px base grid with a 4px sub-grid for tight spacing is the more common
  default (Material Design's 8dp base, Workday Canvas's 8pt grid,
  Tailwind's 4-based scale used as the sub-grid) than a flat 4px-only
  scale: [Mantlr spacing cheat sheet](https://mantlr.com/blog/spacing-system-cheat-sheet),
  [Workday Canvas](https://canvas.workday.com/tokens/space).

These sources are practitioner/vendor writeups, not a settled W3C
standard — treat this as current common practice, re-checked per the
freshness rule, not an immutable law.

Noticed while dogfooding `frontend-web-styles` on a real project
(`my-world`, see `skills/BACKLOG.md`): it had colors centralized but
thematically named, and no spacing scale at all. The dogfood surfaced
the gap; the external sources above are what actually settled the
convention.

## Mechanism per platform

| Platform | Isolation mechanism | Style authoring | Token consumption | Baseline reset | Global application point |
|---|---|---|---|---|---|
| Browser, Electron, Tauri (Chromium/WebKit) | CSS Modules (`*.module.css`, build-time scoped class names) | Plain CSS (native nesting, custom properties) — no Sass/SCSS | `:root` CSS custom properties | `normalize.css` against the browser's default stylesheet | `global.css`, imported once at the app entry |
| React Native / Expo | File scope: `Component.styles.ts` next to `Component.tsx` | `StyleSheet.create({...})`, plain JS objects | imported JS/TS token module | neutralize per-platform default quirks (iOS/Android default `TextInput` padding, safe-area insets, default font) in one shared file | a root theme/context provider wrapping the app |
| Other native UI engine (WinUI/AppKit/Qt/...) | that engine's own style/resource system | platform-native (XAML, Storyboard, QML, ...) | tokens exported to that platform's resource format | that engine's own default-style override, applied once at the app/window root | the engine's own app-wide resource dictionary or theme object |

Electron and Tauri render through an embedded browser engine, so they take
the *same* row as the browser — no separate rule set, no separate skill.
A genuinely different render engine (React Native today; a native
desktop toolkit if one is ever used) needs its own platform skill,
written only when that platform is actually in use in a project — do not
pre-build a skill for a platform nothing here targets yet.

## One default implementation per platform row, more allowed later

A platform row can end up with more than one implementation skill — the
same platform, a different concrete technology (e.g. browser styling via
plain CSS Modules today, via Tailwind in some future project). When that
happens:

- **Exactly one is marked default** in this table, and is what gets
  proposed first for new work on that platform — not re-decided per
  project.
- **Default row, current:** Browser/Electron/Tauri → `frontend-web-styles`
  (CSS Modules, plain CSS). No alternative exists yet.
- **Adding an alternative:** write it as its own skill
  (`frontend-web-styles-<technology>`, following the same shape:
  mechanism, token consumption, baseline reset, global application
  point), add one line to this table naming it as a non-default option
  for that row, and state in the new skill which concept it implements —
  exactly like `frontend-web-styles` already does. Do not fold the
  alternative into the default skill as a conditional branch; keep one
  skill per concrete technology.
- **Choosing non-default:** only when the project states a reason (an
  existing codebase already on that technology, an explicit user
  preference for this project). Ask once, settle it for that project,
  and do not re-ask on later tasks inside the same project.

## Applying this when starting a new project

0. Apply the platform's baseline reset first (the "Baseline reset" column
   above) — before any token or component style exists, so every later
   style is written against a known-zero starting point.
1. Decide the project's token values once (palette, spacing scale, type
   scale, breakpoints, motion curve). This lives in exactly one place —
   for web, that is the `:root` block described in `frontend-web-styles`.
2. Pick the platform row above. Read that platform's skill
   (`frontend-web-styles` for browser/Electron/Tauri) for the concrete
   file layout and authoring rules.
3. If the project targets more than one platform (e.g. a web app and a
   React Native app sharing a brand), keep the token *values* identical
   across both, generated or hand-copied from one canonical source —
   never let the web and native palettes drift independently.

## What this skill does not cover

Component-level naming, CSS Modules file layout, the global reset, dark/
light theming mechanics — all in `frontend-web-styles`. This skill only
answers "which mechanism, and why is it still the same system."
