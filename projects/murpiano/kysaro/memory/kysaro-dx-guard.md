---
name: kysaro-dx-guard
description: "murpiano-dx pre-commit guard runs in kysaro through ~/.config/husky/init.sh, not through the repo"
metadata:
  node_type: memory
  type: project
  originSessionId: 864cb467-6ffb-428a-a059-750131bf84c8
  modified: 2026-10-16T20:25:30.014Z
---

kysaro has its own husky `pre-commit` (`npm test`), so murpiano-dx `sync.sh` does not install its guard there. Since 2026-10-16 the guard (no commits on main, agent traces, secrets) runs from `~/.config/husky/init.sh`, limited to origin `murpiano/kysaro`. Husky sources that file before every hook, even with `HUSKY=0`.

**Why:** a path to murpiano-dx in the tracked `.husky/pre-commit` would be an agent-tooling trace in the public repo. The user approved a local, kysaro-only setup.

**How to apply:** do not add the guard to `.husky/pre-commit`. Commits on main in kysaro need `MURPIANO_ON_MAIN=1` and the user's request. Old-style `chore(build): release X` commits on main are blocked now; see [[kysaro-release]].
