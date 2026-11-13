---
name: backend-testing
description: Use when deciding what to test and how in a backend project — unit tests for service logic vs. integration tests through the real router/validation chain. Not frontend component/e2e testing (frontend-testing) or deciding the stack itself (backend-stack-selection).
---

# Backend testing conventions

Scope: what gets a unit test vs. an integration test on the backend, and
what tool does each — the backend counterpart to `frontend-testing`,
same reasoning shape, different boundary (there's no DOM to approximate
here, only a network/database boundary).

Governs `project-profile.md` fields: Backend → Unit tests (backend),
Integration/API tests (backend).

## The default: unit-test the service layer, integration-test through the router

This follows directly from `backend-project-setup`'s own
schema → service → router layering — each layer has a different thing
worth testing, and a different right-sized tool for it:

1. **Unit test the service layer** (`<feature>.service.ts`) with
   Vitest. This is plain TypeScript with no Fastify/tRPC/HTTP involved,
   so it's directly testable — mock only the Prisma client (or run
   against a real test database, see below), not the whole request
   pipeline. This is where business-logic edge cases belong: what
   happens on a duplicate entry, an empty result, a boundary value.
2. **Integration-test through `appRouter.createCaller()`**, tRPC's own
   direct-call mechanism — it runs a request through the real router,
   the real Zod validation, and the real service, without going over
   HTTP. This is the default integration layer: it catches "the
   validation schema doesn't match what the service expects" and "the
   router wired the wrong procedure" in a way a mocked-service unit
   test never would, at a fraction of the cost of a real HTTP round
   trip. Use a real test database (a separate Postgres instance or
   schema, migrated the same way as dev) rather than mocking Prisma at
   this layer — the whole point is testing the real chain.
3. **Don't add a separate backend-only end-to-end HTTP layer
   (Supertest, a live server + real network calls) as a default.**
   `frontend-testing`'s own Playwright E2E tests already exercise the
   real backend over real HTTP as part of a full user flow — a second,
   backend-only HTTP test suite would duplicate that coverage for
   marginal benefit. Add one only for a backend with no frontend at all
   (a pure API service), where Playwright's own E2E layer never runs
   against it.

## Test database

A dedicated test database (a second Postgres database, or a schema reset
between runs), migrated via the same `prisma migrate` flow as dev — never
point tests at the dev database directly (state leaks between runs, and
a failed test can corrupt dev data).

## Test naming

Same convention as `frontend-testing`: `describe('functionName', ...)`
naming the unit under test, `it('<plain-English behavior>', ...)` with
no "should" — one shared convention across the whole codebase, not a
backend-specific variant.

## What this skill does not cover

End-to-end user-flow testing — `frontend-testing`'s Playwright layer
already covers the full stack. Load/performance testing — not a default
for a typical project; add it with a stated reason (a measured
bottleneck), the same build-trigger pattern as background jobs.

## Basis (checked 2026-11-13)

- `createCaller()` as tRPC's own documented mechanism for calling a
  router directly in tests, without an HTTP server — this is tRPC's own
  stated integration-testing pattern, not a third-party convention, so
  it doesn't need the same kind of practitioner-consensus check as a
  tooling popularity claim.
- The extract-logic-and-unit-test-it, cover-the-chain-with-integration-
  tests split mirrors `frontend-testing`'s own already-dated Basis
  section (extract and unit-test, cover behavior with a higher-fidelity
  layer) — same reasoning, applied to the backend's actual boundary
  (the router/validation chain) instead of the DOM.
