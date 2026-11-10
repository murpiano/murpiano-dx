---
name: frontend-testing
description: Use when deciding what to test and how in a frontend project — unit tests vs end-to-end, whether to render a component in isolation, test naming/describe-block style. Not about styling or module structure (frontend-web-styles, frontend-component-structure). Applies whenever writing a new test file or deciding a feature needs test coverage.
---

# Frontend testing conventions

Scope: what gets a unit test, what gets an end-to-end test, and how a
test is named. Not a testing-library tutorial — this settles the
framework's own default so it isn't re-decided per project.

## The default: extract logic, test the function; cover behavior with e2e

Don't render a component in isolation (no React Testing Library /
jsdom component tests) as this framework's default. Instead:

1. **Pull branching/computational logic out of the component** into a
   plain function in a sibling file (e.g. `cardRole`/`wheelSteps` in
   `stack.ts`, next to the component that uses them) — this is also
   what makes the logic genuinely unit-testable, since a plain function
   has no render tree, no DOM, no mocking a store or a ref.
2. **Unit-test that function** with Vitest, colocated as
   `name.test.ts` next to `name.ts`. This is where almost all of a
   typical frontend project's tests live: data transforms, state
   stores, date/geometry/animation math, backend clients — anything
   that isn't "does this JSX render the right DOM."
3. **Cover actual component behavior and user flows with end-to-end
   tests** (Playwright) against the running app, not a jsdom
   approximation — a real browser catches what jsdom can't, and an e2e
   test exercises the real integration (routing, backend, multiple
   components together) that a single component test never would.

**When to deviate**: if a component accumulates enough branching logic
that it can't reasonably be extracted (rare, once step 1 is actually
followed), or a real defect pattern shows component-level bugs e2e
isn't catching, add a component-rendering test for that one component
— state the reason, don't reach for it as a default habit.

## Test naming

- `describe('functionName', ...)` — the describe block names the unit
  under test, not a vague category.
- `it('<plain-English behavior, no "should">', ...)` — a domain expert
  without programming knowledge should be able to read the name and
  know what's being checked. "puts the current album in front with its
  neighbours around it, in a loop", not "should return correct role" or
  "test 1".
- One `it` can assert several related cases of the same behavior
  (several `expect()` calls) when they're genuinely one behavior being
  demonstrated with a few inputs — don't force one assertion per `it`
  if that fragments a single behavior into noise.

## Basis (checked 2026-11-07)

- Skipping isolated component tests in favor of end-to-end plus
  narrowly-scoped unit tests is a named, real alternative — Thoughtworks'
  Technology Radar notes some teams take this path instead of mastering
  component testing, while stopping short of endorsing it over keeping
  component tests:
  [Thoughtworks Radar — component testing](https://www.thoughtworks.com/en-us/radar/techniques/component-testing).
  A jsdom-rendered component test sits in an awkward middle: much slower
  than a unit test, much less faithful than a real browser:
  [component-tests-off-by-default](https://react-saas-course.pages.dev/089-component-tests-off-by-default/1-when-rtl-earns-its-weight/).
- Test names should read as plain-English behavior statements a
  non-programmer could follow, not a rigid
  `UnitOfWork_State_ExpectedResult` template or a bare "should ...":
  [frontend testing guide — naming](https://dev.to/alexanderop/frontend-testing-guide-10-essential-rules-for-naming-tests-3kfl).
  The "should" question has no consensus; this framework drops it,
  matching what `my-world`'s own test suite already did consistently
  before this was written down.

This is a judgment call about *this framework's* default, not a claim
that component-rendering tests are wrong in general — a project with a
real reason (a complex design-system component library, a defect
history concentrated in component logic) states that reason and adds
React Testing Library, the same way any other non-default choice in
this framework gets settled once per project.

## What this skill does not cover

Which end-to-end tool to use, or how to structure one — that's
project-specific infrastructure, not settled here yet. Styling or
module-organization conventions — `frontend-web-styles`,
`frontend-component-structure`.
