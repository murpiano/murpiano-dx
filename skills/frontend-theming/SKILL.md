---
name: frontend-theming
description: Use when a project needs a light/dark toggle or multiple brand themes — the switching mechanism, not the token names themselves. Not about naming tokens (frontend-styling-concept, which this skill assumes is already followed) or the prefers-reduced-motion opt-out (frontend-accessibility).
---

# Theming / dark mode

Governs `project-profile.md` fields: Frontend → Theming / dark mode.

Scope: *how* a theme switches once semantic tokens already exist
(`frontend-styling-concept`'s rule 1 — one token source of truth, named
by role). A project with no theme switch records "none stated" and that
is a valid, final answer, not a gap — this skill is for the moment a
project's real answer becomes "yes."

## Default mechanism: CSS `light-dark()` + `color-scheme`, not duplicated token sets

1. Set `color-scheme: light dark` on `:root` so the browser knows both
   schemes are supported (form controls and scrollbars recolor
   correctly) — and audit the project in dark mode before shipping
   this; declaring support for a scheme nobody has actually looked at
   produces real, visible contrast breaks, not just a theoretical risk.
2. Define each semantic token's value with the CSS `light-dark()`
   function (`--bg: light-dark(#fff, #111)`), not two separate token
   files or a duplicated `--bg-dark` naming scheme — `light-dark()`
   already reads the active `color-scheme` (system preference *or* an
   explicit override), so one token definition serves both themes.
3. **A manual toggle overrides, it doesn't replace, the system
   preference**: set `color-scheme` explicitly (via a `data-theme`
   attribute or inline style on `:root`) only when the user has chosen
   one; default to following `prefers-color-scheme` when they haven't.
   Persist the explicit choice (`localStorage`), not just in-memory —
   losing a manual choice on reload reads as the toggle being broken.
4. **Avoid the flash of the wrong theme**: `light-dark()` only takes
   effect once the stylesheet parses, which is too late to prevent a
   flash for a returning user with a stored manual preference. Set the
   `color-scheme` meta tag (`<meta name="color-scheme" content="light
   dark">`) so the browser knows before any CSS loads, and run a small
   inline script in `<head>` — before first paint, not in a module
   loaded later — that reads the stored preference and sets it on
   `:root` immediately.
5. **`light-dark()` only takes colors.** A non-color theme difference
   (dimming a logo image, swapping an icon) still needs a
   `prefers-color-scheme`/`[data-theme]` media query or selector
   alongside it — don't force a non-color value through `light-dark()`.

## Multi-brand theming

The same mechanism extends to more than two themes: `color-scheme`
itself is still just light/dark, but a brand-selector attribute
(`data-brand="acme"`) combined with that brand's own token overrides
(still role-named, still consumed the same way by every component)
covers it — this is a bigger token-authoring job than a light/dark
toggle, not a different switching mechanism. Only take this on when a
project's real answer is "multi-brand," not speculatively.

## Basis (checked 2026-11-13)

- `light-dark()` reads the element's active `color-scheme` (system
  preference or an explicit override), covering most cases that used to
  need a `prefers-color-scheme` media query, and is in all modern
  browsers as of 2026; it only accepts color values, so non-color theme
  differences still need the media query:
  [web.dev — light-dark()](https://web.dev/articles/light-dark),
  [MDN — light-dark()](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value/light-dark).
- `light-dark()` alone does not prevent a flash of the wrong theme on
  load, since it only applies once the stylesheet parses; the
  `color-scheme` meta tag plus an inline pre-paint script for a stored
  preference is the common fix:
  [No Fuss Light/Dark Modes](https://frontendmasters.com/blog/no-fuss-light-dark-modes/).
- Declaring `color-scheme: light dark` without auditing the project in
  dark mode produces real form-control/scrollbar recoloring and
  contrast breaks, not a theoretical risk — same source as above.
