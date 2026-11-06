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
