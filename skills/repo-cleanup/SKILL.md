---
name: repo-cleanup
description: Use when a repository is about to be pushed or published, or when its files, commit history, authors, branches, pull requests or releases may show that AI agents or assistants were used (CLAUDE.md, AGENTS.md, Co-Authored-By trailers, emoji commits, bot identities), or when it may contain committed secrets (.env files, keys, tokens).
---

# Remove agent traces

Governs `project-profile.md` fields: Git workflow → Pre-commit hooks.

(This skill owns only the secret/agent-trace scan hook; a project's own
lint/format pre-commit hooks are a separate concern.)

Find and remove traces of agent-assisted development from everything a
repository visitor can see. Commit dates, file contents, and merge-commit
structure are preserved.

Also find any secrets that made it into the repository.

What counts as a trace or a secret: [policy.md](policy.md). Repository
scanner: [scan-traces.sh](scan-traces.sh), read-only, changes nothing. Scanner
for free-form text (PR description, release notes — anything that goes to the
GitHub API directly via `gh`, bypassing any git hook):
[check-text.sh](check-text.sh). `repo-commit` and `repo-release` must run a
PR/release draft through it before sending — commit hooks never see this text
at all.

## Steps

1. Scan local state and what's visible on GitHub:

   ```bash
   bash scan-traces.sh <repo>
   bash scan-traces.sh <repo> --published
   ```

2. Review each finding: trace or false positive (e.g. CSS `cursor`). If
   unclear, ask the owner. Show a found secret to the owner immediately per
   section 8 of `policy.md`, without printing the value.
3. Working tree: remove agent files from the index (`git rm --cached -r
   <path>`), remove mentions from text, commit on a `chore/remove-agent-traces`
   branch and merge into `main` per the "Merge" section of
   `repo-commit/rules.md`.
4. History, only after confirmation:
   1. Backup branch `backup/original-history` at the current HEAD.
   2. New messages in files named by the old hash. Check with the linter. Run
      Kysaro outside the kysaro repo itself, so the default preset applies.
   3. `git filter-branch` preserves author and committer dates:
      - messages: `--msg-filter` that prints the file keyed by `$GIT_COMMIT`,
        or the original message;
      - author: `--env-filter` with `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`,
        `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL`;
      - files: `--index-filter 'git rm -r --cached --ignore-unmatch <paths>'`.
   4. Remove `.git/refs/original`.
   5. Verify: `git diff --stat backup/original-history HEAD` shows only the
      intended changes, the commit and merge-commit counts match, the scanner
      is clean.
   6. Set the repository's author: `git config user.name` and `git config
      user.email`.
5. Publish, only after confirmation:
   `git push --force-with-lease=main:<old-sha-on-remote> origin main`. Delete
   any remote branches carrying the old history.
6. GitHub, only after confirmation:
   - PR: `gh api -X PATCH repos/OWNER/REPO/pulls/N -f title=... -f body=...`
     (`gh pr edit` can fail on stale Projects fields);
   - releases: `gh release edit <tag> --notes-file <file>`;
   - bot comments: delete only the ones the owner confirmed.
7. Repeat `scan-traces.sh <repo> --published`. Report to the owner whatever
   remains, and section 7 of `policy.md`.
8. Check the prevention measures in section 6 of `policy.md`. Change global
   settings only after confirmation.

## Ask the owner

- Any history rewrite and any push, especially force.
- Deleting branches, tags, comments on GitHub. Editing PRs and releases.
- A mention that might be part of the product itself.
- A found secret: whether it's been revoked and whether history needs
  cleaning.
- Whether to rewrite old messages that have no traces but break convention.

## Never

- `--force` without a lease.
- Rewrite history without a backup branch.
- Change anything outside the scope defined in `policy.md`.
- Print the value of a found secret.

## Done when

- `scan-traces.sh <repo> --published` shows only findings the owner accepted.
- Every rewrite is confirmed and checked against `backup/original-history`.
- The owner has been told what remains and why.
