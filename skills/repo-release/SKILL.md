---
name: repo-release
description: Use when managing releases, tests, CI, release notes, or release automation.
---

# Releases

Releases follow successful CI on `main`. The agent manages them only when requested.
Commit work belongs to `repo-commit`; README authoring belongs to `repo-readme`.

Rules: [rules.md](rules.md). Project files: `release.yml` and `release.sh`.

## Start releases

1. Verify a GitHub repository and a green workflow named `CI` on `main`.
2. Verify `~/.config/murpiano-dx/release-token` exists and is non-empty. If missing,
   ask the user to run `bash install.sh --release-token`. Never read or print it.
3. Copy the release workflow and script into the project.
4. Add the Release badge for public repositories.
5. Commit on `ci/releases` with `ci: release on every push to main`, then merge it.
6. Set the `RELEASE_TOKEN` GitHub secret from the local token file.
7. If no `v*` tag exists, create the approved first release with release notes.
8. Set the `RELEASES` variable to `on`.

## Manage releases

- Pause: set `RELEASES` to `paused`.
- Resume: set `RELEASES` to `on`.
- Preview: run `bash .github/scripts/release.sh --dry-run`.
- Rewrite notes: read the release commits, show the notes, then edit the release
  after user approval.
- Remove: confirm first, set `RELEASES=off`, delete releases and tags, remove the
  workflow, script, badge, and secret, then commit and merge the change.

## Tests and CI

Configure checks in `ci/tests`, merge with `repo-commit`, and update README CI
information and its badge when applicable.

## Never

- Print or copy the release token anywhere except `gh secret set`.
- Change `package.json` version only to create a release.
- Release a commit whose CI is not green.

## Done when

Release files are in `main`, the secret and `RELEASES=on` are set, a `v*` tag exists,
and public repositories have the Release badge. Pause/resume is verified with
`gh variable get RELEASES`; removal leaves no release tags or files.
