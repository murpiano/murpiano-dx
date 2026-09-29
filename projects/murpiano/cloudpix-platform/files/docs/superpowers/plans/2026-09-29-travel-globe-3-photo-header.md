# Travel globe, part 3: photo window, header, keys, world pause — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open a photo large from the album panel (it grows from the cover, browses with arrows, wheel, swipe and a slideshow, shows its story, likes and comments, and flies back on close) while the whole world pauses; add the header (burger menu, stats, the gear with the pace settings and the help lines); and make Esc close the innermost layer.

**Architecture:** Layers (menu, photo window) live in `appStore`; pure functions in `src/state/layers.ts` open, step and close them and decide what Esc closes. Demo likes and comments are seeded stubs (`src/data/social.ts`) kept in memory by `src/state/social.ts`. Stats are a pure function. The photo window is a React component that measures the stage and animates its image with the Web Animations API.

**Tech Stack:** as in parts 1–2.

**Spec:** [`docs/design/2026-09-29-travel-globe.md`](../../design/2026-09-29-travel-globe.md) — sections 3.7, 3.8, 3.9 and "While the window is open, the whole world pauses". Reference: `docs/design/prototype/flight.html` (photo window 1185–1344, CSS 260–315; menu and settings 1830–1873, CSS 23–71).

**Out of this plan:** links into the archive (country, city, album render as plain text; plan 4), the logged-in menu, "Log in" itself and forms (plan 5: the button is there, disabled), closing into an archive grid tile (plan 4 marks its tiles with the same `data-photo-key`).

## Global Constraints

- Branch `feat/travel-globe`; never push to `main`. `npm run check` green after every task. Style as in parts 1–2.
- Photo window: grows from where it was clicked; left column country, city, album, date, the photo's caption, the album's description, credit; right column like toggle with a count, comments (the wheel scrolls them), comment form; ← → buttons and keys, the wheel over the photo one per notch, a swipe, Slideshow with its own speed slider (2–15 s), also Space, an "n / N" counter; the next photo slides in from its side; closing flies back into the tile now showing it; while open the whole world pauses.
- Header: left burger (logged out: "Log in" and a line about the demo); right stats (countries, photos, km flown; in range or so far) and the gear (photo time 2–15 s, flight time 5–90 s, "Show how to use it"), kept per browser.
- Esc closes the innermost layer: form, menu or settings, photo window, archive, focus, range (form and archive come in plans 4–5).
- Keys: ← → albums or photos, ↑ ↓ scroll albums, Space plays or pauses the tour, or the slideshow in the photo window.

## Review Focus

- **Settings kept by an older build or edited by hand** (a string, an out-of-range number) — clamped to the limits, never NaN. Pinned in Task 1 (`cleanSettings`).
- **A photo album with a single photo** — no arrows, no slideshow step, no crash on the wheel. Pinned in Task 2 ("does not step an album of one").
- **Esc with a menu open over the photo window** — the menu closes first, the photo stays. Pinned in Task 2 (`escapeTarget`).
- **An empty or blank comment** — ignored, no empty line added. Pinned in Task 1 (`addComment`).
- **Closing a photo whose tile is gone** (the panel moved on) — the photo fades out instead of flying into nothing. Checked in Task 6 (browser).

---

## File map

Created:

```
src/data/social.ts, social.test.ts        demo likes/comments, album description, photo note
src/data/stats.ts, stats.test.ts          countries, photos, km flown
src/state/layers.ts, layers.test.ts       photo window and menu state, Esc target
src/state/social.ts, social.test.ts       likes and comments kept in memory
src/lib/useInterval.ts                    world- or real-clock interval hook (moved from panel)
src/features/lightbox/fit.ts, fit.test.ts contain-fit and fly transforms
src/features/lightbox/Lightbox.tsx, lightbox.scss
src/features/header/Header.tsx (rewritten), header.scss (rewritten)
```

Modified: `src/state/settings.ts` (+test), `src/state/app-state.ts`, `src/features/panel/AlbumPanel.tsx` (open the photo, `data-photo-key`, new interval import), `src/app/Stage.tsx`, `src/app/App.tsx`, `src/features/keys/useKeys.ts`. Deleted: `src/features/panel/useWorldInterval.ts`.

---

### Task 1: Social stubs, stats, settings limits

**Files:**
- Create: `src/data/social.ts`, `src/data/stats.ts`
- Modify: `src/state/settings.ts`, `src/state/settings.test.ts`
- Test: `src/data/social.test.ts`, `src/data/stats.test.ts`

**Interfaces:**
- Produces:
  - `interface Comment { who: string; text: string; when: string }`, `interface Social { liked: boolean; likes: number; comments: Comment[] }`
  - `photoKey(photo: PhotoRef): string`, `demoSocial(key: string): Social`, `toggleLike(social: Social): Social`, `addComment(social: Social, text: string): Social`, `describeAlbum(album: Album): string`, `photoNote(photo: PhotoRef): string`
  - `interface Stats { countries; totalCountries; photos; km; scope: 'all' | 'range' | 'so far' }`, `journeyStats(archive, times, range, focus): Stats`
  - `Settings` gains `slideSeconds: number` (default 4); `cleanSettings(raw: unknown): Settings`

- [ ] **Step 1: Write the failing tests**

`src/data/social.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { linkArchive } from './archive';
import { addComment, demoSocial, describeAlbum, photoKey, photoNote, toggleLike } from './social';

const archive = linkArchive({
  countries: [
    {
      id: '250',
      name: 'France',
      cities: [
        {
          key: 'paris',
          name: 'Paris',
          lat: 48.86,
          lon: 2.35,
          albums: [
            {
              id: 'a',
              title: 'Paris again',
              year: 2022,
              month: 4,
              day: 3,
              time: '10:00',
              photoCount: 35,
              photos: [],
            },
          ],
        },
      ],
    },
  ],
  trips: [],
});

describe('demo social', () => {
  it('looks lived in and is the same on every visit', () => {
    const social = demoSocial('w-paris-0.jpg');
    expect(social).toEqual(demoSocial('w-paris-0.jpg'));
    expect(social.liked).toBe(false);
    expect(social.likes).toBeGreaterThanOrEqual(12);
    expect(social.likes).toBeLessThan(242);
    expect(social.comments.length).toBeGreaterThanOrEqual(1);
    expect(social.comments.length).toBeLessThanOrEqual(4);
  });

  it('toggles a like and counts it', () => {
    const social = demoSocial('x');
    const liked = toggleLike(social);
    expect(liked.liked).toBe(true);
    expect(liked.likes).toBe(social.likes + 1);
    expect(toggleLike(liked)).toEqual(social);
  });

  it('adds a comment from you, and ignores a blank one', () => {
    const social = demoSocial('x');
    const next = addComment(social, '  Lovely  ');
    expect(next.comments.at(-1)).toEqual({ who: 'You', text: 'Lovely', when: 'just now' });
    expect(addComment(social, '   ')).toBe(social);
  });
});

describe('texts', () => {
  it('describes an album', () => {
    const album = archive.albums[0];
    if (!album) throw new Error('no album');
    expect(describeAlbum(album)).toMatch(/^35 photos from Paris, Apr 2022\. \S/);
  });

  it('keys photos and prefers the owner caption', () => {
    expect(photoKey({ kind: 'stock', file: 'a.jpg' })).toBe('a.jpg');
    expect(photoKey({ kind: 'own', id: 'u1', name: 'b.jpg' })).toBe('u1');
    expect(photoNote({ kind: 'stock', file: 'a.jpg', caption: 'Mine' })).toBe('Mine');
    expect(photoNote({ kind: 'stock', file: 'a.jpg' }).length).toBeGreaterThan(5);
  });
});
```

`src/data/stats.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { albumTime, yearRange } from '@/timeline/range';
import { linkArchive } from './archive';
import { buildDemo } from './demo';
import { journeyStats } from './stats';
import type { Credit } from './types';

const file = fileURLToPath(new URL('../../public/demo/photos.json', import.meta.url));
const archive = linkArchive(buildDemo(JSON.parse(readFileSync(file, 'utf8')) as Credit[]));
const times = archive.albums.map(albumTime);
const allPhotos = archive.albums.reduce((sum, a) => sum + a.photoCount, 0);

describe('journeyStats', () => {
  it('counts everything with nothing picked', () => {
    const stats = journeyStats(archive, times, null, -1);
    expect(stats.scope).toBe('all');
    expect(stats.countries).toBe(12);
    expect(stats.totalCountries).toBe(12);
    expect(stats.photos).toBe(allPhotos);
    expect(stats.km).toBeGreaterThan(50000);
  });

  it('counts what is in the range', () => {
    const stats = journeyStats(archive, times, yearRange(2023), 5);
    expect(stats.scope).toBe('range');
    expect(stats.countries).toBe(2);
  });

  it('counts so far, up to the album in focus', () => {
    const stats = journeyStats(archive, times, null, 0);
    expect(stats.scope).toBe('so far');
    expect(stats.countries).toBe(1);
    expect(stats.km).toBe(0);
    expect(stats.photos).toBe(archive.albums[0]?.photoCount);
  });
});
```

Append to `src/state/settings.test.ts`:

```ts
describe('cleanSettings', () => {
  it('keeps good values and clamps the rest to their limits', () => {
    expect(cleanSettings({ photoSeconds: 7, flightSeconds: 45, slideSeconds: 3, help: false })).toEqual({
      photoSeconds: 7,
      flightSeconds: 45,
      slideSeconds: 3,
      help: false,
    });
    expect(cleanSettings({ photoSeconds: 99, flightSeconds: 1, slideSeconds: -4 })).toMatchObject({
      photoSeconds: 15,
      flightSeconds: 5,
      slideSeconds: 2,
    });
  });

  it('falls back to the defaults for anything broken', () => {
    expect(cleanSettings({ flightSeconds: 'x', photoSeconds: NaN, help: 'yes' })).toEqual(
      DEFAULT_SETTINGS,
    );
    expect(cleanSettings(null)).toEqual(DEFAULT_SETTINGS);
  });
});
```

and change its import line to `import { cleanSettings, DEFAULT_SETTINGS, settingsStore } from './settings';` and the first test's expected defaults to `{ photoSeconds: 5, flightSeconds: 30, slideSeconds: 4, help: true }`.

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/data/social.test.ts src/data/stats.test.ts src/state/settings.test.ts`
Expected: FAIL — `./social`, `./stats` not found; `cleanSettings` is not a function.

- [ ] **Step 3: Implement**

`src/data/social.ts`:

```ts
import { monthYear } from '@/lib/dates';
import { seedOf } from './order';
import type { Album, PhotoRef } from './types';

export interface Comment {
  who: string;
  text: string;
  when: string;
}

export interface Social {
  liked: boolean;
  likes: number;
  comments: Comment[];
}

const NOTES = [
  'Mostly mornings, before the crowds.',
  'Shot on a phone and an old 35 mm camera.',
  'Three days of rain, then one afternoon of light.',
  'Walked everywhere; the feet still remember.',
  'A short trip that felt long, in the good way.',
  'Friends, late dinners, too many photos of doors.',
];
const PEOPLE = ['Mira', 'Tom', 'Aiko', 'Lucas', 'Nadia', 'Oskar', 'Leila', 'Sam'];
const LINES = [
  'This light!',
  'I want to go back here.',
  'Is this from the same morning?',
  'The colours are unreal.',
  'Adding it to my list.',
  'Remember the rain that day?',
  'Beautiful frame.',
  'Where exactly is this?',
];
const PHOTO_NOTES = [
  'Early light over the rooftops.',
  'The street we kept coming back to.',
  'Nobody else around, for a minute.',
  'Taken on the walk back.',
  'The view from our window.',
  'Waiting for the tram.',
  'Last evening there.',
  'Found this by getting lost.',
];

const pick = (list: readonly string[], n: number): string => list[n % list.length] ?? '';

export const photoKey = (photo: PhotoRef): string =>
  photo.kind === 'stock' ? photo.file : photo.id;

/** Likes and comments are local stubs until the backend exists, seeded per photo. */
export const demoSocial = (key: string): Social => {
  const seed = seedOf(key);
  return {
    liked: false,
    likes: 12 + (seed % 230),
    comments: Array.from({ length: 1 + (seed % 4) }, (_, i) => ({
      who: pick(PEOPLE, seed >>> (i * 3)),
      text: pick(LINES, seed >>> (i * 2 + 1)),
      when: `${1 + ((seed >>> i) % 20)} days ago`,
    })),
  };
};

export const toggleLike = (social: Social): Social => ({
  ...social,
  liked: !social.liked,
  likes: social.likes + (social.liked ? -1 : 1),
});

export const addComment = (social: Social, text: string): Social => {
  const line = text.trim();
  if (!line) return social;
  return { ...social, comments: [...social.comments, { who: 'You', text: line, when: 'just now' }] };
};

/** The album's description: demo text until the owner writes one. */
export const describeAlbum = (album: Album): string =>
  `${album.photoCount} photo${album.photoCount === 1 ? '' : 's'} from ${album.city.name}, ${monthYear(album)}. ${pick(NOTES, seedOf(album.title))}`;

/** The photo's own line: the owner's caption, otherwise a demo line. */
export const photoNote = (photo: PhotoRef): string =>
  photo.caption ?? pick(PHOTO_NOTES, seedOf(photoKey(photo)));
```

`src/data/stats.ts`:

```ts
import { geoDistance } from 'd3-geo';
import { within } from '@/timeline/range';
import type { Range } from '@/timeline/range';
import { EARTH_KM } from '@/tour/flight';
import type { Archive } from './archive';

export interface Stats {
  countries: number;
  totalCountries: number;
  photos: number;
  km: number;
  /** What is counted: everything, the picked range, or the albums up to the one in focus. */
  scope: 'all' | 'range' | 'so far';
}

/** The header's stats: countries, photos and km flown, in the range or so far. */
export const journeyStats = (
  archive: Archive,
  times: readonly number[],
  range: Range | null,
  focus: number,
): Stats => {
  const seen = range
    ? archive.albums.filter((_, i) => within(times[i] ?? 0, range))
    : focus < 0
      ? archive.albums
      : archive.albums.slice(0, focus + 1);
  let km = 0;
  for (let k = 1; k < seen.length; k++) {
    const a = seen[k - 1]?.city;
    const b = seen[k]?.city;
    if (a && b) km += geoDistance([a.lon, a.lat], [b.lon, b.lat]) * EARTH_KM;
  }
  return {
    countries: new Set(seen.map((album) => album.city.country.id)).size,
    totalCountries: archive.countries.filter((c) => c.cities.some((city) => city.albums.length > 0))
      .length,
    photos: seen.reduce((sum, album) => sum + album.photoCount, 0),
    km: Math.round(km),
    scope: range ? 'range' : focus < 0 ? 'all' : 'so far',
  };
};
```

`src/state/settings.ts`:

```ts
import { readJSON, writeJSON } from '@/lib/storage';
import { clamp } from '@/lib/math';
import { createStore } from './store';

/** The pace of the main screen, kept per browser. */
export interface Settings {
  /** Each photo on the main screen, 2–15 s. */
  photoSeconds: number;
  /** Each flight, 5–90 s. */
  flightSeconds: number;
  /** Each photo of the slideshow in the photo window, 2–15 s. */
  slideSeconds: number;
  /** "Show how to use it". */
  help: boolean;
}

export const DEFAULT_SETTINGS: Settings = {
  photoSeconds: 5,
  flightSeconds: 30,
  slideSeconds: 4,
  help: true,
};

export const SETTING_LIMITS = {
  photoSeconds: [2, 15],
  flightSeconds: [5, 90],
  slideSeconds: [2, 15],
} as const;

/** Whatever was kept (maybe by an older build, maybe edited by hand), made safe to use. */
export const cleanSettings = (raw: unknown): Settings => {
  const kept = typeof raw === 'object' && raw !== null ? (raw as Record<string, unknown>) : {};
  const seconds = (key: keyof typeof SETTING_LIMITS): number => {
    const value = kept[key];
    const [lo, hi] = SETTING_LIMITS[key];
    return typeof value === 'number' && Number.isFinite(value)
      ? clamp(Math.round(value), lo, hi)
      : DEFAULT_SETTINGS[key];
  };
  return {
    photoSeconds: seconds('photoSeconds'),
    flightSeconds: seconds('flightSeconds'),
    slideSeconds: seconds('slideSeconds'),
    help: typeof kept.help === 'boolean' ? kept.help : DEFAULT_SETTINGS.help,
  };
};

export const settingsStore = createStore<Settings>(cleanSettings(readJSON<unknown>('settings', {})));

settingsStore.subscribe(() => writeJSON('settings', settingsStore.get()));
```

- [ ] **Step 4: Run the tests and the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data src/state/settings.ts src/state/settings.test.ts
git commit -m "feat: add demo likes and comments, journey stats and safe settings"
```

---

### Task 2: Layers: the photo window, the menus, what Esc closes

**Files:**
- Modify: `src/state/app-state.ts`
- Create: `src/state/layers.ts`, `src/state/social.ts`
- Test: `src/state/layers.test.ts`, `src/state/social.test.ts`

**Interfaces:**
- Produces:
  - `interface Rect { x: number; y: number; width: number; height: number }`
  - `interface PhotoView { albumId: string; index: number; previous: number | null; dir: -1 | 0 | 1; from: Rect | null; slideshow: boolean; closing: boolean }`
  - `AppState` gains `photo: PhotoView | null`, `menu: 'nav' | 'settings' | null`
  - `openPhoto(store, albumId, index, from)`, `stepPhoto(store, count, by)`, `toggleSlideshow(store)`, `closePhoto(store)`, `finishPhoto(store)`, `toggleMenu(store, menu)`, `type EscapeTarget = 'menu' | 'photo' | 'journey'`, `escapeTarget(state): EscapeTarget`
  - `socialStore`, `socialFor(key: string): Social`, `likePhoto(key)`, `commentPhoto(key, text)`

- [ ] **Step 1: Extend the app state**

In `src/state/app-state.ts` add before `AppState`:

```ts
export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** The photo window: which photo of which album, and how it got there. */
export interface PhotoView {
  albumId: string;
  index: number;
  /** The photo it came from, sliding away under the new one. */
  previous: number | null;
  /** The side the photo came from: 1 next, -1 previous, 0 opened. */
  dir: -1 | 0 | 1;
  /** Where it was clicked, to grow out of it. */
  from: Rect | null;
  slideshow: boolean;
  /** Flying back into its tile; the window goes when the flight ends. */
  closing: boolean;
}
```

add to `AppState`:

```ts
  /** The photo window, open over everything. */
  photo: PhotoView | null;
  /** The burger menu or the settings, open under the header. */
  menu: 'nav' | 'settings' | null;
```

and to `INITIAL_STATE`: `photo: null, menu: null,`.

- [ ] **Step 2: Write the failing tests**

`src/state/layers.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { INITIAL_STATE } from './app-state';
import type { AppState } from './app-state';
import {
  closePhoto,
  escapeTarget,
  finishPhoto,
  openPhoto,
  stepPhoto,
  toggleMenu,
  toggleSlideshow,
} from './layers';
import { createStore } from './store';

const setup = () => createStore<AppState>({ ...INITIAL_STATE });
const FROM = { x: 10, y: 20, width: 300, height: 200 };

describe('the photo window', () => {
  it('opens over everything, closes the menus and pauses the world', () => {
    const store = setup();
    toggleMenu(store, 'nav');
    openPhoto(store, 'paris/x', 1, FROM);
    expect(store.get().photo).toEqual({
      albumId: 'paris/x',
      index: 1,
      previous: null,
      dir: 0,
      from: FROM,
      slideshow: false,
      closing: false,
    });
    expect(store.get().menu).toBeNull();
    expect(store.get().paused).toBe(true);
  });

  it('steps through the album in a loop and remembers where it came from', () => {
    const store = setup();
    openPhoto(store, 'a', 0, null);
    stepPhoto(store, 3, -1);
    expect(store.get().photo).toMatchObject({ index: 2, previous: 0, dir: -1 });
    stepPhoto(store, 3, 2);
    expect(store.get().photo).toMatchObject({ index: 1, previous: 2, dir: 1 });
  });

  it('does not step an album of one', () => {
    const store = setup();
    openPhoto(store, 'a', 0, null);
    stepPhoto(store, 1, 1);
    expect(store.get().photo).toMatchObject({ index: 0, previous: null });
  });

  it('toggles the slideshow', () => {
    const store = setup();
    openPhoto(store, 'a', 0, null);
    toggleSlideshow(store);
    expect(store.get().photo?.slideshow).toBe(true);
    toggleSlideshow(store);
    expect(store.get().photo?.slideshow).toBe(false);
  });

  it('flies back before it goes, and the world resumes once it is gone', () => {
    const store = setup();
    openPhoto(store, 'a', 0, null);
    toggleSlideshow(store);
    closePhoto(store);
    expect(store.get().photo).toMatchObject({ closing: true, slideshow: false });
    expect(store.get().paused).toBe(true);
    finishPhoto(store);
    expect(store.get().photo).toBeNull();
    expect(store.get().paused).toBe(false);
  });
});

describe('menus', () => {
  it('opens one menu at a time', () => {
    const store = setup();
    toggleMenu(store, 'nav');
    toggleMenu(store, 'settings');
    expect(store.get().menu).toBe('settings');
    toggleMenu(store, 'settings');
    expect(store.get().menu).toBeNull();
  });
});

describe('escapeTarget', () => {
  it('closes the innermost layer first', () => {
    const store = setup();
    expect(escapeTarget(store.get())).toBe('journey');
    openPhoto(store, 'a', 0, null);
    expect(escapeTarget(store.get())).toBe('photo');
    store.set({ menu: 'settings' });
    expect(escapeTarget(store.get())).toBe('menu');
  });
});
```

`src/state/social.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { demoSocial } from '@/data/social';
import { commentPhoto, likePhoto, socialFor } from './social';

describe('social store', () => {
  it('starts every photo from its demo stub and keeps what you do', () => {
    expect(socialFor('p.jpg')).toEqual(demoSocial('p.jpg'));
    likePhoto('p.jpg');
    commentPhoto('p.jpg', 'Wow');
    const social = socialFor('p.jpg');
    expect(social.liked).toBe(true);
    expect(social.comments.at(-1)?.text).toBe('Wow');
    expect(socialFor('q.jpg').liked).toBe(false);
  });
});
```

- [ ] **Step 3: Run them to see them fail**

Run: `npx vitest run src/state/layers.test.ts src/state/social.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 4: Implement**

`src/state/layers.ts`:

```ts
import type { AppState, Rect } from './app-state';
import type { Store } from './store';

type AppStore = Store<AppState>;

/** The world clock stops while the photo window is open (and the archive, in plan 4). */
const pausedFor = (state: AppState): boolean => state.photo !== null;

export const openPhoto = (store: AppStore, albumId: string, index: number, from: Rect | null) => {
  store.set({
    photo: { albumId, index, previous: null, dir: 0, from, slideshow: false, closing: false },
    menu: null,
  });
  store.set({ paused: pausedFor(store.get()) });
};

/** The next (by > 0) or previous photo of the album, in a loop. */
export const stepPhoto = (store: AppStore, count: number, by: number) => {
  const photo = store.get().photo;
  if (!photo || photo.closing || count < 2 || by === 0) return;
  const index = (((photo.index + by) % count) + count) % count;
  store.set({ photo: { ...photo, index, previous: photo.index, dir: by > 0 ? 1 : -1 } });
};

export const toggleSlideshow = (store: AppStore) => {
  const photo = store.get().photo;
  if (!photo || photo.closing) return;
  store.set({ photo: { ...photo, slideshow: !photo.slideshow } });
};

/** Starts the flight back into the tile; `finishPhoto` ends it. */
export const closePhoto = (store: AppStore) => {
  const photo = store.get().photo;
  if (!photo || photo.closing) return;
  store.set({ photo: { ...photo, closing: true, slideshow: false } });
};

export const finishPhoto = (store: AppStore) => {
  store.set({ photo: null });
  store.set({ paused: pausedFor(store.get()) });
};

export const toggleMenu = (store: AppStore, menu: 'nav' | 'settings') => {
  store.set({ menu: store.get().menu === menu ? null : menu });
};

/** What Esc closes, innermost first: form (plan 5), menu, photo, archive (plan 4), the journey. */
export type EscapeTarget = 'menu' | 'photo' | 'journey';

export const escapeTarget = (state: AppState): EscapeTarget =>
  state.menu ? 'menu' : state.photo ? 'photo' : 'journey';
```

`src/state/social.ts`:

```ts
import { addComment, demoSocial, toggleLike } from '@/data/social';
import type { Social } from '@/data/social';
import { createStore } from './store';

/** Likes and comments while the page is open. Nothing is saved: they are stubs until the backend. */
export const socialStore = createStore<{ byKey: ReadonlyMap<string, Social> }>({ byKey: new Map() });

export const socialFor = (key: string): Social =>
  socialStore.get().byKey.get(key) ?? demoSocial(key);

const update = (key: string, change: (social: Social) => Social) => {
  const byKey = new Map(socialStore.get().byKey);
  byKey.set(key, change(socialFor(key)));
  socialStore.set({ byKey });
};

export const likePhoto = (key: string) => update(key, toggleLike);

export const commentPhoto = (key: string, text: string) =>
  update(key, (social) => addComment(social, text));
```

- [ ] **Step 5: Run the tests and the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/state
git commit -m "feat(state): add the photo window and menu layers and the social stubs"
```

---

### Task 3: The header

**Files:**
- Rewrite: `src/features/header/Header.tsx`, `src/features/header/header.scss`
- Modify: `src/app/App.tsx`

**Interfaces:**
- Consumes: `journeyStats` (Task 1), `toggleMenu` (Task 2), `settingsStore`, `SETTING_LIMITS`, `albumTime`.
- Produces: `Header({ world }: { world: World | null })`.

- [ ] **Step 1: Write the header**

`src/features/header/Header.tsx`:

```tsx
import { useEffect, useMemo, useRef } from 'react';
import type { World } from '@/app/boot';
import { journeyStats } from '@/data/stats';
import { appStore } from '@/state/app-state';
import { toggleMenu } from '@/state/layers';
import { SETTING_LIMITS, settingsStore } from '@/state/settings';
import type { Settings } from '@/state/settings';
import { useStore } from '@/state/store';
import { albumTime } from '@/timeline/range';
import './header.scss';

/** The burger and the brand on the left; the stats and the gear on the right. */
export function Header({ world }: { world: World | null }) {
  const menu = useStore(appStore, (s) => s.menu);
  const help = useStore(settingsStore, (s) => s.help);
  const root = useRef<HTMLElement>(null);

  // a press anywhere outside the header closes the open menu
  useEffect(() => {
    if (!menu) return;
    const onDown = (event: PointerEvent) => {
      if (event.target instanceof Node && root.current?.contains(event.target)) return;
      appStore.set({ menu: null });
    };
    addEventListener('pointerdown', onDown);
    return () => removeEventListener('pointerdown', onDown);
  }, [menu]);

  return (
    <header ref={root} className="header">
      <div className="header__lead">
        <button
          type="button"
          className={`header__round header__burger${menu === 'nav' ? ' is-on' : ''}`}
          aria-label="Menu"
          aria-expanded={menu === 'nav'}
          onClick={() => toggleMenu(appStore, 'nav')}
        >
          <span />
          <span />
          <span />
        </button>
        <div className="header__brand">
          cloudpix<small>every trip I have taken</small>
        </div>
      </div>

      {world && (
        <div className="header__side">
          <div className="header__row">
            <Stats world={world} />
            <button
              type="button"
              className={`header__round header__gear${menu === 'settings' ? ' is-on' : ''}`}
              aria-label="Settings"
              aria-expanded={menu === 'settings'}
              onClick={() => toggleMenu(appStore, 'settings')}
            >
              ⚙
            </button>
          </div>
          <p className={`header__help${help ? '' : ' is-off'}`}>
            <b>Drag</b> and let go to spin · <b>scroll</b> to zoom · <b>click</b> a light
            <br />
            <b>Timeline:</b> drag for a range · click for all up to a point
            <br />a <b>year</b> picks the year, again opens it · <b>Esc</b> lets go
          </p>
        </div>
      )}

      <nav className={`header__menu header__nav${menu === 'nav' ? ' is-on' : ''}`} inert={menu !== 'nav'}>
        {/* logging in comes with the owner mode (plan 5) */}
        <button type="button" className="header__item is-primary" disabled>
          Log in
        </button>
        <p>You are watching a demo traveller. Log in to keep your own trips, albums and photos.</p>
      </nav>

      {world && <SettingsMenu open={menu === 'settings'} />}
    </header>
  );
}

function Stats({ world }: { world: World }) {
  const range = useStore(appStore, (s) => s.range);
  const focus = useStore(appStore, (s) => s.focus);
  const times = useMemo(() => world.archive.albums.map(albumTime), [world]);
  const stats = useMemo(
    () => journeyStats(world.archive, times, range, focus),
    [world, times, range, focus],
  );
  const note = stats.scope === 'range' ? ' in range' : stats.scope === 'so far' ? ' so far' : '';
  return (
    <div className="header__stats">
      <b>{stats.countries}</b> of {stats.totalCountries} countries{note}
      <br />
      <b>{stats.photos.toLocaleString('en')}</b> photos · <b>{stats.km.toLocaleString('en')}</b> km
      flown
    </div>
  );
}

const SLIDERS: { key: 'photoSeconds' | 'flightSeconds'; label: string; step: number }[] = [
  { key: 'photoSeconds', label: 'Each photo', step: 1 },
  { key: 'flightSeconds', label: 'Each flight', step: 5 },
];

function SettingsMenu({ open }: { open: boolean }) {
  const settings = useStore(settingsStore, (s) => s);
  const change = (patch: Partial<Settings>) => settingsStore.set(patch);
  return (
    <div className={`header__menu header__settings${open ? ' is-on' : ''}`} inert={!open}>
      <h4>On the main screen</h4>
      {SLIDERS.map(({ key, label, step }) => (
        <label key={key}>
          <div>
            {label} <output>{settings[key]} s</output>
          </div>
          <input
            type="range"
            min={SETTING_LIMITS[key][0]}
            max={SETTING_LIMITS[key][1]}
            step={step}
            value={settings[key]}
            onChange={(event) => change({ [key]: Number(event.target.value) })}
          />
        </label>
      ))}
      <label className="header__check">
        <input
          type="checkbox"
          checked={settings.help}
          onChange={(event) => change({ help: event.target.checked })}
        />{' '}
        Show how to use it
      </label>
    </div>
  );
}
```

`src/features/header/header.scss` (ported from the prototype, lines 23–71 and the mobile rules):

```scss
.header {
  position: fixed;
  inset: 0 0 auto;
  z-index: 12;
  display: flex;
  justify-content: space-between;
  padding: max(18px, var(--safe-top)) 24px 0;
  pointer-events: none;

  &__lead {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }

  &__round {
    width: 38px;
    height: 38px;
    border: 1px solid rgb(127 137 163 / 35%);
    border-radius: 50%;
    background: rgb(12 16 30 / 60%);
    color: var(--text);
    pointer-events: auto;
    transition:
      border-color 0.3s,
      background 0.3s,
      transform 0.6s var(--ease);

    &:hover,
    &.is-on {
      border-color: rgb(255 200 107 / 60%);
    }
  }

  &__burger {
    display: grid;
    gap: 4px;
    place-content: center;

    span {
      display: block;
      width: 14px;
      height: 1.5px;
      border-radius: 1px;
      background: var(--text);
      transition:
        transform 0.4s var(--ease),
        opacity 0.3s;
    }

    &.is-on span:nth-child(1) {
      transform: translateY(5.5px) rotate(45deg);
    }

    &.is-on span:nth-child(2) {
      opacity: 0;
    }

    &.is-on span:nth-child(3) {
      transform: translateY(-5.5px) rotate(-45deg);
    }
  }

  &__gear {
    font-size: 17px;
    line-height: 1;

    &.is-on {
      transform: rotate(90deg);
    }
  }

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

  &__side {
    display: flex;
    flex-direction: column;
    gap: 10px;
    align-items: flex-end;
  }

  &__row {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }

  &__stats {
    padding-top: 2px;
    font-size: 12px;
    line-height: 1.6;
    text-align: right;
    color: var(--muted);

    b {
      font-weight: 500;
      color: var(--text);
    }
  }

  &__help {
    margin: 0;
    font-size: 11px;
    line-height: 1.7;
    text-align: right;
    color: var(--muted);
    transition: opacity 0.4s;

    b {
      font-weight: 500;
      color: var(--text);
    }

    &.is-off {
      opacity: 0;
    }
  }

  &__menu {
    position: fixed;
    top: calc(max(18px, var(--safe-top)) + 48px);
    left: 24px;
    z-index: 13;
    width: 280px;
    padding: 18px 18px 8px;
    border-radius: 16px;
    background: rgb(12 16 30 / 94%);
    box-shadow:
      0 24px 60px rgb(0 0 0 / 55%),
      0 0 0 1px rgb(255 255 255 / 7%);
    backdrop-filter: blur(10px);
    opacity: 0;
    transform: translateY(-8px);
    pointer-events: none;
    transition:
      opacity 0.35s ease,
      transform 0.45s var(--ease);

    &.is-on {
      opacity: 1;
      transform: none;
      pointer-events: auto;
    }

    h4 {
      margin: 0 0 14px;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--muted);
    }

    label {
      display: block;
      margin-bottom: 16px;
      font-size: 13px;

      div {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
      }
    }

    output {
      color: var(--lamp);
    }

    input[type='range'] {
      width: 100%;
      accent-color: var(--lamp);
    }
  }

  &__settings {
    right: 24px;
    left: auto;
  }

  &__check {
    display: flex !important;
    gap: 10px;
    align-items: center;

    input {
      width: 16px;
      height: 16px;
      accent-color: var(--lamp);
    }
  }

  &__nav {
    width: 260px;
    padding: 12px 10px;

    p {
      margin: 0;
      padding: 6px 10px 4px;
      font-size: 12px;
      line-height: 1.5;
      color: var(--muted);
    }
  }

  &__item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 10px;
    border: 0;
    border-radius: 10px;
    background: none;
    font-size: 14px;
    text-align: left;

    &.is-primary {
      justify-content: center;
      margin: 4px 0 8px;
      background: var(--lamp);
      font-weight: 500;
      color: #1a1406;
    }

    &:disabled {
      opacity: 0.55;
      cursor: default;
    }
  }

  @include mobile {
    padding-inline: 16px;

    &__stats,
    &__help {
      display: none;
    }

    &__menu {
      left: 16px;
      width: calc(100vw - 32px);
    }

    &__settings {
      right: 16px;
      left: 16px;
      width: auto;
    }
  }
}
```

`src/app/App.tsx`: render `<Header world={boot.status === 'ready' ? boot.world : null} />` in place of `<Header />`.

- [ ] **Step 2: Run the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/features/header src/app/App.tsx
git commit -m "feat(header): add the menu, the stats, the pace settings and the help lines"
```

---

### Task 4: The photo window

**Files:**
- Create: `src/lib/useInterval.ts`, `src/features/lightbox/fit.ts`, `src/features/lightbox/Lightbox.tsx`, `src/features/lightbox/lightbox.scss`
- Delete: `src/features/panel/useWorldInterval.ts`
- Modify: `src/features/panel/AlbumPanel.tsx`, `src/app/Stage.tsx`
- Test: `src/features/lightbox/fit.test.ts`

**Interfaces:**
- Consumes: Tasks 1–2, `wheelSteps` (`src/features/panel/stack.ts`), `creditLine`, `photoUrl`, `monthYear`.
- Produces: `useInterval(callback, ms, active, resetKey, clock?: 'world' | 'real')`, `fitRect(box: Rect, aspect: number): Rect`, `flyTransform(from: Rect, to: Rect): string`, `Lightbox({ world })`; album cards open the photo and mark their shown image with `data-photo-key`.

- [ ] **Step 1: Write the failing test**

`src/features/lightbox/fit.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { fitRect, flyTransform } from './fit';

describe('fitRect', () => {
  it('fits a wide photo to the width, centred', () => {
    expect(fitRect({ x: 100, y: 50, width: 800, height: 600 }, 2)).toEqual({
      x: 100,
      y: 150,
      width: 800,
      height: 400,
    });
  });

  it('fits a tall photo to the height, centred', () => {
    expect(fitRect({ x: 0, y: 0, width: 800, height: 600 }, 0.5)).toEqual({
      x: 250,
      y: 0,
      width: 300,
      height: 600,
    });
  });
});

describe('flyTransform', () => {
  it('moves and scales a box onto another from its top-left corner', () => {
    expect(
      flyTransform({ x: 100, y: 100, width: 400, height: 200 }, { x: 10, y: 20, width: 200, height: 50 }),
    ).toBe('translate(-90px, -80px) scale(0.5, 0.25)');
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/features/lightbox/fit.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the helpers and move the interval hook**

`src/features/lightbox/fit.ts`:

```ts
import type { Rect } from '@/state/app-state';

/** The largest box of the given aspect (width / height) that fits in `box`, centred. */
export const fitRect = (box: Rect, aspect: number): Rect => {
  let width = box.width;
  let height = width / aspect;
  if (height > box.height) {
    height = box.height;
    width = height * aspect;
  }
  return { x: box.x + (box.width - width) / 2, y: box.y + (box.height - height) / 2, width, height };
};

/** The transform (origin at the top-left) that lays `from` over `to`. */
export const flyTransform = (from: Rect, to: Rect): string =>
  `translate(${to.x - from.x}px, ${to.y - from.y}px) scale(${to.width / from.width}, ${to.height / from.height})`;
```

`src/lib/useInterval.ts` (replaces `src/features/panel/useWorldInterval.ts`):

```ts
import { useEffect, useRef } from 'react';
import { frameStep } from '@/engine/clock';
import { tickInterval } from '@/lib/interval';
import { appStore } from '@/state/app-state';

/**
 * Calls back every `ms` while `active`, and starts over when `resetKey` changes. On the world
 * clock it waits while the world is paused; on the real clock (the slideshow) it does not.
 */
export const useInterval = (
  callback: () => void,
  ms: number,
  active: boolean,
  resetKey: unknown,
  clock: 'world' | 'real' = 'world',
): void => {
  const saved = useRef(callback);
  useEffect(() => {
    saved.current = callback;
  });

  useEffect(() => {
    if (!active) return;
    let elapsed = 0;
    let last: number | null = null;
    let id = 0;
    const frame = (time: number) => {
      const { dt } = frameStep(time, last, clock === 'world' && appStore.get().paused);
      last = time;
      const [next, fired] = tickInterval(elapsed, dt, ms);
      elapsed = next;
      if (fired) saved.current();
      id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(id);
  }, [ms, active, resetKey, clock]);
};
```

```bash
git rm -q src/features/panel/useWorldInterval.ts
```

- [ ] **Step 4: Open the photo from the album card**

In `src/features/panel/AlbumPanel.tsx`:

1. Replace `import { useWorldInterval } from './useWorldInterval';` with `import { useInterval } from '@/lib/useInterval';`, and the call `useWorldInterval(` with `useInterval(`.
2. Add imports: `import { photoKey } from '@/data/social';` and `import { openPhoto } from '@/state/layers';`.
3. In `AlbumStack`, pass to each `AlbumCard` a new prop:

```tsx
            onOpen={
              role === 'cur'
                ? (photoIndex: number, element: HTMLElement) => {
                    const { x, y, width, height } = element.getBoundingClientRect();
                    openPhoto(appStore, album.id, photoIndex, { x, y, width, height });
                  }
                : undefined
            }
```

4. `AlbumCard` takes `onOpen: ((photoIndex: number, element: HTMLElement) => void) | undefined`, and its root becomes:

```tsx
    <div
      className={`card card--${role}`}
      onClick={(event) => {
        if (onOpen && on >= 0) onOpen(on, event.currentTarget);
        else onSelect?.();
      }}
    >
```

5. The shown image carries the photo's key, so the window can fly back into it:

```tsx
          <img
            key={i}
            src={photoUrl(ref) ?? undefined}
            alt=""
            draggable={false}
            data-photo-key={i === on ? photoKey(ref) : undefined}
            className={i === on ? 'is-on' : i === under ? 'is-under' : undefined}
          />
```

- [ ] **Step 5: Write the photo window**

`src/features/lightbox/Lightbox.tsx`:

```tsx
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { World } from '@/app/boot';
import { creditLine, photoUrl } from '@/data/photos';
import { describeAlbum, photoKey, photoNote } from '@/data/social';
import type { Album } from '@/data/types';
import { wheelSteps } from '@/features/panel/stack';
import { monthYear } from '@/lib/dates';
import { useInterval } from '@/lib/useInterval';
import { appStore } from '@/state/app-state';
import type { PhotoView, Rect } from '@/state/app-state';
import { closePhoto, finishPhoto, stepPhoto, toggleSlideshow } from '@/state/layers';
import { SETTING_LIMITS, settingsStore } from '@/state/settings';
import { commentPhoto, likePhoto, socialFor, socialStore } from '@/state/social';
import { useStore } from '@/state/store';
import { fitRect, flyTransform } from './fit';
import './lightbox.scss';

const ZOOM_MS = 800;
const SLIDE_MS = 700;
const SLIDE_PX = 70;
const SWIPE_PX = 40;
const EASE = 'cubic-bezier(0.2, 0.8, 0.2, 1)';

/** The photo window: the photo large, its story on the left, likes and comments on the right. */
export function Lightbox({ world }: { world: World }) {
  const photo = useStore(appStore, (s) => s.photo);
  const album = photo ? world.archive.albumById.get(photo.albumId) : undefined;
  if (!photo || !album) return null;
  return <PhotoWindow key={photo.albumId} world={world} photo={photo} album={album} />;
}

function PhotoWindow({ world, photo, album }: { world: World; photo: PhotoView; album: Album }) {
  const stage = useRef<HTMLDivElement>(null);
  const swipe = useRef<{ x: number; used: boolean } | null>(null);
  const slideSeconds = useStore(settingsStore, (s) => s.slideSeconds);
  const [shown, setShown] = useState(false);
  const count = album.photos.length;
  const current = album.photos[photo.index];
  const previous = photo.previous === null ? undefined : album.photos[photo.previous];
  const key = current ? photoKey(current) : '';
  const kept = useStore(socialStore, (s) => s.byKey.get(key));
  const social = kept ?? socialFor(key);

  // the window fades in over the world
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  useInterval(
    () => stepPhoto(appStore, count, 1),
    slideSeconds * 1000,
    photo.slideshow && !photo.closing,
    photo.index,
    'real',
  );

  // the wheel over the photo turns the photos
  useEffect(() => {
    const element = stage.current;
    if (!element) return;
    let acc = 0;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
      const [next, steps] = wheelSteps(acc, delta, event.deltaMode);
      acc = next;
      if (steps !== 0) stepPhoto(appStore, count, steps);
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, [count]);

  // closing: the photo flies back into the tile now showing it, or fades if there is none
  useEffect(() => {
    if (!photo.closing) return;
    const image = stage.current?.querySelector<HTMLImageElement>('.lightbox__img.is-current');
    const tile = [...document.querySelectorAll<HTMLElement>(`[data-photo-key="${CSS.escape(key)}"]`)].find(
      (element) => !element.closest('.lightbox'),
    );
    if (!image) {
      finishPhoto(appStore);
      return;
    }
    const box = image.getBoundingClientRect();
    const to = tile?.getBoundingClientRect();
    const animation =
      to && to.width > 0
        ? image.animate(
            [{ transform: 'none' }, { transform: flyTransform(box, to), borderRadius: '14px' }],
            { duration: ZOOM_MS, easing: EASE, fill: 'forwards' },
          )
        : image.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 400, fill: 'forwards' });
    animation.onfinish = () => finishPhoto(appStore);
    return () => {
      animation.onfinish = null;
    };
  }, [photo.closing, key]);

  const close = () => {
    if (swipe.current?.used) {
      swipe.current = null;
      return;
    }
    closePhoto(appStore);
  };

  return (
    <div className={`lightbox${shown && !photo.closing ? ' is-on' : ''}`} role="dialog" aria-label="Photo">
      <button type="button" className="lightbox__close" aria-label="Close" onClick={() => closePhoto(appStore)}>
        ✕
      </button>

      <aside className="lightbox__info">
        <div className="lightbox__country">{album.city.country.name}</div>
        <div className="lightbox__city">{album.city.name}</div>
        <div className="lightbox__album">{album.title}</div>
        <div className="lightbox__date">
          {monthYear(album)} · {album.photoCount} photos
        </div>
        <p className="lightbox__note">{current ? photoNote(current) : ''}</p>
        <p className="lightbox__desc">{describeAlbum(album)}</p>
        <p className="lightbox__credit">{current ? creditLine(current, album.city, world.credits) : ''}</p>
      </aside>

      <div
        ref={stage}
        className="lightbox__stage"
        onClick={close}
        onPointerDown={(event) => {
          swipe.current = { x: event.clientX, used: false };
        }}
        onPointerUp={(event) => {
          const start = swipe.current;
          if (!start) return;
          const distance = event.clientX - start.x;
          if (Math.abs(distance) > SWIPE_PX) {
            start.used = true;
            stepPhoto(appStore, count, distance < 0 ? 1 : -1);
          }
        }}
      >
        {previous && photo.previous !== photo.index && (
          <StageImage
            key={`under-${photo.previous}-${photo.index}`}
            src={photoUrl(previous)}
            stage={stage}
            from={null}
            dir={0}
            current={false}
          />
        )}
        {current && (
          <StageImage
            key={`photo-${photo.index}`}
            src={photoUrl(current)}
            stage={stage}
            from={photo.dir === 0 ? photo.from : null}
            dir={photo.dir}
            current
          />
        )}
        {count > 1 && (
          <>
            <button
              type="button"
              className="lightbox__nav lightbox__nav--prev"
              aria-label="Previous photo"
              onClick={(event) => {
                event.stopPropagation();
                stepPhoto(appStore, count, -1);
              }}
            >
              ←
            </button>
            <button
              type="button"
              className="lightbox__nav lightbox__nav--next"
              aria-label="Next photo"
              onClick={(event) => {
                event.stopPropagation();
                stepPhoto(appStore, count, 1);
              }}
            >
              →
            </button>
          </>
        )}
        <div className="lightbox__bar" onClick={(event) => event.stopPropagation()}>
          {count > 1 && (
            <button
              type="button"
              className={photo.slideshow ? 'is-on' : undefined}
              onClick={() => toggleSlideshow(appStore)}
            >
              {photo.slideshow ? '❚❚ Slideshow' : '▶ Slideshow'}
            </button>
          )}
          {count > 1 && (
            <label>
              <input
                type="range"
                min={SETTING_LIMITS.slideSeconds[0]}
                max={SETTING_LIMITS.slideSeconds[1]}
                step={1}
                value={slideSeconds}
                aria-label="Slideshow speed"
                onChange={(event) => settingsStore.set({ slideSeconds: Number(event.target.value) })}
              />
              <output>{slideSeconds} s</output>
            </label>
          )}
          <span>
            {photo.index + 1} / {count}
          </span>
        </div>
      </div>

      <aside className="lightbox__social">
        <button
          type="button"
          className={`lightbox__like${social.liked ? ' is-on' : ''}`}
          aria-pressed={social.liked}
          onClick={() => likePhoto(key)}
        >
          <i>♥</i>
          <span>{social.likes.toLocaleString('en')}</span>
        </button>
        <h4>Comments · {social.comments.length}</h4>
        <div className="lightbox__comments">
          {social.comments.map((comment, i) => (
            <div key={i} className="lightbox__comment">
              <b>{comment.who}</b>
              <small>{comment.when}</small>
              <p>{comment.text}</p>
            </div>
          ))}
        </div>
        <CommentForm onSend={(text) => commentPhoto(key, text)} />
        <div className="lightbox__demo">Demo: comments are not saved yet.</div>
      </aside>
    </div>
  );
}

function CommentForm({ onSend }: { onSend: (text: string) => void }) {
  const [text, setText] = useState('');
  const send = () => {
    onSend(text);
    setText('');
  };
  return (
    <form
      className="lightbox__form"
      onSubmit={(event) => {
        event.preventDefault();
        send();
      }}
    >
      <textarea
        value={text}
        placeholder="Add a comment…"
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            send();
          }
        }}
      />
      <button type="submit">Post</button>
    </form>
  );
}

/**
 * One photo on the stage, fitted into it. The one opened grows from where it was clicked; the
 * next one slides in from its side; the one under it just waits to be covered.
 */
function StageImage({
  src,
  stage,
  from,
  dir,
  current,
}: {
  src: string | null;
  stage: RefObject<HTMLDivElement | null>;
  from: Rect | null;
  dir: -1 | 0 | 1;
  current: boolean;
}) {
  const image = useRef<HTMLImageElement>(null);
  const played = useRef(false);
  const [fit, setFit] = useState<Rect | null>(null);

  const measure = () => {
    const element = image.current;
    const box = stage.current?.getBoundingClientRect();
    if (!element || !box || !element.naturalWidth) return;
    setFit(fitRect(box, element.naturalWidth / element.naturalHeight));
  };

  useEffect(() => {
    const onResize = () => {
      const element = image.current;
      const box = stage.current?.getBoundingClientRect();
      if (element && box && element.naturalWidth) {
        setFit(fitRect(box, element.naturalWidth / element.naturalHeight));
      }
    };
    addEventListener('resize', onResize);
    return () => removeEventListener('resize', onResize);
  }, [stage]);

  useLayoutEffect(() => {
    const element = image.current;
    if (!fit || !element || !current || played.current) return;
    played.current = true;
    if (dir === 0 && from) {
      element.animate(
        [
          { transform: flyTransform(fit, from), borderRadius: '14px' },
          { transform: 'none', borderRadius: '10px' },
        ],
        { duration: ZOOM_MS, easing: EASE },
      );
    } else if (dir !== 0) {
      element.animate(
        [
          { transform: `translateX(${dir * SLIDE_PX}px)`, opacity: 0 },
          { transform: 'none', opacity: 1 },
        ],
        { duration: SLIDE_MS, easing: EASE },
      );
    }
  }, [fit, current, dir, from]);

  return (
    <img
      ref={image}
      src={src ?? undefined}
      alt=""
      draggable={false}
      className={`lightbox__img ${current ? 'is-current' : 'is-under'}`}
      onLoad={measure}
      style={
        fit
          ? { left: fit.x, top: fit.y, width: fit.width, height: fit.height }
          : { visibility: 'hidden' }
      }
    />
  );
}
```

`src/features/lightbox/lightbox.scss` (ported from the prototype, lines 260–315 and the mobile rules):

```scss
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 29;
  display: grid;
  grid-template-columns: minmax(220px, 280px) 1fr minmax(260px, 340px);
  gap: 32px;
  padding: 34px 32px 30px;
  background: rgb(4 6 13 / 96%);
  opacity: 0;
  transition: opacity 0.6s ease;

  &.is-on {
    opacity: 1;
  }

  &__close {
    position: absolute;
    top: 30px;
    left: 32px;
    z-index: 2;
    width: 44px;
    height: 44px;
    border: 1px solid rgb(127 137 163 / 35%);
    border-radius: 50%;
    background: rgb(12 16 30 / 70%);
    font-size: 16px;

    &:hover {
      border-color: rgb(255 200 107 / 60%);
    }
  }

  &__info,
  &__social {
    min-height: 0;
    padding-top: 70px;
    opacity: 0;
    transform: translateY(12px);
    transition:
      opacity 0.5s ease 0.25s,
      transform 0.6s var(--ease) 0.25s;
  }

  &.is-on &__info,
  &.is-on &__social {
    opacity: 1;
    transform: none;
  }

  &__country {
    font-size: 12px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--lamp);
  }

  &__city {
    margin-top: 8px;
    font-family: var(--font-family-display);
    font-style: italic;
    font-weight: 300;
    font-size: 46px;
    line-height: 1;
  }

  &__album {
    margin-top: 18px;
    font-family: var(--font-family-display);
    font-style: italic;
    font-weight: 500;
    font-size: 22px;
    line-height: 1.15;
  }

  &__date {
    margin-top: 8px;
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
  }

  &__note {
    margin: 18px 0 0;
    font-family: var(--font-family-display);
    font-style: italic;
    font-size: 18px;
    line-height: 1.35;
  }

  &__desc {
    margin: 14px 0 0;
    font-size: 14px;
    line-height: 1.6;
    color: #c3c9d8;
  }

  &__credit {
    margin: 18px 0 0;
    font-size: 11px;
    line-height: 1.5;
    color: var(--muted);
  }

  &__stage {
    position: relative;
    min-height: 0;
    margin-bottom: 50px;
    cursor: pointer;
  }

  &__img {
    position: fixed;
    z-index: 30;
    max-width: none;
    object-fit: cover;
    border-radius: 10px;
    transform-origin: 0 0;
    will-change: transform;

    &.is-under {
      z-index: 29;
      animation: lightbox-under 0.7s ease forwards;
    }
  }

  &__nav {
    position: absolute;
    top: 50%;
    z-index: 31;
    width: 48px;
    height: 48px;
    margin-top: -24px;
    border: 1px solid rgb(255 255 255 / 25%);
    border-radius: 50%;
    background: rgb(4 6 13 / 50%);
    backdrop-filter: blur(6px);
    font-size: 18px;
    color: #fff;
    opacity: 0.8;
    transition:
      opacity 0.3s,
      background 0.3s;

    &:hover {
      opacity: 1;
      background: rgb(4 6 13 / 75%);
    }

    &--prev {
      left: 14px;
    }

    &--next {
      right: 14px;
    }
  }

  &__bar {
    position: absolute;
    bottom: -46px;
    left: 50%;
    z-index: 31;
    display: flex;
    gap: 12px;
    align-items: center;
    font-size: 12px;
    white-space: nowrap;
    color: var(--muted);
    transform: translateX(-50%);
    cursor: default;

    button {
      padding: 6px 14px;
      border: 1px solid rgb(127 137 163 / 35%);
      border-radius: 99px;
      background: rgb(12 16 30 / 70%);
      font-size: 12px;
      color: var(--text);

      &.is-on {
        border-color: rgb(255 200 107 / 60%);
        color: var(--lamp);
      }
    }

    label {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    input {
      width: 110px;
      accent-color: var(--lamp);
    }
  }

  &__social {
    display: flex;
    flex-direction: column;

    h4 {
      margin: 26px 0 0;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--muted);
    }
  }

  &__like {
    display: inline-flex;
    align-self: flex-start;
    gap: 10px;
    align-items: center;
    padding: 9px 16px;
    border: 1px solid rgb(255 200 107 / 45%);
    border-radius: 99px;
    background: rgb(255 200 107 / 6%);
    font-size: 14px;
    color: var(--text);
    transition:
      background 0.3s,
      transform 0.3s var(--ease);

    i {
      display: inline-block;
      font-style: normal;
      color: var(--muted);
      transition:
        color 0.3s,
        transform 0.4s var(--ease);
    }

    &.is-on {
      background: rgb(255 200 107 / 16%);

      i {
        color: #ff8a7a;
        transform: scale(1.25);
      }
    }

    &:active {
      transform: scale(0.96);
    }
  }

  &__comments {
    flex: 1;
    min-height: 0;
    margin-top: 12px;
    padding-right: 6px;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  &__comment {
    padding: 12px 0;
    border-bottom: 1px solid rgb(127 137 163 / 15%);
    font-size: 13px;
    line-height: 1.5;

    b {
      font-weight: 500;
    }

    small {
      margin-left: 8px;
      font-size: 11px;
      color: var(--muted);
    }

    p {
      margin: 3px 0 0;
      color: #c3c9d8;
    }
  }

  &__form {
    display: flex;
    gap: 8px;
    margin-top: 14px;

    textarea {
      flex: 1;
      height: 44px;
      padding: 11px 12px;
      border: 1px solid rgb(127 137 163 / 35%);
      border-radius: 12px;
      background: rgb(12 16 30 / 80%);
      font-size: 13px;
      color: var(--text);
      resize: none;
      user-select: text;
      -webkit-user-select: text;

      &:focus {
        outline: none;
        border-color: rgb(255 200 107 / 60%);
      }
    }

    button {
      padding: 0 16px;
      border: 0;
      border-radius: 12px;
      background: var(--lamp);
      font-weight: 500;
      color: #1a1406;
    }
  }

  &__demo {
    margin-top: 8px;
    font-size: 11px;
    color: var(--muted);
  }

  @include mobile {
    grid-template-rows: 44vh 1fr;
    grid-template-columns: 1fr;
    gap: 14px;
    padding: 64px 12px 12px;
    overflow-y: auto;

    &__stage {
      grid-row: 1;
      margin-bottom: 44px;
    }

    &__info {
      grid-row: 2;
      padding-top: 0;
    }

    &__social {
      grid-row: 3;
      padding-top: 0;
    }

    &__close {
      top: 12px;
      left: 12px;
    }

    &__city {
      font-size: 34px;
    }

    &__bar {
      bottom: -40px;
    }

    &__nav {
      width: 40px;
      height: 40px;
      margin-top: -20px;
    }
  }
}

@keyframes lightbox-under {
  from {
    opacity: 1;
  }

  to {
    opacity: 0;
  }
}
```

`src/app/Stage.tsx`: import `Lightbox` from `@/features/lightbox/Lightbox` and render `<Lightbox world={world} />` last inside the provider.

- [ ] **Step 6: Run the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A src
git commit -m "feat(lightbox): open photos large with their story, likes, comments and a slideshow"
```

---

### Task 5: Keys: the Esc chain and the photo window

**Files:**
- Modify: `src/features/keys/useKeys.ts`, `src/app/Stage.tsx`

**Interfaces:**
- Consumes: `escapeTarget`, `closePhoto`, `stepPhoto`, `toggleSlideshow` (Task 2); `Archive`.
- Produces: `useKeys(director: Director, archive: Archive): void`.

- [ ] **Step 1: Rewrite the keys hook**

`src/features/keys/useKeys.ts`:

```ts
import { useEffect } from 'react';
import type { Archive } from '@/data/archive';
import { appStore } from '@/state/app-state';
import { closePhoto, escapeTarget, stepPhoto, toggleSlideshow } from '@/state/layers';
import type { Director } from '@/tour/director';

/**
 * Esc closes the innermost layer (menu, photo window, then the place in focus, then the range).
 * In the photo window ← → turn the photos and Space runs the slideshow; on the main screen
 * ← → move between albums, ↑ ↓ scroll them and Space plays or pauses the tour.
 */
export const useKeys = (director: Director, archive: Archive): void => {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest('input, textarea, select')) return;
      const state = appStore.get();

      if (event.key === 'Escape') {
        const layer = escapeTarget(state);
        if (layer === 'menu') appStore.set({ menu: null });
        else if (layer === 'photo') closePhoto(appStore);
        else director.escape();
        return;
      }

      if (state.photo) {
        const count = archive.albumById.get(state.photo.albumId)?.photos.length ?? 0;
        if (event.key === 'ArrowRight') stepPhoto(appStore, count, 1);
        else if (event.key === 'ArrowLeft') stepPhoto(appStore, count, -1);
        else if (event.key === ' ') {
          if (target?.closest('button')) return;
          event.preventDefault();
          toggleSlideshow(appStore);
        }
        return;
      }

      switch (event.key) {
        case 'ArrowRight':
          director.next(1);
          break;
        case 'ArrowLeft':
          director.next(-1);
          break;
        case 'ArrowDown':
          event.preventDefault();
          director.scroll(1);
          break;
        case 'ArrowUp':
          event.preventDefault();
          director.scroll(-1);
          break;
        case ' ':
          // a focused button already takes Space as its own click
          if (target?.closest('button')) return;
          event.preventDefault();
          director.play();
          break;
        default:
          return;
      }
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  }, [director, archive]);
};
```

In `src/app/Stage.tsx` change `useKeys(director);` to `useKeys(director, world.archive);`.

- [ ] **Step 2: Run the check and commit**

Run: `npm run check`
Expected: PASS.

```bash
git add src/features/keys src/app/Stage.tsx
git commit -m "feat(keys): close the innermost layer on Esc and drive the photo window"
```

---

### Task 6: Check it in the browser

- [ ] **Step 1:** `npm run check && npm run build` — PASS.
- [ ] **Step 2:** With `npm run dev`, write down what you saw:
  1. Land on Paris, click the cover: the photo grows from the card into the middle; the left column shows country, city, album, date, caption, description, credit; the right the like, comments, form. The globe, the sky and the cycling stop (`__globe.state().worldNow` stays still).
  2. → and ← (buttons and keys), the wheel over the photo, a horizontal swipe: the next photo slides in from its side; the counter follows. Slideshow and Space advance it at the slider's pace.
  3. Like toggles and counts; a comment posts with Enter; a blank one does nothing.
  4. Esc (or ✕, or a click on the photo) flies it back into the cover showing it now; when the panel moved on to another photo, it fades instead. The world resumes.
  5. The burger opens the demo menu; the gear opens the settings; sliders change the photo and flight time (kept after a reload); unchecking "Show how to use it" hides the help lines. A click outside closes them; Esc closes the menu before the photo window.
  6. The stats read "12 of 12 countries", then "in range" with a range, "so far" with a place in focus.
  7. At 390 × 844 the photo window stacks the photo on top, the header hides the stats.
