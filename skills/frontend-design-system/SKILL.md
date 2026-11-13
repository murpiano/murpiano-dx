---
name: frontend-design-system
description: Use when deciding whether a component should move from feature-local to a shared design-system tier, where shared components live, or how to shape a shared component's variant API. Not about design tokens themselves (frontend-styling-concept) or Storybook/component-workshop tooling (frontend-component-workshop) — this is the promotion rule and the API shape for what's promoted.
---

# Design system / shared component library

Governs `project-profile.md` fields: Frontend → Design system / shared components.

Scope: the rule for when a component stops being one feature's private
detail and becomes shared UI, where shared UI lives once promoted, and
how its API stays stable as more features start depending on it. Token
values (color, spacing, type scale) are `frontend-styling-concept`'s
job, not this skill's — a design system *consumes* those tokens, it
doesn't define new ones.

## Foundation: don't build primitives from scratch — start from shadcn/ui

Before the promotion question below even comes up: what are shared
components actually built *out of*? Building every primitive (dialog,
dropdown, popover — anything with real accessibility/focus-management
behavior) from scratch is real, avoidable work with real bug surface
(focus traps, ARIA roles, keyboard nav are each individually easy to
get subtly wrong).

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **shadcn/ui** | Copy-paste components (via its CLI) built on accessible headless primitives (Radix, or Base UI in newer shadcn projects) styled with Tailwind — you own the generated code outright, no runtime dependency to version-bump | Components live in your repo once generated — updates to shadcn's own templates don't auto-propagate (a deliberate tradeoff, not a bug) | **Default** — matches this framework's own Tailwind/CSS-token stack, gives real design control without hand-building accessibility behavior |
| **Radix UI primitives directly** | Headless accessible primitives as a real npm dependency, full styling freedom, what shadcn itself is built on | More assembly required than shadcn's pre-built components | Building a genuinely custom design system where shadcn's own component shapes don't fit |
| **MUI / Ant Design** | Complete, fully-styled component sets out of the box (Material Design / enterprise-data-table-heavy, respectively) | Harder to make *not* look like Material Design or Ant's own aesthetic — real friction for a distinctive visual identity (see `frontend-design`) | A large, data-table-heavy internal tool where shipping speed matters more than visual distinctiveness, or the team already standardized on one |

**Default: shadcn/ui**, consistent with this framework's Tailwind
default in `frontend-styling-concept` — it's the primitive layer
underneath everything the promotion rule below governs, not a
replacement for that rule (a shadcn component still only gets copied
into the shared tier once it has two real consumers, same as any other
component).

## Default: feature-local until promoted, not a shared folder from day one

`frontend-component-structure` already says every component lives in
its owning feature folder. This skill adds the one exception: a
component moves to a shared tier only when it is **actually used
identically by two or more feature folders** — the classic Rule of
Three's two-strikes-you-extract variant (see `Basis`). Don't pre-build
a `src/components/` (or `src/ui/`) folder speculatively "in case
something needs sharing later" — an empty or near-empty shared folder
is exactly the premature abstraction `AGENTS.md`'s own project rules
warn against. A project with no promoted component yet records "none —
feature-local only" in its profile row, and that is the *correct*
state, not a gap to fill.

## Promoting a component

1. **Confirm it's really the same component, not a coincidence.** Two
   buttons that happen to look similar today but serve different roles
   (a destructive confirm vs. a primary submit) are not automatically
   one shared component — check whether they're expected to change
   together before merging them.
2. **Move it to the shared tier** (`src/components/<Name>/`, same
   internal shape as a feature folder — co-located styles, its own
   barrel) and update both call sites to import from there instead of
   from each other's feature folder (a cross-feature deep import is
   exactly what `frontend-component-structure`'s barrel rule exists to
   prevent).
3. **Give it a closed variant API**, not an open escape hatch. Enumerate
   the actual variants/sizes as a typed union (`variant: 'primary' |
   'secondary' | 'danger'`), not a raw `className` prop that lets every
   call site reinvent its own appearance — an open style prop is how a
   shared component silently stops being shared in practice. An
   explicit **"why not just add a prop" exception** exists for truly
   generic HTML attributes (`disabled`, `aria-label`) — pass those
   through normally; the closed-API rule is about visual/behavioral
   variants, not accessibility or native attributes.
4. **Give it the accessibility baseline `frontend-accessibility`
   already states** before it has two consumers depending on it — a
   shared component's accessibility bugs multiply by every place that
   uses it, so this is not optional polish to add later.
5. **Record the promotion** in the profile's decision file
   (`decisions/design-system.md` if the move is non-obvious) — what was
   duplicated, why it's now one component, which call sites changed.

## Changing a promoted component's API later

A breaking change to a promoted component (removing a variant, changing
a required prop) is the same "changing a governed cell is a trigger"
situation `project-profile/SKILL.md` describes generally — update every
call site in the same change, don't leave one on the old shape. For a
solo/small-team project this framework does not impose a formal
semver/deprecation process (that belongs to the Level 4–5 "scaled/public
system" maturity tier most product teams never need — see `Basis`); a
dated line in the component's own decision file recording what changed
and why is enough until a project's real scale demands more.

## What this skill does not cover

Token values and naming — `frontend-styling-concept`. Component
file/folder structure mechanics and the barrel rule —
`frontend-component-structure`. The isolated dev/documentation
environment (Storybook or similar) for browsing and visually testing
these components — `frontend-component-workshop`.

## Basis (checked 2026-11-13)

- The "Rule of Three" (or its two-strikes variant used here) — extract
  shared code on the second duplication, not preemptively on the
  first guess that something *might* repeat — is long-standing,
  widely-cited refactoring guidance, not specific to design systems;
  applied here to component promotion specifically rather than
  arbitrary code reuse.
- Design-system maturity models converge on a 4–5 level ladder (UI kit →
  design library → design system → scaled system → public system) and
  explicitly note most product teams should target the middle tier
  (a documented, governed component set), with the top tier or two
  reserved for multi-product organizations — supporting "don't build
  the governed/versioned tier for a solo project":
  [Design system maturity](https://atomize.tools/blog/design-system-maturity/).
- shadcn/ui as copy-paste components owned in-repo (built on Radix, or
  Base UI in newer projects) vs. Radix UI directly vs. MUI/Ant Design's
  fully-styled, harder-to-restyle component sets: aggregated across
  multiple 2026 comparison posts, e.g.
  [shadcn/ui vs MUI vs Ant Design](https://adminlte.io/blog/shadcn-ui-vs-mui-vs-ant-design/) —
  download/star-count figures conflict between sources and are treated
  as directional only.
- Token names, component prop signatures, and slot/class names are all
  part of a shared component's public API surface, and a closed,
  intentional variant set (not an open style escape hatch) is what
  keeps that surface stable as more consumers depend on it:
  [Component API versioning for design systems](https://www.pathtoproject.com/blog/20260505-component-api-versioning-for-enterprise-design-systems.md).
