---
name: backend-stack-selection
description: Use when a project needs a custom backend — deciding language, web framework, API style, architecture pattern, database, ORM, auth mechanism, and background-job approach. Each is a real, bounded 2026 option set with tradeoffs and a stated default, not an open question. Not for the frontend's own client-side auth pattern (frontend-auth) or whether a frontend needs a backend at all (stack-selection routes here once it does).
---

# Backend stack selection — the option matrix for a custom backend

Governs `project-profile.md` fields: Backend → Language, Framework, API
style, Architecture pattern, Database, ORM / query layer, Request
validation (API boundary), Auth, Background jobs / queue, Transactional
email, File / object storage, API documentation, Search (ask explicitly
— see project-profile/SKILL.md).

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

**This is a default, not a mandate — per `DELEGATION-MODEL.md`'s
"a stated preference is a default, not a mandate" rule.** Every row below
keeps its real non-JS/TS alternatives live for exactly this reason: when
a specific task's actual technical requirement outgrows what Node/TS
reasonably does well, say so and name the better-suited option — a
single CPU-heavy service (video/image processing, ML inference, a
latency-critical hot path) written in Go, Rust, or Python *alongside* an
otherwise Node/TS codebase is a normal, expected outcome of this rule,
not a contradiction of the framework default. The goal is a project
that's JS/TS wherever that's genuinely the right tool, not JS/TS
everywhere regardless of fit.

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

**Default: layered/feature-folder monolith — this is the recognized best
practice, not a concession to project size.** "Monolith first" is Martin
Fowler's own named recommendation: even teams planning to end up with
microservices are told to start as a monolith until the real service
boundaries are known from working code, because guessing them upfront
reliably gets them wrong. Segment's widely-cited "Goodbye Microservices"
post is the sharper version of the same lesson — they built real
production microservices, hit the operational cost (every one needed its
own on-call, monitoring, deploy pipeline), and moved back to a monolith.
Netflix, Amazon, and other microservices-heavy companies got there after
years of monolith operation revealed the actual boundaries, not before.
Reaching for microservices/CQRS/DDD before a concrete trigger exists
(multiple teams needing independent deploys, a measured scaling mismatch
between specific services) isn't the advanced path skipped for
simplicity — it's the mistake the industry's own case studies warn
against. A monolith split into services later, once a real trigger
exists, is the normal, well-trodden evolution.

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
| **Prisma** | The most mature migration tooling/documentation of the two — typed migration history, auto-generated types from the schema; Prisma 7 dropped its Rust engine for pure TypeScript, much smaller bundle and faster cold starts | Its own schema language to learn (not plain SQL/TS) | **Default for this framework** — the deployment target here is a normal long-lived Node process, where Prisma's tooling maturity outweighs Drizzle's edge-specific advantage |
| **Drizzle** | Schemas are plain TypeScript, queries map directly to SQL (full visibility into what runs), smaller footprint, the clear choice for edge/serverless runtimes | Thinner migration tooling/docs than Prisma's | Deploying to Cloudflare Workers/Vercel Edge Functions, or the team wants queries that read as direct SQL |
| **Raw SQL** | No abstraction to learn or fight | No type safety, manual migration tracking | A very small project where the ORM's own overhead isn't worth it — rare as a deliberate choice, not a default |

**Default: Prisma.** Drizzle's real advantage (closer to raw SQL, smaller
footprint) matters most on edge/serverless runtimes — not this stack's
deployment target (`repo-hosting`'s managed-platform default runs a
normal long-lived Node process, not an edge function). On a plain Node
server, Prisma's migration tooling (typed migration history, a
documented path for schema drift, auto-generated types from the schema)
is the stronger default: it's the same reasoning as picking Fastify over
NestJS — take the option with less operational ceremony for the actual
deployment shape in front of you, not the one with the most theoretical
headroom. Switch to Drizzle the moment the deploy target becomes an edge
runtime, or the team wants the schema itself to be plain TypeScript.

## Request validation (API boundary)

TypeScript types are compile-time only — erased completely by the time
code runs, so they give zero protection against what actually arrives
over the network (a malformed body, a missing field, a client bug, a
hostile request). Every API boundary needs a **runtime** check that
real, arriving data matches the shape the handler assumes. This is a
distinct decision from the API-style row above — it's what validates
the data, independent of REST/tRPC/GraphQL.

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Zod** | Schema defined once in plain TypeScript, infers the static type from itself (`z.infer<typeof schema>`) — one definition is both the runtime check and the compile-time type; the same schema object is importable by the frontend's own form validation (`frontend-forms`'s React Hook Form + Zod default) with zero duplication in a shared-TS codebase | Slightly more verbose than some alternatives for deeply nested unions | **Default** — direct synergy with every other default in this stack: tRPC procedures take a Zod schema as their input validator natively, so this isn't an extra library bolted on, it's the same mechanism tRPC already needs |
| **Fastify's native JSON Schema** | Built into Fastify, no extra dependency, fastest validation (compiled ahead of time) | A separate schema language from TypeScript — no shared-type inference, can't reuse the schema on the frontend | Raw performance is the literal bottleneck and the schema never needs to cross into frontend code |
| **class-validator** (NestJS's own default) | Decorator-based, fits NestJS's DI/class model directly | Tied to NestJS's class-based style; doesn't fit a plain Fastify/tRPC setup | Already on NestJS, where it's the idiomatic choice |
| **Joi / Yup** | Mature, widely used historically | No first-class TypeScript type inference the way Zod has (Yup's is weaker; Joi has none built in) | An existing codebase already standardized on one — not a reason to start with it |

**Default: Zod**, validating every tRPC procedure's input (and every REST
handler's body/params/query, if REST is used instead) — this is not
optional hardening added later, it's part of the API boundary from the
first endpoint written, the same way `frontend-security` treats the
raw-HTML/XSS boundary as never-skip.

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

## Transactional email

Near-universal the moment `frontend-auth`/this skill's own Auth row
exists — password reset and email verification both need it, not just
a "nice to have" marketing feature.

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Resend** | Cleanest API for a TypeScript project, pairs with React Email for templates written as React components — the natural fit for this stack specifically | Younger company than the alternatives below | **Default** — matches this framework's own TypeScript-everywhere reasoning the same way tRPC/Zod do |
| **Postmark** | Repeatedly cited as the deliverability leader; strict separation of transactional from bulk mail (refuses marketing traffic on the same infra) | Slightly more expensive at the low end than Resend | Deliverability is the literal top priority (e.g. financial/time-sensitive transactional email) |
| **AWS SES** | Cheapest at real scale (~$0.10 per 1,000 messages) | You own reputation/bounce-handling yourself — real operational work | High volume, with the engineering capacity to manage deliverability directly |
| **SendGrid** | Transactional + marketing email from one vendor | Broadest/most complex deliverability history of the options here | Marketing email is also needed from the same vendor as transactional |

**Default: Resend.** Switch to Postmark if deliverability becomes a
measured problem, to SES once volume/cost makes self-managed
reputation worth it.

## File / object storage

Needed the moment a feature accepts a user-uploaded file (an avatar, a
document, an image) — storing it in the database or on the server's own
disk is not a default to reach for.

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Cloudflare R2** | S3-compatible API (same client libraries work), zero egress fees — the real cost difference at any real traffic volume (S3 charges for every byte served out) | Smaller feature surface than S3 (fewer storage classes, no Object Lock/WORM) | **Default** — egress cost alone makes this the right starting choice for a typical app serving files to users |
| **AWS S3** | Broadest feature set (versioning, Object Lock/WORM for regulated/immutable-storage needs, Storage Lens) | Egress fees add up fast once files are actually served to users | A regulated-industry need for immutable storage (WORM), or already deep in AWS for other reasons |
| **Supabase Storage** | Bundled with Supabase if that BaaS path was chosen instead of this framework's own stack (see the Database-hosting row's Supabase option in `repo-hosting`) | Another piece of Supabase lock-in, same tradeoff as that row | Already committed to Supabase as the bundled backend platform |

**Default: Cloudflare R2**, using the S3-compatible SDK so switching to
real S3 later (for a WORM/compliance need) is a config change, not a
rewrite.

## API documentation (build-trigger, not default-on)

With tRPC as this stack's default API style, the types themselves
already are the documentation for the one client that matters (the
project's own frontend) — a human-readable spec adds nothing there.

| Option | Pick it when |
|---|---|
| **None** | **Default** — tRPC + shared TypeScript types already give the frontend full autocomplete/type-checking on every procedure; a separate doc describes what the compiler already enforces |
| **OpenAPI/Swagger** (`@fastify/swagger` + `trpc-openapi` or a REST fallback) | A non-TypeScript or third-party client needs to read the API without access to the TS types — the same trigger as switching the API-style row itself toward REST |

**Default: none.** Add OpenAPI generation the moment a real external/
non-TS consumer exists — the same "ask when there's a real client, not
before" reasoning as the API-style row above, not separate scaffolding
to add speculatively.

## Search (ask explicitly — see `project-profile/SKILL.md`)

Not every project needs this row at all — ask explicitly whether the
product has a real search feature (not just filtering/sorting a list,
which plain SQL `WHERE`/`ORDER BY` already handles).

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **None** | Nothing to add | — | **Default** — most CRUD apps have no real search need, only filtering, which is just a query, not a search feature |
| **PostgreSQL full-text search** (`tsvector`/`tsquery`, or `pg_trgm` for fuzzy/typo-tolerant matching) | No new infrastructure — runs on the Postgres already in this stack | Weaker relevance ranking and typo tolerance than a dedicated search engine at real scale | A real search feature exists, data already lives in Postgres, and scale/relevance needs are modest — the default once search is needed at all |
| **Meilisearch** (self-hosted) or **Algolia** (managed) | Purpose-built relevance ranking, typo tolerance, faceting, fast at scale | A second system to sync data into and keep in sync with Postgres | Postgres FTS's relevance/typo-tolerance genuinely isn't good enough — a measured gap, not assumed upfront |

**Default: none until a real search feature is stated; PostgreSQL
full-text search once it is** — avoid adding a second search
infrastructure before Postgres's own capability has actually been
tried and found wanting, same reasoning as every other build-trigger
row in this skill.

## Next: scaffolding it

Once these rows are settled (the framework defaults, unless this project
states a reason to deviate), go to `backend-project-setup` for the actual
step-by-step walkthrough — project init, folder shape, database, first
feature, auth wiring — applying every default above instead of
re-deciding it.

## What this skill does not cover

Whether a backend exists at all, or routing here from the frontend
(`stack-selection`). The actual scaffolding steps (`backend-project-setup`).
The frontend's own client-side session-storage pattern (`frontend-auth`).
Hosting/deploy target for the backend service (`repo-hosting`) and
whether it needs containerizing (`repo-containerization`).

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
- Resend as the TypeScript-ecosystem consensus default, Postmark's
  deliverability reputation, SES's scale pricing: aggregated across
  multiple 2026 comparison posts, e.g.
  [Resend vs Postmark vs SES, 2026](https://dev.to/ericwoooo_kr/aws-ses-vs-postmark-vs-resend-which-one-actually-holds-up-when-youre-sending-real-email-in-2026-38da) —
  pricing figures conflict by source and change often.
- Cloudflare R2's zero-egress-fee advantage over S3, S3's broader
  feature set (WORM/Object Lock for regulated storage):
  [Cloudflare R2 vs AWS S3 vs Azure Blob vs GCS, 2026](https://inventivehq.com/blog/cloudflare-r2-vs-aws-s3-vs-azure-blob-vs-google-cloud-storage-comparison) —
  mostly vendor-authored comparisons; exact per-GB figures vary by source.
- "Monolith first" and the real-world case against premature
  microservices: Martin Fowler's own named article,
  [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html),
  and Segment's widely-cited production account,
  [Goodbye Microservices](https://segment.com/blog/goodbye-microservices/) —
  both are primary, named sources (not an aggregated blog consensus),
  which is why this row is argued more strongly than the others in this
  skill.
- Zod as tRPC's native input-validator mechanism and its type-inference
  advantage over Joi/Yup/class-validator: documented directly in tRPC's
  and Zod's own docs — a stable, structural fact about how the chosen
  stack's pieces fit together, not a trend that needs a freshness
  re-check the way a framework-popularity ranking does.

These are 2026 practitioner-consensus snapshots from aggregated blogs,
not a formal standards body — re-verify via `knowledge-refresh` before
trusting an old date here, same caveat as `frontend-stack-selection`.
