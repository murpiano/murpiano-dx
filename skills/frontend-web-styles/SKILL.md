---
name: frontend-web-styles
description: Use when styling components in a browser, Electron, or Tauri app — writing or editing CSS, CSS Modules, design tokens, naming classes, light/dark theming, or setting up a web project's style layer. Not for React Native or other native UI engines (see frontend-styling-concept for the mechanism table). Not for backend, API, or database code — stop reading immediately if the task has no visual/styling part.
---

# Web styling (browser, Electron, Tauri)

Scope: CSS Modules, design tokens, global reset, naming, light/dark
theming for anything that renders through a browser engine — a plain web
app, an Electron app, or a Tauri app render the same way, so they share
this one skill. Implements the rules in `frontend-styling-concept`. If
the current task is backend, API, database, or React Native work, this
file has nothing relevant — stop here.

## No Sass/SCSS

Modern CSS (native nesting, custom properties, `clamp()`, `color-mix()`)
covers what a preprocessor used to be needed for. Do not add Sass/SCSS to
a new project for styling; it is extra tooling for capability plain CSS
already has.

## CSS Modules, one per component

Every component's styles live in `Component.module.css`, colocated with
`Component.tsx`:

```css
/* Button.module.css — plain CSS, nothing module-specific in the syntax */
.button {
  padding: 10px 20px;
  border-radius: 8px;
  background: var(--accent);

  &:hover {
    opacity: 0.9;
  }
}
```

```tsx
// Button.tsx
import styles from './Button.module.css';

export function Button() {
  return <button className={styles.button}>Click</button>;
}
```

The build tool (Vite, etc.) generates a unique class name per component
scope. This is why BEM is unnecessary here: a plain `.title` in
`UserCard.module.css` can never collide with `.title` in
`NewsArticle.module.css` — the mechanism BEM existed to simulate
(collision-free naming) is already provided by the build.

- Class names inside a module: plain, short, semantic (`.button`,
  `.title`, `.isOpen`) — no block/element prefixing, no `__`/`--`.
- A variant or state is its own class, composed at the call site
  (`` `${styles.button} ${isOpen ? styles.isOpen : ''}` `` or a small
  `clsx`/`classnames` helper), not a second BEM-style modifier selector.
- Keep one `.module.css` per component file; do not share one module file
  across multiple components.

## Global layer — not a module

One `global.css` (plain, no `.module.` in the name) holds what must be
shared, imported once at the app entry — this is the "global application
point" from `frontend-styling-concept`:

- reset/normalize (see `templates/normalize.css`) — this is the
  "baseline reset" rule from `frontend-styling-concept`, applied once,
  before any token or component style
- `box-sizing`, base font, base color from tokens
- the `:root` design tokens (below)

Nothing else goes in `global.css` — no component selectors, no
one-off overrides. If something only applies to one component, it
belongs in that component's module file, not here.

## Design tokens

CSS custom properties on `:root`, dark as the default, light as an
override block — see `templates/tokens.css`:

```css
:root {
  --bg: #04060d;
  --accent: #ffc86b;
  --text: #e8ecf6;
  --muted: #7f89a3;
  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);
}

:root[data-theme='light'] {
  --bg: #f4f6fb;
  --accent: #b8860b;
  --text: #11131a;
  --muted: #5b6478;
}
```

Switch theme by setting `data-theme="light"`/`"dark"` on `<html>`;
omitting the attribute uses the dark default. Never hardcode a color,
spacing, or font value inside a `.module.css` file — reference the
token (`var(--accent)`).

Naming — semantic by default, a spacing scale on an 8px base grid (4px
sub-grid for tight spacing only), thematic names only as a stated
exception: full rule and external basis in `frontend-styling-concept` →
"Token naming convention" / "Basis". `templates/tokens.css` already
includes the `--space-4`…`--space-64` scale; add project colors
alongside the existing `--bg`/`--accent`/`--accent-2`/`--text`/`--muted`
placeholders rather than inventing new role names for the same roles.

## Breakpoints — written by hand, no abstraction layer

Plain CSS has no mixins. Do not reach for Sass just to get one. Use the
project's agreed breakpoint numbers directly in each module's `@media`:

```css
.panel {
  padding: 24px;
}

@media (width <= 767px) {
  .panel {
    padding: 16px;
  }
}
```

Default breakpoints (keep unless the project states its own):
`laptop: 1440px`, `tablet: 1023px`, `mobile: 767px`, `mobile-s: 480px`.
Write the number directly in the query; do not invent a custom-property
indirection for it (`var()` inside a media condition is not reliably
supported).

For fluid type sizing, `clamp()` is native CSS — no Sass function needed:

```css
.title {
  font-size: clamp(1rem, 0.6rem + 1.5vw, 3rem);
}
```

## Raw markup injected via `dangerouslySetInnerHTML` keeps its own class names

An SVG (or other markup) inlined as a raw string — `dangerouslySetInnerHTML`,
`?raw` imports — never goes through the CSS Modules transform, so its
class names stay exactly as written in that file, unhashed. A selector
for one of them in your `.module.css` must be wrapped in `:global()`
(`:global(.cz-f) { ... }`), not written as a plain local class — a
plain `.cz-f` would hash to a name the injected markup never has, and
the rule would silently never match. Find these class names by reading
the raw asset file directly, not by guessing from the component code.

## Sharing one module between sibling components

Most components get their own `.module.css`. A genuinely shared set of
primitives (a form's field/button/row vocabulary, used by many sibling
components with no single natural owner) is the one case where several
files legitimately import the *same* module — don't force a shared
vocabulary into one file's exclusive styles just to keep the "one file
per component" rule literal. Prefer exposing it as small components
(`Field`, `Btn`, `Row`, ...) from whichever file owns the module, so
consumers write `<Btn variant="main">` instead of a raw
`className={styles.btn}` — this keeps the CSS Modules import itself
confined to one file, and gives every consumer a typed API instead of
guessing a class name.

## A CSS Modules import under `exactOptionalPropertyTypes`

`vite/client`'s type for a `.module.css` import is a bare index
signature (`{ readonly [key: string]: string }`). Under
`noUncheckedIndexedAccess`, dot access through it (`styles.foo`) types
as `string | undefined`, not `string`. If a component you write re-wraps
a class name into an *optional* prop (e.g. `Acts({ className }: {
className?: string })`), passing `styles.foo` there fails under
`exactOptionalPropertyTypes` (`TS2375`) — the fix is declaring that prop
as `className?: string | undefined`, explicitly, not just `className?:
string`. Only matters for your own components' optional props; a
built-in element's `className` already includes `undefined` in its type
and needs no change.

## A style class is not a JS hook — check this before deleting any old file

CSS Modules turns a class name into a build-time hash
(`Header_brand__a1b2c`), so any `document.querySelector('.foo')` or
`element.querySelector('.foo')` that assumed a literal class name
breaks silently (no build error — it just stops finding the element).
This has turned up in nearly every file migrated so far — self-queries
inside the same component (`PlaceField`'s own dropdown list, a
lightbox slide's own "current" lookup), and cross-file ones (`Splash.tsx`
querying the header's `.header__brand`/`.header__burger`; the lightbox
querying `.archive` — a *different feature's* root class — to tell
whether a photo tile sits inside the open archive overlay).

Before deleting an old `.scss` file (not just editing the one component
being migrated), run `grep -rn "querySelector\|\.closest(" src` once for
the whole project and check every hit's selector string against the
classes you are removing — a match anywhere in the codebase, not only
in the file you're touching, is a real breakage. Fix each one with a
`data-*` attribute for the JS lookup, separate from the style class —
styling and element-identity are different concerns and stay on
different attributes. A self-referential query inside one component
(an element looking up its own child by class) is usually better fixed
with a direct `ref` instead of a `data-*` attribute, since the lookup
never needs to cross a component boundary.

## Checks before calling styling done

- No hex/rgb/px-literal color in a `.module.css` file — grep for
  `#[0-9a-f]{3,6}` outside `tokens.css`/`global.css` and justify any hit.
- No `_`/`--` BEM-style class names inside a module file.
- Every component folder has exactly one `.module.css`, imported from
  exactly one component file.
- If the project has a `data-theme` toggle, every token touched by a
  feature exists in both the default and `[data-theme='light']` block,
  or is intentionally theme-invariant (state that in a one-line comment).

Full templates: [templates/tokens.css](templates/tokens.css),
[templates/normalize.css](templates/normalize.css),
[templates/global.css](templates/global.css).
