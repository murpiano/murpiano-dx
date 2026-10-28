---
name: project-known-issues
description: Copycat repo — known non-obvious test flakiness and native-module ABI tradeoff
metadata:
  node_type: memory
  type: project
  originSessionId: dbcb7f87-5691-4a01-a426-8d24f3d05a1f
  modified: 2026-10-28T06:57:05.354Z
---

Copycat (Windows clipboard-history manager, Electron+React+TS+SQLite) has two known environment quirks discovered during initial implementation (2026-10-13):

1. `npm test` is occasionally flaky with a native SIGABRT ("Assertion failed: (env) != nullptr" in `Database::~Database()`) — a known better-sqlite3 + Jest worker-teardown interaction, not a code bug. Retrying the run passes. If this recurs frequently, consider isolating storage-touching suites into their own Jest project/process.
2. `better-sqlite3`'s native binary needs different ABI builds for `npm run dev` (Electron's NODE_MODULE_VERSION) vs `npm test` (plain Node's NODE_MODULE_VERSION, via ts-jest). There is no single `postinstall` hook that satisfies both — adding `electron-builder install-app-deps` as postinstall breaks Jest. Switching between dev and test currently requires manually rebuilding (`npx electron-builder install-app-deps` for dev, `npm install` to restore for test).

Why: discovered while implementing the full app (see git log on master for the commit history — the SDD plan workspace that had full context was deleted per [[superpowers-sdd]] convention once the final review passed).

How to apply: don't treat either symptom as a regression on first sight — reproduce/retry before investigating as a new bug.

## How to run it manually in this sandbox (WSLg)

`npm run dev` fails here: the harness auto-injects `--host/--port/--strictPort`
into dev-server-looking commands, which `electron-vite dev`'s CLI rejects.
Workaround — build once, then launch the built app directly, bypassing both
that CLI and the sandbox's `ELECTRON_RUN_AS_NODE=1` (which otherwise makes
Electron boot as plain Node and crash on `app.whenReady`):

```bash
npm run build
npx electron-builder install-app-deps   # rebuild better-sqlite3 for Electron's ABI (see ABI note above)
env -u ELECTRON_RUN_AS_NODE npx electron out/main/index.js
```

Remember to `npm install` afterward (or rerun this rebuild) before running
`npm test` again — same ABI tradeoff as above.

## Better recipe (verified 2026-10-28)

No rebuild juggling is needed for either side:

```bash
# Dev with HMR; COPYCAT_DEV_WINDOW=1 gives a framed window that survives blur.
env -u ELECTRON_RUN_AS_NODE -u WSLENV COPYCAT_DEV_WINDOW=1 npx electron-vite dev

# Run the sqlite-touching suites against Electron's own Node, matching the ABI
# better-sqlite3 was built for — no "Module did not self-register".
ELECTRON_RUN_AS_NODE=1 npx electron node_modules/jest/bin/jest.js --runInBand tests/unit
```

Killing instances: `pkill -f "[e]lectron-vite"` also matches the shell running
it and kills your own session (exit 144). Collect PIDs first instead:
`pgrep -f 'dist/[e]lectron' | xargs -r kill`.

Screenshotting the GUI: there is no `import`/`scrot`/`grim` here, and Playwright's
`_electron` `page.screenshot()` hangs under WSLg. What works is serving the built
renderer over HTTP (`python3 -m http.server` inside `out/renderer`; `file://`
breaks ES module loading) and opening it in Playwright's chromium with
`window.copycat` stubbed via `addInitScript`.
