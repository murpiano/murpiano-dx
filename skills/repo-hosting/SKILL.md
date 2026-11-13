---
name: repo-hosting
description: Use when deciding where a project is hosted, how many environments it needs, how secrets are managed, and whether a compliance framework applies. Each is a real option set with tradeoffs and a default — not a question to leave to the owner unprompted. Not CI/CD pipeline stages (repo-ci) or containerization itself (repo-containerization).
---

# Hosting, environments, secrets, compliance

Governs `project-profile.md` fields: Infrastructure & delivery → Hosting /
deploy target, Database hosting, Environments, Secrets management,
Constraints & non-functional requirements → Primary market / user
jurisdiction (ask explicitly — see project-profile/SKILL.md), Security /
compliance (ask explicitly — see project-profile/SKILL.md).

Scope: these rows look like "just describe your project" fields, but each
one has a real, bounded set of 2026 options with known tradeoffs. Reaching
one of these rows means presenting that option set, a recommendation, and
why — the same way `frontend-stack-selection` does for the frontend stack
— not silently writing down whatever the owner says first.

## Hosting / deploy target

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Vercel / Netlify / Cloudflare Pages** (managed static+serverless) | Git-push deploy, automatic preview URL per PR, zero server ops, generous free tier | Serverless function limits (cold starts, execution time caps); can get expensive at real scale; some framework-specific lock-in (Vercel + Next.js) | Default for a frontend (static or SSR) with no heavy custom backend — the lowest-ops option |
| **Railway / Render / Fly.io** (managed app platform) | Still Git-push deploy, but runs a real long-lived process/container — fits a custom backend, worker, or database alongside the frontend | More to configure than the static platforms above; smaller free tier | A custom backend/API needs to run somewhere and you don't want to manage servers yourself |
| **AWS / GCP / Azure** (cloud provider, direct) | Full control, every primitive available, scales to anything | Real ops burden — you're now responsible for what a managed platform used to handle; steep learning curve | Scale, compliance, or a specific managed service (e.g. a particular database, queue) genuinely requires it — not a default starting point |
| **Self-hosted / on-prem / VPS** | No vendor dependency, full control, can be cheaper at steady-state scale | You own everything: patching, scaling, uptime, backups | Data residency/compliance requires it, or an existing self-hosted PaaS (Coolville/Dokploy, see `repo-containerization`) is already in place |
| **Russian-jurisdiction cloud** (Yandex Cloud, Selectel, VK Cloud) | Physical data centers inside the Russian Federation, needed the moment 152-ФЗ's localization rule applies (see Security/compliance below) | Smaller global footprint/ecosystem than the hyperscalers; provider compliance claims (ФСТЭК certification, "соответствие 152-ФЗ") describe their own infrastructure, not automatically your application — your own operator obligations below still apply on top | The product has Russian citizens' personal data and the localization rule applies — not a general-purpose default otherwise |

**Default: a managed platform (Vercel/Netlify/Cloudflare Pages for a pure
frontend; Railway/Render/Fly.io once a custom backend exists) over a raw
cloud provider or self-hosting** — the ops cost of AWS/self-hosted is real
and shouldn't be paid without a concrete reason (compliance, cost at scale,
a specific managed service need). **If 152-ФЗ's localization rule applies,
this row and the database-hosting row below both narrow to a
Russian-jurisdiction option — read Security/compliance first, since it
constrains this row, not the other way around** (same "bigger decision
constrains smaller ones that follow it" ordering `project-profile.md`
already states for the whole table).

## Database hosting

A real, separate decision from the row above — "where the app runs" and
"where its database runs" are often different providers, and the backend
stack's own default (`backend-stack-selection`: PostgreSQL) narrows this
to Postgres-specific options.

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Neon** | Serverless Postgres, scales to zero — cheapest for a spiky or dev/staging workload, generous branching for per-PR preview databases | Cold start on scale-from-zero; smaller region count than the hyperscalers | A solo/small project, or any preview-environment-per-PR workflow (pairs naturally with the Environments row above) |
| **Supabase** | Postgres plus a bundled backend platform (auth, storage, realtime, edge functions) — can replace several of this framework's own rows (Auth, Request validation's transport) if adopted wholesale | Bundling is also lock-in — harder to swap just the database later without touching the rest | The project wants a bundled BaaS instead of this framework's own Fastify+tRPC+Better-Auth stack — a deliberate alternative path, not a default on top of it |
| **Railway (managed Postgres)** | Database colocated with the app on the same platform chosen in the Hosting row above — simplest ops story when both are Railway | Smaller region selection than the dedicated DB services | Already hosting the backend app itself on Railway — avoids a second provider relationship for no real benefit |
| **AWS RDS** | Most mature, 30+ regions, deepest IAM/VPC integration | Typically the most expensive of these options; real setup complexity | Already on AWS for other reasons (see Hosting row), or a specific compliance/IAM requirement needs it |
| **Self-hosted Postgres** (on a VPS, or inside the project's own `docker-compose`) | No managed-service cost, full control | Backups, failover, and patching become the project's own job | Data residency requires it (self-hosted inside a Russian-jurisdiction VPS, for 152-ФЗ) or cost at real scale justifies the ops burden |

**Default: Neon** for a solo/small project with no data-localization
constraint — scale-to-zero pricing and per-PR branching fit this
framework's own Environments default well. **Railway's managed Postgres**
if the app itself is already on Railway. **A Russian-jurisdiction
provider's managed Postgres (Yandex Cloud, Selectel) or a self-hosted
instance inside one** once 152-ФЗ's localization rule applies — none of
Neon/Supabase/RDS satisfy it as US/EU-region services.

## Environments

The near-universal pattern, regardless of hosting choice: **development
(local) → preview (per-PR/branch, ephemeral) → staging (optional, a stable
pre-prod mirror) → production.** Every managed platform above gives preview
deployments per PR for free — use them; they're the standard way a
reviewer checks a change before it merges, not an extra step to skip.

- **Skip staging** for a solo/small project — preview environments already
  cover "see it before it's live"; a separate staging environment earns its
  keep once production incidents are costly enough that one more gate
  before prod is worth the extra deploy step.
- **Never skip the dev/production split** — even a one-person project
  needs a way to test a change without it being live; this is not a row
  to answer "just production."

## Secrets management

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **`.env` files locally + platform env vars in deploy** | Zero extra tooling; every hosting platform above has a built-in encrypted env-var store | No audit trail of who changed what/when; no automatic rotation; secrets duplicated per environment by hand | Default for a solo/small-team project — this is what "platform env vars" already gives you for free |
| **Doppler / Infisical** (secrets-as-a-service) | Single source of truth synced to every environment/platform, change history, access control | Another service/account to manage; a paid tier for teams | Multiple environments/platforms need the same secret kept in sync, or more than one person needs controlled access |
| **Cloud-native secrets manager** (AWS Secrets Manager, GCP Secret Manager, Vault) | Fine-grained IAM-based access, automatic rotation, audit logging | Real setup overhead; tied to (or requires running) that cloud's own infra | Already on that cloud provider for compliance/scale reasons (see Hosting row above), or a compliance framework below requires rotation/audit trails |

**Default: `.env` locally + the hosting platform's own env-var store in
deploy.** The universal rule regardless of tier: `.env` files are
git-ignored, never committed (this is exactly what `repo-cleanup`'s
pre-publish scan checks for) and no secret is ever hardcoded in source —
moving to a dedicated secrets manager is a scale/compliance decision, not
a starting requirement.

## Primary market / user jurisdiction (ask explicitly — see `project-profile/SKILL.md`)

**Ask this before Security/compliance, not after — it's what determines
which law(s) even apply.** Legal/compliance obligations are not one
global checklist; they come from *which country's users the product
actually has*, and that's a fact only the owner knows (where the company
is based doesn't answer it — a Russian company selling to EU customers
owes both 152-ФЗ and GDPR; a US company with Russian users owes 152-ФЗ
too). Get a real answer here before touching the Security/compliance row
below — don't infer it from where the owner happens to be working, and
don't assume "no specific jurisdiction stated" means "no law applies":
every real user base lives somewhere.

| Market | What it routes to below |
|---|---|
| **Russia** | 152-ФЗ applies |
| **EU** | GDPR applies |
| **US** | CCPA/CPRA if California users exist (a US-wide product almost always has some); HIPAA additionally if the product handles health data; neither is assumed from "US" alone — check which actually applies |
| **Global / no specific jurisdiction stated** | Not a real answer for a product anyone can sign up for — ask again, naming likely markets (where the owner expects to launch/market first), and treat GDPR's floor as the safest default baseline if genuinely undecided, since it's the strictest of the common regimes and over-complying elsewhere costs little |
| **More than one of the above** | Normal, not an edge case — every regime that applies to any real slice of the user base applies independently; satisfying one doesn't satisfy the others |
| **A country not listed here** | Say so explicitly rather than silently defaulting to one of the above — this skill doesn't yet have that jurisdiction's specifics written up (see `DELEGATION-MODEL.md`'s "a new domain gets written up, not improvised" rule) |

Working for a foreign company on a product with no Russian users at all
is exactly the case where 152-ФЗ is *not* the relevant row — this is
precisely why this question is asked explicitly per-project instead of
assumed from the owner's own location once and reused everywhere.

## Security / compliance (ask explicitly — see `project-profile/SKILL.md`)

This row isn't "pick the best option" — it's "does a real regulatory/
contractual obligation apply," routed from the Primary market row above.
The agent should explain what each applicable option actually means
before asking, not just read the acronym back:

- **GDPR** — applies if the product has any EU users and processes
  personal data (nearly every app with user accounts/analytics). The
  practical floor: a privacy policy, a lawful basis for processing, data
  deletion on request, and (per `frontend-analytics`) favoring
  cookie-less analytics to avoid a consent-banner requirement in the
  first place.
- **CCPA/CPRA** — California's state-level privacy law, the closest US
  equivalent to GDPR's general scope (not health-specific like HIPAA
  below). Applies once the product has California users and meets the
  law's size/revenue thresholds — gives users the right to know what's
  collected, to delete it, and to opt out of its sale. Distinct from
  HIPAA: a product can owe CCPA/CPRA with zero health data involved,
  purely from having US/California consumer users.
- **SOC 2** — a third-party audit of security controls (access control,
  change management, monitoring), typically required by enterprise
  B2B customers before they'll sign a contract — not something a product
  needs technically, but something a sales process can demand. Relevant
  once selling to enterprise customers, essentially never for a
  consumer/solo project.
- **HIPAA** — applies only if the product handles US health information.
  Name it explicitly if the domain is healthcare; otherwise it doesn't
  apply and shouldn't be on the table.
- **None stated** — the correct, default answer for most solo/small
  projects with no enterprise sales process and no regulated-data domain.
  Not a gap — stating it explicitly (rather than leaving the row blank)
  is what distinguishes "considered and not applicable" from "never
  asked," per `project-profile.md`'s own "ask explicitly" rows (same
  pattern as i18n, SEO, analytics).
- **152-ФЗ "О персональных данных"** — applies the moment the product
  collects *any* personal data (name, email, phone, IP address bound to
  an account) from users who are Russian citizens or residents, which is
  essentially every app with user accounts/analytics serving a Russian
  audience — the same breadth GDPR has for an EU audience, but it is a
  distinct law with its own distinct, concrete obligations, not a
  regional GDPR variant:
  - **Privacy policy (Политика конфиденциальности)** — a published
    document describing what's collected and why. A missing one is
    independently finable even with no other violation.
  - **Explicit consent (Согласие на обработку ПД)** — a real,
    affirmative checkbox at the point of collection (signup, a contact
    form), not implied by "using the site."
  - **Cookie disclosure/consent banner** — if cookies collect anything
    tied to an identifiable user (most analytics/ad cookies do).
  - **Data localization (ч. 5 ст. 18, 152-ФЗ)** — the *initial* recording
    and storage of Russian users' personal data must happen on a database
    physically inside the Russian Federation. This is the row that
    constrains Hosting and Database hosting above once it applies — a
    US/EU-region Neon/Supabase/RDS instance does not satisfy it; a
    Russian-jurisdiction provider (Yandex Cloud, Selectel, VK Cloud) or
    self-hosted RF server does. Cross-border transfer *after* that
    initial local recording has its own, separately tightening rules (a
    2026 amendment strengthens Roskomnadzor's review of the receiving
    country's actual data-protection practice, not just its law on
    paper) — treat any transfer of this data outside the RF as its own
    question, not assumed-fine by default.
  - **Roskomnadzor notification** — an operator processing personal data
    (again, essentially any app with accounts) must notify Roskomnadzor
    it is doing so, with limited stated exemptions.
  - **Data-subject request handling** — a user's request to access,
    correct, or delete their own data has a mandated response, with
    fines for ignoring it, distinct from the breach-notification fines
    below.
  - **Special category personal data** (health, biometric, race,
    religion, criminal record) — heightened requirements and explicit,
    separate consent; name this specifically if the product touches any
    of these, don't fold it into the general-PD answer.
  - **Breach/leak fines** — materially increased in recent amendments;
    Russian companies collectively paid real, reported sums for leaks in
    just the first half of 2026 per regulatory reporting. Not a
    theoretical risk to wave off for a small project.
  This is the correct row to raise for any project with a Russian user
  base, parallel to how GDPR is raised for an EU one — don't let "ask
  explicitly" default to only naming GDPR/SOC2/HIPAA and silently skip
  152-ФЗ for a Russian-market product.

## What this skill does not cover

Containerization/orchestration itself (`repo-containerization`). The CI
pipeline that deploys to these environments (`repo-ci`). Dependency
vulnerability scanning (`repo-dependency-security`). The commit-message/
secret-scanning pre-commit hook (`repo-cleanup`).

## Basis (checked 2026-11-13)

- The dev → preview → staging(optional) → production environment ladder
  and git-push-to-preview-URL as the standard flow: this is the Twelve-
  Factor App methodology's config/environment-parity principle, still the
  reference standard for this —
  [The Twelve-Factor App](https://12factor.net/config).
- `.env` files for local + platform env vars for deploy as the baseline,
  escalating to a dedicated secrets manager only for multi-environment
  sync or compliance-driven rotation/audit needs: standard, uncontested
  industry practice (not tied to a single 2026 source) matching this
  framework's existing "build-trigger, not default-on" pattern already
  used in `repo-containerization` and `frontend-feature-flags`.
- GDPR/SOC 2/HIPAA/CCPA-CPRA applicability conditions: general, stable
  regulatory facts (EU personal-data scope for GDPR, enterprise-sales
  trigger for SOC 2, US health-data scope for HIPAA, California
  consumer-data scope for CCPA/CPRA) rather than a claim needing a
  freshness check — re-verify only if a specific jurisdiction's rules are
  in question, which is outside this skill's scope.
- **Jurisdiction-first ordering (market determines which law applies,
  not the other way around) is this skill's own structural fix, not an
  external claim needing a citation** — the underlying facts (GDPR scopes
  to the EU, 152-ФЗ to Russia, CCPA/CPRA to California, HIPAA to US
  health data, SOC2 to enterprise sales in any market, and more than one
  can apply simultaneously to the same product) are each individually
  well-established law, cited where each one is first introduced above.
- Neon/Supabase/Railway/AWS RDS tradeoffs for managed Postgres hosting:
  aggregated across multiple 2026 comparison posts, e.g.
  [Best PostgreSQL Hosting in 2026: RDS vs Supabase vs Neon vs Self-hosted](https://dev.to/philip_mcclarence_2ef9475/best-postgresql-hosting-in-2026-rds-vs-supabase-vs-neon-vs-self-hosted-5fkp) —
  several sources are vendor blogs (Railway comparing itself), pricing
  figures conflict and should be re-checked on each provider's own site
  before deciding.
- **152-ФЗ, unlike the GDPR/SOC2/HIPAA rows above, is actively changing
  in 2026 and needs a tighter freshness window than this skill's other
  rows** — a cross-border-transfer tightening bill passed its third
  Duma reading on 2026-07-08, and sources disagree on exactly when
  recording/storage abroad counts as a violation vs. when only
  cross-border *transfer* is restricted (ч. 5 ст. 18, 152-ФЗ is cited
  for the stricter reading). Re-run `knowledge-refresh` on this specific
  row before relying on it for a real project, don't treat this date as
  good for the usual ~month window: aggregated from 2026 Russian-language
  legal/compliance roundups, e.g.
  [Персональные данные: полный гайд на 2026 год](https://www.sostav.ru/blogs/288674/82716),
  cross-checked against Yandex Cloud's own stated 152-ФЗ compliance page,
  [Yandex Cloud — Выполнение требований ФЗ-152](https://yandex.cloud/ru/docs/troubleshooting/legal/how-to/fl-152).
  Provider compliance claims (Selectel/Yandex Cloud/VK Cloud's own
  ФСТЭК-certification statements) describe their infrastructure, not an
  application built on it — don't treat a provider's own marketing page
  as confirmation that a specific project is compliant.
