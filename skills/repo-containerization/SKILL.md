---
name: repo-containerization
description: Use when deciding whether a project needs Docker/docker-compose at all, or setting one up once it does. Not for a deploy target that doesn't need it (static hosting, a managed platform that builds from source directly).
---

# Containerization

Governs `project-profile.md` fields: Infrastructure & delivery →
Containerization, Orchestration.

## The decision: does this project need Docker at all

**No, by default**, for a project whose deploy target already handles
building and running it without one — a static build on GitHub
Pages/Netlify/Vercel, or a managed platform that builds directly from
source. `my-world`'s own GitHub Pages deployment is the worked example:
a static build artifact, no server process to containerize, no Docker
anywhere in its pipeline.

**Yes**, once at least one of these is real:

- The deploy target is a plain VPS/self-hosted box with no platform
  doing the packaging for you.
- The app needs a database, background worker, or another service
  running alongside it, and the project wants the same setup locally
  and in production (`docker-compose` gives this without each
  developer hand-installing those services).
- Local dev environment drift between contributors' machines is a real,
  recurring problem a shared container image would solve.

Don't add Docker speculatively "in case we need to self-host later" —
same premature-infrastructure caution this framework already applies
elsewhere (`frontend-design-system`'s promotion rule, `AGENTS.md`'s own
project rules against unneeded abstraction).

## Once it's needed

- **Multi-stage build**: a build stage with the full toolchain (compiler,
  package manager, dev dependencies), then a slim runtime stage that
  copies only the built artifact and production dependencies — don't
  ship the build toolchain in the image that actually runs.
- **`docker-compose` for local dev parity**: the app plus whatever it
  depends on (database, cache, queue) as one `docker-compose.yml`, so
  "clone and run" works without each dependency installed by hand.
- **A self-hosted PaaS (Coolify, Dokploy) is a stated middle ground**
  between a fully-managed platform and raw Docker-on-a-VPS — it runs a
  project's own `docker-compose` stack with a push-to-deploy workflow,
  for a project that wants self-hosting's cost/control without hand-
  managing the VPS itself. Not a default, a named option.

## Basis (checked 2026-11-13)

- Managed platforms (Vercel, Netlify) bundle hosting/CDN/deploy so a
  project doesn't need to provision or containerize anything; Docker
  earns its place once a project needs a database/background service
  alongside the app or wants dev/prod parity, which several 2026
  self-hosting comparisons converge on as the real trigger, not project
  age or size on its own:
  [Vercel for speed, Docker for scale](https://sacra.com/chat/h/d90ad3f5-ac08-4f7b-aa2b-0b6f1f2a5153/).
- Self-hosted PaaS tools (Coolify, Dokploy) running a project's own
  Docker Compose stack with push-to-deploy are repeatedly named as the
  middle ground between a managed platform and raw VPS+Docker — noted
  with the honest caveat that these comparisons are largely vendor/
  affiliate content, not an independent benchmark.
