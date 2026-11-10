---
name: frontend-accessibility
description: Use when building or reviewing any frontend UI for accessibility — keyboard navigation, screen-reader semantics (aria-*, roles), focus management, color contrast, motion, alt text. Not about styling mechanics or component file structure (frontend-web-styles, frontend-component-structure). Applies to every interactive component, not just forms.
---

# Frontend accessibility

Scope: what this framework holds every frontend project to by default,
and where the line sits between "settled default" and "project states
its own target." Read this when building new interactive UI, not only
when something is explicitly a "form" or "a11y task" — a custom
dropdown, a modal, a hover-driven card, a canvas-based view (a globe, a
chart) all have real accessibility surface.

Governs `project-profile.md` fields: Constraints & non-functional
requirements → Accessibility target.

## Default target: WCAG 2.2 AA

State this as the framework default, not a question, unless the
project has a stated reason for a different target (an internal tool
with no external users and no compliance exposure might reasonably
settle for less; a target audience or a legal requirement might push
to AAA for specific criteria). Record the project's actual target in
`project-profile.md` — "not stated" is not a real answer, write "AA"
(or whatever was decided) once this is discussed.

## The concrete checks, not just the label

"Target AA" means nothing by itself — these are the checks that make
it true, in roughly the order to think about them when building a new
interactive piece:

1. **Keyboard**: every interactive control reachable and operable by
   keyboard alone (tab order, Enter/Space on custom buttons, Escape to
   close a layer). If a custom widget (a dropdown, a carousel) needs
   its own key handling, write it — don't rely on a `<div onClick>`
   with no keyboard path.
2. **Screen-reader semantics**: real semantic elements first
   (`<button>`, `<nav>`, `<dialog>`-like `role="dialog"` +
   `aria-modal`) before reaching for ARIA to patch a `<div>`. Label
   every control that isn't self-describing (`aria-label` on an icon
   button, `aria-expanded` on a disclosure, `aria-selected` /
   `role="option"` on a custom list, `aria-pressed` on a toggle). A
   `<label htmlFor>` on every form field, not a placeholder standing in
   for one.
3. **Focus management**: a layer that opens (a modal, a menu) traps or
   at least starts focus sensibly, and gives it back on close; a
   closed/hidden layer gets `inert` so it can't be tabbed into or read
   by a screen reader while invisible — not just `display`/`opacity`
   tricks that leave it in the tab order.
4. **Color contrast** (WCAG 1.4.3): 4.5:1 for normal text, 3:1 for
   large text (≥24px, or ≥19px bold) and for meaningful UI/icon
   outlines. Check an actual token pair (e.g. `--muted` on `--bg`)
   against this ratio before shipping a new text/background
   combination, not just "it reads fine to me" on one screen.
5. **Motion**: `prefers-reduced-motion: reduce` is not an AA
   requirement for every animation (WCAG 2.3.3, the closest criterion,
   is AAA and only covers interaction-triggered motion) — but it's the
   common technique for it and costs little to extend broadly. Target
   the *decorative* motion (hover transforms, parallax, card dissolve)
   with a reduced-motion override; don't blanket-disable *functional*
   motion that carries information (a loading spinner, a progress
   fill) under the same rule — that can make the UI look frozen/broken
   instead of calmer. A motion effect running autonomously longer than
   5 seconds needs a pause/stop/hide control (WCAG 2.2.2) unless it's
   essential to the activity it represents (a load-in-progress
   indicator is the usual exception).
6. **Images**: `alt=""` only when the image is decorative *or* a
   visible, adjacent text already conveys the equivalent information
   (a caption, a title) — state which case applies, don't leave it
   silent. A content-bearing image with no nearby equivalent text needs
   real alt text, even if writing one is awkward for user-generated
   content.
7. **Target size** (WCAG 2.5.8, new in 2.2): every pointer target —
   icon button, checkbox, close "×" — is at least 24×24 CSS px, unless
   one of: it has ≥24px spacing to the next target; an equivalent
   larger control exists elsewhere on the page; it sits inline in a
   sentence/text block; its size is set by the user agent (a native
   checkbox); or a smaller size is essential to what it represents (a
   map pin). A visually small icon still needs a 24px *hit area* —
   padding, not just the glyph's own box. The 44×44 "enhanced" size
   (2.5.5) is AAA, not required by the AA default.

## What already existing code tells you

Before assuming a project has no accessibility practice, grep it:
`aria-`, `role=`, `focus-visible`, `prefers-reduced-motion`, `inert`,
`alt=`. A project can be meaningfully ahead of "not stated" in its
profile without anyone having written the target down — read the code,
don't just read the profile field.

**A keyword grep counting hits per file is not the same check as "is
this already covered."** A single global rule (a universal `*`
selector, a reset applied once at the app root) can satisfy a
requirement for every component in the project without that
component's own file ever mentioning the keyword — e.g. one
`prefers-reduced-motion` block in a baseline-reset file, using `*`
with `!important`, already overrides every component's
animation/transition duration, even though grepping feature-by-feature
would show the string in only one file. Check whether a narrower
finding is actually already resolved by a broader rule before reporting
it as a gap.

## Basis (checked 2026-11-07)

- WCAG 2.3.3 (Animation from Interactions) is AAA, not a blanket "all
  animations" rule — that's a common team policy built on top of the
  criterion, not the criterion itself; a global `prefers-reduced-motion`
  override can break functional motion (spinners, progress) if it
  isn't scoped to decorative effects:
  [WCAG 2.3.3 overview](https://testparty.ai/blog/wcag-2-3-3-animation-from-interactions-2025-guide),
  [animation accessibility anti-pattern](https://webgency.github.io/design-system/foundations/anti-patterns/animation-without-reduced-motion).
- WCAG 2.2.2 (Pause, Stop, Hide) requires a control for autonomous
  motion lasting over 5 seconds, with an exception when the motion is
  essential to the activity (a load-in-progress indicator is the
  standard example of the exception):
  [WCAG 2.2 criteria reference](https://www.disabilityworld.org/toolkit/standards/wcag/2-3-3-animation-from-interactions/).
- WCAG 1.1.1 doesn't mandate the `alt` attribute's text specifically —
  it requires an equivalent text alternative; `alt=""` is correct when
  adjacent visible text already serves that purpose, and real alt text
  is needed when it doesn't. Practitioners differ on how readily to
  rely on a nearby caption instead of writing alt text — the safer
  default some teams use is to write alt text regardless:
  [alt text and nearby captions](https://www.boia.org/blog/should-you-include-alt-text-for-pictures-with-captions),
  [redundant-alt rule](https://getwcag.com/accessibility-guide/image-redundant-alt).
- WCAG 2.5.8 (Target Size Minimum) is new in 2.2, level AA: pointer
  targets need 24×24 CSS px unless spacing, an equivalent control,
  inline placement, user-agent-controlled sizing, or essential
  presentation applies. The 44×44 enhanced size is the separate AAA
  criterion 2.5.5, not required by default:
  [W3C Understanding: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

## What this skill does not cover

Styling mechanics, module structure, or test strategy —
`frontend-web-styles`, `frontend-component-structure`,
`frontend-testing`. This skill only answers "is this UI usable without
a mouse, without sight, or with motion sensitivity."
