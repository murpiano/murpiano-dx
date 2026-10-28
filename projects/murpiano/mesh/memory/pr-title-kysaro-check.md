---
name: pr-title-kysaro-check
description: PR title/body must be run through kysaro before gh pr create; never rerun a failed kysaro job after editing a PR
metadata:
  node_type: memory
  type: feedback
  originSessionId: dedb86d2-f997-494d-ac6b-49c414f0d752
  modified: 2026-10-28T18:21:24.496Z
---

Run the pull request title and body through kysaro before `gh pr create`:
`printf '%s\n\n%s\n' "$title" "$body" | npx kysaro --type request`. If a title
check fails in CI, fix it by editing the PR (`gh api -X PATCH .../pulls/N`) and
let the `edited` event start a fresh run — never `gh run rerun` the failed job.

**Why:** the kysaro hook is on `commit-msg` only, so it never sees a PR title; CI
catches it, which costs the author a red run and a mail. A rerun replays the old
event with the old title, fails again and buries the green run the edit produced.
Both happened on mesh PR #11 on 2026-10-28.

**How to apply:** treat the kysaro pre-flight as part of opening any PR in a
murpiano repo. The rule now also lives in
`~/projects/murpiano-dx/skills/repo-commit` (SKILL.md and rules.md section 7),
merged into murpiano-dx main as 2d5977b on 2026-10-28.
