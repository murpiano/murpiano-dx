# Release and CI rules

## CI

CI must run the project’s tests and relevant static checks on pull requests and
pushes to `main`. Keep the workflow reproducible and fail on errors. Do not publish
artifacts from an unverified commit.

## Versioning

| Option | Strengths | Weaknesses | Pick it when |
|---|---|---|---|
| **Semantic Versioning (semver)** | `MAJOR.MINOR.PATCH` communicates breaking-vs-additive-vs-fix at a glance; the near-universal convention for anything with a package/API consumers depend on (npm itself enforces semver ranges) | Requires actual discipline about what counts as breaking — a team that bumps patch versions for breaking changes gets all of semver's cost with none of its benefit | **Default** — any project with real external consumers (an npm package, a library, an API with a client), which this framework assumes by default |
| **Calendar-based** (e.g. `2026.11`, CalVer) | Communicates *when* a release shipped, not its compatibility impact — fine for a product with no real "breaking change" concept from a consumer's point of view | Tells a consumer nothing about whether upgrading is safe — the opposite of what semver optimizes for | A SaaS/internal product with no external API consumers who need to reason about compatibility (nothing to "break" from their side) |
| **None / unversioned** | Nothing to maintain | No way to reference "what shipped when," no rollback point to name | A project genuinely never released as a discrete unit (continuously deployed with no tagged releases at all) — rare as a deliberate choice |

**Default: Semantic Versioning.** Use `0.x.y` while a project is
experimental; reserve `1.0.0` for a stable public contract. Tags and
release titles use `vX.Y.Z`. Calendar-based is a real, named
alternative — not a worse-semver — for a product with no consumers who
need compatibility signals from the version number itself; state that
reason explicitly if choosing it, don't default to it by omission.

## Release notes

Group user-visible changes under Added, Changed, Fixed, and Removed when useful.
Use commit bodies to add concrete implementation points, then merge equivalent
points, remove duplicates, and resolve contradictions in favor of the latest
commit. Release descriptions must be strictly English. Mention migrations or
breaking behavior explicitly. Do not include agent traces.

## Automation

Automatic releases require green `CI`, the `RELEASE_TOKEN` secret, and
`RELEASES=on`. Keep the token outside the repository. A release workflow must not
run when CI fails. Public repositories may show the Release badge.

## First release

Verify tests, CI, README, metadata, and tags before publishing. For an experimental
framework the first release is `v0.1.0` unless the user specifies another version.

## npm package

The npm package contains runtime files only. Keep `package.json` `files` as an
allowlist; never include `tests/`, `.github/`, `.git/`, `projects/`, `.agents/`,
`.kysaro/`, logs, or machine configuration.

Run `npm pack --dry-run` locally and in CI. The package version must match the
GitHub release tag. Publish only from the release workflow with `NPM_TOKEN` stored
as a GitHub Secret; never print or commit the token.
