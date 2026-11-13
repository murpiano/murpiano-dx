---
name: backend-stack-selection
description: Use when a project needs a custom backend — deciding language, web framework, API style, architecture pattern, database, ORM, auth mechanism, and background-job approach. Each is a real, bounded 2026 option set with tradeoffs and a stated default, not an open question. Not for the frontend's own client-side auth pattern (frontend-auth) or whether a frontend needs a backend at all (stack-selection routes here once it does).
---

# Backend stack selection — the option matrix for a custom backend

Governs `project-profile.md` fields: Backend → Language, Framework, API
style, Architecture pattern, Database, ORM / query layer, Auth,
Background jobs / queue.

Scope: `stack-selection` decides a project needs a backend at all and
routes here. This skill is the backend's own tier-0 — same role
`frontend-stack-selection` plays for the frontend — eight rows, each a
real option set with a reasoned default, confirmed in this order because
each later row depends on the one before it (language constrains
framework; framework and API style constrain how much structure the
architecture row needs; database constrains the ORM).

**This framework's maintainer default: Node.js + TypeScript.** Not
because it's the only valid backend stack — the table below is honest
about the real alternatives — but for a stated, legitimate reason:
sharing one language across frontend and backend means every file in the
project is readable with the same knowledge, and it's the one precondition
for the tRPC end-to-end-types option this framework's own
`frontend-stack-selection` already prefers for a single-codebase app.
Per `DELEGATION-MODEL.md`'s "project-level overrides" rule, team fluency
is itself a valid, explicit override reason — it doesn't need to be
re-litigated per project once stated here.

## Language

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Node.js + TypeScript** | Same language as the frontend — one mental model, one type system, tRPC becomes possible; huge package ecosystem (npm) | Single-threaded event loop needs care for CPU-heavy work (rarely the bottleneck for a typical CRUD/API backend) | **Default** — the project's own frontend is already TypeScript, or the team's own fluency is in JS/TS |
| **Python** | Best ecosystem for data/ML-adjacent work (pandas, PyTorch); FastAPI is excellent and simple | A second language and type system alongside a TS frontend | The project is data/ML-heavy, or the team is already Python-fluent and there's no frontend-language-sharing benefit to give up |
| **Go** | Compiled, fast, excellent concurrency primitives, tiny deploy artifacts | More verbose for typical CRUD; smaller web-framework ecosystem than Node/Python | High-concurrency/low-latency services, or a team that already knows Go |
| **Java/Kotlin, C#/.NET** | Mature, strongly-typed, proven at large enterprise scale | Heavier setup/ceremony than the above for a small project | Enterprise context already standardized on the JVM or .NET |
| **Rust** | Maximum performance and memory safety | Steepest learning curve, slowest to write for a typical web backend | Performance is the literal bottleneck and the team has Rust experience |

**Default: Node.js + TypeScript**, for the stated reason above. Pick
something else only for a concrete reason (a data/ML workload, an
existing non-JS team), not speculatively.

## Framework (assuming Node.js + TypeScript)

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Fastify** | Fast (consistently benchmarks ahead of Express — tens of thousands of req/s higher in most 2026 comparisons), first-class TypeScript support, schema-based validation built in | Smaller plugin ecosystem than Express's long tail | **Default** — a new TypeScript backend with no reason to want heavier structure |
| **Express** | The most familiar, largest tutorial/StackOverflow coverage, simplest mental model | 2026 sources show new-project adoption falling sharply; no built-in TS-first validation/structure | An existing Express codebase, or genuinely wants the simplest possible thing with no schema validation layer |
| **NestJS** | Full, Angular-inspired structure (modules, DI, decorators) — enforces consistency across a large team/codebase; can run on the Fastify adapter underneath for speed | Steepest learning curve of the three (real ramp-up time for a newcomer); likely overkill for a solo project | A large team needs enforced architecture, or the project is expected to grow well past a single maintainer |

**Default: Fastify.** It gets the performance and TS-native ergonomics
without NestJS's ceremony — right-sized for a solo/small-team project.
Move to NestJS only once team size or enforced structure becomes a real
need, not before.

## API style

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **tRPC** | End-to-end TypeScript types with zero schema layer — a frontend call is type-checked against the actual backend function, catches mismatches at compile time | Only works when frontend and backend are both TypeScript in the same or tightly-coupled repos — no third-party client story | **Default** — matches this framework's own frontend default (`frontend-stack-selection`'s Data fetching row already picks tRPC+TanStack Query for this exact case) |
| **REST** | Universally understood, works with any client, simplest to debug with generic tools | No automatic type-sharing — a frontend/backend mismatch is a runtime bug, not a compile error | A public/third-party API, or any non-TypeScript client needs to call it |
| **GraphQL** | One query shape serves many different clients with different data needs | Real setup overhead (resolvers, schema) wasted on a single first-party client | Multiple real clients (web, mobile, a partner API) actually exist with different data shapes |
| **gRPC** | Highest performance, strict contracts, great for service-to-service calls | Not browser-native (needs a proxy), unfamiliar to most frontend-only developers | Internal service-to-service communication, not a browser-facing API |
| **WebSocket** | Real-time, bidirectional | Not a general API style — a transport for specific features | A specific feature needs live updates (chat, live collaboration) — layered alongside one of the above, not a replacement for it |

**Default: tRPC**, for the single-client TypeScript case this framework
already assumes. Fall back to REST the moment a non-TypeScript or
third-party client enters the picture.

## Architecture pattern

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Layered / feature-folder monolith** (routes → service → data-access layers, grouped per feature) | Simple to understand and navigate; mirrors the frontend's own public-API-barrel-per-feature convention (`frontend-component-structure`) | Can get tangled if business logic isn't kept out of route handlers | **Default** — a solo/small-team project, especially a first backend |
| **Clean / hexagonal architecture** | Business logic fully isolated from framework/DB specifics — easy to swap either later, very testable | Real ceremony (ports/adapters/use-cases) that's wasted on a small, simple app | Business logic is genuinely complex and expected to outlive the current framework/DB choice |
| **DDD (Domain-Driven Design)** | Models match real business language/boundaries for a complex domain | Significant upfront modeling investment | A large, complex business domain with a team that can sustain the modeling discipline |
| **CQRS** | Separates read/write models — scales reads and writes independently | Real complexity; usually paired with event sourcing | A specific, measured read/write scaling mismatch — not a starting architecture |
| **Microservices** | Independent deployability and scaling per service | Full distributed-systems tax: network calls where there were function calls, deployment/observability overhead | Multiple teams need to ship independently, or one specific service has a real, separate scaling need — never a starting point |

**Default: layered/feature-folder monolith.** Don't reach for clean
architecture, DDD, CQRS, or microservices speculatively — same
premature-infrastructure caution already applied to Docker
(`repo-containerization`) and feature flags (`frontend-feature-flags`).
A monolith split into services later, once a real trigger exists, is a
normal evolution, not a mistake to avoid up front.

## Database

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **PostgreSQL** | The 2026 consensus default: structured data, complex queries/joins, ACID, and an extension ecosystem (pgvector, PostGIS) that covers most "but what if I need X later" cases without switching databases; JSONB covers document-shaped data too, narrowing Mongo's advantage | None significant for a typical app | **Default** |
| **MongoDB** | Good fit when data is genuinely document-shaped and the schema changes often/unpredictably | Loses the relational/ACID guarantees a typical app benefits from; Postgres's JSONB already covers most of the flexible-schema case | Data is genuinely document-shaped with frequent, unpredictable schema change — a real, stated reason, not a default |
| **MySQL** | Mature, widely hosted | No real technical advantage over Postgres for a new project | An existing team/hosting environment already standardized on it |
| **SQLite** | Zero setup, a single file, great for prototypes and genuinely single-user/local apps | No real concurrent-write story for a multi-user service | A prototype, a CLI tool, or a local-first single-user app |
| **Redis** | Not a primary database — an in-memory cache/queue-backing store | — | Alongside Postgres, for caching or as BullMQ's backing store (see Background jobs row) — not instead of it |

**Default: PostgreSQL.** This is the strongest formal consensus of any
row in this skill (Stack Overflow-level adoption data, not just blog
opinion) — don't default to MongoDB without a stated document-shaped-data
reason.

## ORM / query layer

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Prisma** | The most polished migration/tooling experience and documentation of the two — matters most for someone newer to backend/SQL; Prisma 7 dropped its Rust engine for pure TypeScript, much smaller bundle and faster cold starts | Its own schema language to learn (not plain SQL/TS) | **Default for this framework** — the more beginner-friendly migration workflow matters more than Drizzle's edge advantage for a Node-server (not edge-function) deployment |
| **Drizzle** | Schemas are plain TypeScript, queries map directly to SQL (full visibility into what runs), smaller footprint, the clear choice for edge/serverless runtimes | Thinner tooling/docs than Prisma's for migrations as a newcomer | Deploying to Cloudflare Workers/Vercel Edge Functions, or the team already knows SQL well and wants a thinner layer |
| **Raw SQL** | No abstraction to learn or fight | No type safety, manual migration tracking | A very small project where the ORM's own overhead isn't worth it — rare as a deliberate choice, not a default |

**Default: Prisma**, specifically because this framework's standing
assumption is a team newer to backend/SQL (per the owner's own stated
learning stage) — Prisma's migration tooling and documentation reduce
that specific risk more than Drizzle's edge-runtime or SQL-proximity
advantages matter for a plain Node.js server deployment (not an edge
function).

## Auth (backend mechanism)

Distinct from `frontend-auth`'s client-side row (where the session token
lives in the browser) — this is what the server actually issues and
verifies.

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Session-based (server-side session, `HttpOnly` cookie)** | Simplest to revoke (delete the server-side session); matches `frontend-auth`'s own already-chosen cookie default, so both ends agree on the mechanism | Needs a session store (the database, or Redis) | **Default** — pairs directly with `frontend-auth`'s cookie-based session default |
| **JWT** | Stateless — no server-side session store needed, easy to verify across services | Harder to revoke before expiry (needs a blocklist to do it properly, which erodes the "stateless" benefit) | Multiple independent services need to verify identity without a shared session store |
| **OAuth2 / SSO (Google, GitHub, ...)** | No password handling at all; fast to ship | Dependent on the provider; still need a session mechanism (above) once the user is back on your app | "Sign in with Google/GitHub" is a real product requirement — usually layered on top of session-based auth, not a replacement for it |

**Library: Better Auth** (TypeScript-native, self-hosted, actively
maintained) is the 2026 default for a new Node.js project — Lucia (the
previous lightweight default) stopped receiving updates in mid-2025 and
its own docs now point newcomers to Better Auth or Auth.js instead;
Auth.js itself moved to security-only maintenance under the Better Auth
project. Auth.js remains a reasonable pick specifically if the project
needs its 80+ built-in OAuth provider integrations and is Next.js-based.

**Default: session-based auth via Better Auth.**

## Background jobs / queue

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **None** | Nothing to run or maintain | — | **Default** — most CRUD apps have no real background-job need at first |
| **Cron (scheduled, no queue)** | Simplest possible "runs later" mechanism | No retry/failure handling, no on-demand triggering | A periodic task (nightly cleanup, a scheduled report) with no need to enqueue work on demand |
| **BullMQ (Redis-backed queue)** | The 2026 de-facto standard for Node/TypeScript job queues — retries, delayed jobs, rate limiting, concurrency control | Needs Redis running alongside the app — real infra to add | On-demand background work (emails, image processing, webhooks) with retry/failure handling actually needed |
| **Graphile Worker (PostgreSQL-backed queue)** | Same job-queue guarantees as BullMQ without adding Redis — runs on the Postgres already in this stack | Smaller ecosystem/community than BullMQ | Same need as BullMQ, but avoiding a second piece of infrastructure (Redis) matters more than BullMQ's larger ecosystem |

**Default: none, until a real on-demand background-work need exists**
— the same build-trigger pattern as Docker and feature flags: name the
trigger explicitly when this row comes up rather than leaving it
unconsidered. Once needed: **BullMQ** if Redis is already acceptable
infrastructure, **Graphile Worker** if the project wants to avoid adding
Redis on top of the already-chosen Postgres.

## What this skill does not cover

Whether a backend exists at all, or routing here from the frontend
(`stack-selection`). The frontend's own client-side session-storage
pattern (`frontend-auth`). Hosting/deploy target for the backend service
(`repo-hosting`) and whether it needs containerizing (`repo-containerization`).

## Basis (checked 2026-11-13)

- Fastify's throughput lead over Express and NestJS's structure-vs-overhead
  tradeoff: [NestJS vs Fastify vs Express, 2026](https://dev.to/ihor_ostin/nestjs-vs-fastify-vs-express-which-backend-wins-in-2026-2ep2),
  cross-checked against the broader 2026 roundup noting Express's new-project
  adoption falling sharply. Benchmark req/s figures vary by source (treated
  as directional, not exact).
- Prisma 7's move to a pure-TypeScript engine (dropping the Rust query
  engine) and its more polished migration tooling vs. Drizzle's SQL-proximity
  and edge-runtime advantage: [Prisma vs Drizzle vs TypeORM, 2026](https://encore.dev/articles/prisma-vs-drizzle-vs-typeorm).
- PostgreSQL as the 2026 consensus default, with Stack Overflow-level
  adoption figures (~55.6% vs. MongoDB's ~24–26%) as the more credible
  anchor among the sources checked: aggregated across multiple 2026
  comparison posts, e.g. [MongoDB vs PostgreSQL, 2026](https://dev.to/philip_mcclarence_2ef9475/postgresql-vs-mongodb-in-2026-when-to-choose-sql-over-nosql-1no1).
- Lucia's maintenance stopping (last push mid-2025) and its own docs
  redirecting new projects to Better Auth/Auth.js; Better Auth as the
  2026 default, Auth.js's move to security-only maintenance under it:
  aggregated across multiple 2026 auth-library comparison posts, e.g.
  [Self-hosted Node.js authentication in 2026](https://dev.to/noorix1/self-hosted-nodejs-authentication-in-2026-9ao).
- BullMQ as the de-facto standard Node.js job queue, Graphile Worker as
  the Postgres-native alternative avoiding a Redis dependency:
  aggregated across multiple 2026 job-queue comparison posts.

These are 2026 practitioner-consensus snapshots from aggregated blogs,
not a formal standards body — re-verify via `knowledge-refresh` before
trusting an old date here, same caveat as `frontend-stack-selection`.
