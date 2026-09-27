---
name: voyager-env-config
description: voyager-dashboard reads server URL and auth header from .env via webpack DefinePlugin; token must never be committed
metadata:
  type: project
---

Server URL and the Basic auth header for the user's personal backend (bvtrots-test-server on Render, path /voyager-dashboard) come from `.env` (`VOYAGER_SERVER_URL`, `VOYAGER_API_AUTH`), injected at build time. `.env.example` is committed with an empty token. The auto-mode classifier blocks pushing the token to a public repo.

**Why:** 2026-09-27 the repo was recreated as murpiano/voyager-dashboard (GitHub account bvtrots was renamed to murpiano); the old public repo had the token in source.

**How to apply:** never inline the token in source or docs; related: [[no-agent-traces]].
