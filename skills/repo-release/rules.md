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

Group user-visible changes under Breaking changes, New, and Fixed. One bullet
per commit, the subject line only — a short thesis, never commit-body prose.
If a breaking change needs its actual impact stated, say it in the commit
subject itself (still one short line), not as a second line pulled from the
body. Release descriptions must be strictly English. Do not include agent
traces.

## Automation

Automatic releases require green `CI`, the `RELEASE_TOKEN` secret, and
`RELEASES=on`. Keep the token outside the repository. A release workflow must not
run when CI fails. Public repositories may show the Release badge.

## First release

Verify tests, CI, README, metadata, and tags before publishing. For an experimental
framework the first release is `v0.1.0` unless the user specifies another version.

## App signing / publisher trust (desktop/mobile only)

Not an e-signature/legal-document question — this is about the built app itself
being trusted by the OS and the user, independent of what the app does. Ask only
when the project ships a desktop or mobile binary; not applicable for a web/SaaS
app with no installable artifact.

| Platform | Option | Pick it when |
|---|---|---|
| **Windows** | Authenticode (OV or EV) code-signing certificate on the `.exe`/`.msi` | Any Windows installer — unsigned binaries trigger an "Unknown publisher" SmartScreen warning. Certificates issued from 2026-03-01 are capped at 460 days validity (CA/Browser Forum baseline requirement); plan renewal around that, not the old 1-3 year assumption. EV no longer reliably grants an instant SmartScreen reputation bump by itself — treat it as a nice-to-have, not a guaranteed bypass |
| **macOS** | Apple Developer ID certificate + notarization | Any macOS app distributed outside the Mac App Store — without it, Gatekeeper blocks the app with a hard warning the user has to bypass manually. Requires an active Apple Developer Program membership |
| **Android** | APK/AAB signing (self-signed key, or Google Play App Signing when distributed through Play) | Required by the platform regardless of trust goals — every APK must be signed to install at all; Play Store's own reputation (Play Protect) carries most of the user-facing trust signal, no paid certificate needed |
| **None** | **Default for a web/SaaS app** — nothing to sign when there's no installable binary |

**Default: sign for the platform(s) actually shipped** — this isn't optional
polish once a desktop/mobile build exists; an unsigned Windows/macOS build reads
as broken or malicious to most users, which directly undercuts the "made with
care" impression a product should give. Treat it as part of the release
checklist for that platform, not a later nice-to-have.

**Release checksums.** Publish a SHA-256 checksum (or signature) file alongside
each GitHub Release's downloadable artifacts regardless of platform — lets a
user verify what they downloaded wasn't tampered with in transit, cheap to add
to the existing release workflow.

## npm package

The npm package contains runtime files only. Keep `package.json` `files` as an
allowlist; never include `tests/`, `.github/`, `.git/`, `projects/`, `.agents/`,
`.kysaro/`, logs, or machine configuration.

Run `npm pack --dry-run` locally and in CI. The package version must match the
GitHub release tag. Publish only from the release workflow with `NPM_TOKEN` stored
as a GitHub Secret; never print or commit the token.
