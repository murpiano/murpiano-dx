# Travel globe, part 1: React foundation and the living globe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old CloudPix app with a React app that shows the demo traveller's night globe: stars and sky events, land and lights, the 22 demo places and the home house, with spin, trackball drag, throw, wheel and pinch zoom, the unroll to a flat map, and the hover label.

**Architecture:** React renders the DOM (header, label, loading screen). A canvas engine (`src/engine/engine.ts`) owns one `requestAnimationFrame` loop, a world clock, the camera and the pointer input; it draws with pure-ish render modules and talks to React only through a tiny store (`src/state/store.ts`) read with `useSyncExternalStore`. All math that went wrong in the prototype lives in pure modules (`geo/`, `render/places.ts`, `engine/throw.ts`, `engine/clock.ts`) under Vitest.

**Tech Stack:** React 19, TypeScript 6 (strict, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`), Vite 8 with `@vitejs/plugin-react`, SCSS, Vitest 5 (node environment), `d3-geo`, `topojson-client`.

**Spec:** [`docs/design/2026-09-29-travel-globe.md`](../../design/2026-09-29-travel-globe.md). Reference prototype: [`docs/design/prototype/flight.html`](../../design/prototype/flight.html) and [`atlas-data.js`](../../design/prototype/atlas-data.js). When the spec and the prototype disagree, the spec wins.

**The whole build is five plans.** Each one ends with a working app:

1. **This plan.** React foundation, data model, demo data, the globe, the sky, input.
2. Timeline, place states, flights and the camera, the album panel, tours, "Show on map" hooks.
3. Photo window, header (burger, stats, settings), keys, world pause.
4. Archive layer: tabs, pages, folders.
5. Owner mode: repositories (local and demo), login, account, forms, photo storage; README rewrite; merge.

## Global Constraints

- Work on the branch `feat/travel-globe`. Never push to `main` until plan 5: every push to `main` deploys to GitHub Pages (`.github/workflows/deploy.yml`).
- Node `>=22.12` (package.json `engines`). Vite serves on `127.0.0.1:3001`.
- The app is served from `/cloudpix-platform/` in production (`VITE_BASE`). Build every asset URL from `import.meta.env.BASE_URL`, never from a bare `/`.
- New runtime dependencies are exactly: `react`, `react-dom`, `d3-geo`, `topojson-client`. Nothing else at runtime.
- `npm run check` (typecheck, lint, test) stays green after every task.
- Code style: Prettier (`singleQuote`, `printWidth: 100`, `trailingComma: all`); ESLint `typescript-eslint` strict (no `!` non-null assertions, `consistent-type-imports`, `eqeqeq`); `import type` for types (`verbatimModuleSyntax`).
- Code, comments, commit messages in English. Commits follow Conventional Commits.
- Colours: star blue `#8fb8ff`, lamp yellow `#ffc86b`, sky `#04060d`.
- Timings from the spec: place fades about 0.4 s; pulse is a raised cosine over 1.5 s; unroll 1.1 s; sky events every 7–20 s, meteor about 2.5 s, satellite 16–24 s.
- Zoom: farthest is half the resting size (`Z_MIN = 0.5`); unroll notch three wheel notches before the ball would touch the screen edge, never at the resting size.
- Devices: 60 fps on a laptop, usable on a phone at 390 px.

## Review Focus

- **Resizing or rotating a phone while the map is flat** — the flat map must still cover the whole screen with no gap. Pinned in Task 6 (`zFlat` covers a 390 × 844 phone).
- **A tab coming back from the background** — the first frame after a long gap must not jump the world forward by seconds. Pinned in Task 12 (`frameStep` clamps to 70 ms).
- **A trackpad sending small wheel deltas right at the unroll notch** — the map must not flip between ball and flat while the zoom target stays put. Pinned in Task 6 (`stepUnroll` is stable at the notch).
- **The map or the credits failing to load** (offline, wrong base path on Pages) — the page shows a note and a retry, never a blank sky. Pinned in Task 13 (`loadWorld` rejects on HTTP errors) and its manual check.
- **Lights and places behind the ball, or at the edges of the flat map** — hidden behind the ball, all shown on the flat map, and a hidden place is never hovered. Pinned in Task 6 (`faces`).

---

## File map

Created:

```
index.html                       rewritten: #root, fonts
src/main.tsx                     mounts <App/>
src/app/App.tsx, app.scss        boot screen, then the globe and the header
src/app/boot.ts                  loadWorld(): map + demo archive
src/state/store.ts               createStore, useStore
src/state/app-state.ts           appStore: labelCityKey, paused
src/lib/easing.ts                smooth, smoother, ease, pulse
src/lib/random.ts                seeded
src/data/types.ts                the data model
src/data/order.ts                byDate, slugOf, seedOf
src/data/demo.ts                 DEMO_HOME, buildDemo(credits)
src/data/archive.ts              linkArchive, photoTotal, visitYears
src/geo/vector.ts                Vec3, vec, dot
src/geo/camera.ts                quaternions, turn, camCurve
src/geo/projection.ts            blend projection, clips, zoom notch, unroll, faces
src/geo/world.ts                 EarthGeo from the TopoJSON
src/render/lights.ts             faint city lights on land
src/render/places.ts             place states and their looks
src/render/sky.ts                star field, twinkles, meteors, satellites
src/render/house.ts              isometric house and chimney smoke
src/render/globe.ts              painter: earth, places, home
src/engine/clock.ts              frameStep
src/engine/throw.ts              drag samples, throw velocity, spin direction
src/engine/engine.ts             the frame loop and the input
src/features/globe/GlobeStage.tsx, PlaceLabel.tsx, globe.scss
src/features/header/Header.tsx, header.scss
```

Kept: `src/lib/math.ts`, `src/lib/storage.ts`, `src/styles/normalize.scss`, `src/styles/helpers/*`, `public/*`.
Rewritten: `src/styles/variables.scss`, `src/styles/globals.scss`, `src/styles/fonts.scss`, `src/styles/index.ts`, `package.json`, `vite.config.ts`, `tsconfig.json`, `eslint.config.js`.
Deleted: the old app (`src/main.ts`, `src/config.ts`, `src/api/`, `src/app/*.ts`, `src/features/*`, most of `src/lib/`, `src/styles/utils.scss`).

---

### Task 1: Branch and React scaffold in place of the old app

**Files:**
- Modify: `package.json`, `vite.config.ts`, `tsconfig.json`, `eslint.config.js`, `index.html`, `src/styles/index.ts`, `src/styles/variables.scss`, `src/styles/globals.scss`, `src/styles/fonts.scss`
- Create: `src/main.tsx`, `src/app/App.tsx`, `src/app/app.scss`
- Delete: `src/main.ts`, `src/config.ts`, `src/api/`, `src/app/guard.ts`, `src/app/flags.ts`, `src/app/likes.ts`, `src/features/` (all), `src/lib/async.ts`, `src/lib/decode.ts`, `src/lib/dom.ts`, `src/lib/format.ts`, `src/lib/icons.ts`, `src/lib/monogram.ts`, `src/lib/monogram.test.ts`, `src/lib/sort.ts`, `src/lib/sort.test.ts`, `src/styles/utils.scss`

**Interfaces:**
- Consumes: nothing.
- Produces: `App` component (`src/app/App.tsx`), the `@/` alias, the CSS tokens `--sky`, `--lamp`, `--star`, `--text`, `--muted`, `--ease`, `--font-family-base`, `--font-family-display`, `--safe-top`.

- [ ] **Step 1: Create the branch**

```bash
git switch -c feat/travel-globe
```

- [ ] **Step 2: Delete the old app**

```bash
git rm -r -q src/main.ts src/config.ts src/api src/app src/features \
  src/lib/async.ts src/lib/decode.ts src/lib/dom.ts src/lib/format.ts src/lib/icons.ts \
  src/lib/monogram.ts src/lib/monogram.test.ts src/lib/sort.ts src/lib/sort.test.ts \
  src/styles/utils.scss
ls src src/lib
```

Expected: `src` holds `lib` and `styles`; `src/lib` holds `math.ts` and `storage.ts`.

- [ ] **Step 3: Install the dependencies**

```bash
npm install react react-dom d3-geo topojson-client
npm install -D @vitejs/plugin-react @types/react @types/react-dom @types/d3-geo \
  @types/topojson-client @types/topojson-specification @types/geojson eslint-plugin-react-hooks
```

Expected: both commands finish without `ERESOLVE` errors. If `eslint-plugin-react-hooks` refuses the installed ESLint major, stop and report the exact peer range it asks for.

- [ ] **Step 4: Update `package.json` description**

Change the `description` field to:

```json
"description": "A personal travel archive on a night globe: places, albums, and a plane that flies the trips in order.",
```

- [ ] **Step 5: Wire React into Vite, TypeScript and ESLint**

`vite.config.ts` — add the plugin (keep everything else as it is):

```ts
/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  // GitHub Pages serves the app from /cloudpix-platform/, see .github/workflows/deploy.yml
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '@use "@/styles/helpers" as *;\n',
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 3001,
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 3001,
    strictPort: true,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
```

`tsconfig.json` — add `"jsx": "react-jsx"` to `compilerOptions`, right after `"lib"`:

```json
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
```

`eslint.config.js` — the design prototype is throwaway JavaScript and must not be linted; add the React hooks rules:

```js
import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'node_modules', '.temp', '.superpowers', 'docs'] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: {
      globals: { ...globals.browser },
    },
    rules: {
      eqeqeq: 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'prefer-const': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
    },
  },
);
```

- [ ] **Step 6: Rewrite `index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <title>CloudPix — every trip on a night globe</title>
    <meta
      name="description"
      content="CloudPix is a personal travel archive on a night globe: places, albums, and a plane that flies the trips in order."
    />
    <meta name="author" content="Bogdan Trotsenko" />
    <meta name="theme-color" content="#04060d" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Fraunces:ital,opsz,wght@1,9..144,300;1,9..144,500&display=swap"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Rewrite the global styles**

`src/styles/index.ts`:

```ts
import './normalize.scss';
import './fonts.scss';
import './variables.scss';
import './globals.scss';
```

`src/styles/fonts.scss`:

```scss
// Space Grotesk (text) and Fraunces italic (display) are served by Google Fonts —
// see the <link> in `index.html`. Families are exposed through
// --font-family-base / --font-family-display in `variables.scss`.
//
// Declare @font-face rules here only for families that cannot be loaded that way.
```

`src/styles/variables.scss`:

```scss
:root {
  --sky: #04060d;
  --lamp: #ffc86b;
  --star: #8fb8ff;
  --text: #e8ecf6;
  --muted: #7f89a3;

  --ease: cubic-bezier(0.2, 0.8, 0.2, 1);

  --font-family-base: 'Space Grotesk', -apple-system, 'Segoe UI', helvetica, arial, sans-serif;
  --font-family-display: 'Fraunces', georgia, serif;

  --safe-top: env(safe-area-inset-top, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
}
```

`src/styles/globals.scss`:

```scss
html,
body,
#root {
  height: 100%;
}

html {
  background-color: var(--sky);
  overscroll-behavior: none;
  -webkit-text-size-adjust: 100%;
}

body {
  overflow: hidden;
  overscroll-behavior: none;
  font-family: var(--font-family-base);
  font-size: 14px;
  color: var(--text);
  background-color: var(--sky);
  user-select: none;
  -webkit-user-select: none;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button {
  color: inherit;
}
```

- [ ] **Step 8: Create the entry point and an App shell**

`src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from '@/app/App';
import '@/styles/index';

const root = document.getElementById('root');
if (!root) {
  throw new Error('#root is missing from index.html');
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`src/app/App.tsx` (Task 13 replaces the body):

```tsx
import './app.scss';

export function App() {
  return <p className="boot">Loading the map…</p>;
}
```

`src/app/app.scss`:

```scss
.boot {
  position: fixed;
  inset: 0;
  display: grid;
  place-content: center;
  gap: 14px;
  margin: 0;
  text-align: center;
  color: var(--muted);

  button {
    justify-self: center;
    padding: 8px 18px;
    border: 1px solid rgb(127 137 163 / 35%);
    border-radius: 999px;
    background: rgb(12 16 30 / 60%);
  }
}
```

- [ ] **Step 9: Verify the scaffold**

Run: `npm run typecheck && npm run lint && npm run build`
Expected: all three pass. `npm run test` has no test files yet and may exit non-zero with "No test files found" — that is expected until Task 2.

Run: `npm run dev`, open `http://127.0.0.1:3001/`.
Expected: a near-black page with "Loading the map…" in the middle, no console errors. Stop the server.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: replace the old app with a React scaffold"
```

---

### Task 2: Store and app state

**Files:**
- Create: `src/state/store.ts`, `src/state/app-state.ts`
- Test: `src/state/store.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `interface Store<T extends object> { get(): T; set(patch: Partial<T>): void; subscribe(listener: () => void): () => void }`
  - `createStore<T extends object>(initial: T): Store<T>`
  - `useStore<T extends object, S>(store: Store<T>, select: (state: T) => S): S`
  - `interface AppState { labelCityKey: string | null; paused: boolean }`, `appStore: Store<AppState>`

- [ ] **Step 1: Write the failing test**

`src/state/store.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import { createStore } from './store';

describe('createStore', () => {
  it('returns the initial state', () => {
    const store = createStore({ count: 1, name: 'a' });
    expect(store.get()).toEqual({ count: 1, name: 'a' });
  });

  it('merges a patch and tells the listeners', () => {
    const store = createStore({ count: 1, name: 'a' });
    const listener = vi.fn();
    store.subscribe(listener);
    store.set({ count: 2 });
    expect(store.get()).toEqual({ count: 2, name: 'a' });
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it('keeps the same state object and stays quiet when nothing changes', () => {
    const store = createStore({ count: 1 });
    const before = store.get();
    const listener = vi.fn();
    store.subscribe(listener);
    store.set({ count: 1 });
    expect(store.get()).toBe(before);
    expect(listener).not.toHaveBeenCalled();
  });

  it('stops telling a listener after it unsubscribes', () => {
    const store = createStore({ count: 1 });
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);
    unsubscribe();
    store.set({ count: 2 });
    expect(listener).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/state/store.test.ts`
Expected: FAIL — cannot resolve `./store`.

- [ ] **Step 3: Implement the store and the app state**

`src/state/store.ts`:

```ts
import { useSyncExternalStore } from 'react';

export interface Store<T extends object> {
  get(): T;
  set(patch: Partial<T>): void;
  subscribe(listener: () => void): () => void;
}

/**
 * A tiny store. React reads it through `useStore`; the canvas engine reads `get()` every frame
 * and calls `set` only when something changes, so React never renders once per frame.
 */
export const createStore = <T extends object>(initial: T): Store<T> => {
  let state = initial;
  const listeners = new Set<() => void>();

  return {
    get: () => state,
    set(patch) {
      const keys = Object.keys(patch) as (keyof T)[];
      if (!keys.some((key) => !Object.is(patch[key], state[key]))) {
        return;
      }
      state = { ...state, ...patch };
      for (const listener of listeners) {
        listener();
      }
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
};

/** Reads a slice of a store. `select` must return a primitive or an object kept in the state. */
export const useStore = <T extends object, S>(store: Store<T>, select: (state: T) => S): S =>
  useSyncExternalStore(store.subscribe, () => select(store.get()));
```

`src/state/app-state.ts`:

```ts
import { createStore } from './store';

export interface AppState {
  /**
   * The city the hover label shows. It keeps the last city after the cursor leaves, so the label
   * can fade out with its text still in it.
   */
  labelCityKey: string | null;
  /** True while the photo window or the archive is open: the world clock stops. */
  paused: boolean;
}

export const appStore = createStore<AppState>({ labelCityKey: null, paused: false });
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/state/store.test.ts`
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add src/state
git commit -m "feat(state): add a small store for React and the canvas engine"
```

---

### Task 3: Easing and seeded random

**Files:**
- Create: `src/lib/easing.ts`, `src/lib/random.ts`
- Test: `src/lib/easing.test.ts`, `src/lib/random.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `smooth(x: number): number`, `smoother(x: number): number`
  - `ease(value: number, target: number, f: number, k: number): number` — `f` is the frame length in 60 Hz frames
  - `pulse(since: number, duration: number): number`
  - `seeded(seed: number): () => number`

- [ ] **Step 1: Write the failing tests**

`src/lib/easing.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { ease, pulse, smooth, smoother } from './easing';

describe('smooth and smoother', () => {
  it('run from 0 to 1 through the middle', () => {
    for (const curve of [smooth, smoother]) {
      expect(curve(0)).toBe(0);
      expect(curve(0.5)).toBeCloseTo(0.5);
      expect(curve(1)).toBe(1);
    }
  });
});

describe('ease', () => {
  it('does not depend on the frame rate', () => {
    let at60 = 0;
    for (let i = 0; i < 60; i++) at60 = ease(at60, 1, 1, 0.9);
    let at30 = 0;
    for (let i = 0; i < 30; i++) at30 = ease(at30, 1, 2, 0.9);
    expect(at60).toBeCloseTo(at30, 10);
  });

  it('stays put when no time passes', () => {
    expect(ease(0.3, 1, 0, 0.9)).toBe(0.3);
  });
});

describe('pulse', () => {
  it('starts and ends at rest and peaks in the middle', () => {
    expect(pulse(0, 1500)).toBe(0);
    expect(pulse(750, 1500)).toBeCloseTo(1);
    expect(pulse(1500, 1500)).toBe(0);
    expect(pulse(-1, 1500)).toBe(0);
    expect(pulse(-Infinity, 1500)).toBe(0);
  });

  it('has no jolt at either end', () => {
    expect(pulse(15, 1500)).toBeLessThan(0.002);
    expect(pulse(1485, 1500)).toBeLessThan(0.002);
  });
});
```

`src/lib/random.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { seeded } from './random';

describe('seeded', () => {
  it('repeats the same numbers for the same seed', () => {
    const a = seeded(11);
    const b = seeded(11);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });

  it('stays inside (0, 1)', () => {
    const random = seeded(3);
    for (let i = 0; i < 1000; i++) {
      const value = random();
      expect(value).toBeGreaterThan(0);
      expect(value).toBeLessThan(1);
    }
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib`
Expected: FAIL — cannot resolve `./easing` and `./random`.

- [ ] **Step 3: Implement**

`src/lib/easing.ts`:

```ts
/** Smoothstep: zero speed at both ends. */
export const smooth = (x: number): number => x * x * (3 - 2 * x);

/** Smootherstep: zero speed and zero acceleration at both ends. */
export const smoother = (x: number): number => x * x * x * (x * (x * 6 - 15) + 10);

/**
 * Moves `value` toward `target` at the same pace at any frame rate. `f` is the frame length in
 * 60 Hz frames; each 60 Hz frame keeps `k` of the remaining gap.
 */
export const ease = (value: number, target: number, f: number, k: number): number =>
  value + (target - value) * (1 - k ** f);

/** One soft pulse over `duration` ms: 0 → 1 → 0 as a raised cosine, with no jolt at either end. */
export const pulse = (since: number, duration: number): number =>
  since >= 0 && since < duration ? (1 - Math.cos((2 * Math.PI * since) / duration)) / 2 : 0;
```

`src/lib/random.ts`:

```ts
/** A small deterministic generator (Park–Miller), so stars and lights look the same on every visit. */
export const seeded = (seed: number): (() => number) => {
  let state = seed;
  return () => {
    state = (state * 16807) % 2147483647;
    return state / 2147483647;
  };
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/lib`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib
git commit -m "feat(lib): add easing curves and a seeded random generator"
```

---

### Task 4: Data model, ordering and the demo archive

**Files:**
- Create: `src/data/types.ts`, `src/data/order.ts`, `src/data/demo.ts`, `src/data/archive.ts`
- Test: `src/data/order.test.ts`, `src/data/demo.test.ts`, `src/data/archive.test.ts`

**Interfaces:**
- Consumes: `pad2` from `src/lib/math.ts`.
- Produces:
  - Types (`src/data/types.ts`): `Id`, `Place`, `PhotoRef`, `Endpoint`, `AlbumData`, `CityData`, `CountryData`, `Trip`, `ArchiveData`, `Country`, `City`, `Album`, `User`, `Credit` — exactly as in Step 3.
  - `byDate(a, b): number`, `slugOf(text: string): string`, `seedOf(text: string): number`
  - `DEMO_HOME: Place`, `buildDemo(credits: Credit[]): ArchiveData`
  - `interface Archive { data; countries; cities; albums; trips; cityByKey; albumById }`, `linkArchive(data: ArchiveData): Archive`, `photoTotal(city: City): number`, `visitYears(city: City): number[]`

- [ ] **Step 1: Write the failing tests**

`src/data/order.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { byDate, seedOf, slugOf } from './order';

const moment = (year: number, month: number, day: number, time: string, title: string) => ({
  year,
  month,
  day,
  time,
  title,
});

describe('byDate', () => {
  it('orders by year, month, day, time, then title', () => {
    const list = [
      moment(2023, 4, 2, '09:00', 'b'),
      moment(2023, 4, 2, '09:00', 'a'),
      moment(2023, 4, 2, '08:30', 'z'),
      moment(2023, 4, 1, '23:00', 'z'),
      moment(2023, 3, 30, '23:00', 'z'),
      moment(2022, 12, 31, '23:59', 'z'),
    ];
    const sorted = [...list].sort(byDate);
    expect(sorted.map((m) => `${m.year}-${m.month}-${m.day} ${m.time} ${m.title}`)).toEqual([
      '2022-12-31 23:59 z',
      '2023-3-30 23:00 z',
      '2023-4-1 23:00 z',
      '2023-4-2 08:30 z',
      '2023-4-2 09:00 a',
      '2023-4-2 09:00 b',
    ]);
  });
});

describe('slugOf', () => {
  it('drops accents and joins words with dashes', () => {
    expect(slugOf('Reykjavík')).toBe('reykjavik');
    expect(slugOf('Queenstown New Zealand')).toBe('queenstown-new-zealand');
    expect(slugOf('Gaudí & the sea')).toBe('gaudi-the-sea');
    expect(slugOf('Seven hills, one week')).toBe('seven-hills-one-week');
  });
});

describe('seedOf', () => {
  it('is stable', () => {
    expect(seedOf('abc')).toBe(304891);
    expect(seedOf('Tram 28')).toBe(seedOf('Tram 28'));
  });
});
```

`src/data/demo.test.ts`:

```ts
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { buildDemo, DEMO_HOME } from './demo';
import { slugOf } from './order';
import type { Credit } from './types';

const demoDir = fileURLToPath(new URL('../../public/demo/', import.meta.url));
const credits = JSON.parse(readFileSync(`${demoDir}photos.json`, 'utf8')) as Credit[];
const demo = buildDemo(credits);
const cities = demo.countries.flatMap((country) => country.cities);
const albums = cities.flatMap((city) => city.albums);

const cityOf = (key: string) => {
  const city = cities.find((c) => c.key === key);
  if (!city) throw new Error(`no demo city ${key}`);
  return city;
};

describe('demo archive', () => {
  it('has the size the design promises', () => {
    expect(demo.countries).toHaveLength(12);
    expect(cities).toHaveLength(22);
    expect(albums).toHaveLength(32);
    expect(demo.trips).toHaveLength(23);
  });

  it('lives in Kyiv', () => {
    expect(DEMO_HOME).toEqual({
      name: 'Kyiv',
      country: 'Ukraine',
      countryId: '804',
      lat: 50.45,
      lon: 30.52,
    });
  });

  it('gives every album its own id', () => {
    expect(new Set(albums.map((album) => album.id)).size).toBe(albums.length);
  });

  it('puts every album in exactly one trip', () => {
    const counts = new Map<string, number>();
    for (const trip of demo.trips) {
      for (const id of trip.albumIds) counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    expect([...counts.keys()].sort()).toEqual(albums.map((album) => album.id).sort());
    expect([...counts.values()].every((count) => count === 1)).toBe(true);
  });

  it('starts and ends every demo trip at home', () => {
    for (const trip of demo.trips) {
      expect(trip.start).toEqual({ home: true });
      expect(trip.end).toEqual({ home: true });
    }
  });

  it('gives every album a valid day and time', () => {
    for (const album of albums) {
      expect(album.day).toBeGreaterThanOrEqual(1);
      expect(album.day).toBeLessThanOrEqual(26);
      expect(album.time).toMatch(/^([01]\d|2[0-3]):[0-5]\d$/);
    }
  });

  it('gives every album at least one stock photo', () => {
    for (const album of albums) {
      expect(album.photos.length, album.id).toBeGreaterThan(0);
      expect(album.photos.every((photo) => photo.kind === 'stock')).toBe(true);
    }
  });

  it('opens each album of a city on a different photo', () => {
    const barcelona = cityOf('barcelona');
    const covers = barcelona.albums.map((album) => {
      const first = album.photos[0];
      return first?.kind === 'stock' ? first.file : '';
    });
    expect(new Set(covers).size).toBe(barcelona.albums.length);
  });

  it('credits only demo cities', () => {
    const keys = new Set(cities.map((city) => city.key));
    for (const credit of credits) expect(keys.has(slugOf(credit.city)), credit.city).toBe(true);
  });

  it('finds every credited photo on disk', () => {
    for (const credit of credits) {
      expect(existsSync(`${demoDir}photos/${credit.file}`), credit.file).toBe(true);
    }
  });
});
```

`src/data/archive.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { linkArchive, photoTotal, visitYears } from './archive';
import type { AlbumData, ArchiveData } from './types';

const album = (id: string, year: number, month: number, photoCount: number): AlbumData => ({
  id,
  title: id,
  year,
  month,
  day: 1,
  time: '12:00',
  photoCount,
  photos: [],
});

const data: ArchiveData = {
  countries: [
    {
      id: '724',
      name: 'Spain',
      cities: [
        {
          key: 'madrid',
          name: 'Madrid',
          lat: 40.42,
          lon: -3.7,
          albums: [album('m2', 2024, 1, 3), album('m1', 2021, 5, 4), album('m3', 2021, 9, 1)],
        },
        { key: 'empty', name: 'Empty', lat: 0, lon: 0, albums: [] },
      ],
    },
    {
      id: '620',
      name: 'Portugal',
      cities: [{ key: 'lisbon', name: 'Lisbon', lat: 38.7, lon: -9.1, albums: [album('l1', 2019, 4, 2)] }],
    },
  ],
  trips: [{ id: 't', name: 'Trip', start: { home: true }, end: { home: true }, albumIds: ['m1'] }],
};

describe('linkArchive', () => {
  const archive = linkArchive(data);

  it('links albums to cities and cities to countries', () => {
    const madrid = archive.cityByKey.get('madrid');
    expect(madrid?.country.name).toBe('Spain');
    expect(archive.albumById.get('m1')?.city).toBe(madrid);
  });

  it('lights only cities that hold albums', () => {
    expect(archive.cities.map((city) => city.key)).toEqual(['madrid', 'lisbon']);
  });

  it('lists every album oldest first', () => {
    expect(archive.albums.map((a) => a.id)).toEqual(['l1', 'm1', 'm3', 'm2']);
  });

  it('keeps the trips', () => {
    expect(archive.trips).toBe(data.trips);
  });
});

describe('city helpers', () => {
  const archive = linkArchive(data);
  const madrid = archive.cityByKey.get('madrid');

  it('adds up the photos of a city', () => {
    expect(madrid && photoTotal(madrid)).toBe(8);
  });

  it('lists the years of visits once each, in order', () => {
    expect(madrid && visitYears(madrid)).toEqual([2021, 2024]);
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/data`
Expected: FAIL — cannot resolve `./order`, `./demo`, `./archive`.

- [ ] **Step 3: Write the types**

`src/data/types.ts`:

```ts
export type Id = string;

/** A place on Earth: a home base, or a city from the place picker. */
export interface Place {
  name: string;
  country: string;
  /** ISO 3166 numeric code, as in the world map. */
  countryId: string;
  lat: number;
  lon: number;
}

export type PhotoRef =
  /** A bundled demo photo in public/demo/photos. */
  | { kind: 'stock'; file: string; caption?: string }
  /** The owner's photo, a blob in IndexedDB. */
  | { kind: 'own'; id: Id; name: string; caption?: string };

export type Endpoint = { home: true } | { cityKey: Id };

/** An album as stored: plain JSON with no links back up. */
export interface AlbumData {
  id: Id;
  title: string;
  year: number;
  month: number;
  day: number;
  /** "HH:MM", local time. */
  time: string;
  /** Demo albums claim more photos than they carry. */
  photoCount: number;
  photos: PhotoRef[];
}

export interface CityData {
  key: Id;
  name: string;
  lat: number;
  lon: number;
  albums: AlbumData[];
}

export interface CountryData {
  /** ISO 3166 numeric code. */
  id: Id;
  name: string;
  cities: CityData[];
}

/** An album belongs to at most one trip. */
export interface Trip {
  id: Id;
  name: string;
  start: Endpoint;
  end: Endpoint;
  albumIds: Id[];
}

/** Everything the owner keeps, as stored. */
export interface ArchiveData {
  countries: CountryData[];
  trips: Trip[];
}

/** The linked graph the UI reads (see `linkArchive`). */
export interface Country {
  id: Id;
  name: string;
  cities: City[];
}

export interface City {
  key: Id;
  name: string;
  lat: number;
  lon: number;
  country: Country;
  albums: Album[];
}

export interface Album extends AlbumData {
  city: City;
}

export interface User {
  name: string;
  email: string;
  home: Place;
}

/** One line of public/demo/photos.json. */
export interface Credit {
  city: string;
  file: string;
  author: string;
  lic: string;
}
```

- [ ] **Step 4: Write the ordering helpers**

`src/data/order.ts`:

```ts
import type { AlbumData } from './types';

type Moment = Pick<AlbumData, 'year' | 'month' | 'day' | 'time' | 'title'>;

/** Albums sort by year, month, day, time, then title. */
export const byDate = (a: Moment, b: Moment): number =>
  a.year - b.year ||
  a.month - b.month ||
  a.day - b.day ||
  a.time.localeCompare(b.time) ||
  a.title.localeCompare(b.title);

export const slugOf = (text: string): string =>
  text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-+$/g, '');

/** A stable number from a string: demo albums take their day and time from it. */
export const seedOf = (text: string): number => {
  let hash = 7;
  for (const char of text) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
};
```

- [ ] **Step 5: Write the demo archive**

`src/data/demo.ts` (the lists are copied from `docs/design/prototype/atlas-data.js`):

```ts
import { pad2 } from '@/lib/math';
import { seedOf, slugOf } from './order';
import type { AlbumData, ArchiveData, CountryData, Credit, PhotoRef, Place, Trip } from './types';

type RawAlbum = [title: string, year: number, month: number, photoCount: number];

interface RawCity {
  name: string;
  key: string;
  lat: number;
  lon: number;
  albums: RawAlbum[];
}

interface RawCountry {
  id: string;
  name: string;
  cities: RawCity[];
}

/** The demo traveller lives in Kyiv. */
export const DEMO_HOME: Place = {
  name: 'Kyiv',
  country: 'Ukraine',
  countryId: '804',
  lat: 50.45,
  lon: 30.52,
};

const COUNTRIES: RawCountry[] = [
  {
    id: '724',
    name: 'Spain',
    cities: [
      {
        name: 'Barcelona',
        key: 'barcelona',
        lat: 41.39,
        lon: 2.17,
        albums: [
          ['Gaudí & the sea', 2019, 3, 64],
          ['New Year on the roof', 2023, 12, 38],
          ['Sagrada Família, finally', 2023, 6, 52],
        ],
      },
      { name: 'Madrid', key: 'madrid', lat: 40.42, lon: -3.7, albums: [['Prado afternoons', 2021, 10, 41]] },
      {
        name: 'Seville',
        key: 'seville',
        lat: 37.39,
        lon: -5.98,
        albums: [['Orange trees in March', 2024, 3, 69]],
      },
    ],
  },
  {
    id: '620',
    name: 'Portugal',
    cities: [
      {
        name: 'Lisbon',
        key: 'lisbon',
        lat: 38.72,
        lon: -9.14,
        albums: [
          ['Tram 28', 2019, 4, 52],
          ['Pastéis and tiles', 2021, 8, 31],
        ],
      },
      { name: 'Porto', key: 'porto', lat: 41.15, lon: -8.61, albums: [['Rain on the Douro', 2022, 11, 33]] },
    ],
  },
  {
    id: '380',
    name: 'Italy',
    cities: [
      {
        name: 'Rome',
        key: 'rome',
        lat: 41.9,
        lon: 12.5,
        albums: [
          ['Seven hills, one week', 2018, 5, 88],
          ['Trastevere nights', 2024, 10, 44],
        ],
      },
      { name: 'Florence', key: 'florence', lat: 43.77, lon: 11.25, albums: [['Duomo at dawn', 2018, 5, 27]] },
      { name: 'Venice', key: 'venice', lat: 45.44, lon: 12.33, albums: [['Fog and gondolas', 2025, 1, 46]] },
    ],
  },
  {
    id: '250',
    name: 'France',
    cities: [
      {
        name: 'Paris',
        key: 'paris',
        lat: 48.86,
        lon: 2.35,
        albums: [
          ['First trip abroad', 2016, 7, 120],
          ['Paris again', 2022, 4, 35],
          ['Louvre at closing time', 2022, 4, 29],
          ['Montmartre sketches', 2025, 9, 40],
        ],
      },
    ],
  },
  {
    id: '352',
    name: 'Iceland',
    cities: [
      { name: 'Reykjavík', key: 'reykjavik', lat: 64.15, lon: -21.94, albums: [['Midnight sun', 2020, 6, 58]] },
      { name: 'Vík', key: 'vik-i-myrdal', lat: 63.42, lon: -19.0, albums: [['Black sand', 2020, 6, 44]] },
    ],
  },
  {
    id: '578',
    name: 'Norway',
    cities: [
      { name: 'Bergen', key: 'bergen', lat: 60.39, lon: 5.32, albums: [['Fjords by ferry', 2021, 7, 61]] },
      { name: 'Tromsø', key: 'tromso', lat: 69.65, lon: 18.96, albums: [['Chasing the aurora', 2024, 1, 93]] },
    ],
  },
  {
    id: '392',
    name: 'Japan',
    cities: [
      {
        name: 'Tokyo',
        key: 'tokyo',
        lat: 35.68,
        lon: 139.69,
        albums: [
          ['Neon and quiet', 2023, 4, 140],
          ['Shibuya crossing', 2025, 11, 63],
        ],
      },
      {
        name: 'Kyoto',
        key: 'kyoto',
        lat: 35.01,
        lon: 135.77,
        albums: [
          ['Sakura week', 2023, 4, 97],
          ['Autumn temples', 2025, 11, 54],
          ['Bamboo grove', 2023, 4, 38],
        ],
      },
    ],
  },
  {
    id: '554',
    name: 'New Zealand',
    cities: [
      { name: 'Auckland', key: 'auckland', lat: -36.85, lon: 174.76, albums: [['Harbour city', 2024, 2, 29]] },
      {
        name: 'Queenstown',
        key: 'queenstown-new-zealand',
        lat: -45.03,
        lon: 168.66,
        albums: [['Southern Alps road trip', 2024, 2, 131]],
      },
    ],
  },
  {
    id: '268',
    name: 'Georgia',
    cities: [
      { name: 'Tbilisi', key: 'tbilisi', lat: 41.72, lon: 44.79, albums: [['Wine and balconies', 2022, 9, 48]] },
    ],
  },
  {
    id: '504',
    name: 'Morocco',
    cities: [
      { name: 'Marrakesh', key: 'marrakesh', lat: 31.63, lon: -8.0, albums: [['Souks and saffron', 2021, 12, 57]] },
    ],
  },
  {
    id: '840',
    name: 'United States',
    cities: [
      {
        name: 'New York',
        key: 'manhattan',
        lat: 40.71,
        lon: -74.0,
        albums: [['Seven days in Manhattan', 2017, 10, 102]],
      },
      {
        name: 'San Francisco',
        key: 'san-francisco',
        lat: 37.77,
        lon: -122.42,
        albums: [['Fog over the bridge', 2017, 10, 45]],
      },
    ],
  },
  {
    id: '604',
    name: 'Peru',
    cities: [
      { name: 'Cusco', key: 'cusco', lat: -13.53, lon: -71.97, albums: [['Up to Machu Picchu', 2025, 7, 76]] },
    ],
  },
];

/** The demo trips: a name and the titles of the albums it ties together. */
const TRIPS: [name: string, albumTitles: string[]][] = [
  ['First time abroad', ['First trip abroad']],
  ['American autumn', ['Seven days in Manhattan', 'Fog over the bridge']],
  ['Italy by train', ['Seven hills, one week', 'Duomo at dawn']],
  ['Iberian spring', ['Gaudí & the sea', 'Tram 28']],
  ['Iceland in June', ['Midnight sun', 'Black sand']],
  ['Fjords by ferry', ['Fjords by ferry']],
  ['Lisbon, again', ['Pastéis and tiles']],
  ['A weekend in Madrid', ['Prado afternoons']],
  ['Marrakesh before New Year', ['Souks and saffron']],
  ['Paris in April', ['Paris again', 'Louvre at closing time']],
  ['Tbilisi', ['Wine and balconies']],
  ['Porto in the rain', ['Rain on the Douro']],
  ['Japan in bloom', ['Neon and quiet', 'Sakura week', 'Bamboo grove']],
  ['Barcelona summer', ['Sagrada Família, finally']],
  ['New Year in Barcelona', ['New Year on the roof']],
  ['Chasing the aurora', ['Chasing the aurora']],
  ['New Zealand road trip', ['Harbour city', 'Southern Alps road trip']],
  ['Seville in March', ['Orange trees in March']],
  ['Rome in October', ['Trastevere nights']],
  ['Venice in fog', ['Fog and gondolas']],
  ['Peru', ['Up to Machu Picchu']],
  ['Paris, sketching', ['Montmartre sketches']],
  ['Japan in autumn', ['Autumn temples', 'Shibuya crossing']],
];

/** Demo albums get a day and a time of their own, so a trip keeps its order. */
const albumOf = (cityKey: string, [title, year, month, photoCount]: RawAlbum): AlbumData => {
  const seed = seedOf(title);
  return {
    id: `${cityKey}/${slugOf(title)}`,
    title,
    year,
    month,
    day: 1 + (seed % 26),
    time: `${pad2(8 + (seed % 12))}:${pad2((seed >>> 4) % 60)}`,
    photoCount,
    photos: [],
  };
};

/**
 * Builds the demo archive from the photo credits. Each album of a city starts from a different
 * stock photo of that city, so two albums of one city never open on the same picture.
 */
export const buildDemo = (credits: Credit[]): ArchiveData => {
  const pools = new Map<string, Credit[]>();
  for (const credit of credits) {
    const key = slugOf(credit.city);
    pools.set(key, [...(pools.get(key) ?? []), credit]);
  }

  const countries: CountryData[] = COUNTRIES.map((country) => ({
    id: country.id,
    name: country.name,
    cities: country.cities.map((city) => {
      const pool = pools.get(city.key) ?? [];
      return {
        key: city.key,
        name: city.name,
        lat: city.lat,
        lon: city.lon,
        albums: city.albums.map((raw, index) => {
          const shift = pool.length > 0 ? index % pool.length : 0;
          const photos = [...pool.slice(shift), ...pool.slice(0, shift)].map(
            (credit): PhotoRef => ({ kind: 'stock', file: credit.file }),
          );
          return { ...albumOf(city.key, raw), photos };
        }),
      };
    }),
  }));

  const albums = countries.flatMap((country) => country.cities).flatMap((city) => city.albums);
  const trips: Trip[] = TRIPS.map(([name, titles], index) => ({
    id: `d${index}`,
    name,
    start: { home: true },
    end: { home: true },
    albumIds: titles
      .map((title) => albums.find((album) => album.title === title)?.id)
      .filter((id): id is string => id !== undefined),
  }));

  return { countries, trips };
};
```

- [ ] **Step 6: Write the linked archive**

`src/data/archive.ts`:

```ts
import { byDate } from './order';
import type { Album, ArchiveData, City, Country, Id, Trip } from './types';

/** The archive as the UI reads it: linked both ways, with lookups. */
export interface Archive {
  data: ArchiveData;
  countries: Country[];
  /** Cities that hold at least one album: the lights on the globe. */
  cities: City[];
  /** Every album, oldest first. */
  albums: Album[];
  trips: Trip[];
  cityByKey: ReadonlyMap<Id, City>;
  albumById: ReadonlyMap<Id, Album>;
}

export const linkArchive = (data: ArchiveData): Archive => {
  const countries = data.countries.map((countryData) => {
    const country: Country = { id: countryData.id, name: countryData.name, cities: [] };
    country.cities = countryData.cities.map((cityData) => {
      const { albums: albumData, ...place } = cityData;
      const city: City = { ...place, country, albums: [] };
      city.albums = albumData.map((album) => ({ ...album, city }));
      return city;
    });
    return country;
  });

  const allCities = countries.flatMap((country) => country.cities);
  const albums = allCities.flatMap((city) => city.albums).sort(byDate);

  return {
    data,
    countries,
    cities: allCities.filter((city) => city.albums.length > 0),
    albums,
    trips: data.trips,
    cityByKey: new Map(allCities.map((city) => [city.key, city])),
    albumById: new Map(albums.map((album) => [album.id, album])),
  };
};

export const photoTotal = (city: City): number =>
  city.albums.reduce((sum, album) => sum + album.photoCount, 0);

/** The years of visits, once each, oldest first. */
export const visitYears = (city: City): number[] =>
  [...new Set(city.albums.map((album) => album.year))].sort((a, b) => a - b);
```

- [ ] **Step 7: Run the tests**

Run: `npx vitest run src/data`
Expected: PASS. If "finds every credited photo on disk" fails, list the missing files in the report — do not edit `photos.json` to hide them.

- [ ] **Step 8: Run the whole check and commit**

Run: `npm run check`
Expected: PASS.

```bash
git add src/data
git commit -m "feat(data): add the data model and the demo archive"
```

---

### Task 5: Vectors and the camera

**Files:**
- Create: `src/geo/vector.ts`, `src/geo/camera.ts`
- Test: `src/geo/camera.test.ts`

**Interfaces:**
- Consumes: `clamp`, `lerp`, `DEG` from `src/lib/math.ts`.
- Produces:
  - `type Vec3 = [number, number, number]`, `vec(lon: number, lat: number): Vec3`, `dot(a: Vec3, b: Vec3): number`
  - `type Rotation = [number, number, number]` (d3 `rotate` angles in degrees), `type Quat = [number, number, number, number]`
  - `quat(r: Rotation): Quat`, `euler(q: Quat): Rotation`, `qmul(a: Quat, b: Quat): Quat`, `slerp(a: Quat, b: Quat, t: number): Quat`
  - `wrapLon(lon: number): number`
  - `turn(rot: Rotation, dx: number, dy: number, t: number): Rotation` — `dx`, `dy` in degrees, `t` the unroll blend
  - `RAMP = 0.14`, `camCurve(e: number): number`

- [ ] **Step 1: Write the failing test**

`src/geo/camera.test.ts`:

```ts
import { geoDistance, geoRotation } from 'd3-geo';
import { describe, expect, it } from 'vitest';
import { DEG } from '@/lib/math';
import { camCurve, euler, quat, RAMP, slerp, turn, wrapLon } from './camera';
import type { Quat, Rotation } from './camera';
import { dot, vec } from './vector';

/** The lon/lat at the middle of the screen for a d3 rotation. */
const centre = (rot: Rotation) => geoRotation(rot).invert([0, 0]);
const degreesBetween = (a: Rotation, b: Rotation) => geoDistance(centre(a), centre(b)) / DEG;
const norm = (q: Quat) => Math.hypot(...q);

describe('vec and dot', () => {
  it('makes unit vectors on the sphere', () => {
    expect(dot(vec(30, 50), vec(30, 50))).toBeCloseTo(1);
    expect(dot(vec(0, 0), vec(90, 0))).toBeCloseTo(0);
    expect(dot(vec(0, 0), vec(180, 0))).toBeCloseTo(-1);
  });
});

describe('quaternions', () => {
  it('survive a round trip through euler angles', () => {
    const rotations: Rotation[] = [
      [-10, -35, 0],
      [120, 40, 15],
      [-170, -60, -30],
    ];
    for (const rot of rotations) {
      const back = euler(quat(rot));
      back.forEach((angle, i) => expect(angle).toBeCloseTo(rot[i] ?? NaN, 6));
    }
  });

  it('slerp starts at a, ends at b and stays a unit quaternion', () => {
    const a = quat([-10, -35, 0]);
    const b = quat([100, 20, 0]);
    slerp(a, b, 0).forEach((v, i) => expect(v).toBeCloseTo(a[i] ?? NaN));
    slerp(a, b, 1).forEach((v, i) => expect(v).toBeCloseTo(b[i] ?? NaN));
    expect(norm(slerp(a, b, 0.3))).toBeCloseTo(1);
  });

  it('slerp takes the short way when the signs differ', () => {
    const a = quat([0, 0, 0]);
    const b = quat([40, 0, 0]);
    const flipped: Quat = [-b[0], -b[1], -b[2], -b[3]];
    expect(degreesBetween(euler(slerp(a, flipped, 0.5)), [20, 0, 0])).toBeCloseTo(0, 4);
  });
});

describe('turn', () => {
  it('moves the middle of the screen by the dragged angle', () => {
    const start: Rotation = [-10, -35, 0];
    expect(degreesBetween(start, turn(start, 0, 20, 0))).toBeCloseTo(20, 4);
    expect(degreesBetween(start, turn(start, 20, 0, 0))).toBeCloseTo(20, 4);
  });

  it('goes over the pole without a jump', () => {
    // start off the exact pole crossing, where euler angles are degenerate
    let rot: Rotation = [0, -80.3, 0];
    let moved = 0;
    for (let i = 0; i < 40; i++) {
      const next = turn(rot, 0, 1, 0);
      moved += degreesBetween(rot, next);
      rot = next;
    }
    expect(moved).toBeCloseTo(40, 3);
    rot.forEach((angle) => expect(Number.isFinite(angle)).toBe(true));
  });

  it('comes back when the same moves are undone in reverse order', () => {
    // turns about two axes do not commute, so undo them last first
    const start: Rotation = [40, 10, 30];
    const there = turn(turn(start, 7, 0, 0), 0, -5, 0);
    const back = turn(turn(there, 0, 5, 0), -7, 0, 0);
    back.forEach((angle, i) => expect(angle).toBeCloseTo(start[i] ?? NaN, 6));
  });

  it('pans the flat map', () => {
    expect(turn([10, -20, 0], 5, 4, 1)).toEqual([15, -24, 0]);
  });

  it('keeps the longitude inside ±180', () => {
    expect(wrapLon(181)).toBe(-179);
    expect(wrapLon(-181)).toBe(179);
    expect(turn([178, 0, 0], 5, 0, 1)[0]).toBe(-177);
  });
});

describe('camCurve', () => {
  it('starts at 0 and ends at 1', () => {
    expect(camCurve(0)).toBe(0);
    expect(camCurve(1)).toBeCloseTo(1, 12);
  });

  it('is continuous where the ramps meet the cruise', () => {
    for (const edge of [RAMP, 1 - RAMP]) {
      expect(camCurve(edge + 1e-9)).toBeCloseTo(camCurve(edge - 1e-9), 6);
    }
  });

  it('never goes backwards', () => {
    let last = -1;
    for (let i = 0; i <= 1000; i++) {
      const value = camCurve(i / 1000);
      expect(value).toBeGreaterThanOrEqual(last);
      last = value;
    }
  });

  it('starts and stops with no jerk and cruises in the middle', () => {
    const h = 1e-4;
    expect((camCurve(h) - camCurve(0)) / h).toBeLessThan(0.01);
    expect((camCurve(1) - camCurve(1 - h)) / h).toBeLessThan(0.01);
    expect((camCurve(0.5 + h) - camCurve(0.5)) / h).toBeCloseTo(1 / (1 - RAMP), 4);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/geo/camera.test.ts`
Expected: FAIL — cannot resolve `./camera`.

- [ ] **Step 3: Implement**

`src/geo/vector.ts`:

```ts
import { DEG } from '@/lib/math';

export type Vec3 = [number, number, number];

/** The unit vector of a point on the sphere; lon and lat in degrees. */
export const vec = (lon: number, lat: number): Vec3 => [
  Math.cos(lat * DEG) * Math.cos(lon * DEG),
  Math.cos(lat * DEG) * Math.sin(lon * DEG),
  Math.sin(lat * DEG),
];

export const dot = (a: Vec3, b: Vec3): number => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
```

`src/geo/camera.ts`:

```ts
import { clamp, DEG, lerp } from '@/lib/math';

/** d3-geo rotation angles [λ, φ, γ] in degrees. */
export type Rotation = [number, number, number];
export type Quat = [number, number, number, number];

export const quat = ([lam, phi, gam]: Rotation): Quat => {
  const l = (lam * DEG) / 2;
  const p = (phi * DEG) / 2;
  const g = (gam * DEG) / 2;
  const sl = Math.sin(l);
  const cl = Math.cos(l);
  const sp = Math.sin(p);
  const cp = Math.cos(p);
  const sg = Math.sin(g);
  const cg = Math.cos(g);
  return [
    cl * cp * cg + sl * sp * sg,
    cl * cp * sg - sl * sp * cg,
    cl * sp * cg + sl * cp * sg,
    sl * cp * cg - cl * sp * sg,
  ];
};

export const euler = ([a, b, c, d]: Quat): Rotation => [
  Math.atan2(2 * (a * d + b * c), 1 - 2 * (c * c + d * d)) / DEG,
  Math.asin(clamp(2 * (a * c - d * b), -1, 1)) / DEG,
  Math.atan2(2 * (a * b + c * d), 1 - 2 * (b * b + c * c)) / DEG,
];

export const qmul = ([a1, b1, c1, d1]: Quat, [a2, b2, c2, d2]: Quat): Quat => [
  a1 * a2 - b1 * b2 - c1 * c2 - d1 * d2,
  a1 * b2 + b1 * a2 + c1 * d2 - d1 * c2,
  a1 * c2 - b1 * d2 + c1 * a2 + d1 * b2,
  a1 * d2 + b1 * c2 - c1 * b2 + d1 * a2,
];

/** Spherical interpolation along the short way. */
export const slerp = (a: Quat, b: Quat, t: number): Quat => {
  let cos = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
  let to = b;
  if (cos < 0) {
    to = [-b[0], -b[1], -b[2], -b[3]];
    cos = -cos;
  }
  if (cos > 0.9995) {
    const mixed: Quat = [
      lerp(a[0], to[0], t),
      lerp(a[1], to[1], t),
      lerp(a[2], to[2], t),
      lerp(a[3], to[3], t),
    ];
    const length = Math.hypot(...mixed);
    return [mixed[0] / length, mixed[1] / length, mixed[2] / length, mixed[3] / length];
  }
  const theta = Math.acos(cos);
  const sin = Math.sin(theta);
  const wa = Math.sin((1 - t) * theta) / sin;
  const wb = Math.sin(t * theta) / sin;
  return [
    wa * a[0] + wb * to[0],
    wa * a[1] + wb * to[1],
    wa * a[2] + wb * to[2],
    wa * a[3] + wb * to[3],
  ];
};

export const wrapLon = (lon: number): number =>
  lon > 180 ? lon - 360 : lon < -180 ? lon + 360 : lon;

/**
 * A drag of `dx`, `dy` degrees. On the ball (t = 0) it is a small trackball turn about the screen
 * axes, so the globe goes wherever the hand goes, over the poles too. On the flat map (t = 1) it is
 * a plain pan. In between, both in proportion.
 */
export const turn = ([lam, phi, gam]: Rotation, dx: number, dy: number, t: number): Rotation => {
  let rot: Rotation = [lam, phi, gam];
  const ball = 1 - t;
  if (ball > 0) {
    rot = euler(qmul(quat(rot), quat([dx * ball, -dy * ball, 0])));
  }
  if (t > 0) {
    rot = [rot[0] + dx * t, rot[1] - dy * t, rot[2]];
  }
  return [wrapLon(rot[0]), rot[1], rot[2]];
};

/**
 * The camera's share of a flight, for the plane's share `e` (0..1, constant speed). The camera
 * eases in over the first 14 % and out over the last 14 % around the plane's speed: it trails the
 * plane a little on take-off, leads it a little before landing, and lands with it.
 */
export const RAMP = 0.14;
const CRUISE = 1 / (1 - RAMP);

export const camCurve = (e: number): number => {
  // ∫ smoothstep, scaled so the ramps meet the cruise speed
  const ramp = (x: number) => CRUISE * RAMP * (x * x * x - (x * x * x * x) / 2);
  if (e < RAMP) return ramp(e / RAMP);
  if (e > 1 - RAMP) return 1 - ramp((1 - e) / RAMP);
  return CRUISE * (e - RAMP / 2);
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/geo/camera.test.ts`
Expected: PASS. "moves the middle of the screen by the dragged angle" pins the spec's "turns like a trackball about the screen axes": if it fails (for example 16.4° instead of 20°), the turn happens about the globe's own axes. Report that with the numbers; do not loosen the test.

- [ ] **Step 5: Commit**

```bash
git add src/geo/vector.ts src/geo/camera.ts src/geo/camera.test.ts
git commit -m "feat(geo): add the trackball camera and the flight camera curve"
```

---

### Task 6: The blend projection, the zoom notch and the unroll

**Files:**
- Create: `src/geo/projection.ts`
- Test: `src/geo/projection.test.ts`

**Interfaces:**
- Consumes: `clamp`, `DEG` (`src/lib/math.ts`); `smoother` (`src/lib/easing.ts`); `Vec3`, `dot` (`src/geo/vector.ts`).
- Produces:
  - `raw(t: number, lambda: number, phi: number): [number, number]` (radians in, projection units out)
  - `clipCos(t: number): number`, `type ClipKind = 'circle' | 'circle+antimeridian' | 'antimeridian'`, `clipKind(t: number): ClipKind`, `clipFor(t: number): (stream: GeoStream) => GeoStream`
  - `faces(point: Vec3, centre: Vec3, t: number, margin: number): boolean`
  - `createBlendProjection(): { projection: GeoProjection; blend(t: number): void }`
  - `NOTCH`, `WHEEL_ZOOM = 0.0012`, `UNROLL_MS = 1100`, `Z_MIN = 0.5`, `Z_MAX = 7`
  - `interface Viewport { width: number; height: number; cx: number; cy: number; r0: number }`, `zFlat(viewport: Viewport): number`
  - `interface Unroll { flat: boolean; from: number; to: number; at: number }`, `ROLLED: Unroll`, `stepUnroll(unroll: Unroll, t: number, zTarget: number, zf: number, now: number): Unroll`, `unrollT(unroll: Unroll, now: number): number`
  - `flatLatLimit(cy: number, height: number, r: number): number`

- [ ] **Step 1: Write the failing test**

`src/geo/projection.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { DEG } from '@/lib/math';
import {
  clipCos,
  clipKind,
  createBlendProjection,
  faces,
  flatLatLimit,
  NOTCH,
  raw,
  ROLLED,
  stepUnroll,
  UNROLL_MS,
  unrollT,
  zFlat,
} from './projection';
import type { Viewport } from './projection';
import { vec } from './vector';

describe('clip choice', () => {
  it('is a circle on the ball, circle and seam while unrolling, seam alone from t = .5', () => {
    expect(clipKind(0)).toBe('circle');
    expect(clipKind(0.25)).toBe('circle+antimeridian');
    expect(clipKind(0.49)).toBe('circle+antimeridian');
    expect(clipKind(0.5)).toBe('antimeridian');
    expect(clipKind(1)).toBe('antimeridian');
  });

  it('opens the circle as the ball unrolls', () => {
    expect(clipCos(0)).toBe(0);
    expect(clipCos(0.25)).toBeCloseTo(-1 / 3);
    expect(clipCos(0.5)).toBe(-1);
  });
});

describe('unroll without folds', () => {
  const steps = 400;

  it('never folds inside the clip', () => {
    for (const t of [0.1, 0.25, 0.4, 0.49]) {
      const limit = Math.acos(clipCos(t)) - 1e-3;
      let lastX = -Infinity;
      let lastY = -Infinity;
      for (let i = 0; i <= steps; i++) {
        const a = (limit * i) / steps;
        const [x] = raw(t, a, 0);
        const [, y] = raw(t, 0, Math.min(a, Math.PI / 2));
        expect(x).toBeGreaterThan(lastX);
        expect(y).toBeGreaterThanOrEqual(lastY);
        lastX = x;
        lastY = y;
      }
    }
  });

  it('would fold just past the clip, so the clip is tight', () => {
    for (const t of [0.1, 0.25, 0.4]) {
      const limit = Math.acos(clipCos(t));
      expect(raw(t, limit + 0.05, 0)[0]).toBeLessThan(raw(t, limit, 0)[0]);
    }
  });

  it('never folds from t = .5 on', () => {
    for (const t of [0.5, 0.75, 1]) {
      let lastX = -Infinity;
      for (let i = -steps; i <= steps; i++) {
        const [x] = raw(t, (Math.PI * i) / (steps + 1), 0);
        expect(x).toBeGreaterThan(lastX);
        lastX = x;
      }
    }
  });
});

describe('faces', () => {
  const centre = vec(0, 0);

  it('hides what is behind the ball', () => {
    expect(faces(vec(10, 10), centre, 0, 0.02)).toBe(true);
    expect(faces(vec(120, 0), centre, 0, 0.02)).toBe(false);
    expect(faces(vec(89.5, 0), centre, 0, 0.02)).toBe(false);
  });

  it('shows everything on the flat map, the far edges too', () => {
    expect(faces(vec(179, 0), centre, 1, 0.03)).toBe(true);
    expect(faces(vec(-179, 5), centre, 0.5, 0.03)).toBe(true);
  });
});

describe('createBlendProjection', () => {
  it('follows the blend', () => {
    const { projection, blend } = createBlendProjection();
    projection.scale(1).translate([0, 0]).rotate([0, 0, 0]);
    blend(0);
    expect(projection([90, 0])?.[0]).toBeCloseTo(1);
    blend(1);
    expect(projection([90, 0])?.[0]).toBeCloseTo(Math.PI / 2);
  });
});

describe('zFlat', () => {
  it('sits three notches before the ball would touch the screen edge', () => {
    const viewport: Viewport = { width: 2000, height: 2000, cx: 1000, cy: 1000, r0: 300 };
    expect(zFlat(viewport) * viewport.r0 * NOTCH ** 3).toBeCloseTo(1000);
  });

  it('is never at the resting size', () => {
    const laptop: Viewport = { width: 1440, height: 900, cx: 864, cy: 450, r0: 360 };
    expect(zFlat(laptop)).toBeGreaterThanOrEqual(1.05);
  });

  it('leaves no gap around the flat map on a 390 × 844 phone', () => {
    const phone: Viewport = { width: 390, height: 844, cx: 195, cy: 844 * 0.58, r0: 156 };
    const r = zFlat(phone) * phone.r0;
    expect(Math.PI * r).toBeGreaterThanOrEqual(Math.max(phone.cx, phone.width - phone.cx));
    expect((Math.PI / 2) * r).toBeGreaterThanOrEqual(Math.max(phone.cy, phone.height - phone.cy));
  });
});

describe('unroll', () => {
  const zf = 1.4;

  it('rests as a ball', () => {
    expect(unrollT(ROLLED, 0)).toBe(0);
  });

  it('unrolls and rolls back at the very same notch', () => {
    const at = stepUnroll(ROLLED, 0, zf, zf, 1000);
    expect(at.flat).toBe(true);
    expect(stepUnroll(ROLLED, 0, zf - 1e-9, zf, 1000).flat).toBe(false);
    expect(stepUnroll(at, 1, zf, zf, 5000).flat).toBe(true);
    expect(stepUnroll(at, 1, zf - 1e-9, zf, 5000).flat).toBe(false);
  });

  it('takes 1.1 s to unroll', () => {
    const at = stepUnroll(ROLLED, 0, zf, zf, 1000);
    expect(unrollT(at, 1000)).toBe(0);
    expect(unrollT(at, 1000 + UNROLL_MS / 2)).toBeCloseTo(0.5);
    expect(unrollT(at, 1000 + UNROLL_MS)).toBe(1);
  });

  it('turns around from where it is when reversed halfway', () => {
    const going = stepUnroll(ROLLED, 0, zf, zf, 0);
    const t = unrollT(going, 300);
    const back = stepUnroll(going, t, zf - 0.1, zf, 300);
    expect(unrollT(back, 300)).toBeCloseTo(t);
    expect(unrollT(back, 300 + UNROLL_MS)).toBe(0);
  });

  it('does not flip back and forth while the zoom target rests on the notch', () => {
    let unroll = stepUnroll(ROLLED, 0, zf, zf, 0);
    for (let now = 16; now < 3000; now += 16) {
      const next = stepUnroll(unroll, unrollT(unroll, now), zf, zf, now);
      expect(next).toBe(unroll);
      unroll = next;
    }
  });
});

describe('flatLatLimit', () => {
  it('keeps the world edge off screen', () => {
    expect(flatLatLimit(450, 900, 1000)).toBeCloseTo(90 - 450 / 1000 / DEG);
    expect(flatLatLimit(450, 900, 100)).toBe(0);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/geo/projection.test.ts`
Expected: FAIL — cannot resolve `./projection`.

- [ ] **Step 3: Implement**

`src/geo/projection.ts`:

```ts
import { geoClipAntimeridian, geoClipCircle, geoProjectionMutator } from 'd3-geo';
import type { GeoProjection, GeoStream } from 'd3-geo';
import { smoother } from '@/lib/easing';
import { clamp, DEG } from '@/lib/math';
import { dot } from './vector';
import type { Vec3 } from './vector';

/**
 * Zoomed in, the ball (t = 0, orthographic) unrolls into a flat map (t = 1, equirectangular):
 * x = (1 − t)·cos φ sin λ + t·λ, y = (1 − t)·sin φ + t·φ. λ and φ in radians.
 */
export const raw = (t: number, lambda: number, phi: number): [number, number] => [
  (1 - t) * Math.cos(phi) * Math.sin(lambda) + t * lambda,
  (1 - t) * Math.sin(phi) + t * phi,
];

/**
 * The map never folds over itself while cos c > −t / (1 − t), c being the distance from the
 * centre, so the clip circle grows with t; from t = .5 the whole sphere fits.
 */
export const clipCos = (t: number): number => (t <= 0 ? 0 : t >= 0.5 ? -1 : -t / (1 - t));

export type ClipKind = 'circle' | 'circle+antimeridian' | 'antimeridian';

export const clipKind = (t: number): ClipKind =>
  t <= 0 ? 'circle' : t >= 0.5 ? 'antimeridian' : 'circle+antimeridian';

type Clip = (stream: GeoStream) => GeoStream;

export const clipFor = (t: number): Clip => {
  switch (clipKind(t)) {
    case 'circle':
      return geoClipCircle(Math.PI / 2);
    case 'antimeridian':
      return geoClipAntimeridian;
    case 'circle+antimeridian': {
      const circle = geoClipCircle(Math.acos(clipCos(t)));
      return (sink) => circle(geoClipAntimeridian(sink));
    }
  }
};

/**
 * Whether a point shows: on the ball, `margin` inside the clip edge; from t = .5, always (the flat
 * map holds the whole sphere, the far side at its left and right edges).
 */
export const faces = (point: Vec3, centre: Vec3, t: number, margin: number): boolean =>
  clipCos(t) <= -1 || dot(point, centre) >= clipCos(t) + margin;

/** One d3 projection whose raw function follows the unroll blend. */
export const createBlendProjection = (): {
  projection: GeoProjection;
  blend: (t: number) => void;
} => {
  // @types/d3-geo types the mutator without arguments; d3 passes them to the factory.
  const mutate = geoProjectionMutator(
    (t: number) => (lambda: number, phi: number) => raw(t, lambda, phi),
  ) as unknown as (t: number) => GeoProjection;
  const projection = mutate(0).precision(0.8);
  return {
    projection,
    blend: (t) => {
      mutate(t);
    },
  };
};

/** A wheel notch is 100 units of deltaY. */
export const WHEEL_ZOOM = 0.0012;
/** How much one wheel notch zooms. */
export const NOTCH = Math.exp(100 * WHEEL_ZOOM);
export const UNROLL_MS = 1100;
/** Farthest out: half the resting size. */
export const Z_MIN = 0.5;
export const Z_MAX = 7;

export interface Viewport {
  width: number;
  height: number;
  /** Where the globe's centre sits on screen. */
  cx: number;
  cy: number;
  /** Resting radius of the ball. */
  r0: number;
}

/**
 * The zoom where the ball unrolls: three notches before its edge would touch the edge of the
 * screen, never at the resting size, and never so small that the flat map leaves a gap.
 */
export const zFlat = ({ width, height, cx, cy, r0 }: Viewport): number => {
  const touch = Math.min(cx, width - cx, cy, height - cy);
  const fill =
    (Math.max(2 * Math.max(cy, height - cy), Math.max(cx, width - cx)) / Math.PI) * 1.02;
  return Math.max(touch / NOTCH ** 3, r0 * 1.05, fill) / r0;
};

export interface Unroll {
  flat: boolean;
  from: number;
  to: number;
  /** World time the current animation started. */
  at: number;
}

export const ROLLED: Unroll = { flat: false, from: 0, to: 0, at: -Infinity };

/**
 * Decides on the wheel's own target, not on the eased zoom, so zooming in and out switch at the
 * very same notch. A switch mid-animation turns around from the current blend `t`.
 */
export const stepUnroll = (
  unroll: Unroll,
  t: number,
  zTarget: number,
  zf: number,
  now: number,
): Unroll => {
  if (!unroll.flat && zTarget >= zf) return { flat: true, from: t, to: 1, at: now };
  if (unroll.flat && zTarget < zf) return { flat: false, from: t, to: 0, at: now };
  return unroll;
};

export const unrollT = ({ from, to, at }: Unroll, now: number): number =>
  from + (to - from) * smoother(clamp((now - at) / UNROLL_MS, 0, 1));

/** On the flat map the centre may not go so far north or south that the world's edge shows. */
export const flatLatLimit = (cy: number, height: number, r: number): number =>
  Math.max(0, 90 - Math.max(cy, height - cy) / r / DEG);
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/geo/projection.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/geo/projection.ts src/geo/projection.test.ts
git commit -m "feat(geo): add the unrolling projection and the zoom notch"
```

---

### Task 7: The world map and the faint city lights

**Files:**
- Create: `src/geo/world.ts`, `src/render/lights.ts`
- Test: `src/geo/world.test.ts`, `src/render/lights.test.ts`

**Interfaces:**
- Consumes: `seeded` (`src/lib/random.ts`); `DEG` (`src/lib/math.ts`); `Vec3`, `vec` (`src/geo/vector.ts`).
- Produces:
  - `interface EarthGeo { land: MultiPolygon; borders: MultiLineString }` (GeoJSON types)
  - `type WorldTopology = Topology<{ countries: GeometryCollection }>`
  - `earthFromTopology(topology: WorldTopology): EarthGeo`
  - `interface Light { ll: [number, number]; v: Vec3; band: number }`, `LIGHT_COUNT = 1500`, `buildLights(land: MultiPolygon, count?: number): Light[]`

- [ ] **Step 1: Write the failing tests**

`src/geo/world.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { geoContains } from 'd3-geo';
import { describe, expect, it } from 'vitest';
import { earthFromTopology } from './world';
import type { WorldTopology } from './world';

const file = fileURLToPath(new URL('../../public/demo/countries-110m.json', import.meta.url));
const earth = earthFromTopology(JSON.parse(readFileSync(file, 'utf8')) as WorldTopology);

describe('earthFromTopology', () => {
  it('merges the countries into land', () => {
    expect(earth.land.type).toBe('MultiPolygon');
    expect(geoContains(earth.land, [30.52, 50.45])).toBe(true);
    expect(geoContains(earth.land, [-30, 30])).toBe(false);
  });

  it('draws only the borders between countries', () => {
    expect(earth.borders.type).toBe('MultiLineString');
    expect(earth.borders.coordinates.length).toBeGreaterThan(100);
  });
});
```

`src/render/lights.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { geoContains } from 'd3-geo';
import { describe, expect, it } from 'vitest';
import { earthFromTopology } from '@/geo/world';
import type { WorldTopology } from '@/geo/world';
import { buildLights } from './lights';

const file = fileURLToPath(new URL('../../public/demo/countries-110m.json', import.meta.url));
const { land } = earthFromTopology(JSON.parse(readFileSync(file, 'utf8')) as WorldTopology);

describe('buildLights', () => {
  const lights = buildLights(land, 200);

  it('puts the asked number of lights on land', () => {
    expect(lights).toHaveLength(200);
    for (const light of lights) expect(geoContains(land, light.ll)).toBe(true);
  });

  it('is the same on every visit', () => {
    expect(buildLights(land, 200)).toEqual(lights);
  });

  it('keeps away from the poles and uses three brightness bands', () => {
    for (const light of lights) {
      expect(Math.abs(light.ll[1])).toBeLessThan(58.3);
      expect([0, 1, 2]).toContain(light.band);
    }
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/geo/world.test.ts src/render/lights.test.ts`
Expected: FAIL — cannot resolve `./world` and `./lights`.

- [ ] **Step 3: Implement**

`src/geo/world.ts`:

```ts
import type { MultiLineString, MultiPolygon } from 'geojson';
import { merge, mesh } from 'topojson-client';
import type {
  GeometryCollection,
  MultiPolygon as TopoMultiPolygon,
  Polygon as TopoPolygon,
  Topology,
} from 'topojson-specification';

export interface EarthGeo {
  land: MultiPolygon;
  borders: MultiLineString;
}

/** public/demo/countries-110m.json (world-atlas). */
export type WorldTopology = Topology<{ countries: GeometryCollection }>;

const isArea = (geometry: { type: string | null }): geometry is TopoPolygon | TopoMultiPolygon =>
  geometry.type === 'Polygon' || geometry.type === 'MultiPolygon';

export const earthFromTopology = (topology: WorldTopology): EarthGeo => {
  const countries = topology.objects.countries;
  return {
    land: merge(topology, countries.geometries.filter(isArea)),
    borders: mesh(topology, countries, (a, b) => a !== b),
  };
};
```

`src/render/lights.ts`:

```ts
import { geoContains } from 'd3-geo';
import type { MultiPolygon } from 'geojson';
import { vec } from '@/geo/vector';
import type { Vec3 } from '@/geo/vector';
import { DEG } from '@/lib/math';
import { seeded } from '@/lib/random';

export interface Light {
  ll: [number, number];
  v: Vec3;
  /** 0, 1 or 2: faint, medium, bright. */
  band: number;
}

export const LIGHT_COUNT = 1500;

/** Faint city lights: random points on land, the same on every visit, clear of the poles. */
export const buildLights = (land: MultiPolygon, count = LIGHT_COUNT): Light[] => {
  const random = seeded(11);
  const lights: Light[] = [];
  for (let tries = 0; lights.length < count && tries < 30000; tries++) {
    const lon = random() * 360 - 180;
    const lat = Math.asin(random() * 1.7 - 0.85) / DEG;
    if (geoContains(land, [lon, lat])) {
      lights.push({ ll: [lon, lat], v: vec(lon, lat), band: Math.floor(random() * 3) });
    }
  }
  return lights;
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/geo/world.test.ts src/render/lights.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/geo/world.ts src/geo/world.test.ts src/render/lights.ts src/render/lights.test.ts
git commit -m "feat(render): add the land, the borders and the faint city lights"
```

---

### Task 8: Place states and their looks

**Files:**
- Create: `src/render/places.ts`
- Test: `src/render/places.test.ts`

**Interfaces:**
- Consumes: `ease` (`src/lib/easing.ts`).
- Produces:
  - `type PlaceState = 'plain' | 'grey' | 'blue' | 'yellow' | 'current'`
  - `interface PlaceLook { blue: number; warm: number; glow: number; size: number }`, `PLACE_LOOK: Readonly<Record<PlaceState, PlaceLook>>`
  - `interface PlaceFacts { focused: boolean; reached: boolean; inRange: boolean; rangeActive: boolean }`, `placeState(facts: PlaceFacts): PlaceState`
  - `LOOK_EASE = 0.9`, `HOVER_GLOW = 0.25`, `stepLook(look: PlaceLook, state: PlaceState, f: number, hovered: boolean): PlaceLook`

- [ ] **Step 1: Write the failing test**

`src/render/places.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { HOVER_GLOW, PLACE_LOOK, placeState, stepLook } from './places';
import type { PlaceFacts } from './places';

const facts = (patch: Partial<PlaceFacts>): PlaceFacts => ({
  focused: false,
  reached: false,
  inRange: false,
  rangeActive: false,
  ...patch,
});

describe('placeState', () => {
  it('is plain when nothing is active on the timeline', () => {
    expect(placeState(facts({}))).toBe('plain');
  });

  it('is grey outside a picked range', () => {
    expect(placeState(facts({ rangeActive: true }))).toBe('grey');
  });

  it('is blue inside the range until reached', () => {
    expect(placeState(facts({ rangeActive: true, inRange: true }))).toBe('blue');
  });

  it('is yellow once reached', () => {
    expect(placeState(facts({ rangeActive: true, inRange: true, reached: true }))).toBe('yellow');
    expect(placeState(facts({ reached: true }))).toBe('yellow');
  });

  it('is current when in focus, whatever else holds', () => {
    expect(
      placeState({ focused: true, reached: true, inRange: true, rangeActive: true }),
    ).toBe('current');
  });
});

describe('PLACE_LOOK', () => {
  it('makes the current place the brightest and 1.45× bigger', () => {
    expect(PLACE_LOOK.current.size).toBe(1.45);
    for (const look of Object.values(PLACE_LOOK)) {
      expect(PLACE_LOOK.current.glow).toBeGreaterThanOrEqual(look.glow);
    }
  });

  it('gives a plain place no glow', () => {
    expect(PLACE_LOOK.plain.glow).toBe(0);
  });
});

describe('stepLook', () => {
  it('fades most of the way in about 0.4 s', () => {
    let look = PLACE_LOOK.plain;
    for (let frame = 0; frame < 24; frame++) look = stepLook(look, 'blue', 1, false);
    expect(look.blue).toBeGreaterThan(0.9);
    expect(look.blue).toBeLessThan(1);
  });

  it('adds a little glow under the cursor, never past full', () => {
    let look = PLACE_LOOK.plain;
    for (let frame = 0; frame < 200; frame++) look = stepLook(look, 'plain', 1, true);
    expect(look.glow).toBeCloseTo(HOVER_GLOW);
    let current = PLACE_LOOK.current;
    for (let frame = 0; frame < 200; frame++) current = stepLook(current, 'current', 1, true);
    expect(current.glow).toBeCloseTo(1);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/render/places.test.ts`
Expected: FAIL — cannot resolve `./places`.

- [ ] **Step 3: Implement**

`src/render/places.ts`:

```ts
import { ease } from '@/lib/easing';

/**
 *   plain    nothing is active on the timeline: a small pale dot
 *   grey     a range is picked and the place is outside it
 *   blue     inside the picked range, not reached yet
 *   yellow   reached: on the timeline up to the trip in focus
 *   current  the place in focus after the plane lands: brightest and bigger
 */
export type PlaceState = 'plain' | 'grey' | 'blue' | 'yellow' | 'current';

/** How a light looks: blue tint, warmth of the dot, glow (each 0..1), and a size factor. */
export interface PlaceLook {
  blue: number;
  warm: number;
  glow: number;
  size: number;
}

export const PLACE_LOOK: Readonly<Record<PlaceState, PlaceLook>> = {
  plain: { blue: 0, warm: 0.55, glow: 0, size: 0.7 },
  grey: { blue: 0, warm: 0, glow: 0, size: 0.6 },
  blue: { blue: 1, warm: 1, glow: 0.5, size: 0.9 },
  yellow: { blue: 0, warm: 1, glow: 0.72, size: 1 },
  current: { blue: 0, warm: 1, glow: 1, size: 1.45 },
};

export interface PlaceFacts {
  focused: boolean;
  reached: boolean;
  inRange: boolean;
  rangeActive: boolean;
}

export const placeState = ({ focused, reached, inRange, rangeActive }: PlaceFacts): PlaceState =>
  focused ? 'current' : reached ? 'yellow' : inRange ? 'blue' : rangeActive ? 'grey' : 'plain';

/** Each 60 Hz frame keeps this share of the gap: the change settles in about 0.4 s. */
export const LOOK_EASE = 0.9;
/** Extra glow under the cursor. */
export const HOVER_GLOW = 0.25;

export const stepLook = (
  look: PlaceLook,
  state: PlaceState,
  f: number,
  hovered: boolean,
): PlaceLook => {
  const target = PLACE_LOOK[state];
  return {
    blue: ease(look.blue, target.blue, f, LOOK_EASE),
    warm: ease(look.warm, target.warm, f, LOOK_EASE),
    glow: ease(look.glow, Math.min(1, target.glow + (hovered ? HOVER_GLOW : 0)), f, LOOK_EASE),
    size: ease(look.size, target.size, f, LOOK_EASE),
  };
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/render/places.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/render/places.ts src/render/places.test.ts
git commit -m "feat(render): add place states and their fading looks"
```

---

### Task 9: The sky

**Files:**
- Create: `src/render/sky.ts`
- Test: `src/render/sky.test.ts`

**Interfaces:**
- Consumes: `DEG` (`src/lib/math.ts`); `seeded` (`src/lib/random.ts`).
- Produces:
  - `STAR_PAD = 30`
  - `type SkyEvent`, `interface Sky { width: number; height: number; twinklers: Twinkler[]; events: SkyEvent[]; nextEventIn: number }`
  - `createSky(width: number, height: number, mobile: boolean): Sky`
  - `stepSky(sky: Sky, dt: number, random?: () => number): void`
  - `drawStarField(ctx: CanvasRenderingContext2D, width: number, height: number): void`
  - `starDrift(now: number): [number, number]`
  - `drawSky(ctx: CanvasRenderingContext2D, sky: Sky, now: number): void`

- [ ] **Step 1: Write the failing test**

`src/render/sky.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createSky, starDrift, stepSky } from './sky';

/** A random source that returns the given values in turn, then 0.5. */
const queue =
  (...values: number[]) =>
  () =>
    values.shift() ?? 0.5;

describe('createSky', () => {
  it('twinkles about 30 stars, fewer on a phone', () => {
    expect(createSky(1440, 900, false).twinklers).toHaveLength(34);
    expect(createSky(390, 844, true).twinklers).toHaveLength(18);
  });

  it('is the same on every visit', () => {
    expect(createSky(800, 600, false)).toEqual(createSky(800, 600, false));
  });
});

describe('stepSky', () => {
  it('waits before the first event', () => {
    const sky = createSky(800, 600, false);
    stepSky(sky, 4900, queue());
    expect(sky.events).toHaveLength(0);
  });

  it('sends a slow meteor and schedules the next event 7–20 s later', () => {
    const sky = createSky(800, 600, false);
    // next interval, then kind: below .6 is a meteor
    stepSky(sky, 5000, queue(0, 0.1));
    expect(sky.events).toHaveLength(1);
    const [meteor] = sky.events;
    expect(meteor?.kind).toBe('meteor');
    expect(meteor?.life).toBeGreaterThanOrEqual(2300);
    expect(meteor?.life).toBeLessThanOrEqual(3200);
    expect(sky.nextEventIn).toBe(7000);
  });

  it('sends a satellite that takes 16–24 s', () => {
    const sky = createSky(800, 600, false);
    stepSky(sky, 5000, queue(1, 0.9));
    const [satellite] = sky.events;
    expect(satellite?.kind).toBe('satellite');
    expect(satellite?.life).toBeGreaterThanOrEqual(16000);
    expect(satellite?.life).toBeLessThanOrEqual(24000);
    expect(sky.nextEventIn).toBe(20000);
  });

  it('lets an event go when its life is over', () => {
    const sky = createSky(800, 600, false);
    stepSky(sky, 5000, queue(1, 0.1));
    const life = sky.events[0]?.life ?? 0;
    stepSky(sky, life - 1, queue());
    expect(sky.events).toHaveLength(1);
    stepSky(sky, 2, queue());
    expect(sky.events).toHaveLength(0);
  });

  it('stands still while the world is paused', () => {
    const sky = createSky(800, 600, false);
    const before = sky.nextEventIn;
    stepSky(sky, 0, queue());
    expect(sky.nextEventIn).toBe(before);
  });
});

describe('starDrift', () => {
  it('drifts very slowly and only a few pixels', () => {
    const [x0, y0] = starDrift(0);
    const [x1, y1] = starDrift(1000);
    expect(Math.hypot(x1 - x0, y1 - y0)).toBeLessThan(3);
    for (let now = 0; now < 400000; now += 5000) {
      const [x, y] = starDrift(now);
      expect(Math.abs(x)).toBeLessThanOrEqual(18);
      expect(Math.abs(y)).toBeLessThanOrEqual(12);
    }
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/render/sky.test.ts`
Expected: FAIL — cannot resolve `./sky`.

- [ ] **Step 3: Implement**

`src/render/sky.ts`:

```ts
import { DEG } from '@/lib/math';
import { seeded } from '@/lib/random';

/** The star field is a little larger than the screen, so it can drift. */
export const STAR_PAD = 30;

interface Twinkler {
  x: number;
  y: number;
  size: number;
  period: number;
  phase: number;
  tint: boolean;
}

interface Meteor {
  kind: 'meteor';
  x: number;
  y: number;
  dx: number;
  dy: number;
  speed: number;
  age: number;
  life: number;
}

interface Satellite {
  kind: 'satellite';
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  age: number;
  life: number;
}

export type SkyEvent = Meteor | Satellite;

/**
 * The sky is alive, barely: the stars drift, a few twinkle, now and then a star falls or a
 * satellite crosses. It runs on the world clock, so it waits while the world is paused.
 */
export interface Sky {
  width: number;
  height: number;
  twinklers: Twinkler[];
  events: SkyEvent[];
  nextEventIn: number;
}

export const createSky = (width: number, height: number, mobile: boolean): Sky => {
  const random = seeded(29);
  const twinklers = Array.from({ length: mobile ? 18 : 34 }, () => ({
    x: random() * width,
    y: random() * height,
    size: 0.6 + random(),
    period: 900 + random() * 2600,
    phase: random() * 7,
    tint: random() < 0.3,
  }));
  return { width, height, twinklers, events: [], nextEventIn: 5000 };
};

const meteor = ({ width, height }: Sky, random: () => number): Meteor => {
  const direction = random() < 0.5 ? -1 : 1;
  const angle = (20 + random() * 25) * DEG;
  return {
    kind: 'meteor',
    x: width * (0.15 + random() * 0.7),
    y: height * random() * 0.35,
    dx: Math.cos(angle) * direction,
    dy: Math.sin(angle),
    speed: 0.2 + random() * 0.1,
    age: 0,
    life: 2300 + random() * 900,
  };
};

const satellite = ({ width, height }: Sky, random: () => number): Satellite => {
  const fromLeft = random() < 0.5;
  const y0 = height * (0.08 + random() * 0.5);
  return {
    kind: 'satellite',
    x0: fromLeft ? -10 : width + 10,
    y0,
    x1: fromLeft ? width + 10 : -10,
    y1: y0 + (random() - 0.5) * height * 0.4,
    age: 0,
    life: 16000 + random() * 8000,
  };
};

/** Every 7–20 s either a slow meteor (about 2.5 s) or a satellite (16–24 s) crosses. */
export const stepSky = (sky: Sky, dt: number, random: () => number = Math.random): void => {
  // age the events first, so a new one starts at age 0 however long the step
  for (const event of sky.events) {
    event.age += dt;
  }
  sky.events = sky.events.filter((event) => event.age < event.life);

  sky.nextEventIn -= dt;
  if (sky.nextEventIn <= 0) {
    sky.nextEventIn = 7000 + random() * 13000;
    sky.events.push(random() < 0.6 ? meteor(sky, random) : satellite(sky, random));
  }
};

/** The still stars, drawn once per resize on a canvas `STAR_PAD` larger on every side. */
export const drawStarField = (ctx: CanvasRenderingContext2D, width: number, height: number): void => {
  const random = seeded(3);
  ctx.fillStyle = '#04060d';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = '#fff';
  for (let i = 0; i < 560; i++) {
    ctx.globalAlpha = 0.15 + random() * 0.75;
    ctx.beginPath();
    ctx.arc(random() * width, random() * height, random() * 1.1, 0, 2 * Math.PI);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
};

/** Offset of the star field in px: a very slow drift. */
export const starDrift = (now: number): [number, number] => [
  Math.sin(now / 47000) * 18,
  Math.cos(now / 61000) * 12,
];

export const drawSky = (ctx: CanvasRenderingContext2D, sky: Sky, now: number): void => {
  ctx.clearRect(0, 0, sky.width, sky.height);

  for (const star of sky.twinklers) {
    const alpha = 0.08 + 0.7 * ((1 + Math.sin(now / star.period + star.phase)) / 2) ** 4;
    ctx.fillStyle = star.tint ? `rgba(190,215,255,${alpha})` : `rgba(255,255,255,${alpha})`;
    ctx.beginPath();
    ctx.arc(star.x, star.y, star.size, 0, 2 * Math.PI);
    ctx.fill();
    if (alpha > 0.5) {
      // a glint when it is at its brightest
      const arm = star.size * 4;
      ctx.strokeStyle = `rgba(255,255,255,${(alpha - 0.5) * 0.7})`;
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(star.x - arm, star.y);
      ctx.lineTo(star.x + arm, star.y);
      ctx.moveTo(star.x, star.y - arm);
      ctx.lineTo(star.x, star.y + arm);
      ctx.stroke();
    }
  }

  for (const event of sky.events) {
    const k = event.age / event.life;
    if (event.kind === 'meteor') {
      const distance = event.age * event.speed;
      const hx = event.x + event.dx * distance;
      const hy = event.y + event.dy * distance;
      const length = 90 + 60 * Math.sin(Math.PI * k);
      const alpha = Math.sin(Math.PI * k) * 0.85;
      const tail = ctx.createLinearGradient(hx, hy, hx - event.dx * length, hy - event.dy * length);
      tail.addColorStop(0, `rgba(255,255,255,${alpha})`);
      tail.addColorStop(1, 'rgba(180,210,255,0)');
      ctx.strokeStyle = tail;
      ctx.lineWidth = 1.2;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(hx, hy);
      ctx.lineTo(hx - event.dx * length, hy - event.dy * length);
      ctx.stroke();
    } else {
      const x = event.x0 + (event.x1 - event.x0) * k;
      const y = event.y0 + (event.y1 - event.y0) * k;
      const flash = Math.sin(event.age / 260) > 0.92 ? 0.25 : 0;
      const alpha = Math.min(1, k * 8, (1 - k) * 8) * (0.45 + flash);
      ctx.fillStyle = `rgba(230,238,255,${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, 0.9, 0, 2 * Math.PI);
      ctx.fill();
    }
  }
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/render/sky.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/render/sky.ts src/render/sky.test.ts
git commit -m "feat(render): add the drifting sky with meteors and satellites"
```

---

### Task 10: The house and its smoke

**Files:**
- Create: `src/render/house.ts`
- Test: `src/render/house.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ROOF = 'roof'`, `GLASS = 'window'`, `interface HousePart { d: string; fill: string }`
  - `interface HouseGeometry { ox; oy; parts: HousePart[]; roof: [Point, Point]; chimney: Point; window: Point }`, `HOUSE: HouseGeometry`, `HOUSE_SCALE = 0.82`
  - `drawHouse(ctx: CanvasRenderingContext2D, x: number, y: number, k: number, lit: number): void`
  - `interface Smoke { puffs: Puff[]; clock: number }`, `createSmoke(): Smoke`, `stepSmoke(smoke: Smoke, dt: number, lit: number, random?: () => number): void`, `drawSmoke(ctx: CanvasRenderingContext2D, smoke: Smoke, x: number, y: number, k: number): void`

Plan 3 builds the menu's SVG house from `HOUSE.parts`; plan 2 lights the house and starts the smoke.

- [ ] **Step 1: Write the failing test**

`src/render/house.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { createSmoke, GLASS, HOUSE, ROOF, stepSmoke } from './house';

/** Runs the smoke for `ms` in 60 Hz frames. */
const run = (smoke: ReturnType<typeof createSmoke>, ms: number, lit: number) => {
  for (let t = 0; t < ms; t += 16.7) stepSmoke(smoke, 16.7, lit, () => 0.5);
};

describe('HOUSE', () => {
  it('has walls, a roof, a chimney and a 2×2 window', () => {
    expect(HOUSE.parts).toHaveLength(14);
    expect(HOUSE.parts.filter((part) => part.fill === GLASS)).toHaveLength(4);
    expect(HOUSE.parts.filter((part) => part.fill === ROOF)).toHaveLength(1);
  });

  it('draws closed paths only', () => {
    for (const part of HOUSE.parts) expect(part.d).toMatch(/^M.*Z$/);
  });

  it('puts the chimney above the foot of the house', () => {
    expect(HOUSE.chimney[1]).toBeLessThan(HOUSE.oy);
  });
});

describe('smoke', () => {
  it('rises only while someone is home', () => {
    const smoke = createSmoke();
    run(smoke, 2000, 0.3);
    expect(smoke.puffs).toHaveLength(0);
    run(smoke, 1000, 1);
    expect(smoke.puffs.length).toBeGreaterThan(4);
  });

  it('stops when the light goes out, and the last puffs fade away', () => {
    const smoke = createSmoke();
    run(smoke, 1000, 1);
    run(smoke, 3700, 0);
    expect(smoke.puffs).toHaveLength(0);
  });

  it('waits while the world is paused', () => {
    const smoke = createSmoke();
    run(smoke, 500, 1);
    const ages = smoke.puffs.map((puff) => puff.age);
    stepSmoke(smoke, 0, 1, () => 0.5);
    expect(smoke.puffs.map((puff) => puff.age)).toEqual(ages);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/render/house.test.ts`
Expected: FAIL — cannot resolve `./house`.

- [ ] **Step 3: Implement**

`src/render/house.ts` (no `Path2D` at module level: the tests run in node):

```ts
type Point = [number, number];
type Point3 = [number, number, number];

/** Fill names the painter resolves: the roof gradient and the window glass. */
export const ROOF = 'roof';
export const GLASS = 'window';

export interface HousePart {
  d: string;
  fill: string;
}

export interface HouseGeometry {
  /** Offset that puts the foot of the front corner on the origin. */
  ox: number;
  oy: number;
  parts: HousePart[];
  roof: [Point, Point];
  chimney: Point;
  window: Point;
}

/**
 * An isometric house after the reference: a lilac box, a thick purple roof with its ridge running
 * front to back, a 2×2 window on the gable end and a square chimney with an opening on top.
 * Built once in local units (1 unit ≈ 1 px at scale 1).
 */
export const HOUSE: HouseGeometry = (() => {
  const C = Math.cos(Math.PI / 6);
  const S = 0.5;
  const iso = ([x, y, z]: Point3): Point => [(x - y) * C, (x + y) * S - z];
  const d = (...points: Point3[]): string =>
    `M${points.map((p) => iso(p).map((v) => v.toFixed(2)).join(' ')).join('L')}Z`;

  // walls W × D × Hw, ridge height Hr over the middle Dm, eave overhang o, roof thickness th
  const W = 17;
  const D = 14;
  const Hw = 12;
  const Hr = 21;
  const Dm = D / 2;
  const o = 2.2;
  const th = 2.6;
  const xa = -1.2;
  const xb = W + 2;
  const slope = (Hr - Hw) / Dm;
  const ze = Hw - o * slope;
  const roofAt = (y: number) => Hr - Math.abs(y - Dm) * slope;
  const [ox, oy] = iso([W, D, 0]);

  const cx0 = 2;
  const cx1 = 5.6;
  const cy0 = Dm + 0.6;
  const cy1 = Dm + 4;
  const ch = Hr + 5;

  const panes: [number, number][] = [
    [Dm - 3.1, 7.4],
    [Dm + 0.5, 7.4],
    [Dm - 3.1, 3.8],
    [Dm + 0.5, 3.8],
  ];

  return {
    ox,
    oy,
    parts: [
      // the long wall, in the eave's shade
      { d: d([0, D, 0], [W, D, 0], [W, D, Hw], [0, D, Hw]), fill: '#cfc4ef' },
      // the gable end
      { d: d([W, 0, 0], [W, D, 0], [W, D, Hw], [W, Dm, Hr], [W, 0, Hw]), fill: '#efeafd' },
      // the roof plane we see, and its eave edge
      { d: d([xa, Dm, Hr], [xb, Dm, Hr], [xb, D + o, ze], [xa, D + o, ze]), fill: ROOF },
      { d: d([xa, D + o, ze], [xb, D + o, ze], [xb, D + o, ze - th], [xa, D + o, ze - th]), fill: '#5a43a6' },
      // the roof's ends over the gable
      { d: d([xb, Dm, Hr], [xb, D + o, ze], [xb, D + o, ze - th], [xb, Dm, Hr - th]), fill: '#7c63d4' },
      { d: d([xb, Dm, Hr], [xb, -o, ze], [xb, -o, ze - th], [xb, Dm, Hr - th]), fill: '#8f78e0' },
      // the chimney: two sides, the top and its opening
      { d: d([cx1, cy0, roofAt(cy0)], [cx1, cy1, roofAt(cy1)], [cx1, cy1, ch], [cx1, cy0, ch]), fill: '#9d89e6' },
      { d: d([cx0, cy1, roofAt(cy1)], [cx1, cy1, roofAt(cy1)], [cx1, cy1, ch], [cx0, cy1, ch]), fill: '#7a64cf' },
      { d: d([cx0, cy0, ch], [cx1, cy0, ch], [cx1, cy1, ch], [cx0, cy1, ch]), fill: '#6c55c4' },
      {
        d: d([cx0 + 0.8, cy0 + 0.8, ch], [cx1 - 0.8, cy0 + 0.8, ch], [cx1 - 0.8, cy1 - 0.8, ch], [cx0 + 0.8, cy1 - 0.8, ch]),
        fill: '#3b2a7e',
      },
      ...panes.map(([y0, z0]) => ({
        d: d([W, y0, z0], [W, y0 + 2.6, z0], [W, y0 + 2.6, z0 + 3.1], [W, y0, z0 + 3.1]),
        fill: GLASS,
      })),
    ],
    roof: [iso([xa, D + o, ze]), iso([xb, Dm, Hr])],
    chimney: iso([(cx0 + cx1) / 2, (cy0 + cy1) / 2, ch]),
    window: iso([W, Dm, 7.2]),
  };
})();

/** The house on the globe is about half the width of a city label. */
export const HOUSE_SCALE = 0.82;

let paths: { path: Path2D; fill: string }[] | null = null;
const housePaths = () =>
  (paths ??= HOUSE.parts.map((part) => ({ path: new Path2D(part.d), fill: part.fill })));

/** `lit`: 0 dark windows … 1 warm light spilling out. */
export const drawHouse = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  k: number,
  lit: number,
): void => {
  const scale = k * HOUSE_SCALE;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.translate(-HOUSE.ox, -HOUSE.oy);
  ctx.shadowColor = 'rgba(0,0,0,.55)';
  ctx.shadowBlur = 5;
  ctx.shadowOffsetY = 2;

  const [[rx0, ry0], [rx1, ry1]] = HOUSE.roof;
  const roof = ctx.createLinearGradient(rx0, ry0, rx1, ry1);
  roof.addColorStop(0, '#5b44ab');
  roof.addColorStop(1, '#957fe6');
  const glass = `rgb(${Math.round(75 + 180 * lit)},${Math.round(55 + 155 * lit)},${Math.round(150 - 40 * lit)})`;

  housePaths().forEach(({ path, fill }, index) => {
    // only the first wall casts the shadow
    if (index === 1) ctx.shadowColor = 'transparent';
    ctx.fillStyle = fill === ROOF ? roof : fill === GLASS ? glass : fill;
    ctx.fill(path);
  });

  if (lit > 0.02) {
    const [wx, wy] = HOUSE.window;
    const spill = ctx.createRadialGradient(wx, wy, 0, wx, wy, 14);
    spill.addColorStop(0, `rgba(255,210,120,${0.45 * lit})`);
    spill.addColorStop(1, 'rgba(255,190,100,0)');
    ctx.globalCompositeOperation = 'lighter';
    ctx.fillStyle = spill;
    ctx.beginPath();
    ctx.arc(wx, wy, 14, 0, 2 * Math.PI);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.restore();
};

interface Puff {
  age: number;
  life: number;
  dx: number;
  r: number;
}

export interface Smoke {
  puffs: Puff[];
  /** ms until the next puff. */
  clock: number;
}

export const createSmoke = (): Smoke => ({ puffs: [], clock: 0 });

/** Soft puffs rise, drift and fade; new ones come only while someone is home and time runs. */
export const stepSmoke = (
  smoke: Smoke,
  dt: number,
  lit: number,
  random: () => number = Math.random,
): void => {
  smoke.clock -= dt;
  if (dt > 0 && lit > 0.5 && smoke.clock <= 0) {
    smoke.clock = 150;
    smoke.puffs.push({
      age: 0,
      life: 2800 + random() * 900,
      dx: (random() - 0.5) * 0.3,
      r: 2.2 + random() * 1.4,
    });
  }
  for (const puff of smoke.puffs) {
    puff.age += dt;
  }
  smoke.puffs = smoke.puffs.filter((puff) => puff.age < puff.life);
};

export const drawSmoke = (
  ctx: CanvasRenderingContext2D,
  smoke: Smoke,
  x: number,
  y: number,
  k: number,
): void => {
  const scale = k * HOUSE_SCALE;
  const bx = x + (HOUSE.chimney[0] - HOUSE.ox) * scale;
  const by = y + (HOUSE.chimney[1] - HOUSE.oy) * scale;
  for (const puff of smoke.puffs) {
    const u = puff.age / puff.life;
    const alpha = Math.sin(Math.PI * Math.min(1, u * 1.3)) * (1 - u) * 0.38;
    const px = bx + ((puff.dx * puff.age) / 16 + Math.sin(puff.age / 420) * 2.5 + u * 10) * k;
    const py = by - (u * 34 + 2) * k;
    const radius = (puff.r + u * 6) * k;
    const cloud = ctx.createRadialGradient(px, py, 0, px, py, radius);
    cloud.addColorStop(0, `rgba(226,224,240,${alpha})`);
    cloud.addColorStop(1, 'rgba(226,224,240,0)');
    ctx.fillStyle = cloud;
    ctx.beginPath();
    ctx.arc(px, py, radius, 0, 2 * Math.PI);
    ctx.fill();
  }
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/render/house.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/render/house.ts src/render/house.test.ts
git commit -m "feat(render): add the isometric home house and its chimney smoke"
```

---

### Task 11: The painter

**Files:**
- Create: `src/render/globe.ts`
- Test: `src/render/globe.test.ts`

**Interfaces:**
- Consumes: `clamp` (`src/lib/math.ts`); `clipCos`, `faces` (`src/geo/projection.ts`); `Vec3` (`src/geo/vector.ts`); `EarthGeo` (`src/geo/world.ts`); `Light` (`src/render/lights.ts`); `PlaceLook` (`src/render/places.ts`); `drawHouse` (`src/render/house.ts`).
- Produces:
  - `interface GlobeView { width: number; height: number; cx: number; cy: number; r: number; t: number; centre: Vec3 }`
  - `interface PlaceSprite { x: number; y: number; look: PlaceLook; pulse: number; photos: number }`
  - `interface HomeSprite { x: number; y: number; k: number; pulse: number; lit: number }`
  - `placeBase(r: number): number`, `placeRadius(sprite: PlaceSprite, base: number): number`
  - `createPainter(ctx, projection): Painter` with `earth(view, geo, lights)`, `places(sprites, base)`, `home(sprite)`; `type Painter`

- [ ] **Step 1: Write the failing test**

`src/render/globe.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { placeBase, placeRadius } from './globe';
import type { PlaceSprite } from './globe';
import { PLACE_LOOK } from './places';

const sprite = (patch: Partial<PlaceSprite>): PlaceSprite => ({
  x: 0,
  y: 0,
  look: PLACE_LOOK.yellow,
  pulse: 0,
  photos: 100,
  ...patch,
});

describe('placeBase', () => {
  it('grows with the globe inside limits', () => {
    expect(placeBase(38)).toBe(0.6);
    expect(placeBase(380)).toBe(1);
    expect(placeBase(3800)).toBe(2);
  });
});

describe('placeRadius', () => {
  it('grows with the photos of a place', () => {
    expect(placeRadius(sprite({ photos: 400 }), 1)).toBeGreaterThan(placeRadius(sprite({}), 1));
  });

  it('makes the current place 1.45× the size of a reached one', () => {
    const current = placeRadius(sprite({ look: PLACE_LOOK.current }), 1);
    expect(current / placeRadius(sprite({}), 1)).toBeCloseTo(1.45);
  });

  it('swells with the pulse', () => {
    expect(placeRadius(sprite({ pulse: 1 }), 1) / placeRadius(sprite({}), 1)).toBeCloseTo(1.8);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/render/globe.test.ts`
Expected: FAIL — cannot resolve `./globe`.

- [ ] **Step 3: Implement**

`src/render/globe.ts`:

```ts
import { geoPath } from 'd3-geo';
import type { GeoPermissibleObjects, GeoProjection } from 'd3-geo';
import { faces } from '@/geo/projection';
import type { Vec3 } from '@/geo/vector';
import type { EarthGeo } from '@/geo/world';
import { clamp } from '@/lib/math';
import { drawHouse } from './house';
import type { Light } from './lights';
import type { PlaceLook } from './places';

export interface GlobeView {
  width: number;
  height: number;
  cx: number;
  cy: number;
  r: number;
  /** Unroll blend: 0 ball … 1 flat map. */
  t: number;
  /** Unit vector of the point in the middle of the view. */
  centre: Vec3;
}

export interface PlaceSprite {
  x: number;
  y: number;
  look: PlaceLook;
  /** 0..1, see `pulse` in lib/easing. */
  pulse: number;
  photos: number;
}

export interface HomeSprite {
  x: number;
  y: number;
  /** Scale of the house. */
  k: number;
  pulse: number;
  /** 0 dark … 1 someone is home. */
  lit: number;
}

type Rgb = [number, number, number];

const mix = (a: Rgb, b: Rgb, k: number): string =>
  a.map((value, i) => Math.round(value + ((b[i] ?? value) - value) * k)).join(',');

const LIGHT_ALPHA = [0.2, 0.34, 0.5];

/** Size unit for the places: they grow with the globe, within limits. */
export const placeBase = (r: number): number => clamp(r / 380, 0.6, 2);

/** Radius of a place's glow. */
export const placeRadius = ({ photos, look, pulse }: PlaceSprite, base: number): number =>
  (5 + Math.sqrt(photos) * 0.6) * base * look.size * (1 + 0.8 * pulse);

export const createPainter = (ctx: CanvasRenderingContext2D, projection: GeoProjection) => {
  const svg = geoPath(projection).digits(1);
  const shape = (object: GeoPermissibleObjects): Path2D => new Path2D(svg(object) ?? '');

  /** Atmosphere, ocean, land, borders and the faint city lights. */
  const earth = ({ cx, cy, r, t, centre }: GlobeView, geo: EarthGeo, lights: readonly Light[]) => {
    if (t < 1) {
      // the atmosphere fades as the ball unrolls
      const air = ctx.createRadialGradient(cx, cy, r * 0.97, cx, cy, r * 1.14);
      air.addColorStop(0, `rgba(90,140,255,${0.38 * (1 - t)})`);
      air.addColorStop(1, 'rgba(90,140,255,0)');
      ctx.fillStyle = air;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 1.14, 0, 2 * Math.PI);
      ctx.fill();
    }

    const outline = shape({ type: 'Sphere' });
    const ocean = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.4, r * 0.1, cx, cy, r * (1.2 + t * 1.6));
    ocean.addColorStop(0, '#10203d');
    ocean.addColorStop(1, '#050913');
    ctx.fillStyle = ocean;
    ctx.fill(outline);
    ctx.strokeStyle = 'rgba(120,160,240,.18)';
    ctx.lineWidth = 1;
    ctx.stroke(outline);

    const land = shape(geo.land);
    ctx.fillStyle = '#17223d';
    ctx.fill(land);
    ctx.strokeStyle = 'rgba(120,150,210,.17)';
    ctx.lineWidth = 0.6;
    ctx.stroke(shape(geo.borders));
    ctx.strokeStyle = 'rgba(150,185,255,.42)';
    ctx.lineWidth = 0.9;
    ctx.stroke(land);

    const size = clamp(r / 330, 0.8, 2.6);
    ctx.globalCompositeOperation = 'lighter';
    LIGHT_ALPHA.forEach((alpha, band) => {
      ctx.beginPath();
      for (const light of lights) {
        if (light.band !== band || !faces(light.v, centre, t, 0.03)) continue;
        const point = projection(light.ll);
        if (point) ctx.rect(point[0], point[1], size, size);
      }
      ctx.fillStyle = `rgba(255,190,110,${alpha})`;
      ctx.fill();
    });
    ctx.globalCompositeOperation = 'source-over';
  };

  /** The places: a glow, then the dot itself (grey, yellow or star blue). */
  const places = (sprites: readonly PlaceSprite[], base: number) => {
    ctx.globalCompositeOperation = 'lighter';
    for (const sprite of sprites) {
      const { x, y, look, pulse } = sprite;
      const glow = Math.max(look.glow, pulse);
      if (glow <= 0.01) continue;
      const radius = placeRadius(sprite, base);
      const halo = ctx.createRadialGradient(x, y, 0, x, y, radius);
      halo.addColorStop(0, `rgba(${mix([255, 226, 160], [205, 225, 255], look.blue)},${0.85 * glow})`);
      halo.addColorStop(0.25, `rgba(${mix([255, 175, 80], [110, 160, 255], look.blue)},${0.36 * glow})`);
      halo.addColorStop(1, `rgba(${mix([255, 150, 50], [90, 140, 255], look.blue)},0)`);
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';

    for (const { x, y, look } of sprites) {
      const tone: Rgb = [
        255 + (190 - 255) * look.blue,
        228 + (215 - 228) * look.blue,
        175 + (255 - 175) * look.blue,
      ];
      const alpha = 0.55 + 0.45 * Math.max(look.glow, look.warm * 0.4);
      ctx.fillStyle = `rgba(${mix([150, 160, 185], tone, look.warm)},${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, (1.3 + 1.1 * look.size) * base, 0, 2 * Math.PI);
      ctx.fill();
    }
  };

  /** Home: a warm glow and the small house. */
  const home = ({ x, y, k, pulse, lit }: HomeSprite) => {
    const warm = Math.max(pulse, lit * 0.8, 0.15);
    const gy = y - 4 * k;
    const glow = ctx.createRadialGradient(x, gy, 0, x, gy, 22 * k);
    glow.addColorStop(0, `rgba(255,214,150,${0.5 * warm})`);
    glow.addColorStop(1, 'rgba(255,190,120,0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, gy, 22 * k, 0, 2 * Math.PI);
    ctx.fill();
    drawHouse(ctx, x, y, k, lit);
  };

  return { earth, places, home };
};

export type Painter = ReturnType<typeof createPainter>;
```

- [ ] **Step 4: Run the tests and the typecheck**

Run: `npx vitest run src/render/globe.test.ts && npm run typecheck`
Expected: PASS. If `geoPath(...).digits` is missing from the installed `@types/d3-geo`, report it; do not cast it away.

- [ ] **Step 5: Commit**

```bash
git add src/render/globe.ts src/render/globe.test.ts
git commit -m "feat(render): add the globe painter for earth, places and home"
```

---

### Task 12: The engine: clock, throw and the frame loop

**Files:**
- Create: `src/engine/clock.ts`, `src/engine/throw.ts`, `src/engine/engine.ts`
- Test: `src/engine/clock.test.ts`, `src/engine/throw.test.ts`

**Interfaces:**
- Consumes: everything from Tasks 2–11 named in the imports below; `appStore` (`src/state/app-state.ts`); `Archive`, `photoTotal` (`src/data/archive.ts`); `Place` (`src/data/types.ts`).
- Produces:
  - `FRAME_MS = 16.7`, `MAX_STEP_MS = 70`, `interface Step { real: number; dt: number; f: number }`, `frameStep(time: number, last: number | null, paused: boolean): Step`
  - `interface DragSample { at: number; x: number; y: number }`, `THROW_WINDOW = 160`, `THROW_MAX_IDLE = 220`, `THROW_MAX = 6`, `pushSample(samples: DragSample[], sample: DragSample): void`, `throwVelocity(samples: DragSample[], now: number): [number, number]`, `spinDirection(vx: number, vy: number, gam: number, current: 1 | -1): 1 | -1`
  - `interface EngineOptions { stars; sky; globe; label; earth; lights; archive; home }`, `interface GlobeEngine { destroy(): void }`, `createEngine(options: EngineOptions): GlobeEngine`
  - In dev builds only: `window.__globe = { state(), setZoom(z) }` for manual and browser checks.

- [ ] **Step 1: Write the failing tests**

`src/engine/clock.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { FRAME_MS, frameStep, MAX_STEP_MS } from './clock';

describe('frameStep', () => {
  it('treats the first frame as one 60 Hz frame', () => {
    expect(frameStep(1234, null, false)).toEqual({ real: FRAME_MS, dt: FRAME_MS, f: 1 });
  });

  it('measures the time since the last frame', () => {
    const step = frameStep(1033.4, 1000, false);
    expect(step.real).toBeCloseTo(33.4);
    expect(step.f).toBeCloseTo(2);
  });

  it('does not jump when a tab comes back from the background', () => {
    expect(frameStep(60000, 1000, false).dt).toBe(MAX_STEP_MS);
  });

  it('stops the world clock while paused, not the real one', () => {
    const step = frameStep(1016.7, 1000, true);
    expect(step.dt).toBe(0);
    expect(step.f).toBe(0);
    expect(step.real).toBeCloseTo(16.7);
  });

  it('never runs backwards', () => {
    expect(frameStep(900, 1000, false).dt).toBe(0);
  });
});
```

`src/engine/throw.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { pushSample, spinDirection, THROW_MAX, throwVelocity } from './throw';
import type { DragSample } from './throw';

describe('pushSample', () => {
  it('keeps only the last ~160 ms, and at least two samples', () => {
    const samples: DragSample[] = [];
    for (let at = 0; at <= 1000; at += 20) pushSample(samples, { at, x: at, y: 0 });
    expect(samples[0]?.at).toBeGreaterThanOrEqual(1000 - 160);
    const two: DragSample[] = [];
    pushSample(two, { at: 0, x: 0, y: 0 });
    pushSample(two, { at: 500, x: 1, y: 0 });
    expect(two).toHaveLength(2);
  });
});

describe('throwVelocity', () => {
  it('turns the last movement into degrees per 60 Hz frame', () => {
    const samples: DragSample[] = [
      { at: 0, x: 0, y: 0 },
      { at: 100, x: 10, y: -5 },
    ];
    const [vx, vy] = throwVelocity(samples, 110);
    expect(vx).toBeCloseTo(1.67);
    expect(vy).toBeCloseTo(-0.835);
  });

  it('does not throw when the hand rested before letting go', () => {
    const samples: DragSample[] = [
      { at: 0, x: 0, y: 0 },
      { at: 100, x: 10, y: 0 },
    ];
    expect(throwVelocity(samples, 100 + 220)).toEqual([0, 0]);
  });

  it('caps a wild throw', () => {
    const samples: DragSample[] = [
      { at: 0, x: 0, y: 0 },
      { at: 10, x: 500, y: -500 },
    ];
    expect(throwVelocity(samples, 10)).toEqual([THROW_MAX, -THROW_MAX]);
  });

  it('needs two samples', () => {
    expect(throwVelocity([], 0)).toEqual([0, 0]);
    expect(throwVelocity([{ at: 0, x: 3, y: 3 }], 0)).toEqual([0, 0]);
  });
});

describe('spinDirection', () => {
  it('follows a sideways throw', () => {
    expect(spinDirection(-2, 0, 0, 1)).toBe(-1);
    expect(spinDirection(2, 0, 0, -1)).toBe(1);
  });

  it('turns the other way when the globe is upside down', () => {
    expect(spinDirection(2, 0, 180, 1)).toBe(-1);
  });

  it('keeps its way after a soft or vertical throw', () => {
    expect(spinDirection(0.05, 0.05, 0, -1)).toBe(-1);
    expect(spinDirection(0.01, 3, 0, -1)).toBe(-1);
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/engine`
Expected: FAIL — cannot resolve `./clock` and `./throw`.

- [ ] **Step 3: Implement the clock and the throw**

`src/engine/clock.ts`:

```ts
import { clamp } from '@/lib/math';

/** One 60 Hz frame in ms: every per-frame rate in the engine is written for it. */
export const FRAME_MS = 16.7;
/** The longest step the world takes in one frame, so a tab back from the background does not jump. */
export const MAX_STEP_MS = 70;

export interface Step {
  /** Real ms since the last frame. */
  real: number;
  /** World ms: none while the world is paused. */
  dt: number;
  /** `dt` in 60 Hz frames. */
  f: number;
}

export const frameStep = (time: number, last: number | null, paused: boolean): Step => {
  const real = last === null ? FRAME_MS : clamp(time - last, 0, MAX_STEP_MS);
  const dt = paused ? 0 : real;
  return { real, dt, f: dt / FRAME_MS };
};
```

`src/engine/throw.ts`:

```ts
import { clamp, DEG } from '@/lib/math';
import { FRAME_MS } from './clock';

/** Cumulative drag in degrees at a moment. */
export interface DragSample {
  at: number;
  x: number;
  y: number;
}

/** The throw is measured over the last ~160 ms of movement. */
export const THROW_WINDOW = 160;
/** A hand that rests this long before letting go does not throw. */
export const THROW_MAX_IDLE = 220;
/** Fastest throw, in degrees per 60 Hz frame. */
export const THROW_MAX = 6;

export const pushSample = (samples: DragSample[], sample: DragSample): void => {
  samples.push(sample);
  while (samples.length > 2 && sample.at - (samples[0]?.at ?? sample.at) > THROW_WINDOW) {
    samples.shift();
  }
};

/** Throw speed in degrees per 60 Hz frame, about the screen axes. */
export const throwVelocity = (samples: DragSample[], now: number): [number, number] => {
  const first = samples[0];
  const last = samples[samples.length - 1];
  if (!first || !last || samples.length < 2 || now - last.at >= THROW_MAX_IDLE) {
    return [0, 0];
  }
  const span = Math.max(last.at - first.at, 1);
  return [
    clamp(((last.x - first.x) / span) * FRAME_MS, -THROW_MAX, THROW_MAX),
    clamp(((last.y - first.y) / span) * FRAME_MS, -THROW_MAX, THROW_MAX),
  ];
};

/**
 * A sideways throw sets the Earth spinning the same way; upside down (γ past ±90°) its axis turns
 * the other way. A soft or vertical throw keeps the current way.
 */
export const spinDirection = (vx: number, vy: number, gam: number, current: 1 | -1): 1 | -1 => {
  if (Math.hypot(vx, vy) <= 0.12 || Math.abs(vx) <= 0.05) return current;
  const upsideDown = Math.cos(gam * DEG) < 0;
  return (Math.sign(vx) * (upsideDown ? -1 : 1)) as 1 | -1;
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/engine`
Expected: PASS.

- [ ] **Step 5: Write the engine**

`src/engine/engine.ts`:

```ts
import { geoRotation } from 'd3-geo';
import { photoTotal } from '@/data/archive';
import type { Archive } from '@/data/archive';
import type { City, Place } from '@/data/types';
import { turn, wrapLon } from '@/geo/camera';
import type { Rotation } from '@/geo/camera';
import {
  clipFor,
  createBlendProjection,
  faces,
  flatLatLimit,
  raw,
  ROLLED,
  stepUnroll,
  unrollT,
  WHEEL_ZOOM,
  Z_MAX,
  Z_MIN,
  zFlat,
} from '@/geo/projection';
import type { Unroll } from '@/geo/projection';
import { vec } from '@/geo/vector';
import type { Vec3 } from '@/geo/vector';
import type { EarthGeo } from '@/geo/world';
import { ease, pulse } from '@/lib/easing';
import { clamp, DEG } from '@/lib/math';
import { createPainter, placeBase, placeRadius } from '@/render/globe';
import type { PlaceSprite } from '@/render/globe';
import type { Light } from '@/render/lights';
import { PLACE_LOOK, stepLook } from '@/render/places';
import type { PlaceLook } from '@/render/places';
import { createSky, drawSky, drawStarField, STAR_PAD, starDrift, stepSky } from '@/render/sky';
import { appStore } from '@/state/app-state';
import { frameStep } from './clock';
import { pushSample, spinDirection, throwVelocity } from './throw';
import type { DragSample } from './throw';

export interface EngineOptions {
  stars: HTMLCanvasElement;
  sky: HTMLCanvasElement;
  globe: HTMLCanvasElement;
  /** The hover label: the engine moves and fades it, React fills it in. */
  label: HTMLElement;
  earth: EarthGeo;
  lights: Light[];
  archive: Archive;
  home: Place;
}

export interface GlobeEngine {
  destroy(): void;
}

/** Slow spin in degrees per 60 Hz frame. */
const CRUISE = 0.06;
/** Each 60 Hz frame keeps this share of a throw. */
const THROW_DECAY = 0.975;
const PULSE_MS = 1500;
/** A press becomes a drag after this many px. */
const DRAG_THRESHOLD = 5;
/** A place is hit within this many px of its centre, or more for a big glow. */
const HIT_MIN = 14;

interface PlaceRuntime {
  city: City;
  v: Vec3;
  photos: number;
  look: PlaceLook;
  pulseAt: number;
  x: number;
  y: number;
  /** Glow radius, at least `HIT_MIN`. */
  r: number;
  visible: boolean;
}

const context = (canvas: HTMLCanvasElement): CanvasRenderingContext2D => {
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas 2D is not available');
  return ctx;
};

const sizeCanvas = (canvas: HTMLCanvasElement, width: number, height: number, dpr: number) => {
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
};

/**
 * The globe. One requestAnimationFrame loop owns time: a world clock that stops while the app
 * state says `paused`, the camera, the input, and all drawing on the three canvases.
 */
export const createEngine = (options: EngineOptions): GlobeEngine => {
  const { stars, globe, label, earth, lights, archive, home } = options;
  const g = context(globe);
  const skyCtx = context(options.sky);
  const starsCtx = context(stars);
  const { projection, blend } = createBlendProjection();
  const painter = createPainter(g, projection);

  // viewport
  let width = 0;
  let height = 0;
  let mobile = false;
  let r0 = 1;
  let sky = createSky(1, 1, false);

  // camera: rot turns the globe; z is the zoom, 1 = the planet fits, 0.5 = further out
  let rot: Rotation = [-10, -35, 0];
  let z = 1;
  let zTarget = 1;
  // motion: a throw in degrees per 60 Hz frame about the screen axes, gliding out,
  // and the spin about the Earth's own axis
  let vx = 0;
  let vy = 0;
  let spin = CRUISE;
  let spinning = true;
  let spinDir: 1 | -1 = 1;
  let unroll: Unroll = ROLLED;
  let t = 0;
  let r = 1;
  let cx = 0;
  let cy = 0;
  let centre: Vec3 = [1, 0, 0];
  let lim = 90;

  // clock
  let worldNow = 0;
  let lastFrame: number | null = null;
  let frameId = 0;

  const places: PlaceRuntime[] = archive.cities.map((city) => ({
    city,
    v: vec(city.lon, city.lat),
    photos: photoTotal(city),
    look: { ...PLACE_LOOK.plain },
    pulseAt: -Infinity,
    x: 0,
    y: 0,
    r: HIT_MIN,
    visible: false,
  }));
  const homeV = vec(home.lon, home.lat);

  // input
  const pointers = new Map<number, [number, number]>();
  let dragging = false;
  let moved = false;
  let pinch: { distance: number; z: number } | null = null;
  let downAt: [number, number] = [0, 0];
  let samples: DragSample[] = [];
  let dragX = 0;
  let dragY = 0;
  let mouse: [number, number] | null = null;
  let hovered: PlaceRuntime | null = null;

  const resize = () => {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    width = innerWidth;
    height = innerHeight;
    mobile = width < 700;
    sizeCanvas(globe, width, height, dpr);
    sizeCanvas(options.sky, width, height, dpr);
    sizeCanvas(stars, width + STAR_PAD * 2, height + STAR_PAD * 2, dpr);
    for (const ctx of [g, skyCtx, starsCtx]) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    r0 = mobile ? Math.min(width * 0.4, height * 0.28) : Math.min(width * 0.3, height * 0.4);
    drawStarField(starsCtx, width + STAR_PAD * 2, height + STAR_PAD * 2);
    sky = createSky(width, height, mobile);
  };

  const measure = () => {
    cx = mobile ? width / 2 : width * 0.6;
    cy = mobile ? height * 0.58 : height * 0.5;
    const zf = zFlat({ width, height, cx, cy, r0 });
    unroll = stepUnroll(unroll, t, zTarget, zf, worldNow);
    t = unrollT(unroll, worldNow);
    r = r0 * (unroll.flat ? Math.max(z, zf) : z);
    lim = 90 - t * (90 - flatLatLimit(cy, height, r));
  };

  const project = () => {
    blend(t);
    const view: Rotation = [rot[0], rot[1] * (1 - t), rot[2] * (1 - t)];
    const rotation = geoRotation(view);
    // keep the point the camera looks at in the middle of the frame
    const [lon, lat] = rotation([-rot[0], -rot[1]]);
    const [px, py] = raw(t, lon * DEG, lat * DEG);
    projection
      .preclip(clipFor(t))
      .rotate(view)
      .scale(r)
      .translate([cx - r * px, cy + r * py]);
    const [clon, clat] = rotation.invert([0, 0]);
    centre = vec(clon, clat);
  };

  const placeAt = (x: number, y: number): PlaceRuntime | null => {
    let best: PlaceRuntime | null = null;
    let bestDistance = Infinity;
    for (const place of places) {
      if (!place.visible) continue;
      const distance = Math.hypot(place.x - x, place.y - y);
      if (distance < Math.max(HIT_MIN, place.r * 0.55) && distance < bestDistance) {
        best = place;
        bestDistance = distance;
      }
    }
    return best;
  };

  const updateCursor = () => {
    globe.style.cursor = dragging ? 'grabbing' : hovered ? 'pointer' : '';
  };

  const updateHover = () => {
    // the light under a still cursor changes as the globe turns under it
    if (mouse && !dragging) {
      const next = placeAt(mouse[0], mouse[1]);
      if (next !== hovered) {
        hovered = next;
        updateCursor();
        if (next) appStore.set({ labelCityKey: next.city.key });
      }
    }
    const shown = hovered !== null && hovered.visible;
    label.style.opacity = shown ? '1' : '0';
    if (hovered && shown) {
      label.style.transform = `translate(${hovered.x}px, ${hovered.y - hovered.r * 0.6}px) translate(-50%, -100%)`;
    }
  };

  const draw = (f: number) => {
    g.clearRect(0, 0, width, height);
    painter.earth({ width, height, cx, cy, r, t, centre }, earth, lights);

    const base = placeBase(r);
    const sprites: PlaceSprite[] = [];
    for (const place of places) {
      place.look = stepLook(place.look, 'plain', f, place === hovered);
      place.visible = faces(place.v, centre, t, 0.02);
      if (!place.visible) continue;
      const point = projection([place.city.lon, place.city.lat]);
      if (!point) {
        place.visible = false;
        continue;
      }
      const sprite: PlaceSprite = {
        x: point[0],
        y: point[1],
        look: place.look,
        pulse: pulse(worldNow - place.pulseAt, PULSE_MS),
        photos: place.photos,
      };
      place.x = sprite.x;
      place.y = sprite.y;
      place.r = Math.max(HIT_MIN, placeRadius(sprite, base));
      sprites.push(sprite);
    }
    painter.places(sprites, base);

    if (faces(homeV, centre, t, 0.02)) {
      const point = projection([home.lon, home.lat]);
      if (point) {
        painter.home({ x: point[0], y: point[1], k: clamp(r / 300, 1, 2.2) * 0.5, pulse: 0, lit: 0 });
      }
    }

    updateHover();
  };

  const frame = (time: number) => {
    const { dt, f } = frameStep(time, lastFrame, appStore.get().paused);
    lastFrame = time;
    worldNow += dt;

    z = ease(z, zTarget, f, 0.9);
    measure();
    if (!dragging) {
      if (vx || vy) {
        rot = turn(rot, vx * f, vy * f, t);
        const keep = THROW_DECAY ** f;
        vx *= keep;
        vy *= keep;
        if (Math.hypot(vx, vy) < 0.003) vx = vy = 0;
      }
      // the Earth keeps turning while it is a ball; the flat map moves only when dragged
      spin = ease(spin, spinning && !unroll.flat ? CRUISE * spinDir : 0, f, 0.985);
      // and the flat map is always level
      const gam = t > 0 ? rot[2] * (1 - 0.08 * t) ** f : rot[2];
      rot = [wrapLon(rot[0] + spin * f), rot[1], gam];
    }
    rot = [rot[0], clamp(rot[1], -lim, lim), rot[2]];
    project();

    stepSky(sky, dt);
    drawSky(skyCtx, sky, worldNow);
    const [driftX, driftY] = starDrift(worldNow);
    stars.style.transform = `translate(${driftX}px, ${driftY}px)`;

    draw(f);
    frameId = requestAnimationFrame(frame);
  };

  // input: drag, throw, wheel and pinch zoom

  const onPointerDown = (event: PointerEvent) => {
    globe.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, [event.clientX, event.clientY]);
    downAt = [event.clientX, event.clientY];
    dragging = true;
    moved = false;
    samples = [];
    dragX = 0;
    dragY = 0;
    updateCursor();
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      if (a && b) pinch = { distance: Math.hypot(a[0] - b[0], a[1] - b[1]), z: zTarget };
    }
  };

  const onPointerMove = (event: PointerEvent) => {
    if (event.pointerType === 'mouse') mouse = [event.clientX, event.clientY];
    const previous = pointers.get(event.pointerId);
    if (!previous) return;
    pointers.set(event.pointerId, [event.clientX, event.clientY]);

    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      if (a && b) {
        const distance = Math.hypot(a[0] - b[0], a[1] - b[1]);
        zTarget = clamp((pinch.z * distance) / pinch.distance, Z_MIN, Z_MAX);
      }
      return;
    }

    // a real drag starts after a few px, and it stops any spin
    if (!moved && Math.hypot(event.clientX - downAt[0], event.clientY - downAt[1]) > DRAG_THRESHOLD) {
      moved = true;
      vx = vy = spin = 0;
      spinning = false;
    }
    if (!moved) return;

    const perPixel = 1 / DEG / r; // degrees per pixel at the current size
    const dx = (event.clientX - previous[0]) * perPixel;
    const dy = (event.clientY - previous[1]) * perPixel;
    rot = turn(rot, dx, dy, t);
    dragX += dx;
    dragY += dy;
    pushSample(samples, { at: performance.now(), x: dragX, y: dragY });
  };

  const onPointerUp = (event: PointerEvent) => {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size > 0) return;
    dragging = false;
    updateCursor();
    if (!moved) return;
    [vx, vy] = throwVelocity(samples, performance.now());
    spinDir = spinDirection(vx, vy, rot[2], spinDir);
    // let go, with or without a throw: the Earth picks its spin back up
    spinning = true;
  };

  const onPointerLeave = () => {
    mouse = null;
    hovered = null;
    updateCursor();
  };

  const onWheel = (event: WheelEvent) => {
    event.preventDefault();
    zTarget = clamp(zTarget * Math.exp(-event.deltaY * WHEEL_ZOOM), Z_MIN, Z_MAX);
  };

  resize();
  addEventListener('resize', resize);
  globe.addEventListener('pointerdown', onPointerDown);
  globe.addEventListener('pointermove', onPointerMove);
  globe.addEventListener('pointerup', onPointerUp);
  globe.addEventListener('pointercancel', onPointerUp);
  globe.addEventListener('pointerleave', onPointerLeave);
  globe.addEventListener('wheel', onWheel, { passive: false });
  frameId = requestAnimationFrame(frame);

  if (import.meta.env.DEV) {
    Object.assign(window, {
      __globe: {
        state: () => ({ z, zTarget, t, flat: unroll.flat, rot, spin, worldNow }),
        setZoom: (value: number) => {
          zTarget = clamp(value, Z_MIN, Z_MAX);
        },
      },
    });
  }

  return {
    destroy() {
      cancelAnimationFrame(frameId);
      removeEventListener('resize', resize);
      globe.removeEventListener('pointerdown', onPointerDown);
      globe.removeEventListener('pointermove', onPointerMove);
      globe.removeEventListener('pointerup', onPointerUp);
      globe.removeEventListener('pointercancel', onPointerUp);
      globe.removeEventListener('pointerleave', onPointerLeave);
      globe.removeEventListener('wheel', onWheel);
      label.style.opacity = '0';
      appStore.set({ labelCityKey: null });
      if (import.meta.env.DEV) Reflect.deleteProperty(window, '__globe');
    },
  };
};
```

Note: the prototype used `57.3 / R` degrees per pixel; `1 / DEG / r` is the same number.

- [ ] **Step 6: Run the whole check**

Run: `npm run check`
Expected: PASS. The engine is not mounted yet; Task 13 mounts it and checks it in the browser.

- [ ] **Step 7: Commit**

```bash
git add src/engine
git commit -m "feat(engine): add the frame loop with the world clock, drag, throw and zoom"
```

---

### Task 13: Boot, the globe stage, the hover label and the header

**Files:**
- Create: `src/app/boot.ts`, `src/features/globe/GlobeStage.tsx`, `src/features/globe/PlaceLabel.tsx`, `src/features/globe/globe.scss`, `src/features/header/Header.tsx`, `src/features/header/header.scss`
- Modify: `src/app/App.tsx`
- Test: `src/app/boot.test.ts`

**Interfaces:**
- Consumes: `linkArchive`, `Archive`, `visitYears` (`src/data/archive.ts`); `buildDemo`, `DEMO_HOME` (`src/data/demo.ts`); `Credit`, `Place` (`src/data/types.ts`); `earthFromTopology`, `EarthGeo`, `WorldTopology` (`src/geo/world.ts`); `buildLights`, `Light` (`src/render/lights.ts`); `createEngine` (`src/engine/engine.ts`); `appStore` (`src/state/app-state.ts`); `useStore` (`src/state/store.ts`).
- Produces:
  - `interface World { earth: EarthGeo; lights: Light[]; archive: Archive; home: Place }`
  - `demoUrl(path: string): string`, `loadWorld(): Promise<World>`
  - Components `GlobeStage({ world })`, `PlaceLabel({ archive, ref })`, `Header()`, and `App` showing loading, failure with retry, or the globe.

- [ ] **Step 1: Write the failing test**

`src/app/boot.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { demoUrl, loadWorld } from './boot';

const demoDir = fileURLToPath(new URL('../../public/demo/', import.meta.url));

const serve = (status: number) =>
  vi.fn(async (url: string) => {
    const file = url.split('/demo/')[1] ?? '';
    return {
      ok: status === 200,
      status,
      json: async () => JSON.parse(readFileSync(`${demoDir}${file}`, 'utf8')) as unknown,
    };
  });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('demoUrl', () => {
  it('builds on the base path, so it works under /cloudpix-platform/ too', () => {
    expect(demoUrl('photos.json')).toBe(`${import.meta.env.BASE_URL}demo/photos.json`);
  });
});

describe('loadWorld', () => {
  it('loads the map and the demo traveller', async () => {
    const fetch = serve(200);
    vi.stubGlobal('fetch', fetch);
    const world = await loadWorld();
    expect(fetch).toHaveBeenCalledWith(demoUrl('countries-110m.json'));
    expect(fetch).toHaveBeenCalledWith(demoUrl('photos.json'));
    expect(world.archive.cities).toHaveLength(22);
    expect(world.home.name).toBe('Kyiv');
    expect(world.lights.length).toBeGreaterThan(1000);
  });

  it('fails loudly when a file is missing', async () => {
    vi.stubGlobal('fetch', serve(404));
    await expect(loadWorld()).rejects.toThrow(/HTTP 404/);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/app/boot.test.ts`
Expected: FAIL — cannot resolve `./boot`.

- [ ] **Step 3: Implement the boot**

`src/app/boot.ts`:

```ts
import { linkArchive } from '@/data/archive';
import type { Archive } from '@/data/archive';
import { buildDemo, DEMO_HOME } from '@/data/demo';
import type { Credit, Place } from '@/data/types';
import { earthFromTopology } from '@/geo/world';
import type { EarthGeo, WorldTopology } from '@/geo/world';
import { buildLights } from '@/render/lights';
import type { Light } from '@/render/lights';

export interface World {
  earth: EarthGeo;
  lights: Light[];
  archive: Archive;
  home: Place;
}

export const demoUrl = (path: string): string => `${import.meta.env.BASE_URL}demo/${path}`;

const fetchJson = async <T>(path: string): Promise<T> => {
  const response = await fetch(demoUrl(path));
  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
  }
  return (await response.json()) as T;
};

/** Loads the world map and the demo archive. Logged out, the demo traveller is all there is. */
export const loadWorld = async (): Promise<World> => {
  const [topology, credits] = await Promise.all([
    fetchJson<WorldTopology>('countries-110m.json'),
    fetchJson<Credit[]>('photos.json'),
  ]);
  const earth = earthFromTopology(topology);
  return {
    earth,
    lights: buildLights(earth.land),
    archive: linkArchive(buildDemo(credits)),
    home: DEMO_HOME,
  };
};
```

- [ ] **Step 4: Run the test**

Run: `npx vitest run src/app/boot.test.ts`
Expected: PASS.

- [ ] **Step 5: Write the components**

`src/features/globe/PlaceLabel.tsx`:

```tsx
import type { Ref } from 'react';
import { visitYears } from '@/data/archive';
import type { Archive } from '@/data/archive';
import { appStore } from '@/state/app-state';
import { useStore } from '@/state/store';

interface PlaceLabelProps {
  archive: Archive;
  ref: Ref<HTMLDivElement>;
}

/** The label over the light under the cursor. The engine moves and fades it; React fills it in. */
export function PlaceLabel({ archive, ref }: PlaceLabelProps) {
  const key = useStore(appStore, (state) => state.labelCityKey);
  const city = key === null ? undefined : archive.cityByKey.get(key);

  return (
    <div ref={ref} className="place-label" aria-hidden="true">
      {city && (
        <>
          <b>{city.name}</b>
          <span>
            {city.country.name} · {visitYears(city).join(' · ')}
          </span>
        </>
      )}
    </div>
  );
}
```

`src/features/globe/GlobeStage.tsx`:

```tsx
import { useEffect, useRef } from 'react';
import type { World } from '@/app/boot';
import { createEngine } from '@/engine/engine';
import { PlaceLabel } from './PlaceLabel';
import './globe.scss';

/** The three canvases (stars, sky events, globe) and the hover label, driven by the engine. */
export function GlobeStage({ world }: { world: World }) {
  const stars = useRef<HTMLCanvasElement>(null);
  const sky = useRef<HTMLCanvasElement>(null);
  const globe = useRef<HTMLCanvasElement>(null);
  const label = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!stars.current || !sky.current || !globe.current || !label.current) {
      return;
    }
    const engine = createEngine({
      stars: stars.current,
      sky: sky.current,
      globe: globe.current,
      label: label.current,
      ...world,
    });
    return () => engine.destroy();
  }, [world]);

  return (
    <div className="globe-stage">
      <canvas ref={stars} className="globe-stage__stars" aria-hidden="true" />
      <canvas ref={sky} className="globe-stage__sky" aria-hidden="true" />
      <canvas
        ref={globe}
        className="globe-stage__globe"
        role="img"
        aria-label="A night globe of the places visited. Drag to turn it, scroll to zoom."
      />
      <PlaceLabel ref={label} archive={world.archive} />
    </div>
  );
}
```

`src/features/globe/globe.scss`:

```scss
.globe-stage {
  position: fixed;
  inset: 0;
  overflow: hidden;

  canvas {
    position: absolute;
    inset: 0;
    display: block;
  }

  &__stars {
    inset: auto;
    top: -30px;
    left: -30px;
    will-change: transform;
  }

  &__sky {
    pointer-events: none;
  }

  &__globe {
    cursor: grab;
    touch-action: none;
  }
}

.place-label {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 4;
  pointer-events: none;
  white-space: nowrap;
  text-align: center;
  opacity: 0;
  transition: opacity 0.35s ease;

  b {
    display: block;
    font-family: var(--font-family-display);
    font-style: italic;
    font-weight: 500;
    font-size: 20px;
    line-height: 1.1;
    text-shadow: 0 2px 10px rgb(0 0 0 / 80%);
  }

  span {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--lamp);
    text-shadow: 0 1px 6px rgb(0 0 0 / 90%);
  }
}
```

`src/features/header/Header.tsx`:

```tsx
import './header.scss';

export function Header() {
  return (
    <header className="header">
      <div className="header__brand">
        cloudpix<small>every trip I have taken</small>
      </div>
    </header>
  );
}
```

`src/features/header/header.scss`:

```scss
.header {
  position: fixed;
  inset: 0 0 auto;
  z-index: 12;
  display: flex;
  justify-content: space-between;
  padding: max(18px, var(--safe-top)) 24px 0;
  pointer-events: none;

  &__brand {
    padding-top: 5px;
    font-weight: 700;
    font-size: 20px;
    letter-spacing: -0.01em;

    small {
      display: block;
      margin-top: 4px;
      font-weight: 400;
      font-size: 12px;
      letter-spacing: 0;
      color: var(--muted);
    }
  }
}
```

`src/app/App.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { GlobeStage } from '@/features/globe/GlobeStage';
import { Header } from '@/features/header/Header';
import { loadWorld } from './boot';
import type { World } from './boot';
import './app.scss';

type Boot = { status: 'loading' } | { status: 'ready'; world: World } | { status: 'failed' };

export function App() {
  const [boot, setBoot] = useState<Boot>({ status: 'loading' });

  useEffect(() => {
    let live = true;
    loadWorld().then(
      (world) => {
        if (live) setBoot({ status: 'ready', world });
      },
      (error: unknown) => {
        console.error(error);
        if (live) setBoot({ status: 'failed' });
      },
    );
    return () => {
      live = false;
    };
  }, []);

  return (
    <>
      {boot.status === 'ready' && <GlobeStage world={boot.world} />}
      {boot.status === 'loading' && <p className="boot">Loading the map…</p>}
      {boot.status === 'failed' && (
        <div className="boot" role="alert">
          <p>The map did not load.</p>
          <button type="button" onClick={() => location.reload()}>
            Try again
          </button>
        </div>
      )}
      <Header />
    </>
  );
}
```

- [ ] **Step 6: Run the whole check and the build**

Run: `npm run check && npm run build`
Expected: PASS.

- [ ] **Step 7: Check it in the browser**

Run `npm run dev` in the background and open `http://127.0.0.1:3001/` (use the Playwright browser tools if available). Check each line and write down what you saw:

1. The night globe appears on the right of centre with stars, land, borders, faint lights, 22 pale place dots and the small house near Kyiv. The console has no errors.
2. It spins slowly by itself.
3. Drag turns it in any direction, over the poles too. A throw keeps it turning, then it settles into the slow spin.
4. Hovering a place fades in a label with the city, the country and the years (Barcelona: "Spain · 2019 · 2023"), and the cursor becomes a pointer. Moving away fades the label out with its text still in it.
5. Wheel in: at some notch the ball unrolls into a flat map filling the screen in about 1.1 s; drag pans; nothing spins. Wheel out one notch: it rolls back. In the console, `__globe.state()` shows `flat` switching at the same `zTarget` both ways.
6. Wheel all the way out: the ball stops at half its resting size.
7. Every 7–20 s a meteor or a satellite crosses the sky.
8. Resize the window to 390 × 844 (device toolbar): the globe sits lower and centred, the header does not overlap it, the flat map still fills the screen with no gap.
9. In the Performance panel, a 5 s recording while dragging stays near 60 fps on a laptop.
10. With the dev server still running, rename `public/demo/photos.json` for a moment and reload: "The map did not load." and "Try again" show. Rename it back and reload: the globe returns.
11. Stop the dev server. Run `VITE_BASE=/cloudpix-platform/ npm run build && npm run preview`, open `http://127.0.0.1:3001/cloudpix-platform/`: the globe loads, so the demo files resolve under the base path. Stop the preview.

Any line that fails is a bug to fix before the commit — report it with what you saw.

- [ ] **Step 8: Commit**

```bash
git add src/app src/features
git commit -m "feat: show the demo traveller's night globe"
```

---

## After this plan

Plan 2 (timeline, flights, album panel, tours) starts from this branch. It will use: `placeState` and `stepLook` with real facts, `PlaceRuntime.pulseAt`, `camCurve`, `slerp`, `quat`/`euler`, `HomeSprite.lit` and `pulse`, `stepSmoke`/`drawSmoke`, and `appStore` for focus and range.
