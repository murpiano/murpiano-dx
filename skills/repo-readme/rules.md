# README rules

## Order

Use the selected template's section names and order. Preserve its static text,
footer, and links; fill placeholders with verified project facts. Follow explicit
conditional instructions. Existing README structure does not override the template.
Only an explicit user instruction permits a departure. Preserve any existing
agent entry-point notice as the first line. Keep the footer's four links exactly
as written, including MIT regardless of a local LICENSE file; do not insert
separator dots or HTML wrappers. Keep unrelated development traces out of
public product documentation.

## Accuracy

Derive commands, paths, versions, and supported features from the repository.
Keep examples runnable. Do not claim automation that is not configured.

## Metadata and badges

Use a concise GitHub description and only relevant topics. The CI badge requires a
working `.github/workflows/ci.yml`. The Release badge requires a public repository
and at least one published release. Remove stale badges.

## Review

Check links, headings, code fences, spelling, and `git diff --check`. Keep the
README focused on user value; put agent-only workflow in `AGENTS.md` and skills.
Run `bash <murpiano-dx>/sync.sh check-readme <project>` before completion,
commit, PR, or publication. Use `--template <path>` for an explicitly selected
template. Fix all failures and review factual accuracy separately.
