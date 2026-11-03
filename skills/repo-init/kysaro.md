# Kysaro setup

Kysaro is the Git linter, installed separately in each initialized project. murpiano-dx stores the
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

## Rules

- Keep the dependency local to the project.
- Do not download packages during `sync.sh start` or a state-only `init`.
- Preserve existing hooks and report conflicts instead of overwriting them.
- Kysaro validates configured message and PR conventions; the agent chooses the
  branch and explains the change.
- A saved `declined` decision suppresses repeated offers until the owner asks again.
