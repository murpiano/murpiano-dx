---
name: backend-project-setup
description: Use when starting a brand-new backend service from scratch, after backend-stack-selection has already decided language/framework/database/etc. — the step-by-step walkthrough that actually scaffolds it, confirming each piece before moving to the next. Not for adding a feature to an already-running backend, and not for deciding the stack itself (backend-stack-selection).
---

# Guided backend project setup

Scope: the hands-on walkthrough for standing up a new backend from
nothing — one step at a time, each one confirmed before the next, so the
owner sees and understands what's being built rather than receiving a
finished scaffold with no walkthrough. This is the *guided setup* tier
below `backend-stack-selection` (the *concept/implementation* tier), the
same shape `frontend-project-setup` already has for the frontend —
see `DELEGATION-MODEL.md`'s concept → implementation → guided-setup chain.

## The governing rule

Every piece below is already decided by `backend-stack-selection` — state
each default and apply it, don't re-ask. Pause for real input only where
this walkthrough explicitly says to (naming the project/database, a
feature's actual fields) — never for "should we use X or Y," which
`backend-stack-selection` already answered. If a step's own default is
ever wrong for this specific project, say so and name the concrete
reason before deviating — don't silently swap it.

## Step 0 — confirm the stack, don't re-derive it

Read (or create, via `stack-selection` → `backend-stack-selection`) the
project's `.agents/project-profile.md` Backend section. For a fresh
project with no overrides stated, this walkthrough assumes the framework
default end to end: **Node.js + TypeScript, Fastify, tRPC, PostgreSQL,
Prisma, Zod, layered feature-folder monolith, session-based auth via
Better Auth, no job queue yet.** Every step below names which of these it
implements so the chain stays visible.

## Step 1 — project init and folder shape

```
pnpm init
pnpm add fastify @trpc/server zod better-auth
pnpm add -D typescript tsx @types/node
```

`tsconfig.json`: `strict: true` from the start — this is
`repo-lint-format`'s own type-checking default, applied here at project
birth, not as a later tightening pass.

Folder shape — one feature-folder per business capability, mirroring
`frontend-component-structure`'s public-API-barrel convention so the
same mental model applies on both sides of the stack:

```
src/
  features/
    <feature>/
      <feature>.router.ts     # tRPC procedures — the API boundary
      <feature>.service.ts    # business logic, framework-agnostic
      <feature>.schema.ts     # Zod schemas (shared with the frontend)
      index.ts                # public barrel — only what other features import
  db/
    schema.prisma
    client.ts                 # one shared Prisma client instance
  trpc/
    trpc.ts                   # tRPC init — router()/publicProcedure/protectedProcedure
    router.ts                 # merges every feature router
    context.ts                # per-request context (session, db client)
  auth.ts                     # Better Auth instance
  env.ts                      # validated process.env (Step 4)
  server.ts                   # Fastify instance, plugin registration
```

This is the layered/feature-folder monolith `backend-stack-selection`
names as the default — router (API) → service (logic) → schema
(validation) is the layering, repeated per feature instead of per
technical layer across the whole app, which is what keeps a feature
readable as one unit instead of scattered across three app-wide folders.

Confirm this shape with the owner before creating the first real feature
folder — point at this template, don't regenerate it from scratch each
project.

## Step 2 — database: Postgres running locally

A local Postgres instance is needed before Prisma can do anything, even
though the chosen hosting default (`repo-hosting`) is a managed
platform, not Docker. These are two separate questions:

- **Local dev**: run Postgres via `docker-compose` for this one purpose
  — dev-environment parity, not deploy — even on a project whose
  deploy target itself is Docker-free. This is exactly the local-dev-
  parity trigger `repo-containerization` already names, not an exception
  to it.
- **Deploy**: a managed Postgres (the hosting platform's own add-on, or
  Railway/Render's managed database) — no Docker needed there either.

```yaml
# docker-compose.yml — local dev only
services:
  postgres:
    image: postgres:17
    environment:
      POSTGRES_PASSWORD: localdev
    ports: ["5432:5432"]
  # redis: only add this service once BullMQ (background jobs) or
  # Socket.IO's Redis adapter (realtime, multi-instance) is actually
  # adopted — not speculatively alongside Postgres by default.
  # redis:
  #   image: redis:7
  #   ports: ["6379:6379"]
```

`DATABASE_URL` (and `REDIS_URL` once Redis is actually added) goes in
`.env` (git-ignored) per `repo-hosting`'s secrets default — never
hardcoded.

## Step 3 — Prisma schema and first migration

```
pnpm add -D prisma
pnpm add @prisma/client
npx prisma init
```

Write the first model directly from the actual feature being built —
don't scaffold placeholder models. Then:

```
npx prisma migrate dev --name init
```

```ts
// src/db/client.ts — the one shared instance every feature imports
import { PrismaClient } from '@prisma/client';

export const prisma = new PrismaClient();
```

Import `prisma` from here everywhere a feature needs the database —
never call `new PrismaClient()` a second time; each instance opens its
own connection pool, and a second one is a real, easy-to-miss resource
leak, not just a style preference.

Every schema change from here on is a new named migration, never a
hand-edited database — this is what makes the migration history itself
the record of how the schema got here, which is Prisma's own stated
advantage in `backend-stack-selection`.

**Store every timestamp in UTC, always** — Prisma's `DateTime` maps to
Postgres `timestamptz`, which already stores in UTC internally; never
add a separate "local time" column or convert before storing. Convert
to the user's local time only at the display layer (frontend), using
the browser's own timezone, not a value baked into the database. This
is one of the most common real sources of off-by-hours bugs in a
project with users across more than one timezone — decided once, here,
rather than rediscovered as a bug later.

**Back up the database from day one, not after the first real data
loss.** Neon, Supabase, and RDS (`repo-hosting`'s Database hosting row)
all provide automated daily backups plus point-in-time recovery
out of the box — confirm it's actually enabled, don't assume a managed
database backs itself up by default on every plan tier. A self-hosted
Postgres (the 152-ФЗ-driven case in `repo-hosting`) needs this stated
explicitly: a scheduled `pg_dump` plus an off-site copy (not stored on
the same server/VM it backs up) and a periodically *tested* restore —
an untested backup is a hope, not a backup.

**Migrations are forward-only in production — rolling back means
writing a new, backward-compatible migration, not reversing the last
one.** `prisma migrate dev` is a local/dev-only command; once a
migration has run in production, "undo" it by writing a new migration
that reverses the change (dropping a column that was just added, say),
never by editing or deleting the applied migration file — the
migration history is the record of what actually happened to that
database, and rewriting it breaks that record for every environment
that already applied it. For any schema change with real downtime
risk on a live table (renaming or dropping a column still read by the
currently-deployed code), use the expand-and-contract pattern: add the
new column alongside the old one, deploy code that writes to both,
backfill, switch reads to the new column, *then* drop the old one in a
later migration — never a single migration that both app code and old
deployed instances could disagree about mid-rollout.

## Step 4 — Fastify server and the tRPC adapter

```
pnpm add @fastify/helmet @fastify/rate-limit @fastify/cors
```

```ts
// src/env.ts — validate process.env at startup, not on first use
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  NODE_ENV: z.enum(['development', 'production', 'test']),
  FRONTEND_ORIGIN: z.string().url(),
});
export const env = envSchema.parse(process.env);
```

Fail at boot, not three requests into production, if a required env var
is missing or malformed — the same runtime-validation reasoning as the
Request-validation row above, applied to configuration instead of
request bodies.

```ts
// src/trpc/router.ts — every feature's router merges in here (Step 5
// adds one `<feature>: <feature>Router` entry per feature; empty until
// the first one exists)
import { router } from './trpc';

export const appRouter = router({});
export type AppRouter = typeof appRouter;
```

```ts
// src/trpc/context.ts — per-request context, built once per request
import type { CreateFastifyContextOptions } from '@trpc/server/adapters/fastify';

export async function createContext({ req }: CreateFastifyContextOptions) {
  return { req, session: null as null | { userId: string } };
  // Step 6 replaces the `session: null` placeholder with a real lookup
  // once auth exists — every procedure already reads `ctx.session`.
}
export type Context = Awaited<ReturnType<typeof createContext>>;
```

```ts
// src/trpc/trpc.ts — tRPC's own init, imported by router.ts above and
// by every feature's <feature>.router.ts
import { initTRPC } from '@trpc/server';
import type { Context } from './context';

const t = initTRPC.context<Context>().create();
export const router = t.router;
export const publicProcedure = t.procedure;
```

```ts
// src/server.ts
import Fastify from 'fastify';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import cors from '@fastify/cors';
import { fastifyTRPCPlugin } from '@trpc/server/adapters/fastify';
import { appRouter } from './trpc/router';
import { createContext } from './trpc/context';
import { env } from './env';

const app = Fastify({ logger: true }); // Pino — Fastify's built-in
                                        // structured logger, not a
                                        // separate dependency
app.register(helmet);                  // standard security headers
app.register(cors, {
  origin: env.FRONTEND_ORIGIN,         // the frontend's actual origin —
  credentials: true,                   // never '*' once credentials is true
});
app.register(rateLimit, { max: 100, timeWindow: '1 minute' });
app.register(fastifyTRPCPlugin, {
  prefix: '/trpc',
  trpcOptions: { router: appRouter, createContext },
});
app.listen({ port: 3000 });
```

`FRONTEND_ORIGIN` joins `env.ts`'s schema above
(`z.string().url()`, e.g. `http://localhost:5173` in dev, the real
deployed frontend URL in production) — a frontend and backend almost
never share an origin even same-repo (different dev-server ports,
separate deploy targets), and Step 6's cookie-based session needs
`credentials: true` plus a named origin to work at all; the browser
rejects a cross-origin cookie request against a wildcard `origin: '*'`
outright. **This is the piece most often half-done**: `@fastify/cors`
gets installed (it's in the command above) but never actually
registered, or registered with no origin restriction — both leave the
API either unreachable from the frontend or open to any origin.

`logger: true` turns on Pino, which Fastify already ships with — no
separate logging library to add. This is the backend's structured-log
output; pair it with the Sentry Node SDK (same service `frontend-monitoring`
already picked for the frontend, so one dashboard covers both sides) once
error *reporting* (not just logging) matters — add that the same way any
other deferred-trigger row gets added, not speculatively on day one.

`@fastify/helmet` and `@fastify/rate-limit` are not optional hardening
added later — a public-facing API with no rate limiting and no security
headers is a real, known class of vulnerability from the first deployed
request, the same "never-skip" treatment `frontend-security` gives the
XSS boundary.

This is the one piece of genuinely new wiring per project — everything
above it is the stack's own settled shape. Confirm the server starts and
responds before writing the first real feature router.

## Step 5 — first feature: schema → service → router

For each feature, in this order (not router-first — the validation
boundary and the logic underneath it should exist before the API
surface that calls them):

1. **`<feature>.schema.ts`** — the Zod schema for this feature's inputs.
   This file is the one both this backend and the frontend's own form
   (`frontend-forms`'s React Hook Form + Zod default) can import from a
   shared location if frontend and backend share a repo/package — don't
   write the shape twice.
2. **`<feature>.service.ts`** — the actual logic, calling Prisma,
   containing no Fastify/tRPC-specific code so it stays testable in
   isolation.
3. **`<feature>.router.ts`** — a tRPC procedure per operation, each one
   `.input(theZodSchema)` validating before the service is ever called
   — this is `backend-stack-selection`'s Request-validation row applied,
   not an optional extra step.
4. **`index.ts`** — export only what another feature or `trpc/router.ts`
   actually needs.

Write the service-layer unit tests and the router-level integration test
(via `createCaller()`) alongside the feature, not as a separate pass
afterward — see `backend-testing` for which layer gets which kind of
test and why.

## Step 6 — auth

Wire Better Auth with a session-based (cookie) strategy — matching
`frontend-auth`'s already-chosen client-side cookie pattern, so both
ends agree on the mechanism without either side improvising. Better Auth
manages its own cookies through its Fastify route handler below — no
separate `@fastify/cookie` plugin needed, and none was installed in
Step 1.

```ts
// src/auth.ts
import { betterAuth } from 'better-auth';
import { prismaAdapter } from 'better-auth/adapters/prisma';
import { prisma } from './db/client';
import { env } from './env';

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: 'postgresql' }),
  // Cross-origin requests are blocked by default even with Step 4's
  // CORS plugin registered — Better Auth checks this separately.
  trustedOrigins: [env.FRONTEND_ORIGIN],
});
```

```ts
// src/server.ts — add alongside the Step 4 registrations
import { fromNodeHeaders } from 'better-auth/node';
import { auth } from './auth';

app.route({
  method: ['GET', 'POST'],
  url: '/api/auth/*',
  async handler(request, reply) {
    const url = new URL(request.url, `http://${request.headers.host}`);
    const req = new Request(url, {
      method: request.method,
      headers: fromNodeHeaders(request.headers),
      ...(request.body ? { body: JSON.stringify(request.body) } : {}),
    });
    const response = await auth.handler(req);
    reply.status(response.status);
    response.headers.forEach((value, key) => reply.header(key, value));
    return reply.send(response.body ? await response.text() : null);
  },
});
```

Confirm which routes require a session (most of them) vs. which are public
(login, signup, health check) before writing the first protected
procedure. Replace Step 4's `session: null` placeholder in
`trpc/context.ts` with a real lookup, resolved once per request, not
per procedure:

```ts
// src/trpc/context.ts — replaces Step 4's placeholder body
import type { CreateFastifyContextOptions } from '@trpc/server/adapters/fastify';
import { fromNodeHeaders } from 'better-auth/node';
import { auth } from '../auth';

export async function createContext({ req }: CreateFastifyContextOptions) {
  const session = await auth.api.getSession({
    headers: fromNodeHeaders(req.headers),
  });
  return { req, session };
}
export type Context = Awaited<ReturnType<typeof createContext>>;
```

```ts
// src/trpc/trpc.ts — add the protected-procedure helper alongside
// Step 4's publicProcedure
import { TRPCError } from '@trpc/server';

export const protectedProcedure = t.procedure.use(({ ctx, next }) => {
  if (!ctx.session) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({ ctx: { ...ctx, session: ctx.session } });
});
```

Every feature's router (Step 5) imports `protectedProcedure` instead of
`publicProcedure` for anything that isn't explicitly public — checked
once in this one place, not re-implemented per router.

**Login, signup, and password-reset need their own, stricter rate
limit — Step 4's app-wide `@fastify/rate-limit` is not enough on its
own.** A documented real-world gap: a platform's default brute-force
protection not covering its own Forgot Password endpoint, because that
endpoint wasn't included in the general limit. Apply a tighter,
per-route limit (e.g. 5 attempts per 15 minutes) to these three routes
specifically, keyed by **both** the account identifier and the IP
(per-account alone misses a password-spray attack trying one password
across many accounts; per-IP alone misses a distributed attack) — and
keep the response generic either way ("if that email exists, we sent a
reset link") so the endpoint itself can't be used to confirm which
emails have accounts.

## Step 7 — what's deliberately not here yet

- **Background jobs** — `backend-stack-selection`'s own default is none
  until a real on-demand job exists. Don't scaffold BullMQ/Graphile
  Worker speculatively; add it as its own step when a real feature
  needs it, naming which trigger from that skill's table applies.
- **A second service / microservice split** — not before a real,
  measured reason exists (see `backend-stack-selection`'s Architecture
  pattern section). This walkthrough only ever scaffolds one service.
- **Error *reporting* (Sentry) beyond structured logging** — Step 4's
  Pino logging is on from the start; wiring the Sentry Node SDK on top
  of it is a deferred-trigger addition (real production traffic worth
  monitoring), not day-one scaffolding.

## Step 8 — record anything new

If this project's actual experience surfaces something worth keeping —
a folder-shape tweak, a Prisma pattern, a tRPC middleware worth reusing
— propose landing it back into `backend-stack-selection` or this file,
the same "land every substantive discussion back in the framework" rule
`DELEGATION-MODEL.md` states for every domain.

## What this skill does not cover

Which technology to use for each row — that's already decided by
`backend-stack-selection`; read it, don't re-ask it. Day-to-day feature
work once the scaffold exists (Step 5's shape is the ongoing pattern,
not a one-time step repeated only here).
