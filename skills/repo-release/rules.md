# Release and CI rules

## CI

CI must run the project’s tests and relevant static checks on pull requests and
pushes to `main`. Keep the workflow reproducible and fail on errors. Do not publish
artifacts from an unverified commit.

## Versioning

Use Semantic Versioning. Use `0.x.y` while the framework is experimental; reserve
`1.0.0` for a stable public contract. Tags and release titles use `vX.Y.Z`.

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
