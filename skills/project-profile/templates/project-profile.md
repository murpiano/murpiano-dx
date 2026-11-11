# Project profile — <project name>

One standing picture of this project: what it is, what it is built with,
how work flows through it. Filled once at connect/creation, updated
whenever something changes. Read this before asking the owner something
it already answers; a question this table has a value for is a question
already settled, not one to re-ask.

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
| Secondary platforms | — if single-platform | |
| Target OS / browser support | | |

## 3. Frontend

*(leave every row `—` if this project has no frontend)*

| Field | Value | Governed by |
|---|---|---|
| Language | JavaScript / TypeScript | |
| UI framework | React / Vue / Svelte / Angular / vanilla | |
| Meta-framework | Next.js / Nuxt / Remix / Astro / none | |
| Styling approach | CSS Modules / Tailwind / SCSS+BEM / CSS-in-JS (Emotion, styled-components) / vanilla-extract | `frontend-styling-concept` |
| State management | Redux / Zustand / Context API / MobX / Recoil / none | |
| Data fetching | REST client / GraphQL client (Apollo, urql) / tRPC / server actions | |
| Bundler | Vite / Webpack / Turbopack / esbuild / Parcel | |
| Package manager | npm / pnpm / yarn / bun | |
| Unit/component tests | Vitest / Jest / none | |
| E2E tests | Playwright / Cypress / none | |

## 4. Backend

*(leave every row `—` if this project has no backend)*

| Field | Value | Governed by |
|---|---|---|
| Language | Node.js / Python / Go / Java or Kotlin / Rust / C#/.NET / PHP / Ruby | |
| Framework | Express / Fastify / NestJS / Django / FastAPI / Flask / Spring Boot / ASP.NET / Laravel / Rails | |
| API style | REST / GraphQL / gRPC / tRPC / WebSocket | |
| Architecture pattern | layered (MVC) / clean or hexagonal / DDD / CQRS / microservices / monolith | |
| Database | PostgreSQL / MySQL / MongoDB / Redis / SQLite / other | |
| ORM / query layer | Prisma / TypeORM / Drizzle / SQLAlchemy / raw SQL | |
| Auth | session-based / JWT / OAuth2 / SSO | |
| Background jobs / queue | none / cron / message queue (name it) | |

No backend domain skill exists yet in this framework — every row above
is plain information until one is written (see `skills/DELEGATION-MODEL.md`).

## 5. Infrastructure & delivery

| Field | Value | Governed by |
|---|---|---|
| Containerization | Docker / none | |
| Orchestration | none / docker-compose / Kubernetes | |
| CI/CD provider | GitHub Actions / GitLab CI / CircleCI / Jenkins / none | |
| CI pipeline stages | e.g. lint → test → build → deploy | |
| Hosting / deploy target | Vercel / Netlify / AWS / GCP / Azure / self-hosted / on-prem | |
| Environments | dev / staging / production (adjust) | |
| Secrets management | `.env` files / secrets manager (name it) / platform env vars | |
| Monitoring / logging | Sentry / Datadog / none | |
| Release process | semantic versioning / calendar-based / none — changelog: auto / manual | `repo-release` |
| Dependency scanning (ask explicitly — see project-profile/SKILL.md) | Dependabot / Renovate / none — CI audit gate: yes (`--audit-level=_`) / no | `repo-dependency-security` |

## 6. Git workflow

| Field | Value | Governed by |
|---|---|---|
| Branching model | trunk-based / GitHub flow / Git flow | |
| Commit convention | Conventional Commits (enforced by Kysaro / commitlint) / freeform | `repo-commit` |
| PR requirements | required reviewers: _ / none — required checks: | `repo-commit` |
| Merge strategy | squash / merge commit / rebase | `repo-commit` |
| Linter(s) | ESLint / Ruff / golangci-lint / ... | |
| Formatter | Prettier / Black / gofmt / ... | |
| Type checking | TypeScript strict / mypy / none | |
| Pre-commit hooks | Husky / pre-commit / none | `repo-cleanup` (secret/agent-trace scan hook only — a project's own lint/format hooks are separate) |

## 7. Constraints & non-functional requirements

| Field | Value | Governed by |
|---|---|---|
| Performance budget | | `frontend-performance` |
| Accessibility target | WCAG 2.2 AA (framework default) / AAA / none stated | `frontend-accessibility` |
| i18n / l10n (ask explicitly — see project-profile/SKILL.md) | yes — languages: _ / no | `frontend-i18n` |
| Security / compliance | GDPR / SOC2 / none stated | |
| Frontend rendering (XSS) | any raw-HTML rendering (`dangerouslySetInnerHTML`, user-derived URLs) audited / none in use | `frontend-security` |
| Error/loading/empty states | has an app-root error boundary: yes / no — loading and empty states: pattern described | `frontend-resilience` |
| Browser/device support matrix | | |

## Provenance

For each row above that came from scanning the repository rather than
being stated directly by the owner, mark it (e.g. a trailing `(detected)`)
until the owner confirms it — see `skills/repo-init/SKILL.md` → Adopting
an existing project's own conventions. An unconfirmed detected value is
a guess, not a settled fact; do not treat it as one.
