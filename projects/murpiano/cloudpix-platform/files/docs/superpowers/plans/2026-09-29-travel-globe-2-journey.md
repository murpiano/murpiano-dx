# Travel globe, part 2: timeline, flights, album panel and tours — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the demo globe tell the journey: pick a light and the plane flies there; the timeline picks ranges and years and plays the albums in order; the album panel shows the place in focus with cycling photos; year and trip tours run to their end, home with light and smoke, or another city.

**Architecture:** A new pure module, the director (`src/tour/director.ts`), owns the journey: focus, flights, the camera during flights, tours, the timeline range, dwell and arrival. It writes what React needs into `appStore` and hands the engine a camera override and a render view each frame. The engine stays a renderer plus input; React components (timeline, album panel) read the store and call director methods. Everything with logic (range math, flight phases, tour steps, the director itself) is tested in node with a fake clock.

**Tech Stack:** as in part 1 — React 19, TypeScript 6 strict, Vite 8, SCSS, Vitest 5 (node), `d3-geo`.

**Spec:** [`docs/design/2026-09-29-travel-globe.md`](../../design/2026-09-29-travel-globe.md) — sections 3.2–3.6, 3.9 (partly) and 4. Reference: `docs/design/prototype/flight.html` (flights ~941–1015, panel ~1040–1184, tours ~1566–1627, timeline ~1656–1830, CSS 114–166, 249–259, 325–392). Part 1 plan: `2026-09-29-travel-globe-1-foundation.md`.

**Out of this plan** (later plans): the photo window (a click on the current cover does nothing yet), links into the archive (city, country, album, year, trip names render as plain text), the 5 s return to the archive after a tour, the header stats and the settings UI (the settings store exists with defaults), the rest of the Esc chain.

## Global Constraints

- Branch `feat/travel-globe`. Never push to `main`.
- `npm run check` green after every task. Code style as in part 1 (Prettier, strict ESLint, `import type`, no `!`).
- Flights: fade in standing 0.7 s, constant speed for the flight time (30 s default, 5–90 s), stop and fade out 0.38 s, then the place lights up and pulses (raised cosine, 1.5 s).
- Camera: slerp between quaternions, `camCurve` (14 % ease in and out), rises mid-flight in proportion to distance. A pick with nothing to fly from only turns the camera, eased, over 2–4 s.
- Place states: plain, grey (range picked, outside), blue `#8fb8ff` (inside, not reached), yellow `#ffc86b` (reached up to the album in focus), current (in focus after landing, 1.45×). Fades about 0.4 s.
- Home: lit and smoking while the plane stands at home before take-off and after it lands at home; pulses on landing at home.
- Timeline: ▶/❚❚; press and drag picks a range (star blue); a click picks from the start to that point; a year picks the year; a second click on the picked year is for the archive (plan 4, no-op now); an empty range is refused with a short note; the chip shows the range and the album count, ✕ or Esc clears it; yellow progress from the range start (or timeline start) up to the album in focus, reset by a new pick until the plane moves again.
- Panel: years with the current one underlined; in a tour, only the trip name or the year; a stack of cards, the current one cycles photos every photo time (5 s default) with a 1.4 s dissolve; hover shows previous and next with their date and title, the title on the cover, drift after the cursor, and pauses the cycling; wheel one album per notch, a quick double turn two; swipe on a phone; loops by date; in a tour only the tour's albums of this place.
- Dwell after a landing while playing: `max(3500 ms, photo time)`.
- Everything animated runs on the world clock (`appStore.paused` stops it).

## Review Focus

- **The owner drags the globe during a flight** — the camera lets go, the plane keeps flying and lands normally. Pinned in Task 5 ("lets go of the camera").
- **A light clicked while the plane is in the air** — the new flight starts from where the plane is now, not from the last place. Pinned in Task 5 ("redirects from mid-air").
- **The world paused mid-flight or mid-dwell** — nothing moves until it resumes. Pinned in Task 5 ("waits while the world is paused") and Task 1 (`tickInterval`).
- **A range or a year with no albums** — refused with a note, the old state stays sane. Pinned in Task 5 ("refuses a stretch with no album", "a year without albums").
- **A trackpad sending many small wheel deltas over the albums** — one album per 100 units, never a jump of many. Pinned in Task 9 (`wheelSteps`).

---

## File map

Created:

```
src/lib/dates.ts, dates.test.ts            MONTHS, monthYear
src/lib/assets.ts                          demoUrl (moved from app/boot)
src/lib/interval.ts, interval.test.ts      tickInterval
src/data/trips.ts, trips.test.ts           tripOfAlbum, endpointPlace
src/data/photos.ts, photos.test.ts         photoUrl, creditLine, cityPhotos
src/state/settings.ts, settings.test.ts    settingsStore (photo and flight time)
src/timeline/range.ts, range.test.ts       album time, ranges, reach, labels
src/tour/flight.ts, flight.test.ts         flight phases and camera
src/tour/tour.ts, tour.test.ts             tours and the next step
src/tour/director.ts, director.test.ts     the journey
src/app/Stage.tsx                          director + globe + panel + timeline
src/app/director-context.ts                DirectorContext, useDirector
src/features/keys/useKeys.ts               Esc, arrows, Space
src/features/timeline/Timeline.tsx, timeline.scss
src/features/panel/AlbumPanel.tsx, panel.scss, stack.ts, stack.test.ts,
  useWorldInterval.ts, cozy-room.svg
```

Modified: `src/geo/vector.ts` (LonLat), `src/state/app-state.ts`, `src/app/boot.ts` (+test), `src/app/App.tsx`, `src/render/globe.ts`, `src/engine/engine.ts`, `src/features/globe/GlobeStage.tsx`, `src/styles/normalize.scss`.

---

### Task 1: Shared helpers: dates, assets, interval, trips, photos, settings

**Files:**
- Create: `src/lib/dates.ts`, `src/lib/assets.ts`, `src/lib/interval.ts`, `src/data/trips.ts`, `src/data/photos.ts`, `src/state/settings.ts`
- Modify: `src/app/boot.ts` (import and re-export `demoUrl`)
- Test: `src/lib/dates.test.ts`, `src/lib/interval.test.ts`, `src/data/trips.test.ts`, `src/data/photos.test.ts`, `src/state/settings.test.ts`

**Interfaces:**
- Produces:
  - `MONTHS: readonly string[]`, `monthYear(m: { year: number; month: number }): string` → `"Apr 2023"`
  - `demoUrl(path: string): string` (in `src/lib/assets.ts`; `src/app/boot.ts` re-exports it)
  - `tickInterval(elapsed: number, dt: number, ms: number): [number, boolean]`
  - `tripOfAlbum(archive: Archive, albumId: string): Trip | undefined`
  - `interface EndpointPlace { name: string; country: string; lon: number; lat: number; cityKey: string | null }`, `endpointPlace(end: Endpoint, archive: Archive, home: Place): EndpointPlace`
  - `photoUrl(photo: PhotoRef): string | null`, `creditLine(photo: PhotoRef, city: City, credits: ReadonlyMap<string, Credit>): string`, `cityPhotos(city: City): PhotoRef[]`
  - `interface Settings { photoSeconds: number; flightSeconds: number; help: boolean }`, `DEFAULT_SETTINGS`, `settingsStore: Store<Settings>`

- [ ] **Step 1: Write the failing tests**

`src/lib/dates.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { MONTHS, monthYear } from './dates';

describe('monthYear', () => {
  it('names the month and the year', () => {
    expect(monthYear({ year: 2023, month: 4 })).toBe('Apr 2023');
    expect(monthYear({ year: 2016, month: 12 })).toBe('Dec 2016');
    expect(MONTHS).toHaveLength(12);
  });
});
```

`src/lib/interval.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { tickInterval } from './interval';

describe('tickInterval', () => {
  it('fires once the time is up and starts over', () => {
    expect(tickInterval(0, 1000, 2000)).toEqual([1000, false]);
    expect(tickInterval(1000, 1000, 2000)).toEqual([0, true]);
  });

  it('stands still while the world is paused', () => {
    expect(tickInterval(1500, 0, 2000)).toEqual([1500, false]);
  });
});
```

`src/data/trips.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { linkArchive } from './archive';
import { buildDemo, DEMO_HOME } from './demo';
import { endpointPlace, tripOfAlbum } from './trips';
import type { Credit } from './types';

const file = fileURLToPath(new URL('../../public/demo/photos.json', import.meta.url));
const archive = linkArchive(buildDemo(JSON.parse(readFileSync(file, 'utf8')) as Credit[]));

describe('tripOfAlbum', () => {
  it('finds the trip an album belongs to', () => {
    expect(tripOfAlbum(archive, 'kyoto/sakura-week')?.name).toBe('Japan in bloom');
    expect(tripOfAlbum(archive, 'nowhere')).toBeUndefined();
  });
});

describe('endpointPlace', () => {
  it('is home for a home endpoint', () => {
    expect(endpointPlace({ home: true }, archive, DEMO_HOME)).toEqual({
      name: 'Kyiv',
      country: 'Ukraine',
      lon: 30.52,
      lat: 50.45,
      cityKey: null,
    });
  });

  it('is the city for a city endpoint, and home when the city is gone', () => {
    expect(endpointPlace({ cityKey: 'paris' }, archive, DEMO_HOME).name).toBe('Paris');
    expect(endpointPlace({ cityKey: 'atlantis' }, archive, DEMO_HOME).name).toBe('Kyiv');
  });
});
```

`src/data/photos.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { linkArchive } from './archive';
import { cityPhotos, creditLine, photoUrl } from './photos';
import type { AlbumData, Credit } from './types';

const album = (id: string, files: string[]): AlbumData => ({
  id,
  title: id,
  year: 2020,
  month: 1,
  day: 1,
  time: '12:00',
  photoCount: files.length,
  photos: files.map((file) => ({ kind: 'stock', file })),
});

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
          albums: [album('a', ['p0.jpg', 'p1.jpg']), album('b', ['p1.jpg', 'p2.jpg'])],
        },
      ],
    },
  ],
  trips: [],
});
const paris = archive.cityByKey.get('paris');
const credits = new Map<string, Credit>([
  ['p0.jpg', { city: 'Paris', file: 'p0.jpg', author: 'Ann', lic: 'CC BY 4.0' }],
]);

describe('photoUrl', () => {
  it('finds a stock photo under the demo folder', () => {
    expect(photoUrl({ kind: 'stock', file: 'p0.jpg' })).toBe(
      `${import.meta.env.BASE_URL}demo/photos/p0.jpg`,
    );
  });

  it('has no url for an own photo yet', () => {
    expect(photoUrl({ kind: 'own', id: 'x', name: 'x.jpg' })).toBeNull();
  });
});

describe('creditLine', () => {
  it('credits the author and the license', () => {
    if (!paris) throw new Error('no paris');
    expect(creditLine({ kind: 'stock', file: 'p0.jpg' }, paris, credits)).toBe(
      'Paris · photo: Ann · CC BY 4.0 · Wikimedia Commons',
    );
    expect(creditLine({ kind: 'own', id: 'x', name: 'x.jpg' }, paris, credits)).toBe(
      'Paris · your photo',
    );
  });
});

describe('cityPhotos', () => {
  it('lists each photo of a city once', () => {
    if (!paris) throw new Error('no paris');
    expect(cityPhotos(paris).map((p) => (p.kind === 'stock' ? p.file : ''))).toEqual([
      'p0.jpg',
      'p1.jpg',
      'p2.jpg',
    ]);
  });
});
```

`src/state/settings.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS, settingsStore } from './settings';

describe('settingsStore', () => {
  it('starts from the defaults when nothing is kept', () => {
    expect(DEFAULT_SETTINGS).toEqual({ photoSeconds: 5, flightSeconds: 30, help: true });
    expect(settingsStore.get()).toEqual(DEFAULT_SETTINGS);
  });
});
```

- [ ] **Step 2: Run them to see them fail**

Run: `npx vitest run src/lib/dates.test.ts src/lib/interval.test.ts src/data/trips.test.ts src/data/photos.test.ts src/state/settings.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement**

`src/lib/dates.ts`:

```ts
export const MONTHS: readonly string[] = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

export const monthYear = ({ year, month }: { year: number; month: number }): string =>
  `${MONTHS[month - 1] ?? ''} ${year}`;
```

`src/lib/assets.ts`:

```ts
/** A file of the bundled demo, under the base path so it works under /cloudpix-platform/ too. */
export const demoUrl = (path: string): string => `${import.meta.env.BASE_URL}demo/${path}`;
```

`src/lib/interval.ts`:

```ts
/** A repeating timer on the world clock: returns the new elapsed time and whether it fired. */
export const tickInterval = (elapsed: number, dt: number, ms: number): [number, boolean] => {
  const next = elapsed + dt;
  return next >= ms ? [0, true] : [next, false];
};
```

`src/data/trips.ts`:

```ts
import type { Archive } from './archive';
import type { Endpoint, Place, Trip } from './types';

export const tripOfAlbum = (archive: Archive, albumId: string): Trip | undefined =>
  archive.trips.find((trip) => trip.albumIds.includes(albumId));

export interface EndpointPlace {
  name: string;
  country: string;
  lon: number;
  lat: number;
  /** null for home. */
  cityKey: string | null;
}

/** Where a trip starts or ends: home, or a city on the map (home again if the city is gone). */
export const endpointPlace = (end: Endpoint, archive: Archive, home: Place): EndpointPlace => {
  if ('cityKey' in end) {
    const city = archive.cityByKey.get(end.cityKey);
    if (city) {
      return { name: city.name, country: city.country.name, lon: city.lon, lat: city.lat, cityKey: city.key };
    }
  }
  return { name: home.name, country: home.country, lon: home.lon, lat: home.lat, cityKey: null };
};
```

`src/data/photos.ts`:

```ts
import { demoUrl } from '@/lib/assets';
import type { City, Credit, PhotoRef } from './types';

/** The owner's photos get their urls from the local repository in plan 5. */
export const photoUrl = (photo: PhotoRef): string | null =>
  photo.kind === 'stock' ? demoUrl(`photos/${photo.file}`) : null;

export const creditLine = (
  photo: PhotoRef,
  city: City,
  credits: ReadonlyMap<string, Credit>,
): string => {
  if (photo.kind === 'own') return `${city.name} · your photo`;
  const credit = credits.get(photo.file);
  return `${city.name} · photo: ${credit?.author ?? 'unknown'} · ${credit?.lic ?? ''} · Wikimedia Commons`;
};

/** Every photo of a city, once each, in album order. */
export const cityPhotos = (city: City): PhotoRef[] => {
  const seen = new Set<string>();
  const photos: PhotoRef[] = [];
  for (const album of city.albums) {
    for (const photo of album.photos) {
      const key = photo.kind === 'stock' ? photo.file : photo.id;
      if (seen.has(key)) continue;
      seen.add(key);
      photos.push(photo);
    }
  }
  return photos;
};
```

`src/state/settings.ts`:

```ts
import { readJSON, writeJSON } from '@/lib/storage';
import { createStore } from './store';

/** The pace of the main screen, kept per browser. The gear in the header edits it (plan 3). */
export interface Settings {
  /** Each photo on the main screen, 2–15 s. */
  photoSeconds: number;
  /** Each flight, 5–90 s. */
  flightSeconds: number;
  /** "Show how to use it". */
  help: boolean;
}

export const DEFAULT_SETTINGS: Settings = { photoSeconds: 5, flightSeconds: 30, help: true };

export const settingsStore = createStore<Settings>({
  ...DEFAULT_SETTINGS,
  ...readJSON<Partial<Settings>>('settings', {}),
});

settingsStore.subscribe(() => writeJSON('settings', settingsStore.get()));
```

`src/app/boot.ts` — replace the local `demoUrl` with the shared one. Change the top of the file to:

```ts
import { linkArchive } from '@/data/archive';
import type { Archive } from '@/data/archive';
import { buildDemo, DEMO_HOME } from '@/data/demo';
import type { Credit, Place } from '@/data/types';
import { earthFromTopology } from '@/geo/world';
import type { EarthGeo, WorldTopology } from '@/geo/world';
import { demoUrl } from '@/lib/assets';
import { buildLights } from '@/render/lights';
import type { Light } from '@/render/lights';

export { demoUrl };
```

and delete the old `export const demoUrl = ...` line.

- [ ] **Step 4: Run the tests and the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib src/data src/state src/app/boot.ts
git commit -m "feat: add dates, photo, trip and settings helpers for the journey"
```

---

### Task 2: Timeline math

**Files:**
- Create: `src/timeline/range.ts`
- Test: `src/timeline/range.test.ts`

**Interfaces:**
- Consumes: `MONTHS` (`src/lib/dates.ts`), `clamp` (`src/lib/math.ts`).
- Produces:
  - `interface Range { lo: number; hi: number; year?: number }`
  - `albumTime(m: { year; month; day; time }): number` — years, fractional
  - `within(t: number, range: Range | null): boolean`, `yearRange(year: number): Range`
  - `span(times: readonly number[]): [number, number]`
  - `pickedRange(start: number, end: number, moved: boolean, first: number): Range`
  - `timeAt(x: number, width: number, times: readonly number[], bounds: [number, number], snapPx?: number): number`
  - `nearestIndex(t: number, times: readonly number[]): number`
  - `interface Progress { on: boolean; focus: number; ahead: boolean; range: Range | null }`, `isReached(index: number, time: number, progress: Progress): boolean`
  - `stamp(t: number): string`, `rangeLabel(range: Range): string`

- [ ] **Step 1: Write the failing test**

`src/timeline/range.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  albumTime,
  isReached,
  nearestIndex,
  pickedRange,
  rangeLabel,
  span,
  stamp,
  timeAt,
  within,
  yearRange,
} from './range';
import type { Progress } from './range';

const at = (year: number, month: number, day = 1, time = '00:00') =>
  albumTime({ year, month, day, time });

describe('albumTime', () => {
  it('places an album by its month, day and time', () => {
    expect(at(2020, 1)).toBe(2020);
    expect(at(2020, 7)).toBeCloseTo(2020.5);
    expect(at(2020, 7, 2)).toBeGreaterThan(at(2020, 7, 1, '23:59'));
    expect(at(2020, 7, 1, '12:00')).toBeGreaterThan(at(2020, 7, 1, '11:59'));
    expect(at(2020, 12, 31, '23:59')).toBeLessThan(2021);
  });
});

describe('ranges', () => {
  it('holds the times inside it, both ends included', () => {
    const range = { lo: 2019, hi: 2020 };
    expect(within(2019, range)).toBe(true);
    expect(within(2020, range)).toBe(true);
    expect(within(2020.01, range)).toBe(false);
    expect(within(1990, null)).toBe(true);
  });

  it('makes a whole year', () => {
    const year = yearRange(2023);
    expect(year.year).toBe(2023);
    expect(within(at(2023, 12, 31, '23:59'), year)).toBe(true);
    expect(within(2024, year)).toBe(false);
  });

  it('picks a dragged stretch in either direction, and a click from the start', () => {
    expect(pickedRange(2021, 2019, true, 2016)).toEqual({ lo: 2019, hi: 2021 });
    expect(pickedRange(2021, 2021.2, false, 2016)).toEqual({ lo: 2016, hi: 2021.2 });
  });

  it('spans whole years around the albums', () => {
    expect(span([2016.5, 2025.8, 2019.1])).toEqual([2016, 2026]);
  });
});

describe('timeAt', () => {
  const times = [2016.5, 2019.25];
  const bounds: [number, number] = [2016, 2020];

  it('snaps to an album within 10 px', () => {
    // 2019.25 sits at 325 px on a 400 px track
    expect(timeAt(330, 400, times, bounds)).toBe(2019.25);
  });

  it('reads the time under the cursor elsewhere', () => {
    expect(timeAt(200, 400, times, bounds)).toBe(2018);
    expect(timeAt(-50, 400, times, bounds)).toBe(2016);
  });

  it('finds the nearest album', () => {
    expect(nearestIndex(2018.9, times)).toBe(1);
    expect(nearestIndex(2010, times)).toBe(0);
  });
});

describe('isReached', () => {
  const progress = (patch: Partial<Progress>): Progress => ({
    on: true,
    focus: 3,
    ahead: false,
    range: null,
    ...patch,
  });

  it('reaches every album up to the one in focus', () => {
    expect(isReached(3, 2020, progress({}))).toBe(true);
    expect(isReached(4, 2021, progress({}))).toBe(false);
  });

  it('does not count the album the plane is still flying to', () => {
    expect(isReached(3, 2020, progress({ ahead: true }))).toBe(false);
    expect(isReached(2, 2019, progress({ ahead: true }))).toBe(true);
  });

  it('starts at the picked range', () => {
    expect(isReached(1, 2017, progress({ range: { lo: 2018, hi: 2022 } }))).toBe(false);
    expect(isReached(2, 2019, progress({ range: { lo: 2018, hi: 2022 } }))).toBe(true);
  });

  it('shows nothing after a new pick until the plane moves again, or with no focus', () => {
    expect(isReached(1, 2017, progress({ on: false }))).toBe(false);
    expect(isReached(0, 2016, progress({ focus: -1 }))).toBe(false);
  });
});

describe('labels', () => {
  it('names a moment, a stretch and a year', () => {
    expect(stamp(at(2023, 4, 10))).toBe('Apr 2023');
    expect(rangeLabel({ lo: at(2019, 3), hi: at(2021, 10) })).toBe('Mar 2019 – Oct 2021');
    expect(rangeLabel({ lo: at(2019, 3), hi: at(2019, 3) })).toBe('Mar 2019');
    expect(rangeLabel(yearRange(2023))).toBe('2023');
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/timeline/range.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`src/timeline/range.ts`:

```ts
import { MONTHS } from '@/lib/dates';
import { clamp } from '@/lib/math';

/** A stretch of the timeline in fractional years; `year` when it is a whole year. */
export interface Range {
  lo: number;
  hi: number;
  year?: number;
}

const EPS = 1e-6;

/** An album's place on the timeline: its month, and within the month its day and time. */
export const albumTime = ({
  year,
  month,
  day,
  time,
}: {
  year: number;
  month: number;
  day: number;
  time: string;
}): number => {
  const [hours = 0, minutes = 0] = time.split(':').map(Number);
  return year + (month - 1 + (day - 1 + (hours * 60 + minutes) / 1440) / 31) / 12;
};

export const within = (t: number, range: Range | null): boolean =>
  range === null || (t >= range.lo - EPS && t <= range.hi + EPS);

export const yearRange = (year: number): Range => ({ lo: year, hi: year + 1 - EPS, year });

/** The whole years the timeline shows: from the first album's year to after the last one's. */
export const span = (times: readonly number[]): [number, number] =>
  times.length === 0
    ? [2000, 2001]
    : [Math.floor(Math.min(...times)), Math.floor(Math.max(...times)) + 1];

/** A drag picks the stretch; a plain click picks everything from the start up to that point. */
export const pickedRange = (start: number, end: number, moved: boolean, first: number): Range =>
  moved ? { lo: Math.min(start, end), hi: Math.max(start, end) } : { lo: first, hi: end };

/**
 * The time under `x` px of a track `width` px wide. Within `snapPx` of an album it lands on that
 * album, so both ends of a range are easy to hit.
 */
export const timeAt = (
  x: number,
  width: number,
  times: readonly number[],
  [y0, y1]: [number, number],
  snapPx = 10,
): number => {
  let best: number | null = null;
  let bestDistance = snapPx;
  for (const t of times) {
    const distance = Math.abs(((t - y0) / (y1 - y0)) * width - x);
    if (distance < bestDistance) {
      best = t;
      bestDistance = distance;
    }
  }
  return best ?? clamp(y0 + (x / width) * (y1 - y0), y0, y1);
};

export const nearestIndex = (t: number, times: readonly number[]): number => {
  let best = 0;
  let bestDistance = Infinity;
  times.forEach((time, index) => {
    const distance = Math.abs(time - t);
    if (distance < bestDistance) {
      best = index;
      bestDistance = distance;
    }
  });
  return best;
};

export interface Progress {
  /** Off after a new range is picked, until the plane moves again. */
  on: boolean;
  /** Album index in focus, -1 for none. */
  focus: number;
  /** The plane is still on its way to the album in focus. */
  ahead: boolean;
  range: Range | null;
}

/** Reached: on the timeline up to the album in focus, from the start of the picked range. */
export const isReached = (index: number, time: number, { on, focus, ahead, range }: Progress): boolean => {
  if (!on || focus < 0) return false;
  if (index > (ahead ? focus - 1 : focus)) return false;
  return range === null || time >= range.lo - EPS;
};

export const stamp = (t: number): string => {
  const year = Math.floor(t + 1e-9);
  return `${MONTHS[clamp(Math.floor((t - year) * 12), 0, 11)] ?? ''} ${year}`;
};

export const rangeLabel = ({ lo, hi, year }: Range): string =>
  year !== undefined ? String(year) : lo === hi ? stamp(lo) : `${stamp(lo)} – ${stamp(hi)}`;
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/timeline/range.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/timeline
git commit -m "feat(timeline): add ranges, reach and labels for the timeline"
```

---

### Task 3: Flights

**Files:**
- Modify: `src/geo/vector.ts` (add `LonLat`)
- Create: `src/tour/flight.ts`
- Test: `src/tour/flight.test.ts`

**Interfaces:**
- Consumes: `camCurve`, `quat`, `Quat`, `Rotation` (`src/geo/camera.ts`); `Z_MIN` (`src/geo/projection.ts`); `smooth`, `smoother` (`src/lib/easing.ts`).
- Produces:
  - `type LonLat = [number, number]` in `src/geo/vector.ts`
  - `APPEAR_MS = 700`, `VANISH_MS = 380`, `EARTH_KM = 6371`, `type FlightPhase = 'appear' | 'cruise' | 'vanish' | 'done'`
  - `interface Flight { to; path; km; q0; q1; rise; cameraMs; phase; phaseMs; e; c; follow }`
  - `cameraTurnMs(radians: number): number`, `createFlight({ from, to, rot }): Flight`, `stepFlight(flight: Flight, dt: number, cruiseMs: number): void`, `planeAlpha(flight: Flight): number`, `riseZoom(z: number, flight: Flight): number`

- [ ] **Step 1: Add `LonLat` to `src/geo/vector.ts`**

Append:

```ts
/** A point on Earth as d3 takes it: [longitude, latitude] in degrees. */
export type LonLat = [number, number];
```

- [ ] **Step 2: Write the failing test**

`src/tour/flight.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { Z_MIN } from '@/geo/projection';
import type { LonLat } from '@/geo/vector';
import {
  APPEAR_MS,
  cameraTurnMs,
  createFlight,
  planeAlpha,
  riseZoom,
  stepFlight,
  VANISH_MS,
} from './flight';

const KYIV: LonLat = [30.52, 50.45];
const PARIS: LonLat = [2.35, 48.86];
const CRUISE = 30000;

const run = (flight: ReturnType<typeof createFlight>, ms: number) => {
  for (let t = 0; t < ms; t += 10) stepFlight(flight, 10, CRUISE);
};

describe('createFlight', () => {
  it('flies the great circle and knows its length', () => {
    const flight = createFlight({ from: KYIV, to: PARIS, rot: [-30, -50, 0] });
    expect(flight.km).toBeGreaterThan(1990);
    expect(flight.km).toBeLessThan(2060);
    expect(flight.path?.(0)[0]).toBeCloseTo(KYIV[0]);
    expect(flight.path?.(1)[1]).toBeCloseTo(PARIS[1]);
    expect(flight.phase).toBe('appear');
  });

  it('only turns the camera when there is nowhere to fly from', () => {
    expect(createFlight({ from: null, to: PARIS, rot: [0, 0, 0] }).path).toBeNull();
    expect(createFlight({ from: PARIS, to: PARIS, rot: [0, 0, 0] }).path).toBeNull();
  });
});

describe('stepFlight', () => {
  it('fades in standing, flies at constant speed, stops and fades out', () => {
    const flight = createFlight({ from: KYIV, to: PARIS, rot: [-30, -50, 0] });
    run(flight, APPEAR_MS - 10);
    expect(flight.phase).toBe('appear');
    expect(flight.e).toBe(0);
    run(flight, 20);
    expect(flight.phase).toBe('cruise');
    run(flight, CRUISE / 2);
    expect(flight.e).toBeCloseTo(0.5, 2);
    run(flight, CRUISE / 2);
    expect(flight.phase).toBe('vanish');
    expect(flight.e).toBe(1);
    run(flight, VANISH_MS + 10);
    expect(flight.phase).toBe('done');
    expect(flight.c).toBeCloseTo(1);
  });

  it('turns the camera alone in 2 to 4 s', () => {
    expect(cameraTurnMs(0)).toBe(2000);
    expect(cameraTurnMs(Math.PI)).toBe(4000);
    const flight = createFlight({ from: null, to: PARIS, rot: [0, 0, 0] });
    run(flight, flight.cameraMs - 20);
    expect(flight.phase).not.toBe('done');
    run(flight, 30);
    expect(flight.phase).toBe('done');
    expect(flight.c).toBe(1);
  });

  it('stands still while the world is paused', () => {
    const flight = createFlight({ from: KYIV, to: PARIS, rot: [-30, -50, 0] });
    run(flight, 1000);
    const e = flight.e;
    stepFlight(flight, 0, CRUISE);
    expect(flight.e).toBe(e);
  });
});

describe('planeAlpha', () => {
  it('fades the plane in and out', () => {
    const flight = createFlight({ from: KYIV, to: PARIS, rot: [-30, -50, 0] });
    expect(planeAlpha(flight)).toBe(0);
    run(flight, APPEAR_MS + 100);
    expect(planeAlpha(flight)).toBe(1);
    run(flight, CRUISE + VANISH_MS + 20);
    expect(planeAlpha(flight)).toBe(0);
  });
});

describe('riseZoom', () => {
  it('rises mid-flight in proportion to distance and settles at both ends', () => {
    const near = createFlight({ from: KYIV, to: PARIS, rot: [-30, -50, 0] });
    const far = createFlight({ from: KYIV, to: PARIS, rot: [150, 30, 0] });
    expect(riseZoom(1, near)).toBe(1);
    near.c = 0.5;
    far.c = 0.5;
    expect(riseZoom(1, far)).toBeLessThan(riseZoom(1, near));
    expect(riseZoom(1, far)).toBeGreaterThanOrEqual(Z_MIN);
    far.c = 1;
    expect(riseZoom(1, far)).toBeCloseTo(1);
  });
});
```

- [ ] **Step 3: Run it to see it fail**

Run: `npx vitest run src/tour/flight.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement**

`src/tour/flight.ts`:

```ts
import { geoDistance, geoInterpolate } from 'd3-geo';
import { camCurve, quat } from '@/geo/camera';
import type { Quat, Rotation } from '@/geo/camera';
import { Z_MIN } from '@/geo/projection';
import type { LonLat } from '@/geo/vector';
import { smooth, smoother } from '@/lib/easing';
import { clamp } from '@/lib/math';

/** The plane fades in standing still, then flies. */
export const APPEAR_MS = 700;
/** It stops and fades out before the place lights up. */
export const VANISH_MS = 380;
export const EARTH_KM = 6371;

export type FlightPhase = 'appear' | 'cruise' | 'vanish' | 'done';

export interface Flight {
  to: LonLat;
  /** The great circle, 0..1; null when there is nowhere to fly from: the camera only turns. */
  path: ((k: number) => LonLat) | null;
  km: number;
  q0: Quat;
  q1: Quat;
  /** Radians from the middle of the view to the destination: how high the camera rises. */
  rise: number;
  /** For a camera-only turn. */
  cameraMs: number;
  phase: FlightPhase;
  phaseMs: number;
  /** The plane's share of the way, at constant speed. */
  e: number;
  /** The camera's share of the turn. */
  c: number;
  /** False once the owner drags the globe: the camera lets go, the plane flies on. */
  follow: boolean;
}

/** A camera-only turn takes 2 s, up to 4 s for the far side of the globe. */
export const cameraTurnMs = (radians: number): number =>
  2000 + 2000 * clamp(radians / Math.PI, 0, 1);

export const createFlight = ({
  from,
  to,
  rot,
}: {
  from: LonLat | null;
  to: LonLat;
  rot: Rotation;
}): Flight => {
  const distance = from === null ? 0 : geoDistance(from, to);
  const flies = from !== null && distance > 1e-4;
  const rise = geoDistance([-rot[0], -rot[1]], to);
  return {
    to,
    path: flies && from !== null ? geoInterpolate(from, to) : null,
    km: flies ? distance * EARTH_KM : 0,
    q0: quat(rot),
    q1: quat([-to[0], -to[1], 0]),
    rise,
    cameraMs: cameraTurnMs(rise),
    phase: flies ? 'appear' : 'cruise',
    phaseMs: 0,
    e: 0,
    c: 0,
    follow: true,
  };
};

export const stepFlight = (flight: Flight, dt: number, cruiseMs: number): void => {
  if (!flight.path) {
    flight.e = Math.min(1, flight.e + dt / flight.cameraMs);
    flight.c = smoother(flight.e);
    if (flight.e >= 1) flight.phase = 'done';
    return;
  }
  switch (flight.phase) {
    case 'appear':
      flight.phaseMs += dt;
      if (flight.phaseMs >= APPEAR_MS) {
        flight.phase = 'cruise';
        flight.phaseMs = 0;
      }
      break;
    case 'cruise':
      flight.e = Math.min(1, flight.e + dt / cruiseMs);
      if (flight.e >= 1) {
        flight.phase = 'vanish';
        flight.phaseMs = 0;
      }
      break;
    case 'vanish':
      flight.phaseMs += dt;
      if (flight.phaseMs >= VANISH_MS) flight.phase = 'done';
      break;
    case 'done':
      break;
  }
  flight.c = camCurve(flight.e);
};

export const planeAlpha = ({ phase, phaseMs }: Flight): number => {
  if (phase === 'appear') return smooth(clamp(phaseMs / APPEAR_MS, 0, 1));
  if (phase === 'vanish') return 1 - smooth(clamp(phaseMs / VANISH_MS, 0, 1));
  if (phase === 'done') return 0;
  return 1;
};

/** The camera rises mid-flight in proportion to the distance, and settles on arrival. */
export const riseZoom = (z: number, { c, rise }: Flight): number =>
  Math.max(Z_MIN, z * (1 - 0.45 * Math.sin(Math.PI * c) * Math.min(1, rise / 1.4)));
```

- [ ] **Step 5: Run the tests**

Run: `npx vitest run src/tour/flight.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/geo/vector.ts src/tour
git commit -m "feat(tour): add flight phases and the flight camera"
```

---

### Task 4: Tours and the next step

**Files:**
- Create: `src/tour/tour.ts`
- Test: `src/tour/tour.test.ts`

**Interfaces:**
- Consumes: `Archive` (`src/data/archive.ts`), `Endpoint`, `Trip` (`src/data/types.ts`), `within`, `Range` (`src/timeline/range.ts`).
- Produces:
  - `interface Tour { kind: 'year' | 'trip'; list: number[]; start: Endpoint | null; end: Endpoint | null; name: string; tripId: string | null; year: number | null }`
  - `type TourStep = { kind: 'album'; index: number } | { kind: 'end'; end: Endpoint } | { kind: 'stop' }`
  - `nextInRange(from: number, dir: 1 | -1, times: readonly number[], range: Range | null): number`
  - `nextStep(tour: Tour | null, focus: number, times: readonly number[], range: Range | null): TourStep`
  - `cityAlbums(archive: Archive, cityKey: string): number[]`, `scopedAlbums(indices: number[], tour: Tour | null): number[]`
  - `yearTour(year: number, archive: Archive): Tour | null`, `tripTour(trip: Trip, archive: Archive): Tour | null`

- [ ] **Step 1: Write the failing test**

`src/tour/tour.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { linkArchive } from '@/data/archive';
import { buildDemo } from '@/data/demo';
import type { Credit } from '@/data/types';
import { albumTime, yearRange } from '@/timeline/range';
import { cityAlbums, nextInRange, nextStep, scopedAlbums, tripTour, yearTour } from './tour';

const file = fileURLToPath(new URL('../../public/demo/photos.json', import.meta.url));
const archive = linkArchive(buildDemo(JSON.parse(readFileSync(file, 'utf8')) as Credit[]));
const times = archive.albums.map(albumTime);
const titles = (list: number[]) => list.map((i) => archive.albums[i]?.title);
const tripNamed = (name: string) => {
  const trip = archive.trips.find((t) => t.name === name);
  if (!trip) throw new Error(name);
  return trip;
};

describe('tours', () => {
  it('goes through a year in date order', () => {
    const tour = yearTour(2023, archive);
    expect(tour?.kind).toBe('year');
    expect(tour?.end).toBeNull();
    expect(tour?.list).toHaveLength(5);
    expect(tour?.list).toEqual([...(tour?.list ?? [])].sort((a, b) => a - b));
    expect(yearTour(1999, archive)).toBeNull();
  });

  it('goes through a trip in date order and knows where it ends', () => {
    const tour = tripTour(tripNamed('Japan in bloom'), archive);
    expect(titles(tour?.list ?? []).sort()).toEqual(['Bamboo grove', 'Neon and quiet', 'Sakura week']);
    expect(tour?.end).toEqual({ home: true });
    expect(tour?.tripId).toBe(tripNamed('Japan in bloom').id);
  });
});

describe('nextStep', () => {
  it('visits the next album of a trip, then flies to its end', () => {
    const tour = tripTour(tripNamed('Japan in bloom'), archive);
    if (!tour) throw new Error('no tour');
    const [first, second, last] = tour.list;
    expect(nextStep(tour, first ?? -1, times, null)).toEqual({ kind: 'album', index: second });
    expect(nextStep(tour, last ?? -1, times, null)).toEqual({ kind: 'end', end: { home: true } });
  });

  it('stops a year at its last album', () => {
    const tour = yearTour(2023, archive);
    if (!tour) throw new Error('no tour');
    expect(nextStep(tour, tour.list[tour.list.length - 1] ?? -1, times, null)).toEqual({
      kind: 'stop',
    });
  });

  it('plays on through the range with no tour, and stops at its end', () => {
    const range = yearRange(2019);
    const inRange = times.flatMap((t, i) => (t >= 2019 && t < 2020 ? [i] : []));
    expect(nextStep(null, -1, times, range)).toEqual({ kind: 'album', index: inRange[0] });
    expect(nextStep(null, inRange[inRange.length - 1] ?? -1, times, range)).toEqual({
      kind: 'stop',
    });
  });

  it('steps back through the range too', () => {
    const range = yearRange(2019);
    const inRange = times.flatMap((t, i) => (t >= 2019 && t < 2020 ? [i] : []));
    expect(nextInRange(inRange[1] ?? -1, -1, times, range)).toBe(inRange[0]);
    expect(nextInRange(inRange[0] ?? -1, -1, times, range)).toBe(-1);
  });
});

describe('scopedAlbums', () => {
  it('keeps to the tour, or shows every album of the place', () => {
    const kyoto = cityAlbums(archive, 'kyoto');
    expect(kyoto).toHaveLength(3);
    const tour = tripTour(tripNamed('Japan in autumn'), archive);
    expect(titles(scopedAlbums(kyoto, tour))).toEqual(['Autumn temples']);
    expect(scopedAlbums(kyoto, null)).toEqual(kyoto);
    const paris = tripTour(tripNamed('Paris in April'), archive);
    expect(scopedAlbums(kyoto, paris)).toEqual(kyoto);
  });
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/tour/tour.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

`src/tour/tour.ts`:

```ts
import type { Archive } from '@/data/archive';
import type { Endpoint, Trip } from '@/data/types';
import { within } from '@/timeline/range';
import type { Range } from '@/timeline/range';

/** A year or a trip shown on the map: its albums (indices into archive.albums), in order. */
export interface Tour {
  kind: 'year' | 'trip';
  list: number[];
  start: Endpoint | null;
  /** Where a trip ends; a year has no end flight. */
  end: Endpoint | null;
  name: string;
  tripId: string | null;
  year: number | null;
}

export type TourStep =
  | { kind: 'album'; index: number }
  | { kind: 'end'; end: Endpoint }
  | { kind: 'stop' };

export const nextInRange = (
  from: number,
  dir: 1 | -1,
  times: readonly number[],
  range: Range | null,
): number => {
  for (let i = from + dir; i >= 0 && i < times.length; i += dir) {
    const t = times[i];
    if (t !== undefined && within(t, range)) return i;
  }
  return -1;
};

/** What comes after the album in focus: the tour's next album, its end flight, or the range's. */
export const nextStep = (
  tour: Tour | null,
  focus: number,
  times: readonly number[],
  range: Range | null,
): TourStep => {
  if (tour) {
    const next = tour.list[tour.list.indexOf(focus) + 1];
    if (next !== undefined) return { kind: 'album', index: next };
    return tour.end ? { kind: 'end', end: tour.end } : { kind: 'stop' };
  }
  const index = nextInRange(focus, 1, times, range);
  return index < 0 ? { kind: 'stop' } : { kind: 'album', index };
};

/** The albums of a city, oldest first. */
export const cityAlbums = (archive: Archive, cityKey: string): number[] =>
  archive.albums.flatMap((album, index) => (album.city.key === cityKey ? [index] : []));

/** In a tour, only the tour's albums of this place (all of them if it has none). */
export const scopedAlbums = (indices: number[], tour: Tour | null): number[] => {
  if (!tour) return indices;
  const mine = indices.filter((index) => tour.list.includes(index));
  return mine.length > 0 ? mine : indices;
};

export const yearTour = (year: number, archive: Archive): Tour | null => {
  const list = archive.albums.flatMap((album, index) => (album.year === year ? [index] : []));
  return list.length === 0
    ? null
    : { kind: 'year', list, start: null, end: null, name: String(year), tripId: null, year };
};

export const tripTour = (trip: Trip, archive: Archive): Tour | null => {
  const list = trip.albumIds
    .map((id) => archive.albums.findIndex((album) => album.id === id))
    .filter((index) => index >= 0)
    .sort((a, b) => a - b);
  return list.length === 0
    ? null
    : {
        kind: 'trip',
        list,
        start: trip.start,
        end: trip.end,
        name: trip.name,
        tripId: trip.id,
        year: null,
      };
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/tour/tour.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tour/tour.ts src/tour/tour.test.ts
git commit -m "feat(tour): add year and trip tours and the next step"
```

---

### Task 5: The director

**Files:**
- Modify: `src/state/app-state.ts`
- Create: `src/tour/director.ts`
- Test: `src/tour/director.test.ts`

**Interfaces:**
- Consumes: Tasks 1–4; `euler`, `slerp`, `Rotation` (`src/geo/camera.ts`); `Store` (`src/state/store.ts`); `PlaceFacts` (`src/render/places.ts`).
- Produces:
  - `AppState` gains `focus: number; atHome: boolean; flying: boolean; flightKm: number | null; endCard: EndCard | null; range: Range | null; picking: Range | null; progress: boolean; playing: boolean; tour: Tour | null; lastTour: Tour | null`; `interface EndCard { home: boolean; cityKey: string | null; fromAlbumId: string; tour: Tour | null }`; `INITIAL_STATE: AppState`
  - `interface Pace { photoMs: number; flightMs: number }`, `interface Drive { rot: Rotation | null; zoom: number; steering: boolean }`
  - `interface DirectorView { focusCityKey; reached; inLive; rangeActive; homeLit; homePulseAt; pulseAt; route; leg; plane; now }`
  - `createDirector({ archive, home, store, pace }): Director` with: `step(dt, rot, z): Drive`, `view(): DirectorView`, `focused` (getter), `pickCity(key)`, `selectAlbum(index)`, `letGo()`, `deselect()`, `escape()`, `play()`, `stop()`, `next(dir)`, `scroll(dir)`, `beginPick(t)`, `movePick(t)`, `endPick(t, moved): 'ok' | 'empty'`, `cancelPick()`, `clickYear(year): 'ok' | 'empty' | 'open'`, `clearRange()`, `showYear(year): boolean`, `showTrip(tripId): boolean`, `showAlbumOnMap(albumId): boolean`; `type Director`
  - `placeFacts(view: DirectorView, cityKey: string): PlaceFacts`, `DWELL_MIN_MS = 3500`

- [ ] **Step 1: Extend the app state**

`src/state/app-state.ts`:

```ts
import type { Range } from '@/timeline/range';
import type { Tour } from '@/tour/tour';
import { createStore } from './store';

/** The panel's card when a trip has ended: home, or the city it ended in. */
export interface EndCard {
  home: boolean;
  cityKey: string | null;
  /** The last album before the end flight. */
  fromAlbumId: string;
  tour: Tour | null;
}

export interface AppState {
  /**
   * The city the hover label shows. It keeps the last city after the cursor leaves, so the label
   * can fade out with its text still in it.
   */
  labelCityKey: string | null;
  /** True while the photo window or the archive is open: the world clock stops. */
  paused: boolean;
  /** Album index (into archive.albums) in focus, -1 for none. */
  focus: number;
  /** The plane has landed at home after a trip. */
  atHome: boolean;
  /** A flight (or a camera turn) is under way. */
  flying: boolean;
  /** Length of the flight under way, for the caption. */
  flightKm: number | null;
  endCard: EndCard | null;
  range: Range | null;
  /** The range being dragged out on the timeline, before it is let go. */
  picking: Range | null;
  /** Yellow progress on; off after a new pick until the plane moves again. */
  progress: boolean;
  playing: boolean;
  tour: Tour | null;
  /** The tour that just ended, still shown above the end card. */
  lastTour: Tour | null;
}

export const INITIAL_STATE: AppState = {
  labelCityKey: null,
  paused: false,
  focus: -1,
  atHome: false,
  flying: false,
  flightKm: null,
  endCard: null,
  range: null,
  picking: null,
  progress: true,
  playing: false,
  tour: null,
  lastTour: null,
};

export const appStore = createStore<AppState>({ ...INITIAL_STATE });
```

- [ ] **Step 2: Write the failing test**

`src/tour/director.test.ts`:

```ts
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { geoDistance, geoRotation } from 'd3-geo';
import { describe, expect, it } from 'vitest';
import { linkArchive } from '@/data/archive';
import { buildDemo, DEMO_HOME } from '@/data/demo';
import type { Credit } from '@/data/types';
import type { Rotation } from '@/geo/camera';
import { INITIAL_STATE } from '@/state/app-state';
import type { AppState } from '@/state/app-state';
import { createStore } from '@/state/store';
import { albumTime } from '@/timeline/range';
import { createDirector, DWELL_MIN_MS, placeFacts } from './director';
import { APPEAR_MS, VANISH_MS } from './flight';

const file = fileURLToPath(new URL('../../public/demo/photos.json', import.meta.url));
const archive = linkArchive(buildDemo(JSON.parse(readFileSync(file, 'utf8')) as Credit[]));
const FLIGHT_MS = 1000;
const LEG_MS = APPEAR_MS + FLIGHT_MS + VANISH_MS + 100;
const indexOf = (title: string) => archive.albums.findIndex((a) => a.title === title);
const tripId = (name: string) => archive.trips.find((t) => t.name === name)?.id ?? '';

const setup = () => {
  const store = createStore<AppState>({ ...INITIAL_STATE });
  const director = createDirector({
    archive,
    home: DEMO_HOME,
    store,
    pace: () => ({ photoMs: 1000, flightMs: FLIGHT_MS }),
  });
  let rot: Rotation = [-10, -35, 0];
  const changes: { focus: number; flying: boolean }[] = [];
  const run = (ms: number) => {
    for (let t = 0; t < ms; t += 20) {
      const before = store.get().focus;
      const drive = director.step(20, rot, 1);
      if (drive.rot) rot = drive.rot;
      if (store.get().focus !== before) changes.push({ focus: store.get().focus, flying: store.get().flying });
    }
  };
  const state = () => store.get();
  const centre = () => geoRotation(rot).invert([0, 0]);
  return { store, director, run, state, centre, changes };
};

describe('picking a place', () => {
  it('flies from home to the earliest album of the place', () => {
    const { director, run, state } = setup();
    director.pickCity('paris');
    expect(state().focus).toBe(indexOf('First trip abroad'));
    expect(state().flying).toBe(true);
    expect(state().flightKm).toBeGreaterThan(1990);
    expect(state().flightKm).toBeLessThan(2060);
    // the plane stands at home before take-off: the house is lit
    expect(director.view().homeLit).toBe(1);
    run(APPEAR_MS + 40);
    expect(director.view().homeLit).toBe(0);
    expect(director.view().plane).not.toBeNull();
    run(LEG_MS);
    expect(state().flying).toBe(false);
    expect(director.view().focusCityKey).toBe('paris');
    expect(director.view().pulseAt.get('paris')).toBeGreaterThan(0);
  });

  it('turns the camera onto the place on landing', () => {
    const { director, run, centre } = setup();
    director.pickCity('paris');
    run(LEG_MS);
    expect(geoDistance(centre(), [2.35, 48.86])).toBeLessThan(0.01);
  });

  it('switches albums in the same city without a flight', () => {
    const { director, run, state } = setup();
    director.pickCity('paris');
    run(LEG_MS);
    director.selectAlbum(indexOf('Paris again'));
    expect(state().focus).toBe(indexOf('Paris again'));
    expect(state().flying).toBe(false);
    director.pickCity('paris');
    expect(state().flying).toBe(false);
  });

  it('redirects from mid-air', () => {
    const { director, run, state } = setup();
    director.pickCity('paris');
    run(APPEAR_MS + FLIGHT_MS / 2);
    director.pickCity('rome');
    const fromHalfway = state().flightKm ?? 0;
    // Kyiv → Rome is about 1680 km; from halfway to Paris it is much shorter
    expect(fromHalfway).toBeGreaterThan(0);
    expect(fromHalfway).toBeLessThan(1400);
  });

  it('lets go of the camera when the owner drags during a flight', () => {
    const { director, run, state } = setup();
    director.pickCity('paris');
    run(APPEAR_MS + 100);
    director.letGo();
    expect(director.step(20, [0, 0, 0], 1).rot).toBeNull();
    run(LEG_MS);
    expect(state().flying).toBe(false);
    expect(director.view().focusCityKey).toBe('paris');
  });

  it('waits while the world is paused', () => {
    const { director, state } = setup();
    director.pickCity('paris');
    for (let i = 0; i < 500; i++) director.step(0, [0, 0, 0], 1);
    expect(state().flying).toBe(true);
    expect(director.view().homeLit).toBe(1);
  });

  it('lets go of the place and then of the range on Esc', () => {
    const { director, run, state } = setup();
    director.clickYear(2022);
    director.pickCity('paris');
    run(LEG_MS);
    director.escape();
    expect(state().focus).toBe(-1);
    expect(state().range?.year).toBe(2022);
    director.escape();
    expect(state().range).toBeNull();
  });
});

describe('the timeline', () => {
  it('picks a dragged stretch and starts the yellow over', () => {
    const { director, run, state } = setup();
    director.pickCity('paris');
    run(LEG_MS);
    expect(director.view().reached.has('paris')).toBe(true);
    director.beginPick(2019);
    director.movePick(2020.5);
    expect(state().picking).toEqual({ lo: 2019, hi: 2020.5 });
    expect(director.endPick(2020.5, true)).toBe('ok');
    expect(state().range).toEqual({ lo: 2019, hi: 2020.5 });
    expect(state().progress).toBe(false);
    const view = director.view();
    expect(view.reached.size).toBe(0);
    expect(view.inLive.has('barcelona')).toBe(true);
    expect(view.inLive.has('tokyo')).toBe(false);
    expect(placeFacts(view, 'tokyo')).toEqual({
      focused: false,
      reached: false,
      inRange: false,
      rangeActive: true,
    });
  });

  it('picks everything from the start with a click', () => {
    const { director, state } = setup();
    director.beginPick(2018.5);
    director.endPick(2018.5, false);
    expect(state().range).toEqual({ lo: 2016, hi: 2018.5 });
  });

  it('refuses a stretch with no album', () => {
    const { director, state } = setup();
    director.beginPick(2016.9);
    expect(director.endPick(2016.95, true)).toBe('empty');
    expect(state().range).toBeNull();
    expect(state().picking).toBeNull();
  });

  it('picks a year, and asks for the archive on a second click', () => {
    const { director, state } = setup();
    expect(director.clickYear(2023)).toBe('ok');
    expect(state().range?.year).toBe(2023);
    expect(director.clickYear(2023)).toBe('open');
  });

  it('refuses a year without albums', () => {
    const { director, state } = setup();
    expect(director.clickYear(2026)).toBe('empty');
    expect(state().range).toBeNull();
  });
});

describe('tours', () => {
  it('flies a trip from its start through its albums and home, with the light on', () => {
    const { director, run, state, changes } = setup();
    expect(director.showTrip(tripId('Japan in bloom'))).toBe(true);
    expect(state().tour?.name).toBe('Japan in bloom');
    expect(state().playing).toBe(true);
    expect(state().flying).toBe(true);
    run(40000);
    expect(state().atHome).toBe(true);
    expect(state().endCard?.home).toBe(true);
    expect(state().playing).toBe(false);
    expect(state().tour).toBeNull();
    expect(state().lastTour?.name).toBe('Japan in bloom');
    expect(director.view().homeLit).toBe(1);
    expect(director.view().homePulseAt).toBeGreaterThan(0);
    // albums in the same city switch without a flight
    for (let k = 1; k < changes.length; k++) {
      const a = archive.albums[changes[k - 1]?.focus ?? -1];
      const b = archive.albums[changes[k]?.focus ?? -1];
      if (a && b && a.city === b.city) expect(changes[k]?.flying).toBe(false);
    }
  });

  it('shows a year, starts at its first album and stops at its last', () => {
    const { director, run, state } = setup();
    expect(director.showYear(2023)).toBe(true);
    const tour = state().tour;
    expect(state().range?.year).toBe(2023);
    expect(state().focus).toBe(tour?.list[0]);
    expect(state().flying).toBe(false);
    expect(state().playing).toBe(true);
    run(60000);
    expect(state().focus).toBe(tour?.list[tour.list.length - 1]);
    expect(state().playing).toBe(false);
    expect(state().endCard).toBeNull();
    // ▶ plays the year again
    director.play();
    expect(state().focus).toBe(tour?.list[0]);
  });

  it('rests on each place before flying on', () => {
    const { director, run, state } = setup();
    director.showYear(2023);
    const first = state().focus;
    run(DWELL_MIN_MS - 200);
    expect(state().focus).toBe(first);
  });

  it('leaves a tour when a light outside it is picked', () => {
    const { director, state } = setup();
    director.showYear(2023);
    director.pickCity('cusco');
    expect(state().tour).toBeNull();
    expect(state().focus).toBe(indexOf('Up to Machu Picchu'));
  });

  it('plays the range from its start', () => {
    const { director, state } = setup();
    director.clickYear(2017);
    director.play();
    const first = archive.albums[state().focus];
    expect(first?.year).toBe(2017);
    expect(state().playing).toBe(true);
  });

  it('shows one album on the map without playing', () => {
    const { director, state } = setup();
    const index = indexOf('Tram 28');
    expect(director.showAlbumOnMap(archive.albums[index]?.id ?? '')).toBe(true);
    const t = albumTime(archive.albums[index] ?? { year: 0, month: 1, day: 1, time: '00:00' });
    expect(state().range).toEqual({ lo: t, hi: t });
    expect(state().focus).toBe(index);
    expect(state().playing).toBe(false);
    expect(state().flying).toBe(false);
  });
});
```

- [ ] **Step 3: Run it to see it fail**

Run: `npx vitest run src/tour/director.test.ts`
Expected: FAIL — cannot resolve `./director`.

- [ ] **Step 4: Implement**

`src/tour/director.ts`:

```ts
import { geoDistance } from 'd3-geo';
import type { Archive } from '@/data/archive';
import { endpointPlace } from '@/data/trips';
import type { City, Endpoint, Place } from '@/data/types';
import { euler, slerp } from '@/geo/camera';
import type { Rotation } from '@/geo/camera';
import type { LonLat } from '@/geo/vector';
import { clamp } from '@/lib/math';
import type { PlaceFacts } from '@/render/places';
import type { AppState } from '@/state/app-state';
import type { Store } from '@/state/store';
import { albumTime, isReached, pickedRange, span, within, yearRange } from '@/timeline/range';
import { createFlight, planeAlpha, riseZoom, stepFlight } from './flight';
import type { Flight } from './flight';
import { cityAlbums, nextInRange, nextStep, scopedAlbums, tripTour, yearTour } from './tour';

export interface Pace {
  photoMs: number;
  flightMs: number;
}

export interface DirectorOptions {
  archive: Archive;
  home: Place;
  store: Store<AppState>;
  pace: () => Pace;
}

/** What the director asks of the camera this frame. */
export interface Drive {
  /** The camera's rotation, when the director steers it. */
  rot: Rotation | null;
  /** The zoom with the mid-flight rise. */
  zoom: number;
  steering: boolean;
}

export interface LegView {
  path: (k: number) => LonLat;
  upto: number;
  alpha: number;
}

export interface PlaneView {
  at: LonLat;
  behind: LonLat;
  ahead: LonLat;
  alpha: number;
}

/** Everything the engine draws from the journey. */
export interface DirectorView {
  focusCityKey: string | null;
  reached: ReadonlySet<string>;
  inLive: ReadonlySet<string>;
  rangeActive: boolean;
  /** 0 or 1: someone is home. */
  homeLit: number;
  homePulseAt: number;
  pulseAt: ReadonlyMap<string, number>;
  /** Faint great circles between the places already reached. */
  route: [LonLat, LonLat][];
  leg: LegView | null;
  plane: PlaneView | null;
  now: number;
}

/** After a landing, a playing tour rests on the place at least this long. */
export const DWELL_MIN_MS = 3500;
/** The last leg fades to a trace over this time. */
const LEG_FADE_MS = 3000;

export const placeFacts = (view: DirectorView, cityKey: string): PlaceFacts => ({
  focused: view.focusCityKey === cityKey,
  reached: view.reached.has(cityKey),
  inRange: view.inLive.has(cityKey),
  rangeActive: view.rangeActive,
});

interface Leg {
  flight: Flight;
  /** The city of the album in focus; null for a trip's end flight. */
  city: City | null;
  end: Endpoint | null;
  fromHome: boolean;
}

/**
 * The journey on the globe: which album is in focus, the flight to it, tours, the timeline range.
 * Pure: the engine calls `step` every frame with the world time and draws `view()`; React reads
 * the store and calls the other methods.
 */
export const createDirector = ({ archive, home, store, pace }: DirectorOptions) => {
  const albums = archive.albums;
  const times = albums.map(albumTime);
  const [firstYear] = span(times);
  const homeAt: LonLat = [home.lon, home.lat];
  const at = (city: City): LonLat => [city.lon, city.lat];
  const timeOf = (index: number) => times[index] ?? 0;
  const get = store.get;
  const set = store.set;

  let now = 0;
  let rot: Rotation = [0, 0, 0];
  let leg: Leg | null = null;
  let lastLeg: { path: (k: number) => LonLat; end: number } | null = null;
  /** Where the next flight starts when it is not the place in focus: a trip's start or end. */
  let origin: LonLat | null = null;
  let snap: Rotation | null = null;
  let dwell = 0;
  let pickFrom: number | null = null;
  const pulseAt = new Map<string, number>();
  let homePulseAt = -Infinity;

  const dwellMs = () => Math.max(DWELL_MIN_MS, pace().photoMs);

  const stop = () => {
    dwell = 0;
    set({ playing: false });
  };

  const leaveTour = () => {
    if (!get().tour) return;
    set({ tour: null });
    stop();
  };

  /** Another album of the place already in focus: no flight. */
  const showAlbum = (index: number) => set({ focus: index });

  const flyTo = (index: number) => {
    const album = albums[index];
    if (!album) return;
    const { focus, endCard } = get();
    const here = leg ? leg.city : endCard ? null : (albums[focus]?.city ?? null);
    if (here === album.city) {
      showAlbum(index);
      return;
    }
    const focusCity = albums[focus]?.city;
    const from: LonLat | null = leg
      ? leg.flight.path
        ? leg.flight.path(leg.flight.e)
        : null
      : (origin ?? (focusCity ? at(focusCity) : homeAt));
    const fromHome = leg === null && from !== null && geoDistance(from, homeAt) < 1e-4;
    origin = null;
    const flight = createFlight({ from, to: at(album.city), rot });
    leg = { flight, city: album.city, end: null, fromHome };
    set({
      focus: index,
      atHome: false,
      endCard: null,
      progress: true,
      flying: true,
      flightKm: flight.km > 0 ? flight.km : null,
    });
  };

  /** Fly there; if no flight was needed, rest there before the next step. */
  const go = (index: number) => {
    flyTo(index);
    if (!leg) dwell = dwellMs();
  };

  /** The last leg of a trip: to its end, home or another city, with the end card in the panel. */
  const flyEnd = (end: Endpoint) => {
    const { focus, tour } = get();
    const last = albums[focus];
    if (!last) {
      set({ tour: null });
      stop();
      return;
    }
    const place = endpointPlace(end, archive, home);
    const flight = createFlight({ from: at(last.city), to: [place.lon, place.lat], rot });
    leg = { flight, city: null, end, fromHome: false };
    set({
      flying: true,
      flightKm: flight.km > 0 ? flight.km : null,
      lastTour: tour,
      endCard: { home: place.cityKey === null, cityKey: place.cityKey, fromAlbumId: last.id, tour },
    });
  };

  const playNext = () => {
    dwell = 0;
    const { playing, tour, focus, range } = get();
    if (!playing) return;
    const step = nextStep(tour, focus, times, range);
    if (step.kind === 'album') go(step.index);
    else if (step.kind === 'end') flyEnd(step.end);
    else stop();
  };

  const arrive = () => {
    const done = leg;
    if (!done) return;
    leg = null;
    if (done.flight.path) lastLeg = { path: done.flight.path, end: now };
    if (done.city) pulseAt.set(done.city.key, now);
    const patch: Partial<AppState> = { flying: false, flightKm: null };
    if (done.end) {
      origin = done.flight.to;
      const card = get().endCard;
      if (card?.cityKey) pulseAt.set(card.cityKey, now);
      else homePulseAt = now;
      patch.atHome = card?.home ?? true;
      patch.tour = null;
      patch.playing = false;
      dwell = 0;
    }
    set(patch);
    if (get().playing) dwell = dwellMs();
  };

  const deselect = () => {
    leg = null;
    lastLeg = null;
    origin = null;
    dwell = 0;
    set({
      focus: -1,
      atHome: false,
      endCard: null,
      tour: null,
      playing: false,
      flying: false,
      flightKm: null,
    });
  };

  /** The place in focus without a flight: the light pulses, the panel shows its photos. */
  const focusOn = (index: number) => {
    const album = albums[index];
    if (!album) return;
    leg = null;
    set({ focus: index, atHome: false, endCard: null, progress: true, flying: false, flightKm: null });
    pulseAt.set(album.city.key, now);
  };

  const snapTo = ([lon, lat]: LonLat) => {
    snap = [-lon, -lat, 0];
  };

  /** Leave whatever was on: "Show on map" starts clean. */
  const toMap = () => {
    if (get().focus >= 0 || get().endCard) deselect();
    stop();
    set({ tour: null, picking: null });
  };

  const view = (): DirectorView => {
    const { focus, progress, range, picking, endCard, atHome } = get();
    const live = picking ?? range;
    const state = { on: progress, focus, ahead: leg !== null && leg.end === null, range };
    const reachedFlags = albums.map((_, k) => isReached(k, timeOf(k), state));
    const reached = new Set<string>();
    const inLive = new Set<string>();
    const route: [LonLat, LonLat][] = [];
    albums.forEach((album, k) => {
      if (reachedFlags[k]) reached.add(album.city.key);
      if (live && within(timeOf(k), live)) inLive.add(album.city.key);
      const previous = albums[k - 1];
      if (k > 0 && k <= focus && previous && reachedFlags[k - 1] && reachedFlags[k]) {
        route.push([at(previous.city), at(album.city)]);
      }
    });

    const flight = leg?.flight;
    let legView: LegView | null = null;
    if (flight) {
      legView = flight.path ? { path: flight.path, upto: flight.e, alpha: 0.9 } : null;
    } else if (lastLeg) {
      const alpha = clamp(1 - (now - lastLeg.end) / LEG_FADE_MS, 0.25, 0.9);
      legView = { path: lastLeg.path, upto: 1, alpha };
    }
    const plane =
      flight?.path && flight.phase !== 'done'
        ? {
            at: flight.path(flight.e),
            behind: flight.path(Math.max(0, flight.e - 0.003)),
            ahead: flight.path(Math.min(1, flight.e + 0.003)),
            alpha: planeAlpha(flight),
          }
        : null;

    const standing = leg !== null && leg.fromHome && leg.flight.phase === 'appear';
    return {
      focusCityKey: focus >= 0 && !leg && !endCard ? (albums[focus]?.city.key ?? null) : null,
      reached,
      inLive,
      rangeActive: live !== null,
      homeLit: atHome || standing ? 1 : 0,
      homePulseAt,
      pulseAt,
      route,
      leg: legView,
      plane,
      now,
    };
  };

  return {
    step(dt: number, current: Rotation, z: number): Drive {
      now += dt;
      rot = current;
      let turnTo: Rotation | null = null;
      if (snap) {
        turnTo = snap;
        rot = snap;
        snap = null;
      }
      let zoom = z;
      if (leg) {
        const flight = leg.flight;
        stepFlight(flight, dt, pace().flightMs);
        if (flight.follow) {
          turnTo = euler(slerp(flight.q0, flight.q1, flight.c));
          rot = turnTo;
        }
        zoom = riseZoom(z, flight);
        if (flight.phase === 'done') arrive();
      }
      if (dwell > 0) {
        dwell -= dt;
        if (dwell <= 0) playNext();
      }
      return { rot: turnTo, zoom, steering: turnTo !== null };
    },

    view,

    /** A place is in focus: the Earth does not spin by itself. */
    get focused(): boolean {
      return get().focus >= 0;
    },

    /** A light was clicked: its album inside the tour or the range, or its earliest one. */
    pickCity(cityKey: string) {
      const own = cityAlbums(archive, cityKey);
      if (own.length === 0) return;
      stop();
      const before = get().tour;
      if (before && !own.some((index) => before.list.includes(index))) leaveTour();
      const { tour, range, focus, endCard } = get();
      const index =
        (tour ? own.find((i) => tour.list.includes(i)) : undefined) ??
        own.find((i) => within(timeOf(i), range)) ??
        own[0];
      if (index === undefined) return;
      const landedHere = !leg && !endCard && albums[focus]?.city.key === cityKey;
      if (!landedHere) flyTo(index);
    },

    /** An album of the place in focus, from the panel. */
    selectAlbum(index: number) {
      stop();
      showAlbum(index);
    },

    /** The owner dragged the globe: the camera lets go, the plane flies on. */
    letGo() {
      if (leg) leg.flight.follow = false;
    },

    deselect,

    /** Esc on the main screen: let go of the place, then of the range. */
    escape() {
      if (get().focus >= 0 || get().endCard) deselect();
      else {
        pickFrom = null;
        set({ range: null, picking: null });
      }
    },

    play() {
      const { playing, tour, focus, endCard } = get();
      if (playing) {
        stop();
        return;
      }
      if (tour && focus >= 0 && !endCard) {
        set({ playing: true });
        const at = tour.list.indexOf(focus);
        const first = tour.list[0];
        // at the last album of a year, ▶ plays the year again
        if (!tour.end && at === tour.list.length - 1 && first !== undefined) go(first);
        else playNext();
        return;
      }
      set({ tour: null, playing: true });
      const { range } = get();
      const next = nextInRange(focus, 1, times, range);
      const index = next >= 0 ? next : nextInRange(-1, 1, times, range);
      if (index < 0) stop();
      else go(index);
    },

    stop,

    /** ← → : the previous or next album in the range. */
    next(dir: 1 | -1) {
      stop();
      const index = nextInRange(get().focus, dir, times, get().range);
      if (index >= 0) flyTo(index);
    },

    /** ↑ ↓ : the albums of the place in focus, in a loop. */
    scroll(dir: 1 | -1) {
      const album = albums[get().focus];
      if (!album || get().endCard) return;
      const list = scopedAlbums(cityAlbums(archive, album.city.key), get().tour);
      const at = list.indexOf(get().focus);
      const index = list[(((at + dir) % list.length) + list.length) % list.length];
      stop();
      if (index !== undefined) showAlbum(index);
    },

    beginPick(t: number) {
      pickFrom = t;
      set({ range: null, picking: { lo: t, hi: t } });
    },

    movePick(t: number) {
      if (pickFrom === null) return;
      set({ picking: { lo: Math.min(pickFrom, t), hi: Math.max(pickFrom, t) } });
    },

    endPick(t: number, moved: boolean): 'ok' | 'empty' {
      const start = pickFrom ?? t;
      pickFrom = null;
      leaveTour();
      const next = pickedRange(start, t, moved, firstYear);
      if (!times.some((time) => within(time, next))) {
        set({ range: null, picking: null });
        return 'empty';
      }
      set({ range: next, picking: null, progress: false });
      return 'ok';
    },

    cancelPick() {
      pickFrom = null;
      set({ picking: null });
    },

    /** A year on the timeline: picks it; the picked year again asks for the archive. */
    clickYear(year: number): 'ok' | 'empty' | 'open' {
      if (!albums.some((album) => album.year === year)) return 'empty';
      if (get().range?.year === year) return 'open';
      leaveTour();
      set({ range: yearRange(year), picking: null, progress: false });
      return 'ok';
    },

    clearRange() {
      pickFrom = null;
      set({ range: null, picking: null });
    },

    /** Show on map: a year. Its first album in focus, then the tour plays the year. */
    showYear(year: number): boolean {
      const tour = yearTour(year, archive);
      const first = tour?.list[0];
      const album = first === undefined ? undefined : albums[first];
      if (!tour || first === undefined || !album) return false;
      toMap();
      set({ range: yearRange(year), tour });
      snapTo(at(album.city));
      focusOn(first);
      set({ playing: true });
      dwell = dwellMs();
      return true;
    },

    /** Show on map: a trip. The globe looks at its start and the plane takes off from there. */
    showTrip(tripId: string): boolean {
      const trip = archive.trips.find((t) => t.id === tripId);
      const tour = trip ? tripTour(trip, archive) : null;
      const first = tour?.list[0];
      const last = tour?.list[tour.list.length - 1];
      if (!trip || !tour || first === undefined || last === undefined) return false;
      toMap();
      set({ range: { lo: timeOf(first), hi: timeOf(last) }, tour });
      const start = endpointPlace(trip.start, archive, home);
      snapTo([start.lon, start.lat]);
      origin = [start.lon, start.lat];
      set({ playing: true });
      flyTo(first);
      return true;
    },

    /** Show on map: one album. Its moment on the timeline, its place in focus, no autoplay. */
    showAlbumOnMap(albumId: string): boolean {
      const index = albums.findIndex((album) => album.id === albumId);
      const album = albums[index];
      if (!album) return false;
      toMap();
      set({ range: { lo: timeOf(index), hi: timeOf(index) } });
      snapTo(at(album.city));
      focusOn(index);
      return true;
    },
  };
};

export type Director = ReturnType<typeof createDirector>;
```

- [ ] **Step 5: Run the tests**

Run: `npx vitest run src/tour/director.test.ts`
Expected: PASS. A failing tour test prints the step it stopped at; fix the director, not the test.

- [ ] **Step 6: Run the whole check and commit**

Run: `npm run check`
Expected: PASS (the engine still compiles: `appStore` kept its old fields).

```bash
git add src/state/app-state.ts src/tour/director.ts src/tour/director.test.ts
git commit -m "feat(tour): add the director that runs flights, tours and the timeline range"
```

---

### Task 6: Engine and painter: flights, routes, places and home from the director

**Files:**
- Modify: `src/render/globe.ts`, `src/engine/engine.ts`, `src/features/globe/GlobeStage.tsx`

**Interfaces:**
- Consumes: `Director`, `placeFacts` (Task 5), `placeState` (`src/render/places.ts`), `createSmoke`, `stepSmoke`, `drawSmoke`, `Smoke` (`src/render/house.ts`), `LonLat` (`src/geo/vector.ts`).
- Produces:
  - Painter gains `route(segments: readonly [LonLat, LonLat][])`, `leg(points: LonLat[], alpha: number, dashOffset: number)`, `plane(x, y, angle, alpha)`; `home(sprite, smoke)` now draws the smoke too.
  - `EngineOptions` gains `director: Director`. `GlobeStage` takes `director` and passes it on.

- [ ] **Step 1: Extend the painter**

In `src/render/globe.ts`:

1. Change the imports to add `drawSmoke`, `Smoke` and `LonLat`:

```ts
import { drawHouse, drawSmoke } from './house';
import type { Smoke } from './house';
```

and add `import type { LonLat, Vec3 } from '@/geo/vector';` in place of `import type { Vec3 } from '@/geo/vector';`.

2. Inside `createPainter`, after `const shape = ...`, add the line path bound to the canvas:

```ts
  const line = geoPath(projection, ctx);
```

3. Replace `home` with:

```ts
  /** Home: a warm glow, the chimney smoke and the small house. */
  const home = ({ x, y, k, pulse, lit }: HomeSprite, smoke: Smoke) => {
    const warm = Math.max(pulse, lit * 0.8, 0.15);
    const gy = y - 4 * k;
    const glow = ctx.createRadialGradient(x, gy, 0, x, gy, 22 * k);
    glow.addColorStop(0, `rgba(255,214,150,${0.5 * warm})`);
    glow.addColorStop(1, 'rgba(255,190,120,0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, gy, 22 * k, 0, 2 * Math.PI);
    ctx.fill();
    drawSmoke(ctx, smoke, x, y, k);
    drawHouse(ctx, x, y, k, lit);
  };

  /** The route so far: faint great circles between the places already reached. */
  const route = (segments: readonly [LonLat, LonLat][]) => {
    if (segments.length === 0) return;
    ctx.beginPath();
    for (const [a, b] of segments) line({ type: 'LineString', coordinates: [a, b] });
    ctx.strokeStyle = 'rgba(255,200,120,.16)';
    ctx.lineWidth = 1;
    ctx.stroke();
  };

  /** The current leg, dashed and moving, drawn up to the plane. */
  const leg = (points: LonLat[], alpha: number, dashOffset: number) => {
    ctx.beginPath();
    line({ type: 'LineString', coordinates: points });
    ctx.strokeStyle = `rgba(255,214,150,${alpha})`;
    ctx.lineWidth = 1.8;
    ctx.setLineDash([6, 6]);
    ctx.lineDashOffset = dashOffset;
    ctx.stroke();
    ctx.setLineDash([]);
  };

  /** The plane: a small white arrow with a warm glow. */
  const plane = (x: number, y: number, angle: number, alpha: number) => {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.shadowColor = 'rgba(255,220,160,.9)';
    ctx.shadowBlur = 12;
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.moveTo(9, 0);
    ctx.lineTo(-6, -5.5);
    ctx.lineTo(-3, 0);
    ctx.lineTo(-6, 5.5);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  };
```

4. Return them: `return { earth, places, home, route, leg, plane };`

- [ ] **Step 2: Wire the director into the engine**

In `src/engine/engine.ts`:

1. Imports — add:

```ts
import { vec } from '@/geo/vector';
import type { LonLat, Vec3 } from '@/geo/vector';
import { createSmoke, stepSmoke } from '@/render/house';
import { PLACE_LOOK, placeState, stepLook } from '@/render/places';
import { placeFacts } from '@/tour/director';
import type { Director } from '@/tour/director';
```

(replacing the existing `vec`/`Vec3` and `PLACE_LOOK, stepLook` imports; remove `import { pulse } from '@/lib/easing'` only if unused — it stays used).

2. `EngineOptions` gets `director: Director;` and `createEngine` destructures it: `const { stars, globe, label, earth, lights, archive, home, director } = options;`.

3. `PlaceRuntime` loses `pulseAt` (the director keeps pulses); delete `pulseAt: -Infinity,` from the places map.

4. After `const homeV = vec(home.lon, home.lat);` add:

```ts
  let homeLit = 0;
  const smoke = createSmoke();
  let wasFocused = false;
```

5. `measure` takes the zoom to use on the ball:

```ts
  const measure = (zoom: number) => {
    cx = mobile ? width / 2 : width * 0.6;
    cy = mobile ? height * 0.58 : height * 0.5;
    const zf = zFlat({ width, height, cx, cy, r0 });
    unroll = stepUnroll(unroll, t, zTarget, zf, worldNow);
    t = unrollT(unroll, worldNow);
    r = r0 * (unroll.flat ? Math.max(z, zf) : zoom);
    lim = 90 - t * (90 - flatLatLimit(cy, height, r));
  };
```

6. Replace `draw` with:

```ts
  const draw = (f: number, dt: number) => {
    const view = director.view();
    g.clearRect(0, 0, width, height);
    painter.earth({ width, height, cx, cy, r, t, centre }, earth, lights);

    const base = placeBase(r);
    const sprites: PlaceSprite[] = [];
    for (const place of places) {
      const state = placeState(placeFacts(view, place.city.key));
      place.look = stepLook(place.look, state, f, place === hovered);
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
        pulse: pulse(view.now - (view.pulseAt.get(place.city.key) ?? -Infinity), PULSE_MS),
        photos: place.photos,
      };
      place.x = sprite.x;
      place.y = sprite.y;
      place.r = Math.max(HIT_MIN, placeRadius(sprite, base));
      sprites.push(sprite);
    }
    painter.places(sprites, base);

    // home: lit while someone is there, one pulse on coming home
    homeLit = ease(homeLit, view.homeLit, f, 0.95);
    stepSmoke(smoke, dt, homeLit);
    if (faces(homeV, centre, t, 0.02)) {
      const point = projection([home.lon, home.lat]);
      if (point) {
        const homePulse = pulse(view.now - view.homePulseAt, PULSE_MS);
        const k = clamp(r / 300, 1, 2.2) * 0.5 * (1 + 0.35 * homePulse);
        painter.home({ x: point[0], y: point[1], k, pulse: homePulse, lit: homeLit }, smoke);
      }
    }

    painter.route(view.route);
    if (view.leg) {
      const { path, upto, alpha } = view.leg;
      const points: LonLat[] = [];
      for (let k = 0; k <= upto + 1e-4; k += 0.005) points.push(path(Math.min(k, upto)));
      if (points.length < 2) points.push(path(upto));
      painter.leg(points, alpha, -view.now / 60);
    }
    if (view.plane && faces(vec(view.plane.at[0], view.plane.at[1]), centre, t, 0)) {
      const p = projection(view.plane.at);
      const q0 = projection(view.plane.behind);
      const q1 = projection(view.plane.ahead);
      if (p && q0 && q1) {
        painter.plane(p[0], p[1], Math.atan2(q1[1] - q0[1], q1[0] - q0[0]), view.plane.alpha);
      }
    }

    updateHover();
  };
```

7. Replace the body of `frame` up to `project();` with:

```ts
  const frame = (time: number) => {
    const { dt, f } = frameStep(time, lastFrame, appStore.get().paused);
    lastFrame = time;
    worldNow += dt;

    z = ease(z, zTarget, f, 0.9);
    const drive = director.step(dt, rot, z);
    if (drive.rot) {
      rot = drive.rot;
      vx = vy = 0;
    }
    if (drive.steering) spin = 0;
    // a place in focus stops the spin; letting go of it starts it again
    const focused = director.focused;
    if (focused !== wasFocused) {
      spinning = !focused;
      wasFocused = focused;
    }
    measure(unroll.flat ? z : drive.zoom);
    if (!dragging && !drive.steering) {
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
```

and further down in `frame` change `draw(f);` to `draw(f, dt);`.

8. `release` gets the pointer position and handles a tap; a real drag lets go of the camera:

```ts
  const release = (dragged: boolean, x: number, y: number) => {
    dragging = false;
    updateCursor();
    if (!dragged) {
      // a tap on a light picks it
      const place = placeAt(x, y);
      if (place) director.pickCity(place.city.key);
      return;
    }
    [vx, vy] = throwVelocity(samples, performance.now());
    spinDir = spinDirection(vx, vy, rot[2], spinDir);
    // a throw sets the Earth spinning; without one it spins again only if nothing is in focus
    spinning = !director.focused || Math.hypot(vx, vy) > 0.12;
  };
```

In `onPointerMove`, a release that comes from a mouse moving with no button held (after a context menu) is never a tap. Replace the `release` branch with:

```ts
    if (next.kind === 'release') {
      if (next.dragged) release(true, event.clientX, event.clientY);
      else {
        dragging = false;
        updateCursor();
      }
      return;
    }
```

and inside the drag branch, after `spinning = false;` in `if (next.started)`, add `director.letGo();`.

In `onPointerUp`: `if (done) release(done.dragged, event.clientX, event.clientY);`

- [ ] **Step 3: Pass the director through `GlobeStage`**

`src/features/globe/GlobeStage.tsx`: the props become `{ world, director }: { world: World; director: Director }` (import `type { Director } from '@/tour/director'`), `createEngine({ ..., ...world, director })`, and the effect depends on `[world, director]`.

- [ ] **Step 4: Run the check**

Run: `npm run check`
Expected: typecheck fails only in `src/app/App.tsx` (GlobeStage now needs `director`). That is fixed in Task 7; do not commit yet.

---

### Task 7: The stage: director, keys, credits

**Files:**
- Create: `src/app/director-context.ts`, `src/app/Stage.tsx`, `src/features/keys/useKeys.ts`
- Modify: `src/app/App.tsx`, `src/app/boot.ts`, `src/app/boot.test.ts`

**Interfaces:**
- Consumes: `createDirector`, `Director` (Task 5), `settingsStore` (Task 1), `appStore`.
- Produces: `DirectorContext`, `useDirector(): Director`, `useKeys(director: Director): void`, `Stage({ world })`, `World.credits: ReadonlyMap<string, Credit>`.

- [ ] **Step 1: Write the failing test**

In `src/app/boot.test.ts`, in "loads the map and the demo traveller", add after the lights line:

```ts
    expect(world.credits.get('w-paris-0.jpg')?.city).toBe('Paris');
```

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/app/boot.test.ts`
Expected: FAIL — `world.credits` is undefined.

- [ ] **Step 3: Implement**

`src/app/boot.ts`: `World` gains `credits: ReadonlyMap<string, Credit>;` and `loadWorld` returns `credits: new Map(credits.map((credit) => [credit.file, credit])),`.

`src/app/director-context.ts`:

```ts
import { createContext, useContext } from 'react';
import type { Director } from '@/tour/director';

export const DirectorContext = createContext<Director | null>(null);

export const useDirector = (): Director => {
  const director = useContext(DirectorContext);
  if (!director) throw new Error('useDirector needs a DirectorContext');
  return director;
};
```

`src/features/keys/useKeys.ts`:

```ts
import { useEffect } from 'react';
import type { Director } from '@/tour/director';

/** Esc lets go (place, then range), ← → move between albums, ↑ ↓ scroll them, Space plays. */
export const useKeys = (director: Director): void => {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest('input, textarea, select')) return;
      switch (event.key) {
        case 'Escape':
          director.escape();
          break;
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
  }, [director]);
};
```

`src/app/Stage.tsx` (the panel and the timeline join in Tasks 8 and 9):

```tsx
import { useState } from 'react';
import { GlobeStage } from '@/features/globe/GlobeStage';
import { useKeys } from '@/features/keys/useKeys';
import { appStore } from '@/state/app-state';
import { settingsStore } from '@/state/settings';
import { createDirector } from '@/tour/director';
import type { World } from './boot';
import { DirectorContext } from './director-context';

/** The main screen once the world is loaded: one director for the globe, the panel, the timeline. */
export function Stage({ world }: { world: World }) {
  const [director] = useState(() =>
    createDirector({
      archive: world.archive,
      home: world.home,
      store: appStore,
      pace: () => {
        const { photoSeconds, flightSeconds } = settingsStore.get();
        return { photoMs: photoSeconds * 1000, flightMs: flightSeconds * 1000 };
      },
    }),
  );
  useKeys(director);

  return (
    <DirectorContext value={director}>
      <GlobeStage world={world} director={director} />
    </DirectorContext>
  );
}
```

`src/app/App.tsx`: replace `import { GlobeStage } from '@/features/globe/GlobeStage';` with `import { Stage } from './Stage';` and `<GlobeStage world={boot.world} />` with `<Stage world={boot.world} />`.

- [ ] **Step 4: Run the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 5: Check the flights in the browser**

With `npm run dev`, click a light: the plane fades in at the house (the house lights up and smokes), flies the dashed great circle as the camera follows and rises, fades out, the light turns current and pulses once. Drag during the flight: the camera lets go, the plane lands. Esc: the focus goes, the Earth spins again. Space: plays through the albums.

- [ ] **Step 6: Commit (Tasks 6 and 7 together)**

```bash
git add src/render/globe.ts src/engine/engine.ts src/features src/app
git commit -m "feat: fly between the places, with routes, a lit home and the director on the stage"
```

---

### Task 8: The timeline

**Files:**
- Create: `src/features/timeline/Timeline.tsx`, `src/features/timeline/timeline.scss`
- Modify: `src/app/Stage.tsx` (render it)

**Interfaces:**
- Consumes: `useDirector` (Task 7), `range.ts` (Task 2), `monthYear` (Task 1), `appStore`, `useStore`.
- Produces: `Timeline({ archive })`.

- [ ] **Step 1: Write the component**

`src/features/timeline/Timeline.tsx`:

```tsx
import { useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import { useDirector } from '@/app/director-context';
import type { Archive } from '@/data/archive';
import { monthYear } from '@/lib/dates';
import { appStore } from '@/state/app-state';
import { useStore } from '@/state/store';
import {
  albumTime,
  isReached,
  nearestIndex,
  rangeLabel,
  span,
  stamp,
  timeAt,
  within,
} from '@/timeline/range';
import './timeline.scss';

const NOTE_MS = 1800;
/** A press moves this far before it counts as a drag. */
const PICK_DRAG_PX = 4;

/** ▶ plays; press and drag picks a range; a click picks up to a point; a year picks the year. */
export function Timeline({ archive }: { archive: Archive }) {
  const director = useDirector();
  const range = useStore(appStore, (s) => s.range);
  const picking = useStore(appStore, (s) => s.picking);
  const focus = useStore(appStore, (s) => s.focus);
  const flying = useStore(appStore, (s) => s.flying);
  const endCard = useStore(appStore, (s) => s.endCard);
  const progress = useStore(appStore, (s) => s.progress);
  const playing = useStore(appStore, (s) => s.playing);

  const times = useMemo(() => archive.albums.map(albumTime), [archive]);
  const bounds = useMemo(() => span(times), [times]);
  const [y0, y1] = bounds;
  const years = useMemo(() => Array.from({ length: y1 - y0 }, (_, i) => y0 + i), [y0, y1]);
  const pos = (t: number) => ((t - y0) / (y1 - y0)) * 100;

  const track = useRef<HTMLDivElement>(null);
  const pick = useRef<{ x: number; moved: boolean } | null>(null);
  const noteTimer = useRef(0);
  const [note, setNote] = useState<string | null>(null);
  const [tip, setTip] = useState<{ left: number; text: string } | null>(null);

  const flash = (text: string) => {
    setNote(text);
    clearTimeout(noteTimer.current);
    noteTimer.current = window.setTimeout(() => setNote(null), NOTE_MS);
  };

  const timeFor = (clientX: number): number => {
    const rect = track.current?.getBoundingClientRect();
    return rect ? timeAt(clientX - rect.left, rect.width, times, bounds) : y0;
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    pick.current = { x: event.clientX, moved: false };
    director.beginPick(timeFor(event.clientX));
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const rect = track.current?.getBoundingClientRect();
    if (rect) {
      const t = y0 + ((event.clientX - rect.left) / rect.width) * (y1 - y0);
      const index = nearestIndex(t, times);
      const album = archive.albums[index];
      if (album) setTip({ left: pos(times[index] ?? y0), text: `${album.city.name} · ${monthYear(album)}` });
    }
    const current = pick.current;
    if (!current) return;
    if (Math.abs(event.clientX - current.x) > PICK_DRAG_PX) current.moved = true;
    director.movePick(timeFor(event.clientX));
  };

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const current = pick.current;
    if (!current) return;
    pick.current = null;
    if (director.endPick(timeFor(event.clientX), current.moved) === 'empty') {
      flash('No albums in that stretch');
    }
  };

  const onPointerCancel = () => {
    pick.current = null;
    director.cancelPick();
  };

  const onYear = (year: number) => {
    // 'open' asks for the year in the archive: plan 4
    if (director.clickYear(year) === 'empty') flash('No albums that year');
  };

  const live = picking ?? range;
  const progressState = { on: progress, focus, ahead: flying && endCard === null, range };
  const focusTime = focus >= 0 ? times[focus] : undefined;
  const from = range ? pos(range.lo) : 0;
  const done = progress && focusTime !== undefined ? Math.max(0, pos(focusTime) - from) : 0;
  const count = range ? times.filter((t) => within(t, range)).length : 0;
  const focusYear = archive.albums[focus]?.year;

  let chip: ReactNode = null;
  if (range) {
    chip = (
      <>
        <b>{rangeLabel(range)}</b> {count} album{count === 1 ? '' : 's'} <i>✕</i>
      </>
    );
  } else if (picking) {
    chip = (
      <>
        <b>
          {stamp(picking.lo)} – {stamp(picking.hi)}
        </b>{' '}
        <i>release to pick</i>
      </>
    );
  } else if (note) {
    chip = <i>{note}</i>;
  }

  return (
    <div className="timeline">
      <div className="timeline__chips">
        <button
          type="button"
          className={`timeline__chip${chip ? ' is-on' : ''}`}
          onClick={() => director.clearRange()}
          tabIndex={range ? 0 : -1}
          aria-label={range ? `Clear the range ${rangeLabel(range)}` : undefined}
        >
          {chip}
        </button>
      </div>
      <div className="timeline__row">
        <button
          type="button"
          className="timeline__play"
          onClick={() => director.play()}
          aria-label={playing ? 'Pause' : 'Play'}
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <div
          ref={track}
          className="timeline__track"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerCancel}
          onPointerLeave={() => setTip(null)}
        >
          <div
            className={`timeline__band${live ? ' is-on' : ''}${picking ? ' is-pending' : ''}`}
            style={
              live
                ? {
                    left: `calc(${pos(live.lo)}% - 9px)`,
                    width: `calc(${pos(live.hi) - pos(live.lo)}% + 18px)`,
                  }
                : undefined
            }
          />
          <div className="timeline__base" />
          <div className="timeline__done" style={{ left: `${from}%`, width: `${done}%` }} />
          {years.slice(1).map((year) => (
            <div key={`sep-${year}`} className="timeline__sep" style={{ left: `${pos(year)}%` }} />
          ))}
          {times.map((t, k) => {
            const past = isReached(k, t, progressState);
            const inLive = live !== null && within(t, live);
            const classes = [
              'timeline__dot',
              past ? 'is-past' : '',
              !past && inLive ? 'is-ahead' : '',
              live && !inLive && !past ? 'is-out' : '',
            ].join(' ');
            return <div key={k} className={classes} style={{ left: `${pos(t)}%` }} />;
          })}
          {years.map((year) => (
            <button
              key={year}
              type="button"
              className={[
                'timeline__year',
                year === focusYear ? 'is-current' : '',
                range && range.lo < year + 1 && range.hi >= year ? 'is-in' : '',
              ].join(' ')}
              style={{ left: `${pos(year + 0.5)}%` }}
              onPointerDown={(event) => event.stopPropagation()}
              onClick={() => onYear(year)}
            >
              <span className="timeline__full">{year}</span>
              <span className="timeline__short">’{String(year).slice(2)}</span>
            </button>
          ))}
          <div
            className="timeline__knob"
            style={{
              left: `${focusTime === undefined ? 0 : pos(focusTime)}%`,
              opacity: focusTime === undefined ? 0 : 1,
            }}
          />
          {tip && (
            <div className="timeline__tip" style={{ left: `${tip.left}%` }}>
              {tip.text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

`src/features/timeline/timeline.scss` (ported from the prototype, lines 325–345 and 392):

```scss
.timeline {
  position: fixed;
  inset: auto 0 0;
  z-index: 6;
  padding: 0 24px max(18px, var(--safe-bottom));
  background: linear-gradient(transparent, rgb(4 6 13 / 85%) 40%);

  &__chips {
    display: flex;
    justify-content: flex-end;
    align-items: flex-end;
    height: 30px;
    padding-left: 60px;
  }

  &__chip {
    display: inline-flex;
    gap: 10px;
    align-items: center;
    padding: 5px 12px;
    border: 1px solid rgb(143 184 255 / 50%);
    border-radius: 99px;
    background: rgb(12 16 30 / 80%);
    font-size: 12px;
    color: var(--text);
    opacity: 0;
    transform: translateY(6px);
    transition:
      opacity 0.35s,
      transform 0.35s var(--ease);
    pointer-events: none;

    &.is-on {
      opacity: 1;
      transform: none;
      pointer-events: auto;
    }

    b {
      font-weight: 500;
      color: var(--star);
    }

    i {
      font-style: normal;
      color: var(--muted);
    }
  }

  &__row {
    display: flex;
    gap: 14px;
    align-items: center;
  }

  &__play {
    flex: none;
    width: 46px;
    height: 46px;
    border: 1px solid rgb(255 200 107 / 50%);
    border-radius: 50%;
    background: rgb(255 200 107 / 10%);
    font-size: 15px;
    color: var(--lamp);
  }

  &__track {
    position: relative;
    flex: 1;
    height: 62px;
    cursor: crosshair;
    touch-action: none;

    &:hover .timeline__tip {
      opacity: 1;
    }
  }

  &__base {
    position: absolute;
    inset: 29px 0 auto;
    height: 1px;
    background: rgb(127 137 163 / 40%);
  }

  &__done {
    position: absolute;
    top: 29px;
    height: 1px;
    background: var(--lamp);
    transition:
      width 1.2s cubic-bezier(0.3, 0.7, 0.2, 1),
      left 1.2s cubic-bezier(0.3, 0.7, 0.2, 1);
  }

  &__sep {
    position: absolute;
    top: 25px;
    width: 1px;
    height: 9px;
    background: rgb(127 137 163 / 35%);
  }

  &__band {
    position: absolute;
    top: 16px;
    height: 27px;
    border-radius: 6px;
    background: rgb(143 184 255 / 12%);
    box-shadow: inset 0 0 0 1px rgb(143 184 255 / 50%);
    opacity: 0;
    transition:
      opacity 0.35s,
      left 0.35s var(--ease),
      width 0.35s var(--ease);
    pointer-events: none;

    &.is-on {
      opacity: 1;
    }

    &.is-pending {
      background: rgb(143 184 255 / 7%);
      box-shadow: inset 0 0 0 1px rgb(143 184 255 / 32%);
      transition: opacity 0.35s;
    }
  }

  &__dot {
    position: absolute;
    top: 24px;
    width: 11px;
    height: 11px;
    margin-left: -5.5px;
    border: 1px solid var(--muted);
    border-radius: 50%;
    background: var(--sky);
    transition:
      background 0.5s,
      box-shadow 0.5s,
      border-color 0.5s,
      opacity 0.5s;
    pointer-events: none;

    &.is-past {
      border-color: var(--lamp);
      background: var(--lamp);
      box-shadow: 0 0 10px var(--lamp);
    }

    &.is-ahead {
      border-color: var(--star);
      background: var(--star);
      box-shadow: 0 0 10px rgb(143 184 255 / 80%);
    }

    &.is-out {
      opacity: 0.25;
    }
  }

  &__year {
    position: absolute;
    top: 40px;
    padding: 2px 6px;
    border: 0;
    border-radius: 6px;
    background: none;
    font-size: 11px;
    color: var(--muted);
    transform: translateX(-50%);
    transition:
      color 0.5s,
      background 0.3s;

    &:hover {
      color: var(--text);
      background: rgb(127 137 163 / 15%);
    }

    &.is-in {
      color: var(--text);
    }

    &.is-current {
      color: var(--lamp);
    }
  }

  &__short {
    display: none;
  }

  &__knob {
    position: absolute;
    top: 14px;
    width: 2px;
    height: 30px;
    margin-left: -1px;
    background: var(--text);
    transition:
      left 1.2s cubic-bezier(0.3, 0.7, 0.2, 1),
      opacity 0.4s;
    pointer-events: none;
  }

  &__tip {
    position: absolute;
    bottom: 48px;
    padding: 4px 8px;
    border-radius: 6px;
    background: rgb(20 26 44 / 92%);
    font-size: 11px;
    white-space: nowrap;
    color: var(--text);
    opacity: 0;
    transform: translateX(-50%);
    transition: opacity 0.2s;
    pointer-events: none;
  }

  @include mobile {
    padding-inline: 16px;

    &__chips {
      padding-left: 0;
    }

    &__full {
      display: none;
    }

    &__short {
      display: inline;
    }

    &__year {
      padding: 2px;
    }
  }
}
```

`src/app/Stage.tsx`: import `Timeline` from `@/features/timeline/Timeline` and render `<Timeline archive={world.archive} />` after `<GlobeStage ... />`.

- [ ] **Step 2: Run the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 3: Check it in the browser**

Drag along the timeline: the band follows in pale blue, the lights inside turn blue and the rest grey; let go: the chip shows the range and the album count. A click picks from the start. A year picks the year. A stretch with no albums shows "No albums in that stretch". ✕ clears. ▶ plays the range.

- [ ] **Step 4: Commit**

```bash
git add src/features/timeline src/app/Stage.tsx
git commit -m "feat(timeline): add the timeline with ranges, years and play"
```

---

### Task 9: The album panel

**Files:**
- Create: `src/features/panel/stack.ts`, `src/features/panel/useWorldInterval.ts`, `src/features/panel/AlbumPanel.tsx`, `src/features/panel/panel.scss`, `src/features/panel/cozy-room.svg`
- Modify: `src/styles/normalize.scss`, `src/app/Stage.tsx`
- Test: `src/features/panel/stack.test.ts`

**Interfaces:**
- Consumes: Tasks 1, 4, 5, 7; `frameStep` (`src/engine/clock.ts`), `tickInterval` (Task 1).
- Produces: `cardRole(k: number, cur: number, n: number): 'cur' | 'prev' | 'next' | 'far'`, `wheelSteps(acc: number, deltaY: number, deltaMode: number): [number, number]`, `useWorldInterval(callback, ms, active, resetKey)`, `AlbumPanel({ world })`.

- [ ] **Step 1: Write the failing test**

`src/features/panel/stack.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { cardRole, wheelSteps } from './stack';

describe('cardRole', () => {
  it('puts the current album in front with its neighbours around it, in a loop', () => {
    expect([0, 1, 2, 3, 4].map((k) => cardRole(k, 0, 5))).toEqual([
      'cur',
      'next',
      'far',
      'far',
      'prev',
    ]);
    expect([0, 1].map((k) => cardRole(k, 1, 2))).toEqual(['next', 'cur']);
    expect(cardRole(0, 0, 1)).toBe('cur');
  });
});

describe('wheelSteps', () => {
  it('moves one album per notch', () => {
    expect(wheelSteps(0, 100, 0)).toEqual([0, 1]);
    expect(wheelSteps(0, -100, 0)).toEqual([0, -1]);
  });

  it('gathers small trackpad deltas into one step, never a jump', () => {
    let acc = 0;
    let moved = 0;
    for (let i = 0; i < 20; i++) {
      const [next, steps] = wheelSteps(acc, 5, 0);
      acc = next;
      moved += steps;
    }
    expect(moved).toBe(2);
  });

  it('reads line and page deltas as pixels', () => {
    expect(wheelSteps(0, 3, 1)[1]).toBe(1);
    expect(wheelSteps(0, 1, 2)[1]).toBe(4);
  });
});
```

(20 × 5 px = 100 px: a step fires at 50 px, then again at the next 50, so two steps.)

- [ ] **Step 2: Run it to see it fail**

Run: `npx vitest run src/features/panel/stack.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the helpers and the hook**

`src/features/panel/stack.ts`:

```ts
export type CardRole = 'cur' | 'prev' | 'next' | 'far';

/** Albums go by date in a loop: after the last comes the first. */
export const cardRole = (k: number, cur: number, n: number): CardRole => {
  let offset = (((k - cur) % n) + n) % n;
  if (offset > n / 2) offset -= n;
  return offset === 0 ? 'cur' : offset === -1 ? 'prev' : offset === 1 ? 'next' : 'far';
};

/**
 * The wheel over the albums: one album per notch (100 px), a quick double turn moves two.
 * Returns the new accumulated delta and the albums to move.
 */
export const wheelSteps = (acc: number, deltaY: number, deltaMode: number): [number, number] => {
  const pixels = deltaMode === 1 ? deltaY * 33 : deltaMode === 2 ? deltaY * 400 : deltaY;
  const next = acc + pixels;
  if (Math.abs(next) < 50) return [next, 0];
  return [0, Math.sign(next) * Math.max(1, Math.round(Math.abs(next) / 100))];
};
```

`src/features/panel/useWorldInterval.ts`:

```ts
import { useEffect, useRef } from 'react';
import { frameStep } from '@/engine/clock';
import { tickInterval } from '@/lib/interval';
import { appStore } from '@/state/app-state';

/** Calls back every `ms` of world time while `active`; starts over when `resetKey` changes. */
export const useWorldInterval = (
  callback: () => void,
  ms: number,
  active: boolean,
  resetKey: unknown,
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
      const { dt } = frameStep(time, last, appStore.get().paused);
      last = time;
      const [next, fired] = tickInterval(elapsed, dt, ms);
      elapsed = next;
      if (fired) saved.current();
      id = requestAnimationFrame(frame);
    };
    id = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(id);
  }, [ms, active, resetKey]);
};
```

- [ ] **Step 4: Run the tests**

Run: `npx vitest run src/features/panel/stack.test.ts`
Expected: PASS.

- [ ] **Step 5: Extract the cozy room**

Copy the prototype's `COZY` SVG into its own file, unchanged:

```bash
node -e "const s=require('fs').readFileSync('docs/design/prototype/flight.html','utf8');const m=s.match(/const COZY = \`([\s\S]*?)\`;/);if(!m)throw new Error('COZY not found');require('fs').writeFileSync('src/features/panel/cozy-room.svg',m[1]+'\n')"
head -c 120 src/features/panel/cozy-room.svg
```

Expected: the file starts with `<svg viewBox="0 0 360 240"`.

- [ ] **Step 6: Stop normalize from recolouring SVG fills**

In `src/styles/normalize.scss`, delete these two rules (they made every `fill`/`stroke` attribute `currentColor`, which would turn the cozy room and the house one colour; the old app's icons needed them, the new app has none):

```scss
:where([fill]:not([fill='none'], [fill^='url'])) {
  fill: currentColor;
}

:where([stroke]:not([stroke='none'], [stroke^='url'])) {
  stroke: currentColor;
}
```

- [ ] **Step 7: Write the panel**

`src/features/panel/AlbumPanel.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react';
import type { World } from '@/app/boot';
import { useDirector } from '@/app/director-context';
import type { Archive } from '@/data/archive';
import { cityPhotos, creditLine, photoUrl } from '@/data/photos';
import { tripOfAlbum } from '@/data/trips';
import type { Album, Credit } from '@/data/types';
import { monthYear } from '@/lib/dates';
import { appStore } from '@/state/app-state';
import { settingsStore } from '@/state/settings';
import { useStore } from '@/state/store';
import { cityAlbums, scopedAlbums } from '@/tour/tour';
import type { Tour } from '@/tour/tour';
import cozyRoom from './cozy-room.svg?raw';
import { cardRole, wheelSteps } from './stack';
import type { CardRole } from './stack';
import { useWorldInterval } from './useWorldInterval';
import './panel.scss';

/** Each photo dissolves into the next over this time. */
const DISSOLVE_MS = 1400;
/** A vertical swipe this long turns the albums on a phone. */
const SWIPE_PX = 30;

/** The left column: the place in focus, its albums and its caption; hidden with nothing in focus. */
export function AlbumPanel({ world }: { world: World }) {
  const { archive } = world;
  const focus = useStore(appStore, (s) => s.focus);
  const endCard = useStore(appStore, (s) => s.endCard);
  const tour = useStore(appStore, (s) => s.tour);
  const album = archive.albums[focus];
  const scope = tour ?? endCard?.tour ?? null;
  const list = album ? scopedAlbums(cityAlbums(archive, album.city.key), tour) : [];

  return (
    <section className={`panel${album ? '' : ' is-hidden'}`} aria-label="The place in focus">
      <div className="panel__media">
        {album && <PanelHead archive={archive} list={list} focus={focus} scope={scope} />}
        {album && endCard && <EndSlot world={world} />}
        {album && !endCard && <AlbumStack world={world} list={list} focus={focus} />}
      </div>
      {album && <Caption world={world} />}
    </section>
  );
}

/** The years of this place's albums, or in a tour only the trip's name or the year. */
function PanelHead({
  archive,
  list,
  focus,
  scope,
}: {
  archive: Archive;
  list: number[];
  focus: number;
  scope: Tour | null;
}) {
  const director = useDirector();
  if (scope) {
    return (
      <div className="panel__years">
        <span className="is-current">
          {scope.kind === 'year' ? scope.name : `Trip · ${scope.name}`}
        </span>
      </div>
    );
  }
  const current = archive.albums[focus]?.year;
  const years = [
    ...new Set(list.map((i) => archive.albums[i]?.year).filter((y): y is number => y !== undefined)),
  ];
  return (
    <div className="panel__years">
      {years.map((year) => (
        <button
          key={year}
          type="button"
          className={year === current ? 'is-current' : undefined}
          onClick={() => {
            const index = list.find((i) => archive.albums[i]?.year === year);
            if (index !== undefined) director.selectAlbum(index);
          }}
        >
          {year}
        </button>
      ))}
    </div>
  );
}

/** The stack of albums: the current one in front, its photos in turn. */
function AlbumStack({ world, list, focus }: { world: World; list: number[]; focus: number }) {
  const director = useDirector();
  const photoSeconds = useStore(settingsStore, (s) => s.photoSeconds);
  const stack = useRef<HTMLDivElement>(null);
  const swipe = useRef<{ y: number; used: boolean } | null>(null);
  const [hover, setHover] = useState(false);
  const [shown, setShown] = useState<ReadonlyMap<number, number>>(() => new Map());
  const n = list.length;
  const cur = Math.max(0, list.indexOf(focus));
  const current = list[cur];

  const turnBy = (by: number) => {
    if (n < 2) return;
    const index = list[(((cur + by) % n) + n) % n];
    if (index !== undefined) director.selectAlbum(index);
  };

  useWorldInterval(
    () => {
      if (current === undefined) return;
      setShown((map) => new Map(map).set(current, (map.get(current) ?? 0) + 1));
    },
    photoSeconds * 1000 + DISSOLVE_MS,
    !hover && current !== undefined,
    current,
  );

  // the wheel turns the albums; it needs a non-passive listener to keep the page still
  useEffect(() => {
    const element = stack.current;
    if (!element) return;
    let acc = 0;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      if (n < 2) return;
      const [next, steps] = wheelSteps(acc, event.deltaY, event.deltaMode);
      acc = next;
      if (steps === 0) return;
      const index = list[(((cur + steps) % n) + n) % n];
      if (index !== undefined) director.selectAlbum(index);
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, [director, list, cur, n]);

  const drift = (x: string, y: string) => {
    stack.current?.style.setProperty('--px', x);
    stack.current?.style.setProperty('--py', y);
  };

  return (
    <div
      ref={stack}
      className={`stack${n > 1 ? ' is-multi' : ''}`}
      onPointerEnter={(event) => {
        if (event.pointerType === 'mouse') setHover(true);
      }}
      onPointerLeave={() => {
        setHover(false);
        drift('0px', '0px');
      }}
      onPointerDown={(event) => {
        swipe.current = { y: event.clientY, used: false };
      }}
      onPointerMove={(event) => {
        if (event.pointerType === 'mouse') {
          const rect = event.currentTarget.getBoundingClientRect();
          drift(
            `${(0.5 - (event.clientX - rect.left) / rect.width) * 16}px`,
            `${(0.5 - (event.clientY - rect.top) / rect.height) * 12}px`,
          );
          return;
        }
        const start = swipe.current;
        if (!start || start.used) return;
        const distance = event.clientY - start.y;
        if (Math.abs(distance) > SWIPE_PX) {
          start.used = true;
          turnBy(distance < 0 ? 1 : -1);
        }
      }}
      onClickCapture={(event) => {
        if (swipe.current?.used) event.stopPropagation();
        swipe.current = null;
      }}
    >
      {list.map((index, k) => {
        const album = world.archive.albums[index];
        if (!album) return null;
        const role = cardRole(k, cur, n);
        return (
          <AlbumCard
            key={album.id}
            album={album}
            role={role}
            step={shown.get(index) ?? 0}
            position={`${k + 1} / ${n}`}
            credits={world.credits}
            onSelect={role === 'cur' ? undefined : () => director.selectAlbum(index)}
          />
        );
      })}
    </div>
  );
}

function AlbumCard({
  album,
  role,
  step,
  position,
  credits,
  onSelect,
}: {
  album: Album;
  role: CardRole;
  step: number;
  position: string;
  credits: ReadonlyMap<string, Credit>;
  onSelect: (() => void) | undefined;
}) {
  const photos = album.photos;
  const count = photos.length;
  const on = count > 0 ? step % count : -1;
  // the old picture stays under the new one until it is covered
  const under = count > 1 && step > 0 ? (step - 1) % count : -1;
  const photo = photos[on];
  return (
    <div className={`card card--${role}`} onClick={onSelect}>
      <div className="card__pan">
        {photos.map((ref, i) => (
          <img
            key={i}
            src={photoUrl(ref) ?? undefined}
            alt=""
            draggable={false}
            className={i === on ? 'is-on' : i === under ? 'is-under' : undefined}
          />
        ))}
      </div>
      <div className="card__title">
        {album.title}
        <small>
          {monthYear(album)} · {album.photoCount} photos
        </small>
      </div>
      <div className="card__name">
        {monthYear(album)} · {album.title}
      </div>
      <div className="card__count">{position}</div>
      <div className="card__credit">{photo ? creditLine(photo, album.city, credits) : ''}</div>
    </div>
  );
}

/** A trip's end: the cozy room at home, or a photo of the city it ended in. */
function EndSlot({ world }: { world: World }) {
  const endCard = useStore(appStore, (s) => s.endCard);
  const city = endCard?.cityKey ? world.archive.cityByKey.get(endCard.cityKey) : undefined;
  const photo = city ? cityPhotos(city)[0] : undefined;
  const url = photo ? photoUrl(photo) : null;
  return (
    <div className="stack">
      <div className="card card--cur card--end">
        {url ? (
          <div className="card__pan">
            <img className="is-on" src={url} alt="" />
          </div>
        ) : (
          <div className="cozy" dangerouslySetInnerHTML={{ __html: cozyRoom }} />
        )}
      </div>
    </div>
  );
}

function Caption({ world }: { world: World }) {
  const { archive, home } = world;
  const focus = useStore(appStore, (s) => s.focus);
  const endCard = useStore(appStore, (s) => s.endCard);
  const flightKm = useStore(appStore, (s) => s.flightKm);
  const album = archive.albums[focus];
  if (!album) return null;
  const status = flightKm === null ? '' : `in flight · ${Math.round(flightKm).toLocaleString('en')} km`;

  if (endCard) {
    const city = endCard.cityKey ? archive.cityByKey.get(endCard.cityKey) : undefined;
    const from = archive.albumById.get(endCard.fromAlbumId) ?? album;
    const trip = endCard.tour?.kind === 'trip' ? endCard.tour.name : null;
    return (
      <div className="caption" key={`end-${endCard.fromAlbumId}`}>
        <div className="caption__when">{endCard.home ? 'Back home' : 'The end of the road'}</div>
        <div className="caption__place">{city ? city.name : home.name}</div>
        <div className="caption__route">
          {city ? city.country.name : home.country} · from {from.city.name} · {from.title}
        </div>
        <div className="caption__trip">{trip ? `Trip · ${trip}` : ''}</div>
        <div className="caption__status">{status}</div>
      </div>
    );
  }

  const trip = tripOfAlbum(archive, album.id);
  return (
    <div className="caption" key={album.id}>
      <div className="caption__when">
        {monthYear(album)} · album {focus + 1} of {archive.albums.length}
      </div>
      <div className="caption__place">{album.city.name}</div>
      <div className="caption__route">
        <span>{album.city.country.name}</span> · {album.title} · {album.photoCount} photos
      </div>
      <div className="caption__trip">{trip ? `Trip · ${trip.name}` : ''}</div>
      <div className="caption__status">{status}</div>
    </div>
  );
}
```

`src/features/panel/panel.scss` (ported from the prototype, lines 114–166 and 249–259, mobile from 347–392):

```scss
.panel {
  position: fixed;
  top: 100px;
  left: 24px;
  z-index: 5;
  width: min(360px, 30vw);
  pointer-events: none;
  transition:
    opacity 0.7s ease,
    transform 0.7s ease;

  &.is-hidden {
    opacity: 0;
    transform: translateX(-18px);
  }

  &__years {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin-bottom: 46px;
    pointer-events: auto;

    button,
    span {
      padding: 2px 0;
      border: 0;
      border-bottom: 1px solid transparent;
      background: none;
      font-size: 12px;
      letter-spacing: 0.2em;
      color: var(--muted);
      transition:
        color 0.5s,
        border-color 0.5s;
    }

    button:hover {
      color: var(--text);
    }

    .is-current {
      border-color: var(--lamp);
      color: var(--lamp);
    }
  }

  @include mobile {
    top: 80px;
    right: 16px;
    left: 16px;
    display: flex;
    gap: 14px;
    align-items: flex-end;
    width: auto;

    &__media {
      flex: 0 0 44%;
    }

    &__years {
      gap: 2px 10px;
      margin-bottom: 20px;

      button,
      span {
        font-size: 11px;
        letter-spacing: 0.1em;
      }
    }
  }
}

// the albums: the current one in front; the previous and next peek out above and below on hover
.stack {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 2;
  pointer-events: auto;
}

.card {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: 14px;
  background: #0b1020;
  box-shadow:
    0 24px 50px rgb(0 0 0 / 50%),
    0 0 0 1px rgb(255 255 255 / 6%);
  cursor: pointer;
  transition:
    transform 0.7s var(--ease),
    opacity 0.6s ease,
    filter 0.6s ease,
    box-shadow 0.6s ease;

  &--cur {
    z-index: 3;
  }

  &--prev,
  &--next {
    z-index: 2;
    opacity: 0;
    filter: brightness(0.6) saturate(0.85);
    transform: scale(0.9);
    box-shadow:
      0 14px 30px rgb(0 0 0 / 50%),
      0 0 0 1px rgb(255 200 107 / 30%);
  }

  &--far {
    z-index: 1;
    opacity: 0;
    transform: scale(0.84);
    pointer-events: none;
  }

  &--end {
    cursor: default;
  }

  &::before {
    content: '';
    position: absolute;
    inset: 0 0 auto;
    z-index: 1;
    height: 38%;
    background: linear-gradient(rgb(4 6 13 / 70%), transparent);
    opacity: 0;
    transition: opacity 0.45s;
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(transparent 60%, rgb(4 6 13 / 60%));
    pointer-events: none;
  }

  // the pictures drift a little after the cursor
  &__pan {
    position: absolute;
    inset: -16px;
    transform: translate(var(--px, 0px), var(--py, 0px));
    transition: transform 0.9s var(--ease);

    img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      max-width: none;
      object-fit: cover;
      opacity: 0;
      transform: scale(1.02);
      transition:
        opacity 1.4s ease,
        transform 7s linear;

      &.is-under {
        z-index: 0;
        opacity: 1;
        transform: scale(1.08);
        transition: none;
      }

      &.is-on {
        z-index: 1;
        opacity: 1;
        transform: scale(1.08);
      }
    }
  }

  &__title {
    position: absolute;
    top: 11px;
    right: 14px;
    left: 14px;
    z-index: 2;
    font-family: var(--font-family-display);
    font-style: italic;
    font-weight: 500;
    font-size: 19px;
    line-height: 1.15;
    opacity: 0;
    transform: translateY(-6px);
    transition:
      opacity 0.45s ease,
      transform 0.45s var(--ease);
    pointer-events: none;

    small {
      display: block;
      margin-top: 3px;
      font-family: var(--font-family-base);
      font-style: normal;
      font-weight: 400;
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--lamp);
    }
  }

  // the edge of a neighbouring album carries its name
  &__name {
    position: absolute;
    right: 14px;
    left: 14px;
    z-index: 2;
    overflow: hidden;
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: var(--text);
    text-shadow: 0 1px 6px rgb(0 0 0 / 90%);
    opacity: 0;
    transition: opacity 0.4s;
    pointer-events: none;
  }

  &--prev &__name {
    top: 9px;
    opacity: 1;
  }

  &--next &__name {
    bottom: 9px;
    opacity: 1;
  }

  &__credit {
    position: absolute;
    right: 12px;
    bottom: 10px;
    left: 12px;
    z-index: 2;
    overflow: hidden;
    font-size: 10px;
    white-space: nowrap;
    text-overflow: ellipsis;
    color: rgb(232 236 246 / 70%);
  }

  &--next &__credit {
    opacity: 0;
  }

  &__count {
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 2;
    font-size: 10px;
    letter-spacing: 0.14em;
    color: rgb(232 236 246 / 75%);
    opacity: 0;
    transition: opacity 0.45s;
  }
}

.stack:hover {
  .card--cur {
    transform: scale(1.012);
    box-shadow:
      0 30px 60px rgb(0 0 0 / 60%),
      0 0 0 1px rgb(255 200 107 / 35%);
  }

  .card--prev {
    opacity: 1;
    transform: translateY(calc(-5% - 34px)) scale(0.9);
  }

  .card--next {
    opacity: 1;
    transform: translateY(calc(5% + 34px)) scale(0.9);
  }

  .card--prev:hover,
  .card--next:hover {
    filter: brightness(0.85);
  }

  .card--cur::before,
  .card--cur .card__title {
    opacity: 1;
    transform: none;
  }
}

.stack.is-multi:not(:hover) .card--cur .card__count {
  opacity: 1;
}

// coming home: the same quiet room for every trip
.cozy {
  width: 100%;
  height: 100%;

  svg {
    display: block;
    width: 100%;
    height: 100%;
  }

  .cz-f {
    transform-box: fill-box;
    transform-origin: 50% 100%;
    animation: cozy-flame 1.1s ease-in-out infinite alternate;
  }

  .cz-f2 {
    animation-duration: 0.8s;
    animation-delay: -0.3s;
  }

  .cz-s {
    opacity: 0;
    animation: cozy-steam 3.2s ease-in-out infinite;
  }

  .cz-s2 {
    animation-delay: 1.6s;
  }

  .cz-g {
    animation: cozy-glow 2.4s ease-in-out infinite alternate;
  }
}

@keyframes cozy-flame {
  0% {
    transform: scale(1, 1) skewX(0);
  }

  50% {
    transform: scale(0.96, 1.08) skewX(-4deg);
  }

  100% {
    transform: scale(1.03, 0.94) skewX(3deg);
  }
}

@keyframes cozy-steam {
  0% {
    opacity: 0;
    transform: translateY(5px);
  }

  35% {
    opacity: 0.75;
  }

  100% {
    opacity: 0;
    transform: translateY(-9px);
  }
}

@keyframes cozy-glow {
  from {
    opacity: 0.8;
  }

  to {
    opacity: 1;
  }
}

.caption {
  margin-top: 52px;
  animation: caption-in 0.6s ease both;

  &__when {
    font-size: 12px;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--lamp);
  }

  &__place {
    display: inline-block;
    margin-top: 8px;
    font-family: var(--font-family-display);
    font-style: italic;
    font-weight: 300;
    font-size: clamp(40px, 5vw, 76px);
    line-height: 0.95;
    letter-spacing: -0.02em;
  }

  &__route {
    margin-top: 12px;
    font-size: 13px;
    color: var(--muted);

    span {
      font-weight: 500;
      color: var(--text);
    }
  }

  &__trip {
    min-height: 18px;
    margin-top: 8px;
    font-size: 13px;
    color: var(--lamp);
  }

  &__status {
    min-height: 16px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--muted);
  }

  @include mobile {
    min-width: 0;
    margin-top: 0;

    &__when {
      letter-spacing: 0.14em;
    }

    &__place {
      font-size: 34px;
    }

    &__route,
    &__status {
      display: none;
    }
  }
}

@keyframes caption-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}
```

`src/app/Stage.tsx`: import `AlbumPanel` from `@/features/panel/AlbumPanel` and render `<AlbumPanel world={world} />` between `<GlobeStage ... />` and `<Timeline ... />`.

- [ ] **Step 8: Run the check**

Run: `npm run check`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/features/panel src/styles/normalize.scss src/app/Stage.tsx
git commit -m "feat(panel): add the album panel with cycling photos, the caption and the way home"
```

---

### Task 10: Check the journey in the browser

**Files:** none new unless a check fails.

- [ ] **Step 1: Run the whole check and the build**

Run: `npm run check && npm run build`
Expected: PASS.

- [ ] **Step 2: Walk through it with `npm run dev`**

Write down what you saw for each:

1. Click Paris: the house near Kyiv lights up and smokes, the plane fades in, flies the dashed route as the camera follows and rises mid-way, fades out; Paris turns current and pulses once. The panel slides in with Paris's years, the album card and its caption; the status line shows "in flight · 2,0xx km" during the flight.
2. The cover changes every 5 s with a 1.4 s dissolve; hovering the cards stops it, shows the previous and next cards with their names and the title on the cover; the picture drifts with the cursor.
3. The wheel over the cards moves one album per notch; ↑ ↓ do the same; a click on a peeking card selects it.
4. The timeline: a year picks the year (blue band, blue lights inside, grey outside, chip with the count); a drag picks a stretch; a click picks from the start; an empty stretch shows the note; ✕ and Esc clear it. After a new pick the yellow is gone until the next flight.
5. ▶ plays the range: flights, dwell, the next album; ❚❚ stops. ← → move through the range.
6. In the console: `__globe` still works; with the dev tools run `document.querySelector('.panel')` — present. Esc with a place in focus lets go of it and the Earth spins again.
7. At 390 × 844 the panel sits on top in two columns, the timeline shows short years, nothing overlaps the globe's centre.

Trip and year tours start from the archive's "Show on map" (plan 4); the director tests cover them. Here, pick the year 2023 on the timeline and press ▶: it goes through 2023 in order.

- [ ] **Step 3: Commit any fixes** with their own `fix(...)` messages. If there were none, nothing to commit.
