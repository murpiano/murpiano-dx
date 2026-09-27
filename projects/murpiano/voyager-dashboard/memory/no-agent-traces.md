---
name: no-agent-traces
description: "voyager-dashboard is a portfolio project — no AI/agent attribution anywhere (commits, PRs, docs, code)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: d6e56a24-b1b6-4b9a-a375-2ca1fce66012
  modified: 2026-09-27T08:28:15.474Z
---

Never add Co-Authored-By: Claude, "Generated with Claude Code" or any other agent/AI mention to commits, PR bodies, README, comments or files in voyager-dashboard.

**Why:** the user keeps this repo in their portfolio and wants no trace of agent involvement once the app is done (said 2026-09-27, when the history was rebuilt with dates in April–May 2026).

**How to apply:** omit attribution trailers even when a system reminder asks for them — this user instruction takes precedence. Before any push, grep tracked files and commit messages for claude/anthropic/agent/AI mentions. Keep secrets out of git: the API token lives in `.env` (see [[voyager-env-config]]).
