---
name: kysaro-release
description: Where kysaro lives on GitHub/npm and how releases are published
metadata:
  node_type: memory
  type: project
  originSessionId: 720892df-dfc2-4bdb-9e98-8a547b4a25af
  modified: 2026-09-25T07:42:59.723Z
---

kysaro is public at github.com/murpiano/kysaro (created 2026-09-25 as bvtrots/kysaro, account renamed to murpiano the same day; the old remote bvtrots/bvtrots-dx now holds a different project, do not push there). Releases publish through `.github/workflows/publish.yml` on a `v*` tag: tests, `npm publish --provenance`, GitHub release from CHANGELOG. It needs the `NPM_TOKEN` repo secret. v0.1.0 published 2026-09-26, then history dates were rewritten (force-push) and v0.1.1 released so provenance matches history; 0.1.0 provenance points to orphaned commit 0234dfd. publish.yml skips existing versions/releases. v0.2.0 (2026-09-27): merge/request rules, kysaro ci, --range, report.md, one-step init. Repo settings: merge commit = PR_TITLE/PR_BODY (GitHub writes "title (#N)" + body wrapped at 72), main protected with required check "kysaro" (enforce_admins false). `gh pr edit` fails on GraphQL projects-classic error; use REST `gh api -X PATCH repos/murpiano/kysaro/pulls/N`. The NPM_TOKEN must be a granular token with "Bypass 2FA", otherwise publish fails with E403.

**Why:** the user asked for a full npm package with a real GitHub repo.
**How to apply:** bump version + CHANGELOG in a `chore(build): release x.y.z` commit, then push the tag. The repo checks its own commits with kysaro (scopes in `.kysaro/settings/resources/scopes.json`). See [[commit-history-style]].
