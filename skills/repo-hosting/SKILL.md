---
name: repo-hosting
description: Use when deciding where a project is hosted, how many environments it needs, how secrets are managed, and whether a compliance framework applies. Each is a real option set with tradeoffs and a default — not a question to leave to the owner unprompted. Not CI/CD pipeline stages (repo-ci) or containerization itself (repo-containerization).
---

# Hosting, environments, secrets, compliance

Governs `project-profile.md` fields: Infrastructure & delivery → Hosting /
deploy target, Environments, Secrets management, Constraints &
non-functional requirements → Security / compliance (ask explicitly — see
project-profile/SKILL.md).

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

**Default: a managed platform (Vercel/Netlify/Cloudflare Pages for a pure
frontend; Railway/Render/Fly.io once a custom backend exists) over a raw
cloud provider or self-hosting** — the ops cost of AWS/self-hosted is real
and shouldn't be paid without a concrete reason (compliance, cost at scale,
a specific managed service need).

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

## Security / compliance (ask explicitly — see `project-profile/SKILL.md`)

This row isn't "pick the best option" — it's "does a real regulatory/
contractual obligation apply," which only the owner can answer, but the
agent should explain what each option actually means before asking, not
just read the acronym back:

- **GDPR** — applies if the product has any EU users and processes
  personal data (nearly every app with user accounts/analytics). The
  practical floor: a privacy policy, a lawful basis for processing, data
  deletion on request, and (per `frontend-analytics`) favoring
  cookie-less analytics to avoid a consent-banner requirement in the
  first place.
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
- GDPR/SOC 2/HIPAA applicability conditions: general, stable regulatory
  facts (EU personal-data scope for GDPR, enterprise-sales trigger for
  SOC 2, US health-data scope for HIPAA) rather than a claim needing a
  freshness check — re-verify only if a specific jurisdiction's rules are
  in question, which is outside this skill's scope.
