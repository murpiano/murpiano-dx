# Project profile — <project name>

One standing picture of this project: what it is, what it is built with,
how work flows through it. Filled once at connect/creation, updated
whenever something changes. Read this before asking the owner something
it already answers; a question this table has a value for is a question
already settled, not one to re-ask.

The section order below (Identity → Application type & platforms →
Frontend → Backend → Infrastructure & delivery → Git workflow →
Constraints) is the confirmation order, not just a filing order — a
bigger, earlier decision constrains the smaller ones that come after
it, so `repo-init` and `stack-selection` walk every project's table
top to bottom, section by section, row by row, in this same order
every time. See `repo-init/SKILL.md` → "Adopting an existing project's
own conventions" for the full rule.

Leave an inapplicable section's rows as `—`; don't delete the section —
a later change (e.g. adding a backend to a frontend-only app) fills it
in instead of re-deriving the table's shape from scratch.

A value that had real alternatives or a non-obvious reason gets its own
decision file (`decisions/<field-slug>.md`, from
[decision.md](decision.md)) and is written as `Value — [why](decisions/<field-slug>.md)`.
Most rows don't need one — a trivial or forced choice stays a plain
value; don't create a decision file just to have one for every row.

A row's **Governed by** column, when filled, names the framework skill
that owns this field — this value is not free text, it is a technology
name the framework can act on. An empty **Governed by** means this row
is plain information with no skill behind it (yet, or ever). See
`skills/project-profile/SKILL.md` → "Changing a governed cell is a
trigger, not cosmetics" before editing a governed row's value.

## 1. Identity

| Field | Value | Governed by |
|---|---|---|
| Project kind | app / framework / npm-package / library / landing page / personal-brand / internal tool | `repo-readme` |
| One-line description | | |
| Team | solo / team (size) | |
| Repository | | `repo-init` |
| Visibility | private / public | `repo-init` |
| Project status | prototype / active / maintenance / archived | |

## 2. Application type & platforms

| Field | Value | Governed by |
|---|---|---|
| Primary platform | browser web app / Electron / Tauri / native desktop / native mobile / cross-platform mobile (React Native, Expo) / backend service / CLI / library | `stack-selection` |
| Secondary platforms | — if single-platform | `stack-selection` |
| Target OS / browser support | evergreen browsers (web) / latest 2 OS versions (native, mobile) — adjust if stated otherwise | `stack-selection` |

## 3. Frontend

*(leave every row `—` if this project has no frontend)*

Rows go stack → app architecture → UI/design system → feature patterns
→ dev/verification tooling — each tier builds on the one before it, so
confirm them in this order every time (see `repo-init`'s own rule).

| Field | Value | Governed by |
|---|---|---|
| Language | JavaScript / TypeScript | `stack-selection` |
| UI framework | React / Vue / Svelte / Angular / vanilla | `frontend-stack-selection` |
| Meta-framework | Next.js / Nuxt / Remix / Astro / none | `frontend-stack-selection` |
| Module structure | public-API barrel per feature folder (framework default) / other | `frontend-component-structure` |
| Bundler | Vite / Webpack / Turbopack / esbuild / Parcel | `frontend-stack-selection` |
| Package manager | npm / pnpm / yarn / bun | `frontend-stack-selection` |
| Routing / navigation | library (name it) / client-state only, no router / none (single view) | `frontend-routing` |
| Auth / session handling (frontend) | none — no accounts / login-redirect flow, protected routes, session storage (name the approach) | `frontend-auth` |
| State management | Redux / Zustand / Context API / MobX / Recoil / none | `frontend-stack-selection` |
| Data fetching | REST client / GraphQL client (Apollo, urql) / tRPC / server actions | `frontend-stack-selection` |
| Design system / shared components | none — feature-local only / shared component library (name its location) | `frontend-design-system` |
| Styling approach | CSS Modules / Tailwind / SCSS+BEM / CSS-in-JS (Emotion, styled-components) / vanilla-extract | `frontend-styling-concept` |
| Theming / dark mode | none / light+dark / multi-brand | `frontend-theming` |
| Motion/animation approach | CSS transitions only / library (name it) / none stated | `frontend-motion` |
| Forms & validation | none built yet / client-only / client+server — library (name it) or hand-rolled | `frontend-forms` |
| Component dev/doc workshop | Storybook / Ladle / none | `frontend-component-workshop` |
| Unit/component tests | Vitest / Jest / none | `frontend-testing` |
| E2E tests | Playwright / Cypress / none | `frontend-testing` |

The frontend "Auth / session handling" row above is distinct from
section 4's backend "Auth" row: this one is the client-side pattern
(login-redirect flow, protected routes, where the session token lives)
that applies even for a frontend talking to a BaaS (Supabase, Firebase)
with no custom backend of its own; section 4's row is the server-side
mechanism a custom backend implements.

## 4. Backend

*(leave every row `—` if this project has no backend)*

| Field | Value | Governed by |
|---|---|---|
| Language | Node.js / Python / Go / Java or Kotlin / Rust / C#/.NET / PHP / Ruby | `backend-stack-selection` |
| Framework | Express / Fastify / NestJS / Django / FastAPI / Flask / Spring Boot / ASP.NET / Laravel / Rails | `backend-stack-selection` |
| API style | REST / GraphQL / gRPC / tRPC / WebSocket | `backend-stack-selection` |
| Architecture pattern | layered (MVC) / clean or hexagonal / DDD / CQRS / microservices / monolith | `backend-stack-selection` |
| Database | PostgreSQL / MySQL / MongoDB / Redis / SQLite / other | `backend-stack-selection` |
| ORM / query layer | Prisma / TypeORM / Drizzle / SQLAlchemy / raw SQL | `backend-stack-selection` |
| Request validation (API boundary) | Zod / JSON Schema / class-validator / Joi / Yup | `backend-stack-selection` |
| Auth | session-based / JWT / OAuth2 / SSO | `backend-stack-selection` |
| Background jobs / queue | none / cron / message queue (name it) | `backend-stack-selection` |

## 5. Infrastructure & delivery

| Field | Value | Governed by |
|---|---|---|
| Containerization | Docker / none | `repo-containerization` |
| Orchestration | none / docker-compose / Kubernetes | `repo-containerization` |
| CI/CD provider | GitHub Actions / GitLab CI / CircleCI / Jenkins / none | `repo-ci` |
| CI pipeline stages | e.g. lint → test → build → deploy | `repo-ci` |
| Hosting / deploy target | Vercel / Netlify / AWS / GCP / Azure / self-hosted / on-prem | `repo-hosting` |
| Environments | dev / staging / production (adjust) | `repo-hosting` |
| Secrets management | `.env` files / secrets manager (name it) / platform env vars | `repo-hosting` |
| Monitoring / logging | Sentry / Datadog / none | `frontend-monitoring` |
| Release process | semantic versioning / calendar-based / none — changelog: auto / manual | `repo-release` |
| Dependency scanning (ask explicitly — see project-profile/SKILL.md) | Dependabot / Renovate / none — CI audit gate: yes (`--audit-level=_`) / no | `repo-dependency-security` |

## 6. Git workflow

| Field | Value | Governed by |
|---|---|---|
| Branching model | trunk-based / GitHub flow / Git flow | `repo-commit` |
| Commit convention | Conventional Commits (enforced by Kysaro / commitlint) / freeform | `repo-commit` |
| PR requirements | required reviewers: _ / none — required checks: | `repo-commit` |
| Merge strategy | squash / merge commit / rebase | `repo-commit` |
| Linter(s) | ESLint / Ruff / golangci-lint / ... | `repo-lint-format` |
| Formatter | Prettier / Black / gofmt / ... | `repo-lint-format` |
| Type checking | TypeScript strict / mypy / none | `repo-lint-format` |
| Pre-commit hooks | Husky / pre-commit / none | `repo-cleanup` (secret/agent-trace scan hook) + `repo-lint-format` (lint/format hook) |

## 7. Constraints & non-functional requirements

| Field | Value | Governed by |
|---|---|---|
| Performance budget | | `frontend-performance` |
| Accessibility target | WCAG 2.2 AA (framework default) / AAA / none stated | `frontend-accessibility` |
| i18n / l10n (ask explicitly — see project-profile/SKILL.md) | yes — languages: _ / no | `frontend-i18n` |
| Security / compliance (ask explicitly — see project-profile/SKILL.md) | GDPR / SOC2 / HIPAA / none stated | `repo-hosting` |
| Frontend rendering (XSS) | any raw-HTML rendering (`dangerouslySetInnerHTML`, user-derived URLs) audited / none in use | `frontend-security` |
| Error/loading/empty states | has an app-root error boundary: yes / no — loading and empty states: pattern described | `frontend-resilience` |
| SEO / discoverability (ask explicitly — see project-profile/SKILL.md) | public pages meant to be indexed/shared: yes — meta tags present: _ / no | `frontend-seo` |
| Analytics / product telemetry (ask explicitly — see project-profile/SKILL.md) | yes — tool: _ / no | `frontend-analytics` |
| Feature flags / experimentation (ask explicitly — see project-profile/SKILL.md) | yes — tool: _ / no | `frontend-feature-flags` |

## Provenance

For each row above that came from scanning the repository rather than
being stated directly by the owner, mark it (e.g. a trailing `(detected)`)
until the owner confirms it — see `skills/repo-init/SKILL.md` → Adopting
an existing project's own conventions. An unconfirmed detected value is
a guess, not a settled fact; do not treat it as one.
