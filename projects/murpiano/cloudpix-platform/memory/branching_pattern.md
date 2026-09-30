---
name: feature-branch-pattern
description: "All changes go to feature branches; main is protected and receives only completed, verified work"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c19dd132-2367-499c-85d3-ae469dab4fb7
  modified: 2026-09-30T18:08:17.819Z
---

**Rule:** Create feature branch for every change. Main branch receives only finished, tested work via merge or rebase.

**Why:** main — holy grail. Protect it. All development on separate branches keeps main deployable always.

**How to apply:** New feature/fix → create branch from main → develop → test → merge back to main. Never commit directly to main unless it's a hotfix (rare, and still prefer branch). Push only when work verified complete.

**Related:** [[project-deployment-ready]]
