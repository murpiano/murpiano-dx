---
name: frontend-motion
description: Use when adding or reviewing UI animation/transitions — duration/easing tokens, picking CSS vs. an animation library, page-transition vs. component-transition mechanics. Not the prefers-reduced-motion opt-out itself (frontend-accessibility already covers it) or token naming in general (frontend-styling-concept).
---

# Motion / animation

Governs `project-profile.md` fields: Frontend → Motion/animation approach.

Scope: what moves, how long it takes, and which mechanism does the
moving — not whether motion should be respectful of a user who opted
out (`frontend-accessibility` already states that rule; this skill
assumes it and doesn't repeat it, beyond the one note below on where
tokens must honor it).

## Motion tokens, same discipline as spacing tokens

Duration and easing are tokens, named by role, the same way
`frontend-styling-concept` names spacing (`--space-*`) — never a
hardcoded `300ms` or `cubic-bezier(...)` inline in a component. Keep
the set small; a project with a dozen duration tokens effectively has
none, because nobody will remember which one to reach for. A workable
starting set:

- `--motion-fast` (~100–150ms) — hover, focus, small state toggles.
- `--motion-base` (~200ms) — the default for most enter/exit
  transitions.
- `--motion-slow` (reserved for a large spatial change — a panel
  sliding the width of the screen, not a button hover).
- One standard easing curve for most transitions, one separate "exit"
  curve if exits are tuned to feel quicker than entrances (a common
  and defensible choice — see `Basis`).

Every motion token must collapse under `prefers-reduced-motion`
(`frontend-accessibility`'s rule) — when auditing a project, confirm
this is actually true (a global override, or each token individually
guarded), not assumed; `BACKLOG.md` records a real case where a global
`normalize.css` override was the thing actually doing this and a
first-pass grep-based audit missed it.

## Picking the mechanism: default to CSS, reach for a library only when CSS can't

- **CSS transitions/keyframes are the default** for hover, focus, and
  simple enter/exit — they run on the compositor thread (smoother,
  cheaper) and need no dependency.
- **Reach for an animation library (Motion/Framer Motion)** only for
  what CSS genuinely cannot do on its own: animating a component *out*
  of the DOM on unmount (`AnimatePresence`), gesture-driven interaction,
  spring physics, or a shared-layout transition between two different
  DOM positions. Load it lazily (e.g. `LazyMotion` + `domAnimation`) if
  the project otherwise ships little JS-driven animation — pulling in
  the full library for one small bounce is the same bundle-weight
  mistake `frontend-performance` already warns about elsewhere.
- **The View Transitions API** is the current default for page/route-
  level transitions (the "morph from one view to the next" pattern that
  used to need a FLIP-animation library) — pair this with
  `frontend-routing`'s route-change handling, not as a separate system.
- **GSAP** is a stated option only for a genuinely complex, hand-tuned
  timeline (a multi-step scroll-driven sequence) — not a default,
  since most projects never need it.

## Basis (checked 2026-11-13)

- Motion-token scales in the 100–200ms range for small interactions,
  with exits often tuned faster than entrances, and an explicit warning
  against too many duration tokens, appear consistently across
  published design-system motion docs:
  [Atlassian Design System — Motion](https://atlassian.design/foundations/motion),
  [Cognite Aura — Motion](https://docs.cognite.com/aura-design-system/foundations/motion).
- CSS transitions run on the compositor thread and are the right
  default for hover/focus/simple transitions; an animation library
  (Motion/Framer Motion) is for exit animations, gestures, springs, and
  shared layout that CSS cannot do; the View Transitions API now covers
  page-level "morph" transitions that used to need a separate library:
  [CSS vs. JavaScript animation performance](https://joshwcomeau.com/animation/css-vs-javascript),
  [When to use Framer Motion vs. native CSS](https://instagit.com/emilkowalski/skills/when-to-use-framer-motion-vs-native-css-animations/).
