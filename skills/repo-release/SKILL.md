---
name: repo-release
description: Use when managing releases, tests, CI, release notes, or release automation.
---

# Releases

Governs `project-profile.md` fields: Infrastructure & delivery → Release process.

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
Generated notes use commit subjects plus concrete points from commit bodies. The
generator removes duplicate points and keeps the latest point when equivalent
points conflict. Release descriptions must be strictly English; fail generation
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

## Basis (checked 2026-11-13)

- Semantic Versioning as the near-universal convention for anything
  with real external consumers (npm's own ecosystem enforces semver
  ranges in `package.json` dependencies) — the specification itself is
  the primary source: [Semantic Versioning 2.0.0](https://semver.org/).
- Calendar-based versioning (CalVer) as a legitimate, named alternative
  for products with no compatibility-reasoning need from consumers
  (Ubuntu's own `YY.MM` scheme is the commonly-cited real-world
  example) — a stable, well-established naming-scheme fact rather than
  a trend needing a dated freshness check.
