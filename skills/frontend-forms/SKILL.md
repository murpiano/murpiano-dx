---
name: frontend-forms
description: Use when building or reviewing a form — validation library choice, client/server validation split, error display, and double-submit prevention. Not about a specific field's accessibility semantics beyond error association (frontend-accessibility covers labels/roles generally) or the auth login form specifically (frontend-auth).
---

# Forms & validation

Governs `project-profile.md` fields: Frontend → Forms & validation.

## Default library: React Hook Form + Zod

For a project building more than a couple of simple forms: **React Hook
Form** for form state (uncontrolled inputs, near-zero re-renders per
keystroke) with **Zod** for the validation schema, bridged by
`@hookform/resolvers`. Reasoning: this is the most-adopted 2026 pairing
by a wide margin (download counts, ecosystem examples) — same
"mainstream over niche" default this framework already applies to
react-i18next and React Router. See `Basis`.

- **TanStack Form is a stated non-default alternative** for a project
  with genuinely complex, deeply nested, or dynamically-generated
  forms where its type inference earns the smaller ecosystem.
- **Formik is legacy** — don't pick it for new work; it's
  maintenance-only at this point.
- **Hand-rolled validation remains acceptable** for a small, fixed set
  of simple forms (a handful of fields, no dynamic structure) — don't
  force a project to adopt a library it doesn't need yet just because
  this is the default. A project with hand-rolled validation and no
  real pain from it records that as its own value, not a gap; only
  propose migrating when the hand-rolled code is visibly straining
  (duplicated validation logic across forms, a bug from validation
  drifting out of sync between two call sites).

## Client validation is UX, server validation is the actual guarantee

Client-side validation (whichever mechanism) exists to give fast
feedback — it is never the only check. Whatever receives the submitted
data (a custom backend, a BaaS's own rules/row-level security) must
re-validate independently; a client check that's bypassed (disabled JS,
a direct API call, a modified request) must not be able to write
invalid data. Don't treat "the form already validates this" as a
reason to skip the same check server-side.

## Error display

- Associate an error message with its field via `aria-describedby`
  pointing at the message's `id` — color alone (a red border) is not
  sufficient; `frontend-accessibility`'s general labeling rules apply
  here, this is the form-specific instance of them.
- Show the error next to the field it belongs to, not only in a summary
  at the top — a summary is a useful addition for a long form, not a
  replacement for inline errors.
- Validate on blur or submit, not on every keystroke before the user
  has finished typing — showing "invalid email" after the first
  character is noise, not help.

## Double-submit guard

Disable the submit control (and show a pending state — `saving…` or
similar) from the moment a submission starts until it resolves, so a
second click (impatience, a slow network) can't fire the request twice.
This is the same in-flight-state pattern `frontend-resilience` already
names for loading states generally, applied specifically to form
submission.

## Basis (checked 2026-11-13)

- React Hook Form + Zod is the dominant 2026 pairing by adoption and
  download count, with Zod's schema giving both runtime validation and
  static types from one definition; TanStack Form is the stated
  alternative for complex/dynamic forms needing deeper type inference;
  Formik is explicitly called maintenance-only/legacy at this point:
  [Choosing a React form library in 2026](https://formisch.dev/blog/react-form-library-comparison/),
  [React Hook Form vs. TanStack Form](https://blog.logrocket.com/tanstack-form-vs-react-hook-form/).
