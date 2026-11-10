# [Kysaro](https://github.com/murpiano/kysaro) setup

[Kysaro](https://github.com/murpiano/kysaro) is the Git linter, installed separately in each initialized project. murpiano-dx stores the
decision and verifies the setup; it does not replace the project linter.

## Setup sequence

1. Add the local development dependency with the project package manager.
2. Create or preserve `.kysaro/settings/` using the project’s approved message
   and pull request rules.
3. Install the `commit-msg` hook without overwriting an existing custom hook.
4. Add `.github/workflows/kysaro.yml` to run `npx --no-install kysaro ci`.
5. Run valid and invalid message checks locally.
6. Run `bash <murpiano-dx>/sync.sh init --kysaro enabled` only after every component
   is present.
7. Add the squash-merge note below to this project's own
   `project-profile.md` → Git workflow → Merge strategy row, so it is
   visible from the project's own data, not only from this shared file.

## Rules

- Keep the dependency local to the project.
- Do not download packages during `sync.sh start` or a state-only `init`.
- Preserve existing hooks and report conflicts instead of overwriting them.
- [Kysaro](https://github.com/murpiano/kysaro) validates configured message and PR conventions; the agent chooses the
  branch and explains the change.
- A saved `declined` decision suppresses repeated offers until the owner asks again.
- **A server-side squash/merge commit (`gh pr merge --squash`, or the
  GitHub UI's own button) is synthesized by GitHub's merge API, not by
  local `git commit` — the local `commit-msg` hook never runs on it.**
  The PR's own `kysaro` CI check only validates the commits that exist
  *before* the squash, not the squash commit that gets created after
  the merge completes; a push-triggered `kysaro` check on the base
  branch is the only thing that ever sees the real squash message, and
  by then it is already permanent history. Before calling
  `gh pr merge --squash --subject ... --body ...` (or any merge
  carrying a custom body), run `kysaro -m "<the exact composed
  subject+body>"` locally first and fix it until it exits 0 — don't
  rely on hand-wrapping line length by eye, and don't trust the PR
  check to have validated the message that will actually land.
