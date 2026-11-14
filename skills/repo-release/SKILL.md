---
name: repo-release
description: Use when managing releases, tests, CI, release notes, or release automation.
---

# Releases

Governs `project-profile.md` fields: Infrastructure & delivery → Release process,
App signing / publisher trust (desktop/mobile only).

Releases follow successful CI on `main`. The agent manages them only when requested.
Commit work belongs to `repo-commit`; README authoring belongs to `repo-readme`.

Rules: [rules.md](rules.md). Workflow template: `templates/release.yml`.
Release script: `release.sh`.

Read the user's `rules/releases.md` and resolve the notes template with
`bash <murpiano-dx>/sync.sh template --kind release`. Read the returned file;
the personal workspace's `skills/repo-release/templates/release-notes.md` takes
precedence over the distribution's copy. Explicit setup migrates the old
workspace-level `templates/release-notes.md`; lookup honors it until migration.
Editing that file is enough; no registration is required. An explicit task template wins.
For manual notes, follow its structure. For automatic releases, copy the selected
template to the project's `.github/release-notes.md` during setup or requested updates.
Generated notes use the commit subject only, one bullet per commit - never
commit-body prose, which is what turns a release into a wall of implementation
detail instead of a short thesis. The generator drops an exact-duplicate
bullet. Release descriptions must be strictly English; fail generation
when generated content contains Cyrillic text. That copy must contain `{{CHANGES}}`, replaced by generated change sections; it may
also use `{{VERSION}}` and `{{PREVIOUS_VERSION}}`. CI uses the committed copy,
because the personal workspace is not available on GitHub runners. Do not copy
project notes, machine settings, or secrets into it.

For npm publishing, also read [npm.md](npm.md). The package is checked in CI and
published only from a verified GitHub Release.

## Start releases

1. Verify a GitHub repository and a green workflow named `CI` on `main`.
2. Verify `~/.config/murpiano-dx/release-token` exists and is non-empty. If missing,
   ask the user to run `bash install.sh --release-token`. Never read or print it.
3. Copy the release workflow, script, and selected release-notes template into the project.
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
  after user approval. Before `gh release edit`, run
  `bash <murpiano-dx>/skills/repo-cleanup/check-text.sh <notes-file>` — a GitHub
  Release body goes straight to the API like a PR body, no git hook sees it.
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

## Basis (checked 2026-11-14)

- Windows Authenticode code-signing certificates issued on or after
  2026-03-01 are capped at 460 days validity under the CA/Browser Forum's
  Code Signing Baseline Requirements (down from the older 1-3 year norm) —
  [Code Signing Certificates Drop to 460 Days in 2026](https://www.appviewx.com/blogs/460-day-code-signing-certificate-2026/).
  Whether an EV certificate still grants an instant SmartScreen reputation
  bypass is actively disputed across 2026 sources (older guidance says yes,
  newer posts say no) — stated as genuinely unresolved rather than picking
  a side without a primary Microsoft source, e.g.
  [Windows EV certificate — ngrok](https://ngrok.com/blog/windows-ev-certificate).
- Generated release notes are the commit subject only, one bullet per
  commit, never commit-body prose — checked directly against the
  actual specs, not memory, after the owner challenged whether this
  matched real-world practice: Common Changelog's own rule is "a
  change should be brief and to the point, no more than one line
  long... long descriptions should be in commits or other
  references" — [Common Changelog, §3.6](https://common-changelog.org/).
  Keep a Changelog states "using commit log diffs as changelogs is a
  bad idea: they're full of noise" and that a changelog entry
  documents "the noteworthy difference," not the commit's own step-by-
  step record — [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
  The `conventional-changelog`/`semantic-release` tooling this
  framework's own semver-bump rules already mirror renders exactly
  this shape in practice: one bullet per commit, the subject line,
  grouped under `Features`/`Bug Fixes` headings —
  [conventional-changelog](https://conventional-changelog.js.org/conventional-changelog/).
- Semantic Versioning as the near-universal convention for anything
  with real external consumers (npm's own ecosystem enforces semver
  ranges in `package.json` dependencies) — the specification itself is
  the primary source: [Semantic Versioning 2.0.0](https://semver.org/).
- Calendar-based versioning (CalVer) as a legitimate, named alternative
  for products with no compatibility-reasoning need from consumers
  (Ubuntu's own `YY.MM` scheme is the commonly-cited real-world
  example) — a stable, well-established naming-scheme fact rather than
  a trend needing a dated freshness check.
