---
name: commit-history-style
description: "User wants commit history to look chronological, small commits pushed one by one, not bursts"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 720892df-dfc2-4bdb-9e98-8a547b4a25af
  modified: 2026-09-25T07:43:02.771Z
---

The user wants git history that reads chronologically: small commits pushed one at a time, not many commits landing at once. On 2026-09-25 they asked to spread 12 commits made within 6 minutes across days (06.07–21.09) by rewriting author and committer dates.

**Why:** commits appearing "all at once" on GitHub looked wrong to them.
**How to apply:** make small focused commits and push each one separately. Rewriting dates of pushed commits needs a force-push, so ask first. Update hash references in messages and docs after a rewrite. Related: [[kysaro-release]].
